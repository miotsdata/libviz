"""Big-library smoke test (ADR 3): MoNA-sized libraries must stay
interactive. Slow (~10 s to build); run with ``pytest -m slow``."""
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from libviz.core.library import Library

N_COMPOUNDS = 100_000
N_SPECTRA = 500_000


def build_big_library(path: Path) -> Library:
    lib = Library.create(path, name="big", fast_writes=True)
    rng = np.random.default_rng(0)
    blob_mz = np.arange(20, dtype="<f4").tobytes()
    now = datetime.now().isoformat()
    masses = rng.uniform(100, 1200, N_COMPOUNDS)
    with lib.engine.begin() as conn:
        conn.exec_driver_sql(
            "INSERT INTO compound (name, formula, inchikey, exact_mass, added_on) VALUES (?, ?, ?, ?, ?)",
            [(f"compound {i}", f"C{i % 60 + 1}H{i % 90 + 1}O{i % 9}", f"KEY{i:011d}", float(masses[i]), now)
             for i in range(N_COMPOUNDS)])
        conn.exec_driver_sql(
            "INSERT INTO spectrum (compound_id, precursor_mz, adduct_type_id, polarity, collision_energy,"
            " mz_array, intensity_array, added_on, spectrum_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(i % N_COMPOUNDS + 1, float(masses[i % N_COMPOUNDS]) + 1.007, 1 + i % 2,
              "POSITIVE" if i % 3 else "NEGATIVE", float(10 * (i % 5)), blob_mz, blob_mz, now, f"h{i}")
             for i in range(N_SPECTRA)])
    return lib


@pytest.mark.slow
def test_browse_queries_stay_interactive(tmp_path):
    lib = build_big_library(tmp_path / "big.db")
    lib.save_as_db(tmp_path / "big_saved.db")

    def timed(fn, **kw):
        t = time.perf_counter()
        fn(**kw)
        return time.perf_counter() - t

    timings = {
        "count all": timed(lib.count_compounds),
        "first page": timed(lib.search_compounds),
        "deep page": timed(lib.search_compounds, offset=90_000),
        "text": timed(lib.search_compounds, text="compound 4242"),
        "count text": timed(lib.count_compounds, text="compound 4242"),
        "mass": timed(lib.search_compounds, mass=500.0, ppm=10),
        "count polarity": timed(lib.count_compounds, polarity="NEGATIVE"),
        "filter options": timed(lib.filter_options),
        "spectra of compound": timed(lib.get_compound_spectra, compound_id=777),
    }
    print(timings)
    slow = {k: round(v, 3) for k, v in timings.items() if v > 1.0}
    assert not slow, slow


@pytest.mark.slow
def test_export_and_merge_scale(tmp_path):
    from libviz.core.writers import write_msp
    lib = build_big_library(tmp_path / "big.db")
    lib.is_temp = False

    t = time.perf_counter()
    assert write_msp(lib, tmp_path / "big.msp") == N_SPECTRA
    export = time.perf_counter() - t

    target = Library.create(tmp_path / "target.db", name="target")
    t = time.perf_counter()
    counts = target.merge_from(lib.path)
    merge = time.perf_counter() - t
    print({"export": export, "merge": merge})
    assert counts["spectra_added"] == N_SPECTRA
    assert export < 120 and merge < 60
