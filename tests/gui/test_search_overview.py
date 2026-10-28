import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from mzml_factory import write_mzml  # noqa: E402

from libviz.core.library import Library
from libviz.core.readers.mzml_reader import read_scan
from libviz.gui.inspector_bridge import InspectorBridge
from libviz.gui.library_bridge import LibraryBridge
from libviz.gui.search_bridge import SearchBridge, scaled


def make_library(path):
    lib = Library.create(path, name="lib")
    adduct = lib.get_adducts()[0]["id"]
    for i, (peaks, smiles) in enumerate([((50.0, 60.0, 70.0), None), ((50.0, 61.0, 70.0), None), ((90.0,), None)]):
        lib.add_spectra(f"cmp{i}", "C6H6", f"KEY{i}",
                        {"precursor_mz": 100.0 + i * 0.0001, "polarity": "POSITIVE", "collision_energy": 20.0,
                         "mz": np.array(peaks), "intensity": np.ones(len(peaks)) * 100}, adduct)
    return lib


@pytest.fixture
def bridges(tmp_path, qapp, qtbot):
    make_library(tmp_path / "lib.db")
    libraries = LibraryBridge(parent=qapp)
    inspector = InspectorBridge(libraries, parent=qapp)
    search = SearchBridge(libraries, parent=qapp)
    with qtbot.waitSignal(inspector.filterOptionsChanged, timeout=5000):
        libraries.openLibrary(str(tmp_path / "lib.db"))
    qtbot.waitUntil(lambda: inspector.compounds.rowCount() == 3)
    yield libraries, inspector, search
    for lib in libraries.manager.libraries.values():
        lib.close()


def test_scaled():
    assert scaled([1, 2], [5, 10], -1) == [[1.0, -500.0], [2.0, -1000.0]]
    assert scaled([], []) == []


def test_read_scan(tmp_path):
    path = write_mzml(tmp_path / "a.mzML", [dict(ms_level=1), dict(precursor_mz=100.0), dict(precursor_mz=200.0)])
    assert read_scan(path, 3).precursor_mz == 200.0  # id "scan=3"
    with pytest.raises(ValueError, match="no MS2 scan 9"):
        read_scan(path, 9)


def test_search_from_pasted_peaks(qtbot, bridges):
    _, _, search = bridges
    with qtbot.waitSignal(search.selectionChanged, timeout=5000):
        search.search("50 100\n60 100\n70 100", "100.0", "", "10", "0", "0.01", "2")
    names = [h["name"] for h in search.results]
    assert names[0] == "cmp0" and "cmp2" not in names  # cmp2 has 1 peak < min matched
    assert search.results[0]["score"] == pytest.approx(1.0)
    qtbot.waitUntil(lambda: bool(search.mirror.get("hit")))
    assert search.mirror["query"][0] == [50.0, 1000.0] and search.mirror["hit"][0][1] == -1000.0


def test_search_validation_and_similar_excludes_self(qtbot, bridges):
    _, inspector, search = bridges
    with qtbot.waitSignal(search.errorOccurred, timeout=1000):
        search.search("", "100", "", "10", "0", "0.01", "1")
    with qtbot.waitSignal(search.errorOccurred, timeout=1000):
        search.search("50 1", "", "", "10", "0", "0.01", "1")

    with qtbot.waitSignal(inspector.spectrumChanged, timeout=5000):
        inspector.selectCompoundRow(0)
    search.useSpectrum(inspector.spectrum, inspector.compound["name"])
    assert search.query["precursor"] == "100.00000"
    with qtbot.waitSignal(search.resultsChanged, timeout=5000):
        search.search(search.query["peaks"], search.query["precursor"], "", "10", "0", "0.01", "1")
    assert [h["name"] for h in search.results][:1] == ["cmp1"]  # itself excluded


def test_overview_issue_and_compare(qtbot, bridges):
    _, inspector, _ = bridges
    with qtbot.waitSignal(inspector.overviewChanged, timeout=5000):
        inspector.loadOverview()
    issues = {i["key"]: i["count"] for i in inspector.overview["issues"]}
    assert issues["few_peaks"] == 1 and issues["no_smiles"] == 3

    with qtbot.waitSignal(inspector.compounds.countChanged, timeout=5000):
        inspector.setIssue("few_peaks")
    assert inspector.compounds.rowCount() == 1 and inspector.issueLabel.startswith("compounds with a spectrum")
    with qtbot.waitSignal(inspector.compounds.countChanged, timeout=5000):
        inspector.setIssue("")
    assert inspector.compounds.rowCount() == 3

    with qtbot.waitSignal(inspector.spectrumChanged, timeout=5000):
        inspector.selectCompoundRow(0)
    other = inspector.compounds.row_data(1)["id"]
    other_spectrum = Library.load_from_db(Path(inspector._libraries.selectedKey)).get_compound_spectra(other)[0]["id"]
    with qtbot.waitSignal(inspector.comparisonChanged, timeout=5000):
        inspector.compareWith(other_spectrum)
    assert inspector.comparison["n_matched"] == 2
    assert inspector.comparison["score"] == pytest.approx(2 / 3)
    inspector.clearComparison()
    assert inspector.comparison == {}
