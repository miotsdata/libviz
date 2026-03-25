from pathlib import Path
from libviz.core.library import Library

class LibraryManager:

    def __init__(self):
        self._libraries: dict[str, Library] = {}
        self._selected_library: str = None

    def create_library(self, name: str, path: str | Path):
        path = path if isinstance(path, Path) else Path(path)

        lib = Library.create(name=name, path=path)
        self._libraries[lib.path] = lib

    def load_library_from_msp(self, msp_path: str | Path):
        msp_path = msp_path if isinstance(msp_path, Path) else Path(msp_path)

        lib = Library.loadFromMSP(msp_path)
        self._libraries[lib.path] = lib

    def load_library_from_db(self, path: str | Path):
        path = path if isinstance(path, Path) else Path(path)

        lib = Library.load_from_db(path)
        self._libraries[lib.path] = lib
    
    def save_as_db(self, path: str | Path):
        path = path if isinstance(path, Path) else Path(path)

        lib = self.selected_library()
        if lib is None:
            raise ValueError("No library selected to save.")
        lib.save_as_db(path)

    def unload_library(self, path: str | Path):
        path = path if isinstance(path, Path) else Path(path)

        if path in self._libraries:
            del self._libraries[path]

    def selected_library(self) -> Library | None:
        """Return library object of selected library"""
        if self._selected_library is None:
            return None
        return self._libraries.get(self.selected_library_key)

    @property
    def selected_library_key(self) -> str | None:
        return self._selected_library

    @property
    def has_libraries(self) -> bool:
        return bool(self._libraries)

    @property
    def library_count(self):
        return len(self._libraries)


    def get_identical_spectra(self, spectrum):
        """Return list of spectra that are identical to the given spectrum."""
        if self.selected_library() is None:
            return []
        return self.selected_library().get_identical_spectra(spectrum)
