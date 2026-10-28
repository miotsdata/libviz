import numpy as np
import pytest

# Models/bridges below are parented to ``qapp``: freeing one while its Task
# threads are still running (or their queued results are pending) crashes.
from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtGui import QGuiApplication

from libviz.core.library import Library
from libviz.gui import compound_model
from libviz.gui.compound_model import CompoundTableModel
from libviz.gui.inspector_bridge import InspectorBridge, parse_float, peaks_as_text
from libviz.gui.library_bridge import LibraryBridge


def make_library(path, n=5):
    lib = Library.create(path, name="lib")
    adduct = lib.get_adducts()[0]["id"]
    for i in range(n):
        lib.add_spectra(f"cmp{i:03d}", "C6H6", f"KEY{i:03d}",
                        {"precursor_mz": 79.05 + i, "polarity": "POSITIVE", "collision_energy": 20.0,
                         "mz": np.array([50.0 + i]), "intensity": np.array([10.0])}, adduct)
    return lib


def test_parse_float():
    assert parse_float("195,08") == 195.08
    assert parse_float("") is None
    assert parse_float("abc") is None


def test_peaks_as_text():
    assert peaks_as_text({"mz": [50.0, 60.12346], "intensity": [100.0, 5.5]}) == "50.0000\t100\n60.1235\t5.5"


def test_model_pages_rows_lazily(qtbot, qapp, tmp_path, monkeypatch):
    monkeypatch.setattr(compound_model, "PAGE_SIZE", 2)
    lib = make_library(tmp_path / "a.db", n=5)
    model = CompoundTableModel(qapp)
    with qtbot.waitSignal(model.countChanged, timeout=5000):
        model.set_library(lib)

    assert model.rowCount() == 5
    assert model.data(model.index(0, 0)) == "cmp000"
    assert model.data(model.index(4, 0)) == ""  # page 2 not loaded yet: blank, fetch started
    with qtbot.waitSignal(model.dataChanged, timeout=5000):
        pass
    assert model.data(model.index(4, 0)) == "cmp004"
    assert model.data(model.index(0, 4)) == "1"  # n_spectra


def test_model_sort_and_header(qtbot, qapp, tmp_path):
    lib = make_library(tmp_path / "a.db", n=3)
    model = CompoundTableModel(qapp)
    with qtbot.waitSignal(model.countChanged, timeout=5000):
        model.set_library(lib)
    assert model.headerData(0, Qt.Orientation.Horizontal) == "Name ▲"

    with qtbot.waitSignal(model.modelReset, timeout=5000):
        model.sortByColumn(0)
    assert model.headerData(0, Qt.Orientation.Horizontal) == "Name ▼"
    assert model.data(model.index(0, 0)) == "cmp002"

    model.sortByColumn(4)  # n_spectra: not sortable, ignored
    assert model.sortKey == "name"


def test_stale_results_are_dropped(qtbot, qapp, tmp_path):
    lib = make_library(tmp_path / "a.db", n=3)
    model = CompoundTableModel(qapp)
    model.set_library(lib)
    with qtbot.waitSignal(model.countChanged, timeout=5000):
        model.set_filters({"text": "cmp001"})  # supersedes the unfiltered reload
    assert model.rowCount() == 1
    qtbot.wait(100)
    assert model.rowCount() == 1


@pytest.fixture
def bridges(tmp_path, qapp):
    make_library(tmp_path / "lib.db", n=3)
    # Parented to the app like production parents them to the engine: a
    # bridge freed by Python while its Tasks still run would crash.
    libraries = LibraryBridge(parent=qapp)
    inspector = InspectorBridge(libraries, parent=qapp)
    yield libraries, inspector
    for lib in libraries.manager.libraries.values():
        lib.close()


def test_selecting_library_compound_and_spectrum(qtbot, bridges, tmp_path):
    libraries, inspector = bridges
    with qtbot.waitSignal(inspector.filterOptionsChanged, timeout=5000):
        libraries.openLibrary(str(tmp_path / "lib.db"))
    assert inspector.filterOptions["polarities"] == ["POSITIVE"]
    qtbot.waitUntil(lambda: inspector.compounds.rowCount() == 3)

    with qtbot.waitSignal(inspector.spectrumChanged, timeout=5000):
        inspector.selectCompoundRow(1)
    assert inspector.compound["name"] == "cmp001"
    assert len(inspector.spectra) == 1
    assert inspector.spectrum["mz"] == [51.0]

    inspector.copyPeaks()
    assert QGuiApplication.clipboard().text() == "51.0000\t10"

    with qtbot.waitSignal(inspector.compounds.countChanged, timeout=5000):
        inspector.setFilters("cmp002", "", "10", "", "", "")
    assert inspector.compounds.rowCount() == 1


def test_closing_library_clears_inspector(qtbot, bridges, tmp_path):
    libraries, inspector = bridges
    with qtbot.waitSignal(inspector.filterOptionsChanged, timeout=5000):
        libraries.openLibrary(str(tmp_path / "lib.db"))
    with qtbot.waitSignal(inspector.spectrumChanged, timeout=5000):
        inspector.selectCompoundRow(0)

    with qtbot.waitSignal(inspector.compounds.modelReset, timeout=5000):
        libraries.closeLibrary(libraries.selectedKey)
    assert inspector.compound == {}
    assert inspector.compounds.rowCount() == 0


def _open_and_select(qtbot, libraries, inspector, path, row=0):
    with qtbot.waitSignal(inspector.filterOptionsChanged, timeout=5000):
        libraries.openLibrary(str(path))
    qtbot.waitUntil(lambda: inspector.compounds.rowCount() > 0)
    with qtbot.waitSignal(inspector.spectrumChanged, timeout=5000):
        inspector.selectCompoundRow(row)


def test_edit_compound_and_metadata(qtbot, bridges, tmp_path):
    libraries, inspector = bridges
    _open_and_select(qtbot, libraries, inspector, tmp_path / "lib.db")

    with qtbot.waitSignal(inspector.compoundChanged, timeout=5000):
        inspector.updateCompound("Renamed", "C7H8", "Cc1ccccc1", "1140")
    assert inspector.compound["name"] == "Renamed"
    assert inspector.compound["pubchem_id"] == 1140
    qtbot.waitUntil(lambda: inspector.compounds.data(inspector.compounds.index(2, 0)) == "Renamed")

    # Earlier reloads may still be in flight: wait for the state, not a signal.
    inspector.setMetadata("note", "checked")
    qtbot.waitUntil(lambda: inspector.spectrum.get("metadata") == {"note": "checked"})
    inspector.deleteMetadata("note")
    qtbot.waitUntil(lambda: inspector.spectrum.get("metadata") == {})

    with qtbot.waitSignal(inspector.errorOccurred, timeout=1000):
        inspector.updateCompound("x", "C7H8", "", "abc")


def test_delete_spectrum_then_compound(qtbot, bridges, tmp_path):
    libraries, inspector = bridges
    _open_and_select(qtbot, libraries, inspector, tmp_path / "lib.db")

    with qtbot.waitSignal(inspector.spectraChanged, timeout=5000):
        inspector.deleteSpectrum(inspector.spectrum["id"])
    assert inspector.spectra == []
    qtbot.waitUntil(lambda: libraries.selected["nSpectra"] == 2)

    with qtbot.waitSignal(inspector.compounds.countChanged, timeout=5000):
        inspector.deleteCompound()
    assert inspector.compound == {}
    assert inspector.compounds.rowCount() == 2
    qtbot.waitUntil(lambda: libraries.selected["nCompounds"] == 2)


def test_export_compound(qtbot, bridges, tmp_path):
    libraries, inspector = bridges
    _open_and_select(qtbot, libraries, inspector, tmp_path / "lib.db", row=1)
    with qtbot.waitSignal(libraries.infoMessage, timeout=5000):
        inspector.exportCompoundMsp(str(tmp_path / "one"))
    assert "NAME: cmp001" in (tmp_path / "one.msp").read_text()


def test_only_newest_selection_is_applied(qtbot, bridges, tmp_path):
    libraries, inspector = bridges
    _open_and_select(qtbot, libraries, inspector, tmp_path / "lib.db")
    for row in (0, 1, 2, 1, 2):
        inspector.selectCompoundRow(row)
    qtbot.waitUntil(lambda: inspector.compound.get("name") == "cmp002" and inspector.spectrum.get("mz") == [52.0])
    qtbot.wait(100)
    assert inspector.compound["name"] == "cmp002"
