"""
Tests for LibraryManagerBridge and _MspLoaderWorker.

Run with:
    pytest test_library_manager_bridge.py -v

Requires: pytest, pytest-qt (for QThread signal helpers)
"""

import pytest
from unittest.mock import MagicMock
from PySide6.QtCore import QCoreApplication # pylint: disable=no-name-in-module
import sys
from libviz.bridge.library_manager_bridge import _MspLoaderWorker

# ---------------------------------------------------------------------------
# Ensure a QCoreApplication exists for the entire test session
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def qt_app():
    app = QCoreApplication.instance() or QCoreApplication(sys.argv)
    yield app


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_manager():
    """A fully mocked LibraryManager."""
    manager = MagicMock()
    manager.has_libraries = False
    manager.library_count = 0
    manager.selected_library_key = None
    manager._selected_library = None
    return manager


@pytest.fixture()
def bridge(mock_manager):
    from libviz.bridge.library_manager_bridge import LibraryManagerBridge
    return LibraryManagerBridge(mock_manager)


def collect_signals(bridge, *signal_names):
    """Return a dict {signal_name: [emitted_args, ...]} for the given signals."""
    received = {name: [] for name in signal_names}
    for name in signal_names:
        sig = getattr(bridge, name)
        sig.connect(lambda *args, n=name: received[n].append(args))
    return received


# ---------------------------------------------------------------------------
# _MspLoaderWorker
# ---------------------------------------------------------------------------

class TestMspLoaderWorker:
    def test_run_success_emits_finished(self, mock_manager):
        
        worker = _MspLoaderWorker(mock_manager, "/tmp/test.msp")
        finished_args = []
        failed_args = []
        worker.finished.connect(lambda p: finished_args.append(p))
        worker.failed.connect(lambda e: failed_args.append(e))

        worker.run()

        mock_manager.load_library_from_msp.assert_called_once_with("/tmp/test.msp")
        assert finished_args == ["/tmp/test.msp"]
        assert failed_args == []

    def test_run_failure_emits_failed(self, mock_manager):
        from libviz.bridge.library_manager_bridge import _MspLoaderWorker

        mock_manager.load_library_from_msp.side_effect = RuntimeError("parse error")
        worker = _MspLoaderWorker(mock_manager, "/tmp/bad.msp")
        finished_args = []
        failed_args = []
        worker.finished.connect(lambda p: finished_args.append(p))
        worker.failed.connect(lambda e: failed_args.append(e))

        worker.run()

        assert finished_args == []
        assert failed_args == ["parse error"]


# ---------------------------------------------------------------------------
# createLibrary
# ---------------------------------------------------------------------------

class TestCreateLibrary:
    def test_success_emits_library_loaded_and_count_changed(self, bridge, mock_manager):
        received = collect_signals(bridge, "libraryLoaded", "libraryCountChanged", "errorOccurred")

        bridge.createLibrary("MyLib", "/path/to/lib")

        mock_manager.create_library.assert_called_once_with("MyLib", "/path/to/lib")
        assert received["libraryLoaded"] == [("/path/to/lib",)]
        assert len(received["libraryCountChanged"]) == 1
        assert received["errorOccurred"] == []

    def test_success_clears_status(self, bridge):
        statuses = []
        bridge.statusChanged.connect(lambda s: statuses.append(s))

        bridge.createLibrary("MyLib", "/path/to/lib")

        assert statuses[-1] == "", "Status should be cleared after success"

    def test_error_emits_error_occurred(self, bridge, mock_manager):
        mock_manager.create_library.side_effect = ValueError("already exists")
        received = collect_signals(bridge, "errorOccurred", "libraryLoaded")

        bridge.createLibrary("Dup", "/dup/path")

        assert received["errorOccurred"] == [("already exists",)]
        assert received["libraryLoaded"] == []

    def test_error_still_clears_status(self, bridge, mock_manager):
        mock_manager.create_library.side_effect = ValueError("boom")
        statuses = []
        bridge.statusChanged.connect(lambda s: statuses.append(s))

        bridge.createLibrary("X", "/x")

        assert statuses[-1] == "", "Status must be cleared even on error"


# ---------------------------------------------------------------------------
# loadLibraryFromDb
# ---------------------------------------------------------------------------

class TestLoadLibraryFromDb:
    def test_success(self, bridge, mock_manager):
        received = collect_signals(bridge, "libraryLoaded", "libraryCountChanged", "errorOccurred")

        bridge.loadLibraryFromDb("/path/to/lib.db")

        mock_manager.load_library_from_db.assert_called_once_with("/path/to/lib.db")
        assert received["libraryLoaded"] == [("/path/to/lib.db",)]
        assert len(received["libraryCountChanged"]) == 1
        assert received["errorOccurred"] == []

    def test_error(self, bridge, mock_manager):
        mock_manager.load_library_from_db.side_effect = FileNotFoundError("not found")
        received = collect_signals(bridge, "errorOccurred", "libraryLoaded")

        bridge.loadLibraryFromDb("/missing.db")

        assert received["errorOccurred"] == [("not found",)]
        assert received["libraryLoaded"] == []

    def test_status_cleared_on_success(self, bridge):
        statuses = []
        bridge.statusChanged.connect(lambda s: statuses.append(s))
        bridge.loadLibraryFromDb("/lib.db")
        assert statuses[-1] == ""

    def test_status_cleared_on_error(self, bridge, mock_manager):
        mock_manager.load_library_from_db.side_effect = IOError("io")
        statuses = []
        bridge.statusChanged.connect(lambda s: statuses.append(s))
        bridge.loadLibraryFromDb("/lib.db")
        assert statuses[-1] == ""


# ---------------------------------------------------------------------------
# saveAsDb
# ---------------------------------------------------------------------------

class TestSaveAsDb:
    def test_success(self, bridge, mock_manager):
        received = collect_signals(bridge, "errorOccurred")

        bridge.saveAsDb("/out/lib.db")

        mock_manager.save_as_db.assert_called_once_with("/out/lib.db")
        assert received["errorOccurred"] == []

    def test_error(self, bridge, mock_manager):
        mock_manager.save_as_db.side_effect = PermissionError("denied")
        received = collect_signals(bridge, "errorOccurred")

        bridge.saveAsDb("/readonly.db")

        assert received["errorOccurred"] == [("denied",)]

    def test_status_cleared_on_success(self, bridge):
        statuses = []
        bridge.statusChanged.connect(lambda s: statuses.append(s))
        bridge.saveAsDb("/lib.db")
        assert statuses[-1] == ""

    def test_status_cleared_on_error(self, bridge, mock_manager):
        mock_manager.save_as_db.side_effect = IOError("io")
        statuses = []
        bridge.statusChanged.connect(lambda s: statuses.append(s))
        bridge.saveAsDb("/lib.db")
        assert statuses[-1] == ""


# ---------------------------------------------------------------------------
# unloadLibrary
# ---------------------------------------------------------------------------

class TestUnloadLibrary:
    def test_success_emits_unloaded_and_count_changed(self, bridge, mock_manager):
        received = collect_signals(bridge, "libraryUnloaded", "libraryCountChanged", "errorOccurred")

        bridge.unloadLibrary("/path/to/lib")

        mock_manager.unload_library.assert_called_once_with("/path/to/lib")
        assert received["libraryUnloaded"] == [("/path/to/lib",)]
        assert len(received["libraryCountChanged"]) == 1
        assert received["errorOccurred"] == []

    def test_error(self, bridge, mock_manager):
        mock_manager.unload_library.side_effect = KeyError("not loaded")
        received = collect_signals(bridge, "errorOccurred", "libraryUnloaded")

        bridge.unloadLibrary("/ghost.db")

        assert received["errorOccurred"] == [("'not loaded'",)]
        assert received["libraryUnloaded"] == []


# ---------------------------------------------------------------------------
# selectLibrary
# ---------------------------------------------------------------------------

class TestSelectLibrary:
    def test_sets_selected_and_emits_signal(self, bridge, mock_manager):
        received = collect_signals(bridge, "selectedLibraryChanged")

        bridge.selectLibrary("/path/to/lib")

        mock_manager.select_library.assert_called_once_with("/path/to/lib")
        assert len(received["selectedLibraryChanged"]) == 1


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------

class TestProperties:
    def test_has_libraries_delegates_to_manager(self, bridge, mock_manager):
        mock_manager.has_libraries = True
        assert bridge.hasLibraries is True

        mock_manager.has_libraries = False
        assert bridge.hasLibraries is False

    def test_library_count_delegates_to_manager(self, bridge, mock_manager):
        mock_manager.library_count = 5
        assert bridge.libraryCount == 5

    def test_selected_library_key_returns_empty_string_when_none(self, bridge, mock_manager):
        mock_manager.selected_library_key = None
        assert bridge.selectedLibraryKey == ""

    def test_selected_library_key_returns_value(self, bridge, mock_manager):
        mock_manager.selected_library_key = "/some/lib.db"
        assert bridge.selectedLibraryKey == "/some/lib.db"
