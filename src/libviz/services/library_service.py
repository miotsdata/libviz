from pathlib import Path
from libviz.services.classes import Library
from PySide6.QtCore import Property, QObject, Signal, Slot # pylint: disable=no-name-in-module

class LibraryService(QObject):
    libraryChanged = Signal(str, int, int)
    librarySaved = Signal()

    def __init__(self):
        super().__init__()
        self._library = None
        self._connection_name = "library_connection"
        self._db_path = None

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

    @Slot()
    def load(self, path: str):
        self._library = Library.load_from_db(path=Path(path))

    @Slot()
    def loadFromMSP(self, path: str):
        self._library = Library.loadFromMSP(path)
        self.libraryChanged.emit(
                self._library.name, self._library.n_compounds, self._library.n_spectra
            )

    @Property(str, notify=libraryChanged)
    def name(self):
        return self._library.name if self._library else ""

    @Property(int, notify=libraryChanged)
    def n_compounds(self):
        return self._library.n_compounds if self._library else 0

    @Property(int, notify=libraryChanged)
    def n_spectra(self):
        return self._library.n_spectra if self._library else 0
    
    @Property(str)
    def db_path(self):
        return self._library.path if self._library else ""
    
    @Property(str)
    def connection_name(self):
        return self._connection_name if self._connection_name else ""

    def get_adducts(self):
        if self._library:
            return self._library.get_adducts()
        return []

    def get_adduct_delta(self, adduct_id: int):
        if self._library:
            return self._library.get_adduct_delta(adduct_id)
        raise ValueError("No library loaded")
    
    def add_spectra_to_library(self, compound_name: str, compound_formula: str, inchikey: str, spectra_info: dict, adduct_id: float):
        if not self._library:
            raise ValueError("No library loaded")
        self._library.add_spectra(compound_name, compound_formula, inchikey, spectra_info, adduct_id)
        self.libraryChanged.emit(self._library.name, self._library.n_compounds, self._library.n_spectra)

    @Slot(str)
    def save_as_db(self, path: str):
        if "file://" in path:
            path = path.replace("file://", "")
        self._library.save_as_db(path)
        self.librarySaved.emit()
