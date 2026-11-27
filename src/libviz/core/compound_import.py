"""Import compounds (no spectra) from a CSV/TSV or Excel sheet into a library (ADR 10).

``read_table`` → ``guess_mapping`` (the user can change it) → ``check_rows``
(per-row warnings/errors, nothing written) → ``import_compounds``.
"""
import csv
import io
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from libviz.core.builder import INCHIKEY_RE
from libviz.core.utils.mass_utils import calculate_exact_mass, clean_formula

EXCEL_SUFFIXES = (".xlsx", ".xlsm")
MASS_TOLERANCE = 0.01  # Da: a "mass" column further than this from the formula's mass is flagged
FIELDS = {  # field -> label
    "name": "Name",
    "formula": "Formula",
    "mass": "Exact mass",
    "inchikey": "InChIKey",
    "smiles": "SMILES",
    "pubchem_id": "PubChem CID",
}
# Normalised header names (lower case, single spaces, "_" as space), most preferred first.
_ALIASES = {
    "name": ("name", "compound", "compound name", "nome", "nome composto"),
    "formula": ("formula", "molecular formula", "formula molecolare"),
    "mass": ("exact mass", "monoisotopic mass", "mass", "exactmass", "massa esatta", "massa esatta (da)", "massa"),
    "inchikey": ("inchikey", "inchi key"),
    "smiles": ("smiles",),
    "pubchem_id": ("pubchem cid", "pubchem id", "pubchem", "cid"),
}


def _normalise(header: str) -> str:
    return " ".join(header.replace("_", " ").lower().split())


def is_excel(path: Path | str) -> bool:
    return Path(path).suffix.lower() in EXCEL_SUFFIXES


def sheet_names(path: Path | str) -> list[str]:
    """Sheets of an Excel file; ``[]`` for CSV/TSV."""
    if not is_excel(path):
        return []
    with pd.ExcelFile(path) as workbook:
        return [str(name) for name in workbook.sheet_names]


def read_table(path: Path | str, sheet: str | None = None) -> tuple[list[str], list[tuple[int, list[str]]]]:
    """``(header, [(line, cells), ...])``. The header is the first non-empty
    row; ``line`` is the 1-based row number in the file/sheet."""
    path = Path(path)
    if is_excel(path):
        frame = pd.read_excel(path, sheet_name=sheet or 0, header=None, dtype=str).fillna("")
        table = frame.values.tolist()
    else:
        text = path.read_text(encoding="utf-8-sig")
        try:
            dialect = csv.Sniffer().sniff(text.split("\n", 1)[0], delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        table = list(csv.reader(io.StringIO(text), dialect=dialect))
    numbered_rows = [(line, [str(cell).strip() for cell in cells])
                     for line, cells in enumerate(table, start=1) if any(str(cell).strip() for cell in cells)]
    if not numbered_rows:
        raise ValueError(f"{path.name}{f' ({sheet})' if sheet else ''} is empty")
    (_, header), body = numbered_rows[0], numbered_rows[1:]
    width = len(header)
    return header, [(line, (cells + [""] * width)[:width]) for line, cells in body]


def guess_mapping(header: list[str]) -> dict[str, str]:
    """field -> header column ("" when none), from common (also Italian) names."""
    by_normalised = {}
    for column in header:
        by_normalised.setdefault(_normalise(column), column)
    return {field_key: next((by_normalised[alias] for alias in aliases if alias in by_normalised), "")
            for field_key, aliases in _ALIASES.items()}


@dataclass
class CompoundRow:
    line: int
    name: str
    formula: str | None = None
    exact_mass: float | None = None
    inchikey: str = ""
    smiles: str | None = None
    pubchem_id: int | None = None
    warnings: list[str] = field(default_factory=list)
    error: str = ""  # set: the row is not imported

    @property
    def status(self) -> str:
        return "error" if self.error else "warning" if self.warnings else "ok"


def _number(text: str) -> float | None:
    try:
        return float(text.replace(",", "."))
    except ValueError:
        return None


def check_rows(header: list[str], rows: list[tuple[int, list[str]]], mapping: dict[str, str],
               mass_tolerance: float = MASS_TOLERANCE) -> list[CompoundRow]:
    """One :class:`CompoundRow` per table row. Writes nothing.

    - formula: whitespace/zero-width characters removed, ``D`` = deuterium.
    - formula and mass both given: the formula wins; a mass further than
      ``mass_tolerance`` Da is a warning. Mass only: used, with a warning.
      Neither: error.
    - InChIKey missing or invalid: a warning, and the row is still imported
      with the cell's value as its key (``NOKEY:<name>`` when empty).
    - a key seen on an earlier row: error (the first row is kept).
    """
    column_index = {column: index for index, column in reversed(list(enumerate(header)))}
    checked_rows, first_line_by_key = [], {}
    for line, cells in rows:
        def cell(field_key: str) -> str:
            index = column_index.get(mapping.get(field_key, ""))
            return cells[index] if index is not None else ""

        row = CompoundRow(line=line, name=cell("name"))
        checked_rows.append(row)
        if not row.name:
            row.error = "no name"
            continue

        formula_text, mass_text = clean_formula(cell("formula")), cell("mass")
        formula_mass = calculate_exact_mass(formula_text, 6) if formula_text else None
        given_mass = _number(mass_text) if mass_text else None
        if mass_text and given_mass is None:
            row.warnings.append(f"mass {mass_text!r} is not a number")
        if formula_mass is not None:
            row.formula, row.exact_mass = formula_text, formula_mass
            if given_mass is not None and abs(given_mass - formula_mass) > mass_tolerance:
                row.warnings.append(f"mass {given_mass:g} differs from the formula's {formula_mass:.4f} "
                                    f"by {abs(given_mass - formula_mass):.4f} Da (formula used)")
        else:
            no_formula = f"invalid formula {formula_text!r}" if formula_text else "no formula"
            if given_mass is None:
                row.error = f"{no_formula} and no mass"
                continue
            row.exact_mass = given_mass
            row.warnings.append(f"{no_formula}, mass used")

        key_text = cell("inchikey")
        if INCHIKEY_RE.match(key_text.upper()):
            row.inchikey = key_text.upper()
        else:
            row.inchikey = key_text or f"NOKEY:{row.name}"
            row.warnings.append(f"invalid InChIKey {key_text!r}" if key_text else "no InChIKey")
        if row.inchikey in first_line_by_key:
            row.error = f"same key as line {first_line_by_key[row.inchikey]}"
            continue
        first_line_by_key[row.inchikey] = line

        row.smiles = cell("smiles") or None
        pubchem_text = cell("pubchem_id")
        pubchem_number = _number(pubchem_text) if pubchem_text else None
        if pubchem_number is not None and pubchem_number.is_integer() and pubchem_number > 0:
            row.pubchem_id = int(pubchem_number)
        elif pubchem_text:
            row.warnings.append(f"PubChem CID {pubchem_text!r} is not a number")
    return checked_rows


def import_compounds(library, rows: list[CompoundRow]) -> dict[str, int]:
    """Add the rows without errors to ``library`` in one transaction.
    A compound already there (same key) is kept; its missing SMILES and
    PubChem CID are filled in. Returns counts: added, existing, filled."""
    from libviz.core.db.models import Compound

    counts = {"added": 0, "existing": 0, "filled": 0}
    with library.session_scope() as session:
        for row in rows:
            if row.error:
                continue
            compound = session.query(Compound).filter_by(inchikey=row.inchikey).one_or_none()
            if compound is None:
                session.add(Compound(name=row.name, formula=row.formula, inchikey=row.inchikey,
                                     exact_mass=round(row.exact_mass, 4), smiles=row.smiles,
                                     pubchem_id=row.pubchem_id))
                session.flush()  # a later row may look this key up
                counts["added"] += 1
                continue
            counts["existing"] += 1
            if (not compound.smiles and row.smiles) or (not compound.pubchem_id and row.pubchem_id):
                compound.smiles = compound.smiles or row.smiles
                compound.pubchem_id = compound.pubchem_id or row.pubchem_id
                counts["filled"] += 1
    return counts
