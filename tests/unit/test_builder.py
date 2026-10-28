import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from mzml_factory import write_mzml  # noqa: E402

from libviz.core.builder import (BuildParams, TargetListError, commit, conflicts, find_candidates,
                                 parse_targets, process_peaks)
from libviz.core.library import Library
from libviz.core.readers.mzml_reader import iter_ms2

CAFFEINE_MH = 195.087652  # [M+H]+
CAFFEINE_MNA = 217.069597
THEOBROMINE_MH = 181.071999
TARGETS = """name,formula,inchikey,smiles,adducts,rt
Caffeine,C8H10N4O2,RYYVLZVUVIJVGH-UHFFFAOYSA-N,CN1C=NC2=C1C(=O)N(C(=O)N2C)C,[M+H]+|[M+Na]+,
Theobromine,C7H8N4O2,YAPQBXQYLJRXSA-UHFFFAOYSA-N,,,3.0
"""


@pytest.fixture
def targets(tmp_path):
    path = tmp_path / "targets.csv"
    path.write_text(TARGETS)
    return parse_targets(path)


def scan(mz, **kw):
    return dict(precursor_mz=mz, mz=(100.0, 120.0, 150.0), intensity=(1000.0, 500.0, 5.0), **kw)


# ---- target list ----

def test_parse_targets(targets):
    caffeine, theobromine = targets
    assert caffeine.adducts == ("[M+H]+", "[M+Na]+")
    assert caffeine.exact_mass == pytest.approx(194.080376)
    assert caffeine.smiles.startswith("CN1")
    assert theobromine.adducts == ()
    assert (theobromine.rt_min, theobromine.rt_max) == (2.5, 3.5)


def test_parse_targets_tab_separated_and_aliases(tmp_path):
    path = tmp_path / "t.tsv"
    path.write_text("Compound\tFormula\tInChI_Key\tRT_min\tRT_max\nX\tC6H6\tUHOVQNZJYSORNB-UHFFFAOYSA-N\t1\t2\n")
    [t] = parse_targets(path)
    assert (t.name, t.rt_min, t.rt_max) == ("X", 1.0, 2.0)


def test_parse_targets_reports_every_problem(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("name,formula,inchikey,adducts\n"
                    "A,C6H6,NOT-A-KEY,\n"
                    "B,Xx99,UHOVQNZJYSORNB-UHFFFAOYSA-N,\n"
                    "C,C6H6,UHOVQNZJYSORNB-UHFFFAOYSA-N,[M+Foo\n")
    with pytest.raises(TargetListError) as e:
        parse_targets(path)
    message = str(e.value)
    assert "3 problem(s)" in message
    assert "line 2: invalid InChIKey" in message
    assert "line 3: invalid formula" in message
    assert "line 4: unknown adduct" in message


def test_parse_targets_missing_columns(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("name,mass\nA,100\n")
    with pytest.raises(TargetListError, match="missing column.*formula, inchikey"):
        parse_targets(path)


# ---- mzML reader ----

def test_reader_skips_ms1_and_rejects_profile(tmp_path):
    path = write_mzml(tmp_path / "a.mzML", [dict(ms_level=1), scan(CAFFEINE_MH)])
    assert len(list(iter_ms2(path))) == 1
    path = write_mzml(tmp_path / "p.mzML", [scan(CAFFEINE_MH, centroid=False)])
    with pytest.raises(ValueError, match="profile mode"):
        list(iter_ms2(path))


# ---- peak processing ----

def test_process_peaks():
    params = BuildParams(min_relative_intensity=0.01, remove_precursor=True)
    mz, intensity = process_peaks(np.array([150.0, 50.0, 60.0, 199.8, 70.0]), np.array([10, 1000, 5, 300, 0]),
                                  200.0, params)
    assert mz.tolist() == [50.0, 150.0]  # 60 below 1%, 199.8 precursor region, 70 zero
    assert intensity.tolist() == [1000.0, 10.0]


# ---- matching ----

def test_dda_matching_groups_by_adduct_and_ce_and_ranks(tmp_path, targets):
    path = write_mzml(tmp_path / "dda.mzML", [
        scan(CAFFEINE_MH, collision_energy=20, precursor_intensity=1e4),
        scan(CAFFEINE_MH + 0.0005, collision_energy=20, precursor_intensity=5e5),  # 2.6 ppm, best
        scan(CAFFEINE_MH, collision_energy=40, precursor_intensity=1e3),
        scan(CAFFEINE_MNA, collision_energy=20),
        scan(CAFFEINE_MH + 0.01, collision_energy=20),  # 51 ppm: no match
        scan(CAFFEINE_MH, collision_energy=20, polarity="negative"),  # wrong polarity
    ])
    result = find_candidates(targets, [path], BuildParams(ppm=10))
    caffeine = {(g.adduct, g.collision_energy): g for g in result.groups if g.target_index == 0}

    assert set(caffeine) == {("[M+H]+", 20.0), ("[M+H]+", 40.0), ("[M+Na]+", 20.0)}
    best = caffeine[("[M+H]+", 20.0)]
    assert len(best.candidates) == 2
    assert best.chosen == 0
    assert best.candidates[0].precursor_intensity == 5e5
    assert best.candidates[0].ppm_error == pytest.approx(2.56, abs=0.05)
    assert not best.candidates[0].multiplexed
    assert result.n_ms2 == 6


def test_missing_targets_get_empty_rows(tmp_path, targets):
    path = write_mzml(tmp_path / "x.mzML", [scan(CAFFEINE_MH)])
    result = find_candidates(targets, [path])
    missing = [(g.target_index, g.adduct) for g in result.groups if g.collision_energy is None]
    # Theobromine has no adducts of its own: both defaults, none found.
    assert missing == [(0, "[M+Na]+"), (1, "[M+H]+"), (1, "[M-H]-")]
    assert all(g.chosen is None for g in result.groups if not g.candidates)


def test_rt_window_is_respected_when_given(tmp_path, targets):
    path = write_mzml(tmp_path / "rt.mzML", [
        scan(THEOBROMINE_MH, rt_min=1.0),
        scan(THEOBROMINE_MH, rt_min=3.1),
    ])
    [group] = [g for g in find_candidates(targets, [path]).groups if g.target_index == 1 and g.candidates]
    assert [c.rt_min for c in group.candidates] == [3.1]


def test_dia_window_match_is_flagged_multiplexed(tmp_path, targets):
    path = write_mzml(tmp_path / "dia.mzML", [
        scan(200.0, isolation=(20.0, 20.0), rt_min=3.0),  # 180-220: caffeine [M+H]+, [M+Na]+, theobromine [M+H]+
    ])
    groups = [g for g in find_candidates(targets, [path]).groups if g.candidates]
    assert {(g.target_index, g.adduct) for g in groups} == {(0, "[M+H]+"), (0, "[M+Na]+"), (1, "[M+H]+")}
    assert all(g.candidates[0].multiplexed and g.candidates[0].ppm_error is None for g in groups)


def test_progress_spans_all_files(tmp_path, targets):
    a = write_mzml(tmp_path / "a.mzML", [scan(CAFFEINE_MH)] * 3)
    b = write_mzml(tmp_path / "b.mzML", [scan(CAFFEINE_MH)] * 2)
    steps = []
    result = find_candidates(targets, [a, b], progress=lambda d, t: steps.append((d, t)))
    assert steps[-1] == (5, 5)
    assert sum(len(g.candidates) for g in result.groups) == 5


# ---- commit ----

def test_commit_writes_chosen_with_provenance_and_handles_conflicts(tmp_path, targets):
    path = write_mzml(tmp_path / "c.mzML", [scan(CAFFEINE_MH, rt_min=2.0, precursor_intensity=1e5),
                                           scan(CAFFEINE_MH, collision_energy=40)])
    result = find_candidates(targets, [path])
    lib = Library.create(tmp_path / "lib.db", name="built")

    assert commit(lib, result) == {"added": 2, "replaced": 0, "skipped": 0}
    [compound] = lib.search_compounds(text="Caffeine")
    assert compound["n_spectra"] == 2
    spectrum = lib.get_spectrum(lib.get_compound_spectra(compound["id"])[0]["id"])
    assert spectrum["precursor_mz"] == pytest.approx(CAFFEINE_MH, abs=1e-5)
    assert spectrum["intensity"][0] == 1000.0  # normalized
    assert spectrum["metadata"]["source_file"] == "c.mzML"
    assert spectrum["metadata"]["rt_min"] == "2.0000"
    assert lib.get_compound(compound["id"])["smiles"].startswith("CN1")

    assert len(conflicts(lib, result)) == 2
    assert commit(lib, result) == {"added": 0, "replaced": 0, "skipped": 2}
    assert commit(lib, result, on_conflict="replace") == {"added": 0, "replaced": 2, "skipped": 0}
    assert lib.n_spectra == 2


def test_commit_only_chosen_groups(tmp_path, targets):
    path = write_mzml(tmp_path / "c.mzML", [scan(CAFFEINE_MH), scan(CAFFEINE_MNA)])
    result = find_candidates(targets, [path])
    for g in result.groups:
        if g.adduct == "[M+Na]+":
            g.chosen = None
    lib = Library.create(tmp_path / "lib.db", name="built")
    assert commit(lib, result)["added"] == 1
