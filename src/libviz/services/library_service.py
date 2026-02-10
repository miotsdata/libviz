from pathlib import Path
from libviz.services.classes import Library
from PySide6.QtCore import Property, QObject, Signal, Slot # pylint: disable=no-name-in-module

class LibraryService(QObject):
    libraryChanged = Signal(str, int, int)

    def __init__(self):
        super().__init__()
        self._library = None

    @Slot(str, str)
    def create(self, name: str, path: str):
        # Optional validation
        if not name.strip() or not path.strip():
            raise ValueError("Name and path are required")
        lib = Library(name=name, path=Path(path))
        lib.create()  # may raise FileExistsError
        self._library = lib
        self.libraryChanged.emit(lib.name, lib.n_compounds, lib.n_spectra)

    @Slot()
    def refresh_library(self):
        if self._library:
            self.libraryChanged.emit(
                self._library.name, self._library.n_compounds, self._library.n_spectra
            )

    @Property(str)
    def name(self):
        return self._library.name if self._library else ""

    @Property(int)
    def n_compounds(self):
        return self._library.n_compounds if self._library else 0

    @Property(int)
    def n_spectra(self):
        return self._library.n_spectra if self._library else 0
