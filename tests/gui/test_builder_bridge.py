import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from mzml_factory import write_mzml  # noqa: E402

from libviz.core.library import Library
from libviz.gui.builder_bridge import BuilderBridge, short_scan_id
from libviz.gui.library_bridge import LibraryBridge

TARGETS = "name,formula,inchikey\nCaffeine,C8H10N4O2,RYYVLZVUVIJVGH-UHFFFAOYSA-N\n"
MH = 195.087652


@pytest.fixture
def setup(tmp_path, qapp, qtbot):
    (tmp_path / "t.csv").write_text(TARGETS)
    mzml = write_mzml(tmp_path / "a.mzML", [
        dict(precursor_mz=MH, precursor_intensity=10.0, mz=(138.0, 110.0), intensity=(100.0, 50.0)),
        dict(precursor_mz=MH, precursor_intensity=99.0, mz=(138.0,), intensity=(100.0,)),
        dict(precursor_mz=200.0, isolation=(10, 10), collision_energy=40, mz=(1.0,), intensity=(1.0,)),
    ])
    libraries = LibraryBridge(parent=qapp)
    b = BuilderBridge(libraries, parent=qapp)
    with qtbot.waitSignal(b.targetsChanged, timeout=5000):
        b.loadTargets(str(tmp_path / "t.csv"))
    b.addFiles([str(mzml), str(mzml)])  # duplicates ignored
    yield libraries, b
    for lib in libraries.manager.libraries.values():
        lib.close()


def run(qtbot, b):
    with qtbot.waitSignal(b.selectionChanged, timeout=10_000):
        b.run()


def test_short_scan_id():
    assert short_scan_id("controllerType=0 controllerNumber=1 scan=6") == "scan=6"
    assert short_scan_id("S12") == "S12"


def test_target_errors_are_shown(tmp_path, qtbot, setup):
    _, b = setup
    (tmp_path / "bad.csv").write_text("name\nx\n")
    with qtbot.waitSignal(b.targetsChanged, timeout=5000):
        b.loadTargets(str(tmp_path / "bad.csv"))
    assert "missing column" in b.targetsError
    assert b.targetCount == 0 and not b.canRun


def test_params_round_trip(setup):
    _, b = setup
    b.setParam("ppm", "5")
    b.setParam("positiveAdducts", "[M+H]+ [M+Na]+")
    b.setParam("minRelativeIntensity", "2")
    assert b.params["ppm"] == 5.0
    assert b.params["positiveAdducts"] == "[M+H]+ [M+Na]+"
    assert b.params["minRelativeIntensity"] == pytest.approx(2.0)


def test_run_review_choose_and_commit(qtbot, setup, tmp_path):
    libraries, b = setup
    assert len(b.files) == 1
    run(qtbot, b)

    assert b.stage == "review"
    rows = [b.rows.row(i) for i in range(b.rows.count)]
    by_key = {(r["adduct"], r["ce"]): r for r in rows}
    assert by_key[("[M+H]+", "20")]["n"] == 2
    assert by_key[("[M+H]+", "40")]["status"] == "multiplexed"
    assert by_key[("[M-H]-", "")]["status"] == "missing"
    assert b.summary["nChosen"] == 2

    # best (highest precursor intensity) pre-chosen; preview another, compare, use it
    i = by_key[("[M+H]+", "20")]["index"]
    b.selectGroup(i)
    assert b.candidates[0]["intensity"] == "99" and b.candidates[0]["chosen"]
    b.previewCandidate(1)
    assert b.preview["chosenPeaks"] and b.preview["chosenPeaks"][0][1] == -1000.0
    b.choose(i, 1)
    assert b.rows.row(i)["chosen"] == 1 and b.preview["isChosen"]

    b.rejectMultiplexed()
    assert b.summary["nChosen"] == 1

    Library.create(tmp_path / "lib.db", name="Std")
    with qtbot.waitSignal(libraries.libraryOpened, timeout=5000):
        libraries.openLibrary(str(tmp_path / "lib.db"))
    key = libraries.selectedKey
    with qtbot.waitSignal(b.conflictCountChanged, timeout=5000):
        b.countConflicts(key)
    qtbot.waitUntil(lambda: b.conflictCount == 0)

    with qtbot.waitSignal(b.committed, timeout=10_000) as blocker:
        b.commit(key, False)
    assert blocker.args[1].startswith("Added 1,")
    qtbot.waitUntil(lambda: libraries.selected.get("nSpectra") == 1)
    spectrum = Library.load_from_db(tmp_path / "lib.db").search_compounds()[0]
    assert spectrum["n_spectra"] == 1


def test_run_requires_files(qtbot, setup):
    _, b = setup
    b.clearFiles()
    with qtbot.waitSignal(b.errorOccurred, timeout=1000) as blocker:
        b.run()
    assert "mzML" in blocker.args[0]


def test_hand_entered_target_is_identified_as_existing_compound(qtbot, setup, tmp_path):
    libraries, b = setup
    b.removeTarget(0)
    with qtbot.waitSignal(b.errorOccurred, timeout=1000):
        b.addManualTarget("nope", "[M+H]+")
    b.addManualTarget(f"{MH}", "[M+H]+")
    assert b.targetCount == 1 and b.targetsPreview[0]["name"] == "m/z 195.0877 [M+H]+"
    run(qtbot, b)
    [manual] = b.manualTargets
    assert not manual["identified"]

    lib = Library.create(tmp_path / "lib.db", name="Std")
    lib.add_spectra("Caffeine", "C8H10N4O2", "RYYVLZVUVIJVGH-UHFFFAOYSA-N",
                    {"precursor_mz": MH, "polarity": "POSITIVE", "collision_energy": 99.0,
                     "mz": [1.0], "intensity": [1.0]}, lib.get_adducts()[0]["id"])
    with qtbot.waitSignal(libraries.libraryOpened, timeout=5000):
        libraries.openLibrary(str(tmp_path / "lib.db"))
    key = libraries.selectedKey
    with qtbot.waitSignal(b.compoundMatchesChanged, timeout=5000):
        b.findCompounds(key, manual["index"], "")  # by mass
    [match] = b.compoundMatches
    b.identify(manual["index"], match["name"], match["inchikey"], match["formula"], "")
    assert b.manualTargets[0]["identified"] and b.manualTargets[0]["name"] == "Caffeine"

    with qtbot.waitSignal(b.committed, timeout=10_000):
        b.commit(key, False)
    [compound] = Library.load_from_db(tmp_path / "lib.db").search_compounds()
    assert compound["n_spectra"] == 3  # existing + CE 20 + CE 40 (DIA), all on the one compound


def test_selected_row_shows_its_eic_with_the_ms2_scans(qtbot, setup, tmp_path):
    _, b = setup
    ms1 = dict(ms_level=1, mz=(MH, 300.0), intensity=(1000.0, 1.0))
    mzml = write_mzml(tmp_path / "lc.mzML", [
        dict(ms1, rt_min=1.0), dict(precursor_mz=MH, rt_min=1.05, mz=(138.0,), intensity=(100.0,)),
        dict(ms1, rt_min=1.1, intensity=(3000.0, 1.0)), dict(precursor_mz=MH, rt_min=1.15, mz=(138.0,), intensity=(9.0,)),
        dict(ms1, rt_min=1.2, intensity=(500.0, 1.0)),
    ])
    b.clearFiles()
    b.addFiles([str(mzml)])
    run(qtbot, b)
    i = next(r["index"] for r in (b.rows.row(k) for k in range(b.rows.count)) if r["n"] == 2)
    b.selectGroup(i)
    qtbot.waitUntil(lambda: bool(b.eic), timeout=5000)
    groups = {g["key"]: g for g in b.eic["groups"]}
    assert groups["eic0"]["name"] == "lc.mzML"
    assert [p[1] for p in groups["eic0"]["peaks"]] == [1000.0, 3000.0, 500.0]
    assert len(groups["scans"]["peaks"]) + len(groups["chosen"]["peaks"]) == 2
    assert groups["chosen"]["peaks"][0][1] == pytest.approx(2000.0)  # interpolated at RT 1.05 (chosen: most intense)
    assert sorted(c["rt"] for c in b.eic["candidates"]) == pytest.approx([1.05, 1.15])


def test_rt_is_the_chosen_scans_or_set_by_hand(qtbot, setup, tmp_path):
    libraries, b = setup
    mzml = write_mzml(tmp_path / "rt.mzML", [
        dict(precursor_mz=MH, rt_min=2.0, collision_energy=20, mz=(138.0,), intensity=(100.0,)),
        dict(precursor_mz=MH, rt_min=3.0, collision_energy=40, mz=(138.0,), intensity=(100.0,)),
    ])
    b.clearFiles()
    b.addFiles([str(mzml)])
    run(qtbot, b)
    by_ce = {b.rows.row(k)["ce"]: b.rows.row(k)["index"] for k in range(b.rows.count)}
    b.selectGroup(by_ce["20"])
    assert b.rowRt == {"text": "2.000", "edited": False}
    b.setRt(by_ce["20"], "2,1")
    assert b.rowRt == {"text": "2.100", "edited": True} and b.rows.row(by_ce["20"])["rt"] == "2.10 ✎"
    b.setRt(by_ce["40"], "")  # no RT for this one
    with qtbot.waitSignal(b.errorOccurred, timeout=1000):
        b.setRt(by_ce["20"], "abc")

    Library.create(tmp_path / "lib.db", name="Std")
    with qtbot.waitSignal(libraries.libraryOpened, timeout=5000):
        libraries.openLibrary(str(tmp_path / "lib.db"))
    with qtbot.waitSignal(b.committed, timeout=10_000):
        b.commit(libraries.selectedKey, False)
    lib = Library.load_from_db(tmp_path / "lib.db")
    spectra = lib.get_compound_spectra(lib.search_compounds()[0]["id"])
    assert {s["collision_energy"]: s["rt"] for s in spectra} == {20.0: pytest.approx(2.1), 40.0: None}
    b.resetRt(by_ce["20"])
    assert b.rowRt["text"] == "2.000"
