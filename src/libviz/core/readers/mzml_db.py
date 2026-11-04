"""Parsed mzML database (ADR 8): every MS1/MS2 scan of an mzML in SQLite,
parsed once and reused by the builder (MS2 matching, EIC).

The schema is MSIAnalyzer's raw database (``ms1_scans``/``ms2_scans``,
``metadata``, ``commands``; RT in seconds; peaks as zlib float32 blobs), so
both tools read each other's files. Additions, ignored by MSIAnalyzer:
``native_id`` on both scan tables (the mzML spectrum id) and the
``metadata`` keys checked by :func:`is_current`.

``scan_id`` is the ``scan=N`` number of the native id (Thermo, msconvert),
or the 1-based spectrum index for ids without one or where it is not unique
(Waters ``function=… scan=N``), so it is always a unique integer.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sqlite3
import zlib
from collections.abc import Callable, Iterator
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import numpy as np

from libviz.core.readers.mzml_reader import Scan, count_spectra, iter_spectra

logger = logging.getLogger(__name__)

FORMAT_VERSION = "1"  # bump when what is stored changes: cached files get re-parsed
DECIMALS = 4
_SCAN_NUMBER = re.compile(r"(?:^|\s)scan=(\d+)(?:\s|$)")


def array_to_blob(arr: np.ndarray, decimal_places: int = DECIMALS) -> bytes:
    """Same encoding as MSIAnalyzer: rounded, float32, zlib level 1."""
    return zlib.compress(np.round(np.asarray(arr), decimal_places).astype(np.float32).tobytes(), level=1)


def blob_to_array(blob: bytes) -> np.ndarray:
    return np.frombuffer(zlib.decompress(blob), dtype=np.float32).astype(np.float64)


SCHEMA = """
CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT, run_id UUID NOT NULL, command_name TEXT NOT NULL,
    datetime TEXT NOT NULL, arguments TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_command_run_id ON commands(run_id);
CREATE TABLE IF NOT EXISTS ms1_scans (
    scan_id INTEGER PRIMARY KEY, rt REAL NOT NULL, n_peaks INTEGER, mz_min REAL, mz_max REAL,
    tic REAL, polarity TEXT, mz_array BLOB NOT NULL, intensity_array BLOB NOT NULL,
    native_id TEXT);
CREATE INDEX IF NOT EXISTS idx_ms1_rt ON ms1_scans(rt);
CREATE INDEX IF NOT EXISTS idx_ms1_mz_min ON ms1_scans(mz_min);
CREATE INDEX IF NOT EXISTS idx_ms1_mz_max ON ms1_scans(mz_max);
CREATE INDEX IF NOT EXISTS idx_ms1_tic ON ms1_scans(tic);
CREATE INDEX IF NOT EXISTS idx_ms1_pol ON ms1_scans(polarity);
CREATE TABLE IF NOT EXISTS ms2_scans (
    scan_id INTEGER PRIMARY KEY, parent_scan_id INTEGER, polarity TEXT, rt REAL NOT NULL,
    filter_string TEXT NOT NULL, precursor_mz REAL, precursor_charge INTEGER, precursor_intensity REAL,
    isolation_window_target REAL, isolation_window_lower REAL, isolation_window_upper REAL,
    collision_energy REAL, n_peaks INTEGER, tic REAL,
    mz_array BLOB NOT NULL, intensity_array BLOB NOT NULL, native_id TEXT,
    CONSTRAINT fk_ms1_scan FOREIGN KEY (parent_scan_id) REFERENCES ms1_scans(scan_id));
CREATE INDEX IF NOT EXISTS idx_ms2_rt ON ms2_scans(rt);
CREATE INDEX IF NOT EXISTS idx_ms2_precursor_mz ON ms2_scans(precursor_mz);
CREATE INDEX IF NOT EXISTS idx_ms2_isolation_tgt ON ms2_scans(isolation_window_target);
CREATE INDEX IF NOT EXISTS idx_ms2_tic ON ms2_scans(tic);
CREATE INDEX IF NOT EXISTS idx_ms2_parent ON ms2_scans(parent_scan_id);
CREATE INDEX IF NOT EXISTS idx_filter_string ON ms2_scans(filter_string);
"""


def _source_stamp(mzml: Path) -> dict[str, str]:
    st = mzml.stat()
    return {"source_size": str(st.st_size), "source_mtime_ns": str(st.st_mtime_ns),
            "libviz_format_version": FORMAT_VERSION}


def parse_to_db(mzml: Path | str, db: Path | str,
                progress: Callable[[int, int], None] | None = None) -> Path:
    """Parse ``mzml`` into a new database at ``db`` (written to a temp file
    next to it, then renamed: an interrupted parse leaves no half database)."""
    try:
        __version__ = version("libviz")
    except PackageNotFoundError:
        __version__ = "unknown"

    mzml, db = Path(mzml), Path(db)
    tmp = db.with_name(db.name + ".part")
    tmp.unlink(missing_ok=True)
    con = sqlite3.connect(tmp)
    try:
        # A throw-away file until renamed: no journal needed (cf. ADR 1).
        con.execute("PRAGMA journal_mode=OFF")
        con.execute("PRAGMA synchronous=OFF")
        con.executescript(SCHEMA)
        ids: dict[str, int] = {}  # native id -> scan_id
        used: set[int] = set()
        n_profile_ms1 = 0
        ms1, ms2 = [], []

        def scan_id(scan: Scan) -> int:
            m = _SCAN_NUMBER.search(scan.scan_id)
            number = int(m.group(1)) if m and "function=" not in scan.scan_id else None
            sid = number if number is not None and number not in used else scan.index + 1
            if sid in used:  # only if numbering schemes mix
                sid = max(used) + 1
            used.add(sid)
            ids[scan.scan_id] = sid
            return sid

        def flush():
            con.executemany("INSERT INTO ms1_scans (scan_id, rt, n_peaks, mz_min, mz_max, tic, polarity,"
                            " mz_array, intensity_array, native_id) VALUES (?,?,?,?,?,?,?,?,?,?)", ms1)
            con.executemany("INSERT INTO ms2_scans (scan_id, parent_scan_id, polarity, rt, filter_string,"
                            " precursor_mz, precursor_charge, precursor_intensity, isolation_window_target,"
                            " isolation_window_lower, isolation_window_upper, collision_energy, n_peaks, tic,"
                            " mz_array, intensity_array, native_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            ms2)
            ms1.clear()
            ms2.clear()

        for scan in iter_spectra(mzml, progress):
            if scan.rt_min is None:
                continue  # MSIAnalyzer's schema requires RT
            if scan.ms_level == 1 and scan.profile:
                n_profile_ms1 += 1
                continue
            rt = scan.rt_min * 60.0
            sid = scan_id(scan)
            mz_range = (float(scan.mz.min()), float(scan.mz.max())) if len(scan.mz) else (None, None)
            blobs = (array_to_blob(scan.mz), array_to_blob(scan.intensity))
            if scan.ms_level == 1:
                ms1.append((sid, rt, len(scan.mz), *mz_range, scan.tic, scan.polarity, *blobs, scan.scan_id))
            else:
                width = scan.isolation_width
                center = (scan.isolation_lower + width / 2) if width is not None else None
                ms2.append((sid, ids.get(scan.parent_id), scan.polarity, rt, scan.filter_string,
                            scan.precursor_mz, scan.precursor_charge, scan.precursor_intensity, center,
                            width / 2 if width is not None else None, width / 2 if width is not None else None,
                            scan.collision_energy, len(scan.mz), scan.tic, *blobs, scan.scan_id))
            if len(ms1) + len(ms2) >= 500:
                flush()
        flush()

        now = datetime.now().astimezone().isoformat()
        meta = {"source_file": mzml.name, "source_path": str(mzml.resolve()), "db_creation_date": now,
                "libviz_version": __version__, "ms1_profile_skipped": str(n_profile_ms1),
                **_source_stamp(mzml)}
        con.executemany("INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)", meta.items())
        con.execute("INSERT INTO commands (run_id, command_name, datetime, arguments) VALUES (?,?,?,?)",
                    ("parse", "parse", now, json.dumps({"source_file": str(mzml), "decimal_places": DECIMALS,
                                                        "libviz_version": __version__})))
        con.commit()
    except BaseException:
        con.close()
        tmp.unlink(missing_ok=True)
        raise
    con.close()
    os.replace(tmp, db)
    if n_profile_ms1:
        logger.warning("%s: %d profile MS1 scans not stored (no EIC); centroid MS1 too for an EIC",
                       mzml.name, n_profile_ms1)
    return db


def is_current(db: Path, mzml: Path) -> bool:
    """Whether ``db`` was parsed by this format version from ``mzml`` as it is now."""
    if not db.is_file():
        return False
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            stored = dict(con.execute("SELECT key, value FROM metadata").fetchall())
        finally:
            con.close()
    except sqlite3.Error:
        return False
    return all(stored.get(k) == v for k, v in _source_stamp(mzml).items())


def _cache_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
    return Path(base) / "libviz" / "parsed"


def db_path_for(mzml: Path | str) -> Path:
    """``run.mzML`` -> ``run.mzML.db`` next to it, or in the user cache
    folder when the mzML's folder is not writable."""
    mzml = Path(mzml).resolve()
    if os.access(mzml.parent, os.W_OK):
        return mzml.with_name(mzml.name + ".db")
    digest = hashlib.sha1(str(mzml).encode()).hexdigest()[:12]
    return _cache_dir() / f"{mzml.name}.{digest}.db"


def parsed_db(mzml: Path | str, progress: Callable[[int, int], None] | None = None) -> Path:
    """The parsed database of ``mzml``, parsing it first if missing or stale."""
    mzml = Path(mzml)
    db = db_path_for(mzml)
    if is_current(db, mzml):
        if progress:
            total = count_spectra(mzml)
            progress(total, total)
        return db
    db.parent.mkdir(parents=True, exist_ok=True)
    logger.info("parsing %s into %s", mzml.name, db)
    return parse_to_db(mzml, db, progress)


_MS2_COLUMNS = ("scan_id, native_id, polarity, rt, precursor_mz, precursor_charge, precursor_intensity,"
                " isolation_window_target, isolation_window_lower, isolation_window_upper,"
                " collision_energy, tic, filter_string")


def iter_ms2_db(db: Path | str, file: str, keep: Callable[[Scan], bool] = lambda scan: True) -> Iterator[Scan]:
    """Like :func:`mzml_reader.iter_ms2`, from a parsed database: ``keep``
    sees each MS2 scan without peaks; peaks are read only for kept ones."""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        rows = con.execute(f"SELECT {_MS2_COLUMNS} FROM ms2_scans ORDER BY rt, scan_id").fetchall()
        for (sid, native, polarity, rt, prec, charge, prec_int, target, lower, upper, ce, tic, filt) in rows:
            center = target if target is not None else prec
            scan = Scan(
                file=file, scan_id=native or f"scan={sid}", index=sid - 1, polarity=polarity,
                rt_min=rt / 60.0, precursor_mz=prec, precursor_intensity=prec_int, precursor_charge=charge,
                isolation_lower=center - lower if center is not None and lower is not None else None,
                isolation_upper=center + upper if center is not None and upper is not None else None,
                collision_energy=ce, tic=tic, filter_string=filt or "",
            )
            if keep(scan):
                mz, intensity = con.execute("SELECT mz_array, intensity_array FROM ms2_scans WHERE scan_id = ?",
                                            (sid,)).fetchone()
                scan.mz, scan.intensity = blob_to_array(mz), blob_to_array(intensity)
                yield scan
    finally:
        con.close()


def profile_ms1_skipped(db: Path | str) -> int:
    """How many profile MS1 scans the parse left out (they give no EIC)."""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        row = con.execute("SELECT value FROM metadata WHERE key = 'ms1_profile_skipped'").fetchone()
    finally:
        con.close()
    return int(row[0]) if row else 0


def eic(db: Path | str, mz: float, ppm: float, polarity: str | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Extracted-ion chromatogram from the MS1 scans: (RT in minutes, summed
    intensity within ``mz`` ± ``ppm``). Scans of the other polarity are left out."""
    tol = mz * ppm / 1e6
    lo, hi = mz - tol, mz + tol
    sql = "SELECT rt, mz_array, intensity_array, mz_min, mz_max FROM ms1_scans"
    args: tuple = ()
    if polarity:
        sql += " WHERE polarity IS NULL OR polarity = ?"
        args = (polarity,)
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        rts, values = [], []
        for rt, mz_blob, int_blob, mz_min, mz_max in con.execute(sql + " ORDER BY rt", args):
            rts.append(rt / 60.0)
            if mz_min is None or mz_max < lo or mz_min > hi:
                values.append(0.0)
                continue
            mzs = blob_to_array(mz_blob)  # centroids are stored in m/z order
            a, b = int(np.searchsorted(mzs, lo, side="left")), int(np.searchsorted(mzs, hi, side="right"))
            values.append(float(blob_to_array(int_blob)[a:b].sum()) if b > a else 0.0)
    finally:
        con.close()
    return np.array(rts), np.array(values)
