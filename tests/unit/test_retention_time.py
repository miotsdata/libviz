"""Retention time: spectrum.rt (minutes) — migration, MSP in/out, merge, edit, search."""
import sqlite3
from pathlib import Path

import numpy as np
import pytest
from alembic import command
from alembic.config import Config

from libviz.core.db.migrations import _get_alembic_ini, _get_migrations_dir
from libviz.core.library import Library
from libviz.core.writers import write_msp

KEY = "UHOVQNZJYSORNB-UHFFFAOYSA-N"


def add(lib, key=KEY, ce=20.0, rt=None, mz=79.05):
    adduct = lib.get_adducts()[0]["id"]
    lib.add_spectra("Benzene", "C6H6", key, {"precursor_mz": mz, "polarity": "POSITIVE", "collision_energy": ce,
                                             "mz": np.array([50.0, 60.0]), "intensity": np.array([100.0, 50.0]),
                                             "rt": rt}, adduct)
    return lib.get_compound_spectra(lib.search_compounds(text=key)[0]["id"])[-1]["id"]


def alembic(path) -> Config:
    cfg = Config(str(_get_alembic_ini()))
    cfg.set_main_option("script_location", str(_get_migrations_dir()))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{path}")
    return cfg


def test_opening_an_old_library_migrates_and_copies_rt_from_metadata(tmp_path):
    path = tmp_path / "old.db"
    lib = Library.create(path, name="old")
    ids = [add(lib, ce=ce) for ce in (10.0, 20.0, 30.0, 40.0)]
    lib.set_spectrum_metadata(ids[0], "rt_min", "2.5")          # libviz builder provenance
    lib.set_spectrum_metadata(ids[1], "RTINSECONDS", "90")      # MSP, seconds
    lib.set_spectrum_metadata(ids[2], "RetentionTime", "n/a")   # free text
    lib.is_temp = False
    lib.close()
    command.downgrade(alembic(path), "e1a2b3c4d5f6")
    con = sqlite3.connect(path)
    assert "rt" not in {r[1] for r in con.execute("PRAGMA table_info(spectrum)")}
    con.close()

    lib = Library.load_from_db(path)
    assert [lib.get_spectrum(i)["rt"] for i in ids] == [2.5, 1.5, None, None]
    assert lib.get_spectrum(ids[0])["metadata"] == {"rt_min": "2.5"}  # copied, not moved
    lib.close()


def test_msp_rt_is_read_into_the_column_and_written_back(tmp_path):
    msp = tmp_path / "in.msp"
    msp.write_text(f"""NAME: A
INCHIKEY: {KEY}
PRECURSORMZ: 79.05
PRECURSORTYPE: [M+H]+
RTINSECONDS: 120
Num Peaks: 1
50 100

NAME: B
INCHIKEY: YXFVVABEGXRONW-UHFFFAOYSA-N
PRECURSORMZ: 93.07
PRECURSORTYPE: [M+H]+
RETENTIONTIME: unknown
Num Peaks: 1
50 100
""")
    lib = Library.load_from_msp(msp)
    a, b = (lib.get_spectrum(lib.get_compound_spectra(lib.search_compounds(text=n)[0]["id"])[0]["id"])
            for n in ("A", "B"))
    assert a["rt"] == 2.0 and "RTINSECONDS" not in a["metadata"]
    assert b["rt"] is None and b["metadata"]["RETENTIONTIME"] == "unknown"

    write_msp(lib, tmp_path / "out.msp")
    text = (tmp_path / "out.msp").read_text()
    assert text.count("RETENTIONTIME: 2.0000") == 1 and "RTINSECONDS" not in text
    assert "RETENTIONTIME: unknown" in text  # no RT column: free text kept
    lib.close()


def test_merge_copies_rt_and_set_rt(tmp_path):
    a = Library.create(tmp_path / "a.db", name="A")
    b = Library.create(tmp_path / "b.db", name="B")
    sid = add(b, rt=3.25)
    a.merge_from(b.path)
    [merged] = a.get_compound_spectra(a.search_compounds()[0]["id"])
    assert merged["rt"] == 3.25
    b.set_spectrum_rt(sid, None)
    assert b.get_spectrum(sid)["rt"] is None
    with pytest.raises(ValueError):
        b.set_spectrum_rt(sid, -1)


def test_search_hits_carry_rt(tmp_path):
    lib = Library.create(tmp_path / "a.db", name="A")
    add(lib, rt=4.0)
    [hit] = lib.search_spectrum([50.0, 60.0], [100.0, 50.0], precursor_mz=79.05)
    assert hit["rt"] == 4.0
