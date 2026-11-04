import os
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from mzml_factory import write_mzml  # noqa: E402

from libviz.core.readers import mzml_db
from libviz.core.readers.mzml_db import db_path_for, eic, is_current, iter_ms2_db, parse_to_db, parsed_db
from libviz.core.readers.mzml_reader import iter_ms2

MS1 = dict(ms_level=1, mz=(195.0877, 300.0), intensity=(100.0, 5.0))


def run(tmp_path, name="run.mzML"):
    return write_mzml(tmp_path / name, [
        dict(MS1, rt_min=1.0),
        dict(precursor_mz=195.0877, precursor_intensity=50.0, rt_min=1.01, mz=(138.0662, 110.0),
             intensity=(100.0, 20.0)),
        dict(MS1, rt_min=1.1, intensity=(400.0, 5.0)),
        dict(MS1, rt_min=1.2, polarity="negative", intensity=(999.0, 5.0)),
        dict(precursor_mz=500.0, isolation=(10, 10), rt_min=1.21, collision_energy=40),
    ])


def test_parse_matches_the_xml_reader_and_msianalyzer_schema(tmp_path):
    mzml = run(tmp_path)
    db = parsed_db(mzml)
    assert db == tmp_path / "run.mzML.db" and is_current(db, mzml)
    con = sqlite3.connect(db)
    assert con.execute("SELECT scan_id, rt, polarity FROM ms1_scans ORDER BY scan_id").fetchall() == [
        (1, 60.0, "POSITIVE"), (3, 66.0, "POSITIVE"), (4, 72.0, "NEGATIVE")]
    assert con.execute("SELECT isolation_window_target, isolation_window_lower, filter_string"
                       " FROM ms2_scans WHERE scan_id = 5").fetchone() == (500.0, 10.0, "")
    con.close()

    from_xml = list(iter_ms2(mzml))
    from_db = list(iter_ms2_db(db, mzml.name))
    assert [s.scan_id for s in from_db] == [s.scan_id for s in from_xml] == ["scan=2", "scan=5"]
    for a, b in zip(from_xml, from_db):
        assert (a.precursor_mz, a.isolation_lower, a.isolation_upper, a.collision_energy, a.polarity) == \
               (b.precursor_mz, b.isolation_lower, b.isolation_upper, b.collision_energy, b.polarity)
        assert b.rt_min == pytest.approx(a.rt_min)
        np.testing.assert_allclose(b.mz, a.mz, atol=1e-4)
    assert [s.scan_id for s in iter_ms2_db(db, "x", lambda s: s.precursor_mz > 400)] == ["scan=5"]


def test_eic_sums_within_ppm_and_skips_other_polarity(tmp_path):
    db = parsed_db(run(tmp_path))
    rt, intensity = eic(db, 195.0877, 10, "POSITIVE")
    np.testing.assert_allclose(rt, [1.0, 1.1])
    np.testing.assert_allclose(intensity, [100.0, 400.0])
    assert eic(db, 250.0, 10)[1].tolist() == [0.0, 0.0, 0.0]


def test_reparsed_when_the_mzml_changes_and_reused_otherwise(tmp_path, monkeypatch):
    mzml = run(tmp_path)
    db = parsed_db(mzml)
    calls = []
    monkeypatch.setattr(mzml_db, "parse_to_db", lambda *a, **k: calls.append(a) or db)
    parsed_db(mzml)
    assert calls == []
    os.utime(mzml, ns=(0, 0))
    parsed_db(mzml)
    assert len(calls) == 1


def test_ids_without_scan_numbers_use_the_index_and_parent_refs_resolve(tmp_path):
    mzml = run(tmp_path)
    text = mzml.read_text().replace('id="scan=', 'id="sample=1 cycle=').replace(
        "<precursor>", '<precursor spectrumRef="sample=1 cycle=1">')
    mzml.write_text(text)
    db = parse_to_db(mzml, tmp_path / "x.db")
    con = sqlite3.connect(db)
    assert con.execute("SELECT scan_id, parent_scan_id, native_id FROM ms2_scans ORDER BY scan_id").fetchall() == [
        (2, 1, "sample=1 cycle=2"), (5, 1, "sample=1 cycle=5")]
    con.close()


def test_profile_ms1_is_skipped_and_failed_parse_leaves_nothing(tmp_path):
    mzml = write_mzml(tmp_path / "p.mzML", [dict(MS1, centroid=False), dict(precursor_mz=195.0877)])
    db = parsed_db(mzml)
    con = sqlite3.connect(db)
    assert con.execute("SELECT COUNT(*) FROM ms1_scans").fetchone() == (0,)
    assert con.execute("SELECT value FROM metadata WHERE key = 'ms1_profile_skipped'").fetchone() == ("1",)
    con.close()

    bad = write_mzml(tmp_path / "bad.mzML", [dict(precursor_mz=1.0, centroid=False)])
    with pytest.raises(ValueError, match="profile"):
        parsed_db(bad)
    assert not db_path_for(bad).exists() and not Path(str(db_path_for(bad)) + ".part").exists()


def test_unwritable_folder_uses_the_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "access", lambda *a: False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    assert db_path_for(tmp_path / "r.mzML").parent == tmp_path / "cache" / "libviz" / "parsed"
