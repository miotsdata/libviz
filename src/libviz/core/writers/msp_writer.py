"""Export a library as MSP (NIST/MS-DIAL style), streaming in batches."""
from collections.abc import Callable
from pathlib import Path

import numpy as np

from libviz.core.readers.msp_reader import RT_KEYS

BATCH = 2000
# Written from the spectrum/compound columns; same-named metadata is skipped.
_RESERVED = {"NAME", "PRECURSORMZ", "PRECURSORTYPE", "FORMULA", "INCHIKEY", "SMILES", "PUBCHEM",
             "EXACTMASS", "IONMODE", "COLLISIONENERGY", "NUM PEAKS", "COMMENT_LIBVIZ"}


def _clean(value) -> str:
    return " ".join(str(value).split())  # one line, no tabs


def _entry(row, metadata: list[tuple[str, str]]) -> str:
    (name, formula, inchikey, smiles, pubchem, exact_mass, precursor_mz, adduct, polarity, ce, rt,
     mz_blob, int_blob) = row
    mz = np.frombuffer(mz_blob, dtype="<f4")
    intensity = np.frombuffer(int_blob, dtype="<f4")
    lines = [f"NAME: {_clean(name or inchikey)}", f"PRECURSORMZ: {precursor_mz:.5f}"]
    if adduct:
        lines.append(f"PRECURSORTYPE: {adduct}")
    if formula:
        lines.append(f"FORMULA: {formula}")
    if inchikey:
        lines.append(f"INCHIKEY: {inchikey}")
    if smiles:
        lines.append(f"SMILES: {smiles}")
    if pubchem:
        lines.append(f"PUBCHEM: {pubchem}")
    if exact_mass is not None:
        lines.append(f"EXACTMASS: {exact_mass:.5f}")
    if polarity:
        lines.append(f"IONMODE: {polarity.capitalize()}")
    lines.append(f"COLLISIONENERGY: {ce:g}")
    if rt is not None:
        lines.append(f"RETENTIONTIME: {rt:.4f}")  # minutes
    reserved = _RESERVED | set(RT_KEYS) if rt is not None else _RESERVED
    for key, value in metadata:
        key = _clean(key).replace(":", "_")
        if key.upper() not in reserved and key:
            lines.append(f"{key}: {_clean(value)}")
    lines.append(f"Num Peaks: {len(mz)}")
    lines.extend(f"{m:.5f}\t{i:g}" for m, i in zip(mz.tolist(), intensity.tolist()))
    return "\n".join(lines)


def write_msp(library, path: Path | str, *, compound_ids: list[int] | None = None,
              progress: Callable[[int, int], None] | None = None) -> int:
    """Write every spectrum of ``library`` (or of ``compound_ids``) to
    ``path`` atomically; returns the number of spectra written."""
    path = Path(path)
    where, params = "", ()
    if compound_ids is not None:
        where = f"WHERE s.compound_id IN ({','.join('?' * len(compound_ids))})"
        params = tuple(compound_ids)
    tmp = path.with_name(path.name + ".tmp")
    written = 0
    with library.engine.connect() as conn, open(tmp, "w", encoding="utf-8", newline="\n") as out:
        total = conn.exec_driver_sql(f"SELECT COUNT(*) FROM spectrum s {where}", params).scalar()
        last_id = 0
        while True:
            rows = conn.exec_driver_sql(
                "SELECT s.id, c.name, c.formula, c.inchikey, c.smiles, c.pubchem_id, c.exact_mass,"
                " s.precursor_mz, a.formula, s.polarity, s.collision_energy, s.rt, s.mz_array, s.intensity_array"
                " FROM spectrum s JOIN compound c ON c.id = s.compound_id"
                " LEFT JOIN adduct_type a ON a.id = s.adduct_type_id"
                f" {where + ' AND' if where else 'WHERE'} s.id > ? ORDER BY s.id LIMIT {BATCH}",
                params + (last_id,)).fetchall()
            if not rows:
                break
            ids = [r[0] for r in rows]
            metadata: dict[int, list] = {}
            for sid, key, value in conn.exec_driver_sql(
                    f"SELECT spectrum_id, key, value FROM spectrum_metadata WHERE spectrum_id IN "
                    f"({','.join('?' * len(ids))}) ORDER BY id", tuple(ids)):
                metadata.setdefault(sid, []).append((key, value))
            out.write("\n\n".join(_entry(r[1:], metadata.get(r[0], [])) for r in rows) + "\n\n")
            written += len(rows)
            last_id = ids[-1]
            if progress:
                progress(written, total)
    tmp.replace(path)
    return written
