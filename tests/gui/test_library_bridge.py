from pathlib import Path

import pytest
from PySide6.QtCore import QUrl

from libviz.core.library import Library
from libviz.gui.library_bridge import LibraryBridge, to_local_path


@pytest.fixture
def bridge():
    b = LibraryBridge()
    yield b
    for lib in b.manager.libraries.values():
        lib.close()


def _import(qtbot, bridge, msp_file):
    with qtbot.waitSignal(bridge.libraryOpened, timeout=10_000):
        bridge.importMsp(QUrl.fromLocalFile(str(msp_file)).toString())
    return bridge.selectedKey


def test_to_local_path_accepts_urls_and_paths(tmp_path):
    assert to_local_path(QUrl.fromLocalFile(str(tmp_path / "a.db")).toString()) == str(tmp_path / "a.db")
    assert to_local_path(str(tmp_path / "a.db")) == str(tmp_path / "a.db")


def test_import_msp_lists_unsaved_library(qtbot, bridge, msp_file):
    _import(qtbot, bridge, msp_file)

    [info] = bridge.libraries
    assert info["name"] == "small"
    assert info["isTemp"] is True
    assert (info["nCompounds"], info["nSpectra"]) == (2, 2)
    assert bridge.hasUnsaved
    assert not bridge.busy


def test_save_as_rekeys_and_clears_unsaved(qtbot, bridge, msp_file, tmp_path):
    _import(qtbot, bridge, msp_file)
    target = tmp_path / "saved"  # suffix added

    with qtbot.waitSignal(bridge.librariesChanged, timeout=10_000):
        bridge.saveSelectedAs(str(target))

    assert bridge.selected["path"] == str(tmp_path / "saved.db")
    assert not bridge.hasUnsaved
    assert Library.load_from_db(tmp_path / "saved.db").n_spectra == 2


def test_open_existing_library_selects_instead_of_reopening(qtbot, bridge, tmp_path):
    Library.create(tmp_path / "lib.db", name="Mine")
    with qtbot.waitSignal(bridge.libraryOpened, timeout=10_000):
        bridge.openLibrary(str(tmp_path / "lib.db"))
    assert bridge.selected["name"] == "Mine"

    bridge.openLibrary(str(tmp_path / "lib.db"))
    assert len(bridge.libraries) == 1
    assert not bridge.busy


def test_create_rename_close(qtbot, bridge, tmp_path):
    with qtbot.waitSignal(bridge.libraryOpened, timeout=10_000):
        bridge.createLibrary(str(tmp_path / "new.db"), "")
    assert bridge.selected["name"] == "new"
    assert bridge.selected["isTemp"] is False

    with qtbot.waitSignal(bridge.selectedChanged, timeout=10_000):
        bridge.renameSelected("Renamed")
    assert bridge.selected["name"] == "Renamed"
    assert Library.load_from_db(tmp_path / "new.db").name == "Renamed"

    bridge.closeLibrary(bridge.selectedKey)
    assert bridge.libraries == []
    assert bridge.selectedKey == ""
    assert (tmp_path / "new.db").exists()  # saved libraries are never deleted


def test_close_unsaved_deletes_temp_file(qtbot, bridge, msp_file):
    key = _import(qtbot, bridge, msp_file)
    bridge.closeLibrary(key)
    assert not Path(key).exists()


def test_second_task_while_busy_is_rejected(qtbot, bridge, msp_file, tmp_path):
    errors = []
    bridge.errorOccurred.connect(errors.append)
    with qtbot.waitSignal(bridge.libraryOpened, timeout=10_000):
        bridge.importMsp(str(msp_file))
        bridge.createLibrary(str(tmp_path / "other.db"), "")
    assert errors and errors[0].startswith("Please wait")
    assert len(bridge.libraries) == 1


def test_open_failure_reports_error(qtbot, bridge, tmp_path):
    with qtbot.waitSignal(bridge.errorOccurred, timeout=10_000) as blocker:
        bridge.openLibrary(str(tmp_path / "missing.db"))
    assert "missing.db" in blocker.args[0]
    assert not bridge.busy
