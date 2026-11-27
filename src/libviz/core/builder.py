"""Build library spectra from mzML files of known compounds (ADR 4).

1. :func:`parse_targets` reads the target list (CSV/TSV).
2. :func:`find_candidates` streams the mzML files and collects, for every
   (target, adduct, collision energy), the MS2 scans whose precursor matches
   the target's adduct m/z. That works for DDA (selected ion ± ppm), DIA
   (target inside a wide isolation window; flagged ``multiplexed``) and
   spatial/MSI runs (no RT needed).
3. The user (GUI review page) or :func:`BuildResult.auto_choose` picks at
   most one candidate per group: one spectrum per compound/adduct/CE.
4. :func:`commit` writes the chosen spectra into a library.
"""
from __future__ import annotations

import csv
import io
import logging
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from libviz.core.readers.mzml_db import iter_ms2_db, parsed_db
from libviz.core.readers.mzml_reader import Ms2Scan, count_spectra
from libviz.core.utils.mass_utils import adduct_mz, calculate_exact_mass, infer_precursor_delta, neutral_mass

logger = logging.getLogger(__name__)

RANK_BY = ("precursor_intensity", "tic", "n_peaks")
CONFLICT_POLICIES = ("skip", "replace")


# ---------------------------------------------------------------------------
# targets
# ---------------------------------------------------------------------------

@dataclass
class Target:
    name: str
    formula: str
    inchikey: str
    exact_mass: float
    smiles: str | None = None
    pubchem_id: int | None = None
    adducts: tuple[str, ...] = ()  # empty: the build's default adducts
    rt_min: float | None = None  # minutes
    rt_max: float | None = None
    # Hand-entered target ("m/z 195.0877 [M+H]+"): explored without an
    # identity; :func:`identify` sets name/InChIKey before :func:`commit`.
    query: str = ""

    @property
    def identified(self) -> bool:
        return bool(self.inchikey)


class TargetListError(ValueError):
    pass


def manual_target(formula_or_mz: str, adduct: str) -> Target:
    """A target typed by hand: a precursor m/z or a neutral formula, with one adduct."""
    text, adduct = formula_or_mz.strip(), adduct.strip()
    try:
        infer_precursor_delta(adduct)
    except Exception as e:  # pylint: disable=broad-exception-caught
        raise TargetListError(f"unknown adduct {adduct!r}") from e
    try:
        mz = float(text.replace(",", "."))
    except ValueError:
        mz = None
    if mz is not None:
        if mz <= 0:
            raise TargetListError("m/z must be positive")
        query = f"m/z {mz:.4f} {adduct}"
        return Target(name=query, formula="", inchikey="", exact_mass=neutral_mass(mz, adduct),
                      adducts=(adduct,), query=query)
    exact_mass = calculate_exact_mass(text, 6)
    if exact_mass is None:
        raise TargetListError(f"{text!r} is neither an m/z nor a valid formula")
    query = f"{text} {adduct}"
    return Target(name=query, formula=text, inchikey="", exact_mass=exact_mass, adducts=(adduct,), query=query)


def identify(target: Target, name: str, inchikey: str, formula: str = "", smiles: str | None = None):
    """Give a hand-entered target the compound it is added as (new, or an
    existing one of the library: commit matches compounds by InChIKey)."""
    name, inchikey, formula = name.strip(), inchikey.strip(), formula.strip()
    if INCHIKEY_RE.match(inchikey.upper()):
        inchikey = inchikey.upper()
    if not name:
        raise TargetListError("the compound needs a name")
    # Any key is accepted (library compounds may have none, ADR 10); the
    # overview lists invalid ones.
    if not inchikey:
        raise TargetListError("the compound needs an InChIKey (or another unique key)")
    if formula:
        exact_mass = calculate_exact_mass(formula, 6)
        if exact_mass is None:
            raise TargetListError(f"invalid formula {formula!r}")
        target.exact_mass = exact_mass
    target.name, target.inchikey, target.formula = name, inchikey, formula or target.formula
    target.smiles = (smiles or "").strip() or None


_COLUMN_ALIASES = {
    "name": ("name", "compound", "compound_name"),
    "formula": ("formula", "molecular_formula"),
    "inchikey": ("inchikey", "inchi_key"),
    "smiles": ("smiles",),
    "pubchem_id": ("pubchem_id", "pubchem", "pubchem_cid", "cid"),
    "adducts": ("adducts", "adduct", "precursor_type", "precursortype"),
    "rt_min": ("rt_min", "rt_start", "rtmin"),
    "rt_max": ("rt_max", "rt_end", "rtmax"),
    "rt": ("rt",),
}
INCHIKEY_RE = re.compile(r"^[A-Z]{14}-[A-Z]{10}-[A-Z]$")


def _optional_float(value: str, what: str, line: int) -> float | None:
    value = (value or "").strip().replace(",", ".")
    if not value:
        return None
    try:
        return float(value)
    except ValueError as e:
        raise TargetListError(f"line {line}: {what} {value!r} is not a number") from e


def parse_targets(path: Path | str, *, rt_tolerance: float = 0.5) -> list[Target]:
    """Read a target list: CSV/TSV/semicolon-separated, header required.

    Required: ``name``, ``formula``, ``inchikey``. Optional: ``smiles``,
    ``pubchem_id``, ``adducts`` (several separated by ``|`` or spaces, e.g.
    ``[M+H]+|[M+Na]+``), and either ``rt_min``/``rt_max`` or ``rt`` (±
    ``rt_tolerance`` minutes). Every problem found is reported at once.
    """
    text = Path(path).read_text(encoding="utf-8-sig")
    try:
        dialect = csv.Sniffer().sniff(text.split("\n", 1)[0], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    header = {h.strip().lower(): h for h in reader.fieldnames or []}
    columns = {key: next((header[a] for a in aliases if a in header), None)
               for key, aliases in _COLUMN_ALIASES.items()}
    missing = [k for k in ("name", "formula", "inchikey") if columns[k] is None]
    if missing:
        raise TargetListError(f"missing column(s): {', '.join(missing)} "
                              f"(found: {', '.join(reader.fieldnames or []) or 'none'})")

    targets, errors, seen = [], [], {}
    for line, row in enumerate(reader, start=2):
        get = lambda key: (row.get(columns[key]) or "").strip() if columns[key] else ""
        if not any((v or "").strip() for v in row.values() if isinstance(v, str)):
            continue
        try:
            name, formula, inchikey = get("name"), get("formula"), get("inchikey").upper()
            if not name:
                raise TargetListError(f"line {line}: empty name")
            exact_mass = calculate_exact_mass(formula, 6)
            if exact_mass is None:
                raise TargetListError(f"line {line}: invalid formula {formula!r}")
            if not INCHIKEY_RE.match(inchikey):
                raise TargetListError(f"line {line}: invalid InChIKey {inchikey!r}")
            if inchikey in seen:
                raise TargetListError(f"line {line}: InChIKey {inchikey} already on line {seen[inchikey]}")
            adducts = tuple(a for a in re.split(r"[|\s]+", get("adducts")) if a)
            for adduct in adducts:
                try:
                    infer_precursor_delta(adduct)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    raise TargetListError(f"line {line}: unknown adduct {adduct!r}") from e
            rt_min = _optional_float(get("rt_min"), "rt_min", line)
            rt_max = _optional_float(get("rt_max"), "rt_max", line)
            rt = _optional_float(get("rt"), "rt", line)
            if rt is not None and rt_min is None and rt_max is None:
                rt_min, rt_max = rt - rt_tolerance, rt + rt_tolerance
            pubchem = get("pubchem_id")
            targets.append(Target(
                name=name, formula=formula, inchikey=inchikey, exact_mass=exact_mass,
                smiles=get("smiles") or None,
                pubchem_id=int(pubchem) if pubchem.isdigit() else None,
                adducts=adducts, rt_min=rt_min, rt_max=rt_max,
            ))
            seen[inchikey] = line
        except TargetListError as e:
            errors.append(str(e))
    if errors:
        shown = "\n".join(errors[:20]) + (f"\n… and {len(errors) - 20} more" if len(errors) > 20 else "")
        raise TargetListError(f"{len(errors)} problem(s) in the target list:\n{shown}")
    if not targets:
        raise TargetListError("the target list has no rows")
    return targets


# ---------------------------------------------------------------------------
# candidates
# ---------------------------------------------------------------------------

@dataclass
class BuildParams:
    ppm: float = 10.0
    positive_adducts: tuple[str, ...] = ("[M+H]+",)
    negative_adducts: tuple[str, ...] = ("[M-H]-",)
    # Isolation windows wider than this (m/z) are treated as DIA: a target
    # matches when its m/z falls inside the window, and the spectrum is
    # flagged multiplexed (it may hold other compounds' fragments).
    dia_min_width: float = 3.0
    min_relative_intensity: float = 0.01  # fraction of the base peak
    remove_precursor: bool = False  # drop peaks at/above precursor m/z - 0.5
    min_peaks: int = 1
    normalize: bool = True  # base peak = 1000
    rank_by: str = "precursor_intensity"
    store_rt: bool = True  # False for runs where RT means nothing (imaging)

    def __post_init__(self):
        if self.rank_by not in RANK_BY:
            raise ValueError(f"rank_by must be one of {RANK_BY}")
        if self.ppm <= 0:
            raise ValueError("ppm must be positive")


@dataclass
class Candidate:
    file: str
    scan_id: str
    rt_min: float | None
    observed_mz: float | None
    ppm_error: float | None  # None for DIA matches
    precursor_intensity: float | None
    tic: float | None
    multiplexed: bool
    isolation: tuple[float, float] | None
    mz: np.ndarray
    intensity: np.ndarray

    @property
    def n_peaks(self) -> int:
        return len(self.mz)

    def score(self, rank_by: str) -> float:
        value = {"precursor_intensity": self.precursor_intensity, "tic": self.tic,
                 "n_peaks": self.n_peaks}[rank_by]
        if value is None and rank_by == "precursor_intensity":
            value = self.tic
        return value or 0.0


@dataclass
class Group:
    """One (target, adduct, collision energy): at most one spectrum each."""
    target_index: int
    adduct: str
    polarity: str
    target_mz: float
    collision_energy: float | None  # None: no MS2 found for this target/adduct
    candidates: list[Candidate] = field(default_factory=list)
    chosen: int | None = None  # index into candidates; None = not added
    rt_set: bool = False  # True: ``rt`` was set by hand (None = store no RT)
    rt: float | None = None

    @property
    def key(self) -> tuple:
        return (self.target_index, self.adduct, self.collision_energy)

    @property
    def effective_rt(self) -> float | None:
        """RT stored with the spectrum: set by hand, else the chosen scan's."""
        if self.rt_set:
            return self.rt
        return self.candidates[self.chosen].rt_min if self.chosen is not None else None


@dataclass
class BuildResult:
    targets: list[Target]
    groups: list[Group]
    params: BuildParams
    files: list[str]
    n_ms2: int = 0

    def auto_choose(self):
        """Pick the best-ranked candidate of every group (``candidates`` are
        already sorted best first)."""
        for group in self.groups:
            group.chosen = 0 if group.candidates else None

    @property
    def n_chosen(self) -> int:
        return sum(g.chosen is not None for g in self.groups)


def process_peaks(mz: np.ndarray, intensity: np.ndarray, precursor_mz: float | None,
                  params: BuildParams) -> tuple[np.ndarray, np.ndarray]:
    """Clean a raw MS2 spectrum: drop zero/relative-noise peaks and,
    optionally, the precursor region; optionally scale the base peak to 1000."""
    mz, intensity = np.asarray(mz, dtype=float), np.asarray(intensity, dtype=float)
    keep = intensity > 0
    if params.remove_precursor and precursor_mz is not None:
        keep &= mz < precursor_mz - 0.5
    mz, intensity = mz[keep], intensity[keep]
    if len(intensity):
        keep = intensity >= params.min_relative_intensity * intensity.max()
        mz, intensity = mz[keep], intensity[keep]
    if params.normalize and len(intensity):
        intensity = intensity / intensity.max() * 1000.0
    order = np.argsort(mz)
    return mz[order], intensity[order]


def _ion_table(targets: Sequence[Target], params: BuildParams):
    """(target index, adduct, polarity, m/z) for every target ion, sorted by m/z."""
    rows = []
    for i, target in enumerate(targets):
        adducts = target.adducts or (params.positive_adducts + params.negative_adducts)
        for adduct in adducts:
            charge, _, _ = infer_precursor_delta(adduct)
            rows.append((adduct_mz(target.exact_mass, adduct), i, adduct,
                         "POSITIVE" if charge > 0 else "NEGATIVE"))
    rows.sort()
    return np.array([r[0] for r in rows]), rows


def find_candidates(targets: Sequence[Target], mzml_files: Sequence[Path | str],
                    params: BuildParams | None = None,
                    progress: Callable[[int, int], None] | None = None) -> BuildResult:
    """Scan ``mzml_files`` for MS2 spectra of ``targets`` (see module doc).

    ``progress(done, total)`` counts spectra across all files. Candidates
    are kept in memory as float64 arrays.
    """
    # ponytail: candidates live in RAM; spill to a temp SQLite file if target
    # lists x matching scans ever reach millions (ADR 4).
    params = params or BuildParams()
    ion_mz, ions = _ion_table(targets, params)
    groups: dict[tuple, Group] = {}
    n_ms2 = 0
    scan_matches: list[tuple[int, float | None]] = []  # of the scan iter_ms2 yields next

    def matches(scan: Ms2Scan) -> list[tuple[int, float | None]]:
        """Indices into ``ions`` matching this scan, with ppm error (None for DIA)."""
        width = scan.isolation_width
        if width is not None and width >= params.dia_min_width:
            lo, hi = np.searchsorted(ion_mz, [scan.isolation_lower, scan.isolation_upper])
            return [(k, None) for k in range(lo, hi)]
        if scan.precursor_mz is None:
            return []
        tol = scan.precursor_mz * params.ppm / 1e6
        lo, hi = np.searchsorted(ion_mz, [scan.precursor_mz - tol, scan.precursor_mz + tol])
        return [(k, (scan.precursor_mz - ion_mz[k]) / ion_mz[k] * 1e6) for k in range(lo, hi)]

    def keep(scan: Ms2Scan) -> bool:
        nonlocal n_ms2
        n_ms2 += 1
        scan_matches[:] = [
            (k, ppm) for k, ppm in matches(scan)
            if scan.polarity in (None, ions[k][3]) and _in_rt(targets[ions[k][1]], scan.rt_min)
        ]
        return bool(scan_matches)

    totals = [count_spectra(Path(f)) for f in mzml_files] if progress else [0] * len(mzml_files)
    for file_number, path in enumerate(mzml_files):
        base = sum(totals[:file_number])
        file_progress = (lambda done, _total, base=base: progress(base + done, sum(totals))) if progress else None
        db = parsed_db(Path(path), file_progress)  # parsed once, then reused (ADR 8)
        for scan in iter_ms2_db(db, Path(path).name, keep):
            for k, ppm in scan_matches:
                target_mz, target_index, adduct, polarity = ions[k]
                ce = scan.collision_energy if scan.collision_energy is not None else 0.0
                mz, intensity = process_peaks(scan.mz, scan.intensity, target_mz, params)
                if len(mz) < max(params.min_peaks, 1):
                    continue
                width = scan.isolation_width
                group = groups.setdefault((target_index, adduct, ce),
                                          Group(target_index, adduct, polarity, target_mz, ce))
                group.candidates.append(Candidate(
                    file=scan.file, scan_id=scan.scan_id, rt_min=scan.rt_min,
                    observed_mz=scan.precursor_mz, ppm_error=ppm,
                    precursor_intensity=scan.precursor_intensity, tic=scan.tic,
                    multiplexed=width is not None and width >= params.dia_min_width,
                    isolation=(scan.isolation_lower, scan.isolation_upper)
                    if scan.isolation_lower is not None else None,
                    mz=mz, intensity=intensity,
                ))

    for group in groups.values():
        group.candidates.sort(key=lambda c: c.score(params.rank_by), reverse=True)

    # Target ions with no MS2 at all still get a row, so the review shows them.
    found = {(g.target_index, g.adduct) for g in groups.values()}
    for target_mz, target_index, adduct, polarity in ions:
        if (target_index, adduct) not in found:
            groups[(target_index, adduct, None)] = Group(target_index, adduct, polarity, target_mz, None)

    ordered = sorted(groups.values(), key=lambda g: (g.target_index, g.adduct, g.collision_energy is None,
                                                     g.collision_energy or 0.0))
    result = BuildResult(list(targets), ordered, params, [str(Path(f)) for f in mzml_files], n_ms2)
    result.auto_choose()
    return result


def _in_rt(target: Target, rt: float | None) -> bool:
    if rt is None:
        return True
    return ((target.rt_min is None or rt >= target.rt_min)
            and (target.rt_max is None or rt <= target.rt_max))


# ---------------------------------------------------------------------------
# commit
# ---------------------------------------------------------------------------

def _existing_spectrum_ids(session, compound_id, adduct_id, polarity, ce):
    from libviz.core.db.models import Spectrum
    return [sid for (sid,) in session.query(Spectrum.id).filter_by(
        compound_id=compound_id, adduct_type_id=adduct_id, polarity=polarity, collision_energy=ce)]


def conflicts(library, result: BuildResult) -> list[int]:
    """Indices of chosen groups whose (compound, adduct, polarity, CE) the
    library already has a spectrum for."""
    from libviz.core.db.models import AdductType, Compound, Spectrum
    out = []
    with library.session_scope() as session:
        for i, group in enumerate(result.groups):
            if group.chosen is None:
                continue
            hit = (session.query(Spectrum.id)
                   .join(Compound, Compound.id == Spectrum.compound_id)
                   .join(AdductType, AdductType.id == Spectrum.adduct_type_id)
                   .filter(Compound.inchikey == result.targets[group.target_index].inchikey,
                           AdductType.formula == group.adduct, Spectrum.polarity == group.polarity,
                           Spectrum.collision_energy == group.collision_energy)
                   .first())
            if hit is not None:
                out.append(i)
    return out


def commit(library, result: BuildResult, on_conflict: str = "skip") -> dict[str, int]:
    """Write every chosen candidate into ``library`` (one transaction).

    Compounds are matched by InChIKey (created if new; missing SMILES/PubChem
    filled in). ``on_conflict``: ``"skip"`` keeps a spectrum the library
    already has for the same compound/adduct/polarity/CE, ``"replace"``
    deletes it first. Provenance goes into spectrum metadata.
    """
    from libviz.core.db.models import AdductType, Compound, Spectrum, SpectrumMetadata

    if on_conflict not in CONFLICT_POLICIES:
        raise ValueError(f"on_conflict must be one of {CONFLICT_POLICIES}")
    unidentified = {result.targets[g.target_index].query for g in result.groups
                    if g.chosen is not None and not result.targets[g.target_index].identified}
    if unidentified:
        raise ValueError(f"identify these targets first: {', '.join(sorted(unidentified))}")
    counts = {"added": 0, "replaced": 0, "skipped": 0}
    with library.session_scope() as session:
        compounds: dict[str, Compound] = {}
        adducts: dict[str, int] = {}
        for group in result.groups:
            if group.chosen is None:
                continue
            target = result.targets[group.target_index]
            candidate = group.candidates[group.chosen]

            compound = compounds.get(target.inchikey)
            if compound is None:
                compound = session.query(Compound).filter_by(inchikey=target.inchikey).one_or_none()
                if compound is None:
                    compound = Compound(name=target.name, formula=target.formula, inchikey=target.inchikey,
                                        exact_mass=round(target.exact_mass, 4))
                    session.add(compound)
                compound.smiles = compound.smiles or target.smiles
                compound.pubchem_id = compound.pubchem_id or target.pubchem_id
                session.flush()
                compounds[target.inchikey] = compound

            if group.adduct not in adducts:
                adduct = session.query(AdductType).filter_by(formula=group.adduct).one_or_none()
                if adduct is None:
                    charge, delta, multiplier = infer_precursor_delta(group.adduct)
                    adduct = AdductType(formula=group.adduct, charge=charge, delta_mass=delta,
                                        multiplication_factor=multiplier)
                    session.add(adduct)
                    session.flush()
                adducts[group.adduct] = adduct.id
            adduct_id = adducts[group.adduct]

            existing = _existing_spectrum_ids(session, compound.id, adduct_id, group.polarity,
                                              group.collision_energy)
            if existing and on_conflict == "skip":
                counts["skipped"] += 1
                continue
            if existing:
                session.query(SpectrumMetadata).filter(SpectrumMetadata.spectrum_id.in_(existing)).delete()
                session.query(Spectrum).filter(Spectrum.id.in_(existing)).delete()
                counts["replaced"] += 1
            else:
                counts["added"] += 1

            spectrum = Spectrum.from_arrays(
                compound_id=compound.id, precursor_mz=round(group.target_mz, 5), adduct_type_id=adduct_id,
                polarity=group.polarity, collision_energy=group.collision_energy,
                mz=candidate.mz, intensity=candidate.intensity,
                rt=group.effective_rt if result.params.store_rt else None,
            )
            session.add(spectrum)
            session.flush()
            for key, value in _provenance(candidate).items():
                session.add(SpectrumMetadata(spectrum_id=spectrum.id, key=key, value=value))
    return counts


def _provenance(c: Candidate) -> dict[str, str]:
    meta = {"source": "libviz mzML builder", "source_file": c.file, "scan_id": c.scan_id}
    if c.rt_min is not None:
        meta["rt_min"] = f"{c.rt_min:.4f}"
    if c.observed_mz is not None:
        meta["observed_precursor_mz"] = f"{c.observed_mz:.5f}"
    if c.ppm_error is not None:
        meta["precursor_ppm_error"] = f"{c.ppm_error:.2f}"
    if c.precursor_intensity is not None:
        meta["precursor_intensity"] = f"{c.precursor_intensity:.6g}"
    if c.isolation is not None:
        meta["isolation_window"] = f"{c.isolation[0]:.4f}-{c.isolation[1]:.4f}"
    if c.multiplexed:
        meta["multiplexed"] = "true"
    return meta
