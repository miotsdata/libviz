# libviz/bridge/library_manager_bridge.py

from PySide6.QtCore import QObject, Signal, Slot, Property, QThread, QUrl # pylint: disable=no-name-in-module
from libviz.core import LibraryManager


class _MspLoaderWorker(QObject):
    """Runs in a separate thread — no Qt UI calls allowed here."""
    finished = Signal(str)   # emits path on success
    failed = Signal(str)     # emits error message on failure

    def __init__(self, manager: LibraryManager, msp_path: str):
        super().__init__()
        self._manager = manager
        self._msp_path = msp_path

    @Slot()
    def run(self):
        try:
            self._manager.load_library_from_msp(self._msp_path)
            self.finished.emit(self._msp_path)
        except Exception as e:
            self.failed.emit(str(e))


class LibraryManagerBridge(QObject):

    # --- Signals ---
    libraryLoaded = Signal(str)
    libraryUnloaded = Signal(str)
    selectedLibraryChanged = Signal()
    libraryCountChanged = Signal()
    errorOccurred = Signal(str)
    statusChanged = Signal(str)

    def __init__(self, manager: LibraryManager, parent=None):
        super().__init__(parent)
        self._manager = manager
        self._thread: QThread | None = None
        self._worker: _MspLoaderWorker | None = None

    # --- Internal helpers ---

    def _set_status(self, message: str):
        self.statusChanged.emit(message)

    def _clear_status(self):
        self.statusChanged.emit("")

    # --- Slots ---

    @Slot(str, str)
    def createLibrary(self, name: str, path: str):
        try:
            self._set_status(f"Creating: {path}")
            self._manager.create_library(name, path)
            self.libraryCountChanged.emit()
            self.libraryLoaded.emit(path)
        except Exception as e:
            self.errorOccurred.emit(str(e))
        finally:
            self._clear_status()

    @Slot(str)
    def loadLibraryFromMsp(self, msp_path: str):
        """Offloads the heavy parse to a QThread; status bar shown until done."""
        if self._thread and self._thread.isRunning():
            self.errorOccurred.emit("An MSP load is already in progress.")
            return

        msp_path = QUrl(msp_path).toLocalFile()

        self._set_status(f"Loading: {msp_path}")

        self._worker = _MspLoaderWorker(self._manager, msp_path)
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)

        # Wire up lifecycle
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_msp_loaded)
        self._worker.failed.connect(self._on_msp_failed)

        # Clean up thread and worker after work is done
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_msp_loaded(self, path: str):
        self._clear_status()
        self.libraryCountChanged.emit()
        self.libraryLoaded.emit(path)

    def _on_msp_failed(self, message: str):
        self._clear_status()
        self.errorOccurred.emit(message)

    @Slot(str)
    def loadLibraryFromDb(self, path: str):
        try:
            self._set_status(f"Loading: {path}")
            self._manager.load_library_from_db(path)
            self.libraryCountChanged.emit()
            self.libraryLoaded.emit(path)
        except Exception as e:
            self.errorOccurred.emit(str(e))
        finally:
            self._clear_status()

    @Slot(str)
    def saveAsDb(self, path: str):
        try:
            self._set_status(f"Saving: {path}")
            self._manager.save_as_db(path)
        except Exception as e:
            self.errorOccurred.emit(str(e))
        finally:
            self._clear_status()

    @Slot(str)
    def unloadLibrary(self, path: str):
        try:
            self._manager.unload_library(path)
            self.libraryCountChanged.emit()
            self.libraryUnloaded.emit(path)
        except Exception as e:
            self.errorOccurred.emit(str(e))

    @Slot(str)
    def selectLibrary(self, path: str):
        self._manager.select_library(path)
        self.selectedLibraryChanged.emit()

    # --- Properties ---

    @Property(bool, notify=libraryCountChanged)
    def hasLibraries(self) -> bool:
        return self._manager.has_libraries

    @Property(int, notify=libraryCountChanged)
    def libraryCount(self) -> int:
        return self._manager.library_count

    @Property(str, notify=selectedLibraryChanged)
    def selectedLibraryKey(self) -> str:
        return self._manager.selected_library_key or ""