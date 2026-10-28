from pathlib import Path
from libviz.core.library import Library
import pandas as pd


def library_key(path: str | Path) -> str:
    """The one key a library is stored under: its resolved path as a str.

    The bridge hands paths over from QML as strings while core code uses
    ``Path``; normalising both to one form is what keeps select/unload from
    silently missing.
    """
    return str(Path(path).resolve())


class LibraryManager:

    def __init__(self):
        self._libraries: dict[str, Library] = {}
        self._selected_library: str | None = None

    def add(self, lib: Library) -> str:
        """Register an already-open library and select it."""
        key = library_key(lib.path)
        if key in self._libraries:
            self._libraries[key].close()
        self._libraries[key] = lib
        self._selected_library = key
        return key

    def create_library(self, name: str, path: str | Path) -> str:
        return self.add(Library.create(name=name, path=Path(path)))

    def load_library_from_msp(self, msp_path: str | Path) -> str:
        return self.add(Library.load_from_msp(Path(msp_path)))

    def load_library_from_db(self, path: str | Path) -> str:
        key = library_key(path)
        if key in self._libraries:
            self._selected_library = key
            return key
        return self.add(Library.load_from_db(Path(path)))

    def save_as_db(self, path: str | Path) -> str:
        """Save the selected library to ``path``; it is re-keyed there."""
        lib = self.selected_library()
        if lib is None:
            raise ValueError("No library selected to save.")
        old_key = self._selected_library
        lib.save_as_db(Path(path))
        return self.rekey(old_key)

    def rekey(self, old_key: str) -> str:
        """Re-register a library whose ``path`` changed (after a save)."""
        lib = self._libraries.pop(old_key)
        key = library_key(lib.path)
        self._libraries[key] = lib
        self._selected_library = key
        return key

    def unload_library(self, path: str | Path):
        lib = self._libraries.pop(library_key(path), None)
        if lib is None:
            return
        lib.close()
        if self._selected_library == library_key(path):
            self._selected_library = next(iter(self._libraries), None)

    def select_library(self, path: str | Path):
        key = library_key(path)
        if key not in self._libraries:
            raise KeyError(f"Library not loaded: {path}")
        self._selected_library = key

    def selected_library(self) -> Library | None:
        """Return library object of selected library"""
        if self._selected_library is None:
            return None
        return self._libraries.get(self._selected_library)

    def library(self, path: str | Path) -> Library | None:
        return self._libraries.get(library_key(path))

    @property
    def libraries(self) -> dict[str, Library]:
        return dict(self._libraries)

    @property
    def selected_library_key(self) -> str | None:
        return self._selected_library

    @property
    def has_libraries(self) -> bool:
        return bool(self._libraries)

    @property
    def library_count(self):
        return len(self._libraries)


    def get_identical_spectra(self,
                              precursor_mz: float,
                              polarity: str,
                              hash_ref: str,
                              ppm_tolerance: float,
                              return_pd: bool = False) -> list[dict] | pd.DataFrame:
        """Return list of spectra that are identical to the given spectrum."""
        identical_spectra = []
        for lib in self._libraries.values():
            res: list[dict] = lib.get_identical_spectra_compounds_by_spectrum_info(
                precursor_mz=precursor_mz,
                polarity=polarity,
                hash_ref=hash_ref,
                ppm_tolerance=ppm_tolerance,
            )
            for r in res:
                r['library_path'] = lib.path
                identical_spectra.append(r)

        if return_pd:
            return pd.DataFrame(identical_spectra)
        return identical_spectra

    def get_spectra_in_mz_range(self,
                              mz_min: float,
                              mz_max: float,
                              polarity: str | None = None,
                              return_pd: bool = False) -> list[dict] | pd.DataFrame:
        """Return list of spectra that are in the given m/z range."""
        spectra = []
        for lib in self._libraries.values():
            res: list[dict] = lib.get_spectra_in_mz_range(
                mz_min=mz_min,
                mz_max=mz_max,
                polarity=polarity
            )
            for r in res:
                r['library_path'] = lib.path
                spectra.append(r)

        if return_pd:
            return pd.DataFrame(spectra)
        return spectra


    def convert_from_msp_to_db(self, msp_path: str | Path, default_precursor_type: str = "[M+H]+", output_path: str | Path | None = None) -> Path:
        msp_path = Path(msp_path)

        lib = Library.load_from_msp(msp_path, default_precursor_type=default_precursor_type)
        db_path = Path(output_path) if output_path is not None else msp_path.with_suffix('.db')
        lib.save_as_db(db_path)
        lib.close()
        return db_path
