import logging
from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from libviz.core import LibraryManager
from libviz.core.library import Library
from libviz.core.managers.library_manager import library_key
from libviz.core.writers import write_msp
from libviz.gui.worker import start_task

logger = logging.getLogger(__name__)


def to_local_path(url_or_path: str | QUrl) -> str:
    """QML hands over file:// URLs (FileDialog) or plain paths; accept both."""
    url = QUrl(url_or_path)
    return url.toLocalFile() if url.isLocalFile() else str(url_or_path)


def describe(lib: Library) -> dict:
    """What the sidebar shows for one library. Runs COUNT(*) queries, so
    call it on a worker thread (ADR 2)."""
    return {
        "key": library_key(lib.path),
        "name": lib.name,
        "path": str(lib.path),
        "isTemp": lib.is_temp,
        "nCompounds": lib.n_compounds,
        "nSpectra": lib.n_spectra,
    }


class LibraryBridge(QObject):
    """The set of open libraries, for QML.

    Long operations (open, import, save) run on a :class:`Task`; only one
    runs at a time (``busy``). The manager's dict is only touched on the GUI
    thread: tasks build or save a ``Library`` and hand it back.
    """

    librariesChanged = Signal()
    selectedChanged = Signal()
    busyChanged = Signal()
    progressChanged = Signal()
    errorOccurred = Signal(str)
    infoMessage = Signal(str)
    libraryOpened = Signal(str)  # key
    # Emitted after anything that may change a library's content (P2+ views reload).
    libraryContentChanged = Signal(str)  # key

    def __init__(self, manager: LibraryManager | None = None, parent=None):
        super().__init__(parent)
        self._manager = manager or LibraryManager()
        self._info: dict[str, dict] = {}
        self._status = ""
        self._progress = -1.0

    @property
    def manager(self) -> LibraryManager:
        return self._manager

    # --- busy / status ---------------------------------------------------

    def _begin(self, status: str) -> bool:
        if self._status:
            self.errorOccurred.emit(f"Please wait: {self._status}")
            return False
        self._status = status
        self._progress = -1.0
        self.busyChanged.emit()
        self.progressChanged.emit()
        return True

    def _end(self):
        self._status = ""
        self.busyChanged.emit()

    def _fail(self, message: str):
        self._end()
        self.errorOccurred.emit(message)

    def _on_progress(self, done: int, total: int):
        self._progress = done / total if total else -1.0
        self.progressChanged.emit()

    def _run(self, status: str, fn, *args, on_success, progress=False):
        if not self._begin(status):
            return
        def done(result):
            self._end()
            on_success(result)
        start_task(self, fn, *args, on_success=done, on_error=self._fail,
                   on_progress=self._on_progress if progress else None)

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return bool(self._status)

    @Property(str, notify=busyChanged)
    def statusText(self) -> str:
        return self._status

    @Property(float, notify=progressChanged)
    def progress(self) -> float:
        """0..1, or -1 when the task doesn't report progress."""
        return self._progress

    # --- state for QML ---------------------------------------------------

    @Property(list, notify=librariesChanged)
    def libraries(self) -> list:
        return [self._info[k] for k in self._manager.libraries if k in self._info]

    @Property(str, notify=selectedChanged)
    def selectedKey(self) -> str:
        return self._manager.selected_library_key or ""

    @Property("QVariantMap", notify=selectedChanged)
    def selected(self) -> dict:
        return self._info.get(self.selectedKey, {})

    @Property(bool, notify=librariesChanged)
    def hasUnsaved(self) -> bool:
        return any(i["isTemp"] for i in self._info.values())

    def _opened(self, result: tuple[Library, dict]):
        lib, info = result
        key = self._manager.add(lib)
        self._info[key] = info
        self.librariesChanged.emit()
        self.selectedChanged.emit()
        self.libraryOpened.emit(key)

    # --- slots -------------------------------------------------------------

    @Slot(str)
    def openLibrary(self, url: str):
        path = Path(to_local_path(url))
        key = library_key(path)
        if self._manager.library(key) is not None:
            self.selectLibrary(key)
            return

        def load():
            lib = Library.load_from_db(path)
            return lib, describe(lib)
        self._run(f"Opening {path.name}", load, on_success=self._opened)

    @Slot(str)
    def importMsp(self, url: str):
        path = Path(to_local_path(url))

        def load(progress):
            lib = Library.load_from_msp(path, progress=progress)
            return lib, describe(lib)
        self._run(f"Importing {path.name}", load, on_success=self._opened, progress=True)

    @Slot(str, str)
    def createLibrary(self, url: str, name: str):
        path = Path(to_local_path(url))
        if path.suffix != ".db":
            path = path.with_name(path.name + ".db")

        def create():
            lib = Library.create(path=path, name=name.strip() or path.stem)
            lib.is_temp = False
            return lib, describe(lib)
        self._run(f"Creating {path.name}", create, on_success=self._opened)

    @Slot(str)
    def saveSelectedAs(self, url: str):
        lib = self._manager.selected_library()
        if lib is None:
            self.errorOccurred.emit("No library selected.")
            return
        path = Path(to_local_path(url))
        if path.suffix != ".db":
            path = path.with_name(path.name + ".db")
        if library_key(path) in self._manager.libraries and library_key(path) != self.selectedKey:
            self.errorOccurred.emit(f"{path.name} is open; close it first.")
            return
        old_key = self.selectedKey

        def save():
            lib.save_as_db(path)
            return describe(lib)

        def saved(info):
            self._info.pop(old_key, None)
            key = self._manager.rekey(old_key)
            self._info[key] = info
            self.librariesChanged.emit()
            self.selectedChanged.emit()
        self._run(f"Saving {path.name}", save, on_success=saved)

    @Slot(str)
    def exportSelectedMsp(self, url: str):
        lib = self._manager.selected_library()
        if lib is None:
            return
        path = Path(to_local_path(url))
        if path.suffix.lower() != ".msp":
            path = path.with_name(path.name + ".msp")

        def exported(n):
            self.infoMessage.emit(f"Exported {n} spectra to {path.name}.")
        self._run(f"Exporting {path.name}", write_msp, lib, path, on_success=exported, progress=True)

    @Slot(str)
    def mergeIntoSelected(self, url: str):
        """Copy every compound/spectrum of the library file at ``url`` into
        the selected library (identical spectra are skipped)."""
        lib = self._manager.selected_library()
        if lib is None:
            return
        source = Path(to_local_path(url))
        key = self.selectedKey

        def merged(counts):
            self.libraryContentChanged.emit(key)
            self.refresh(key)
            self.infoMessage.emit(
                f"Merged {source.name}: {counts['spectra_added']} spectra added "
                f"({counts['compounds_added']} new compounds), {counts['spectra_skipped']} identical spectra skipped.")
        self._run(f"Merging {source.name}", lib.merge_from, source, on_success=merged)

    @Slot(str)
    def renameSelected(self, name: str):
        lib = self._manager.selected_library()
        name = name.strip()
        if lib is None or not name:
            return
        key = self.selectedKey

        def renamed(_):
            self._info[key] = {**self._info[key], "name": name}
            self.librariesChanged.emit()
            self.selectedChanged.emit()
        self._run("Renaming", lib.rename_library, name, on_success=renamed)

    @Slot(str)
    def refresh(self, key: str):
        """Re-count a library after its content changed."""
        lib = self._manager.library(key)
        if lib is None:
            return

        def refreshed(info):
            if key in self._info:
                self._info[key] = info
                self.librariesChanged.emit()
                self.selectedChanged.emit()
        start_task(self, describe, lib, on_success=refreshed, on_error=self.errorOccurred.emit)

    @Slot(str)
    def closeLibrary(self, key: str):
        if self.busy:
            self.errorOccurred.emit(f"Please wait: {self._status}")
            return
        self._manager.unload_library(key)
        self._info.pop(library_key(key), None)
        self.librariesChanged.emit()
        self.selectedChanged.emit()

    @Slot(str)
    def selectLibrary(self, key: str):
        try:
            self._manager.select_library(key)
        except KeyError as e:
            self.errorOccurred.emit(str(e))
            return
        self.selectedChanged.emit()

    @Slot(str, result=bool)
    def isOpen(self, path: str) -> bool:
        return self._manager.library(to_local_path(path)) is not None

    @Slot(str, result=bool)
    def fileExists(self, path: str) -> bool:
        return Path(to_local_path(path)).is_file()

    @Slot(str, result=str)
    def toLocalPath(self, url: str) -> str:
        return to_local_path(url)
