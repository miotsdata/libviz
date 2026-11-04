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
