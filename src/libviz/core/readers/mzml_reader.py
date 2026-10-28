"""Streaming mzML reader for MS2 scans (ADR 4).

lxml ``iterparse`` over ``<spectrum>`` elements, reading cvParams by
accession; each element is freed after use, so memory stays flat on
multi-GB (spatial) files. Peak arrays are decoded only for scans the caller
keeps, which is what makes scanning a large file for a few targets cheap.
"""
import base64
import logging
import zlib
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from lxml import etree

logger = logging.getLogger(__name__)

MS_LEVEL = "MS:1000511"
POSITIVE = "MS:1000130"
NEGATIVE = "MS:1000129"
CENTROID = "MS:1000127"
PROFILE = "MS:1000128"
TIC = "MS:1000285"
SCAN_START_TIME = "MS:1000016"
ISO_TARGET = "MS:1000827"
ISO_LOWER = "MS:1000828"
ISO_UPPER = "MS:1000829"
SELECTED_MZ = "MS:1000744"
PEAK_INTENSITY = "MS:1000042"
COLLISION_ENERGY = "MS:1000045"
CHARGE = "MS:1000041"

FLOAT64, FLOAT32 = "MS:1000523", "MS:1000521"
ZLIB, NO_COMPRESSION = "MS:1000574", "MS:1000576"
MZ_ARRAY, INTENSITY_ARRAY = "MS:1000514", "MS:1000515"


@dataclass
class Ms2Scan:
    file: str
    scan_id: str
    index: int
    polarity: str | None  # "POSITIVE" / "NEGATIVE"
    rt_min: float | None
    precursor_mz: float | None  # selected ion m/z (or isolation target)
    precursor_intensity: float | None
    precursor_charge: int | None
    isolation_lower: float | None  # absolute m/z bounds
    isolation_upper: float | None
    collision_energy: float | None
    tic: float | None
    mz: np.ndarray = field(default_factory=lambda: np.empty(0))
    intensity: np.ndarray = field(default_factory=lambda: np.empty(0))

    @property
    def isolation_width(self) -> float | None:
        if self.isolation_lower is None or self.isolation_upper is None:
            return None
        return self.isolation_upper - self.isolation_lower


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _params(elem, groups: dict) -> dict[str, tuple[str, str]]:
    """accession -> (value, unitName) for every cvParam below ``elem``
    (including referenced param groups), except inside binary data arrays."""
    out = {}
    for child in elem:
        tag = _local(child.tag)
        if tag == "cvParam":
            out[child.get("accession")] = (child.get("value"), child.get("unitName") or "")
        elif tag == "referenceableParamGroupRef":
            out.update(groups.get(child.get("ref"), {}))
        elif tag != "binaryDataArrayList":
            out.update(_params(child, groups))
    return out


def _decode_arrays(elem) -> tuple[np.ndarray, np.ndarray]:
    arrays = {}
    for bda in elem.iter("{*}binaryDataArray"):
        acc = {p.get("accession") for p in bda.iter("{*}cvParam")}
        kind = MZ_ARRAY if MZ_ARRAY in acc else INTENSITY_ARRAY if INTENSITY_ARRAY in acc else None
        if kind is None:
            continue
        if not acc & {ZLIB, NO_COMPRESSION}:
            raise ValueError("Unsupported binary compression (e.g. MS-Numpress); "
                             "convert with msconvert using zlib or no compression.")
        binary = bda.find("{*}binary")
        raw = base64.b64decode(binary.text or "") if binary is not None else b""
        if ZLIB in acc:
            raw = zlib.decompress(raw)
        dtype = "<f4" if FLOAT32 in acc else "<f8"
        arrays[kind] = np.frombuffer(raw, dtype=dtype).astype(np.float64)
    mz = arrays.get(MZ_ARRAY, np.empty(0))
    intensity = arrays.get(INTENSITY_ARRAY, np.empty(0))
    n = min(len(mz), len(intensity))
    return mz[:n], intensity[:n]


def _scan_from(elem, file: str, p: dict) -> Ms2Scan:
    rt, unit = p.get(SCAN_START_TIME, (None, ""))
    rt = _float(rt)
    if rt is not None and unit.lower().startswith("second"):
        rt /= 60.0
    target = _float(p.get(ISO_TARGET, (None,))[0])
    selected = _float(p.get(SELECTED_MZ, (None,))[0])
    lower = _float(p.get(ISO_LOWER, (None,))[0])
    upper = _float(p.get(ISO_UPPER, (None,))[0])
    center = target if target is not None else selected
    charge = _float(p.get(CHARGE, (None,))[0])
    return Ms2Scan(
        file=file,
        scan_id=elem.get("id", ""),
        index=int(elem.get("index", 0)),
        polarity="POSITIVE" if POSITIVE in p else "NEGATIVE" if NEGATIVE in p else None,
        rt_min=rt,
        precursor_mz=selected if selected is not None else target,
        precursor_intensity=_float(p.get(PEAK_INTENSITY, (None,))[0]),
        precursor_charge=int(charge) if charge else None,
        isolation_lower=center - lower if center is not None and lower is not None else None,
        isolation_upper=center + upper if center is not None and upper is not None else None,
        collision_energy=_float(p.get(COLLISION_ENERGY, (None,))[0]),
        tic=_float(p.get(TIC, (None,))[0]),
    )


def count_spectra(path: Path) -> int:
    """``<spectrumList count>``, read from the head of the file (0 if absent)."""
    with open(path, "rb") as f:
        for _, elem in etree.iterparse(f, events=("start",), tag="{*}spectrumList"):
            return int(elem.get("count", 0))
    return 0


def iter_ms2(path: Path, keep: Callable[[Ms2Scan], bool] = lambda scan: True,
             progress: Callable[[int, int], None] | None = None) -> Iterator[Ms2Scan]:
    """Yield the MS2 scans of ``path`` for which ``keep(scan)`` is true, with
    their peaks decoded. ``keep`` sees the scan without peaks.

    Raises ``ValueError`` on profile-mode MS2: library spectra must be
    centroided (msconvert ``--filter "peakPicking true 1-"``).
    """
    path = Path(path)
    total = count_spectra(path) if progress else 0
    groups: dict[str, dict] = {}
    n = 0
    with open(path, "rb") as f:
        for _, elem in etree.iterparse(f, events=("end",), tag=("{*}referenceableParamGroup", "{*}spectrum")):
            if _local(elem.tag) == "referenceableParamGroup":
                groups[elem.get("id")] = _params(elem, groups)
                continue
            n += 1
            p = _params(elem, groups)
            if p.get(MS_LEVEL, (None,))[0] == "2":
                if PROFILE in p:
                    raise ValueError(f"{path.name}: MS2 spectra are in profile mode; centroid them first "
                                     "(e.g. msconvert --filter \"peakPicking true 1-\").")
                scan = _scan_from(elem, path.name, p)
                if keep(scan):
                    scan.mz, scan.intensity = _decode_arrays(elem)
                    yield scan
            # free the element and already-processed siblings
            elem.clear()
            parent = elem.getparent()
            while parent is not None and elem.getprevious() is not None:
                del parent[0]
            if progress and n % 500 == 0:
                progress(n, total)
    if progress:
        progress(total, total)


def read_scan(path: Path, scan: int | str) -> Ms2Scan:
    """One MS2 scan by number: matches ``scan=N`` in the native id (Thermo,
    msconvert), else the 0-based spectrum index."""
    scan = str(scan).strip()
    token = f"scan={scan}"

    def wanted(s: Ms2Scan) -> bool:
        return token in s.scan_id.split() or s.scan_id == scan or str(s.index) == scan
    for s in iter_ms2(Path(path), wanted):
        return s
    raise ValueError(f"no MS2 scan {scan} in {Path(path).name}")
