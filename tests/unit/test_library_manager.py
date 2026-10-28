from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from libviz.core import LibraryManager

# pylint: disable=protected-access, redefined-outer-name, unused-argument, no-self-use

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_mock_library(path: Path = Path("/fake/lib.db"), name: str = "TestLib"):
    lib = MagicMock()
    lib.path = path
    lib.name = name
    return lib

def _make_mock_library(path: str, results: list[dict]) -> MagicMock:
    """A mock Library that returns `results` from get_identical_spectra_compounds_by_spectrum_info."""
    lib = MagicMock()
    lib.path = path
    lib.get_identical_spectra_compounds_by_spectrum_info.return_value = results
    return lib


PRECURSOR_MZ = 100.0
POLARITY = "positive"
HASH_REF = "abc123"
PPM = 5.0

@pytest.fixture
def mock_manager() -> LibraryManager:
    return LibraryManager()


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------

class TestInit:
    def test_libraries_empty_on_init(self):
        mgr = LibraryManager()
        assert mgr._libraries == {}

    def test_selected_library_none_on_init(self):
        mgr = LibraryManager()
        assert mgr._selected_library is None


# ---------------------------------------------------------------------------
# create_library
# ---------------------------------------------------------------------------

class TestCreateLibrary:
    @patch("libviz.core.managers.library_manager.Library")
    def test_creates_library_and_stores_it(self, MockLibrary):
        lib = make_mock_library()
        MockLibrary.create.return_value = lib

        mgr = LibraryManager()
        mgr.create_library("TestLib", "/fake/lib.db")

        MockLibrary.create.assert_called_once_with(name="TestLib", path=Path("/fake/lib.db"))
        assert mgr._libraries[str(lib.path)] is lib

    @patch("libviz.core.managers.library_manager.Library")
    def test_accepts_path_object(self, MockLibrary):
        lib = make_mock_library()
        MockLibrary.create.return_value = lib

        mgr = LibraryManager()
        mgr.create_library("TestLib", Path("/fake/lib.db"))

        MockLibrary.create.assert_called_once_with(name="TestLib", path=Path("/fake/lib.db"))

    @patch("libviz.core.managers.library_manager.Library")
    def test_converts_string_to_path(self, MockLibrary):
        lib = make_mock_library()
        MockLibrary.create.return_value = lib

        mgr = LibraryManager()
        mgr.create_library("TestLib", "/fake/lib.db")

        _, kwargs = MockLibrary.create.call_args
        assert isinstance(kwargs["path"], Path)

    @patch("libviz.core.managers.library_manager.Library")
    def test_propagates_file_exists_error(self, MockLibrary):
        MockLibrary.create.side_effect = FileExistsError("Library already exists")

        mgr = LibraryManager()
        with pytest.raises(FileExistsError):
            mgr.create_library("TestLib", "/fake/lib.db")


# ---------------------------------------------------------------------------
# load_library_from_msp
# ---------------------------------------------------------------------------

class TestLoadLibraryFromMsp:
    @patch("libviz.core.managers.library_manager.Library")
    def test_loads_and_stores_library(self, MockLibrary):
        lib = make_mock_library()
        MockLibrary.load_from_msp.return_value = lib

        mgr = LibraryManager()
        mgr.load_library_from_msp("/fake/lib.msp")

        MockLibrary.load_from_msp.assert_called_once_with(Path("/fake/lib.msp"))
        assert mgr._libraries[str(lib.path)] is lib

    @patch("libviz.core.managers.library_manager.Library")
    def test_accepts_path_object(self, MockLibrary):
        lib = make_mock_library()
        MockLibrary.load_from_msp.return_value = lib

        mgr = LibraryManager()
        mgr.load_library_from_msp(Path("/fake/lib.msp"))

        MockLibrary.load_from_msp.assert_called_once_with(Path("/fake/lib.msp"))

    @patch("libviz.core.managers.library_manager.Library")
    def test_converts_string_to_path(self, MockLibrary):
        lib = make_mock_library()
        MockLibrary.load_from_msp.return_value = lib

        mgr = LibraryManager()
        mgr.load_library_from_msp("/fake/lib.msp")

        args, _ = MockLibrary.load_from_msp.call_args
        assert isinstance(args[0], Path)

    @patch("libviz.core.managers.library_manager.Library")
    def test_propagates_exceptions(self, MockLibrary):
        MockLibrary.load_from_msp.side_effect = FileNotFoundError("File not found")

        mgr = LibraryManager()
        with pytest.raises(FileNotFoundError):
            mgr.load_library_from_msp("/fake/lib.msp")


# ---------------------------------------------------------------------------
# load_library_from_db
# ---------------------------------------------------------------------------

class TestLoadLibraryFromDb:
    @patch("libviz.core.managers.library_manager.Library")
    def test_loads_and_stores_library(self, MockLibrary):
        lib = make_mock_library()
        MockLibrary.load_from_db.return_value = lib

        mgr = LibraryManager()
        mgr.load_library_from_db("/fake/lib.db")

        MockLibrary.load_from_db.assert_called_once_with(Path("/fake/lib.db"))
        assert mgr._libraries[str(lib.path)] is lib

    @patch("libviz.core.managers.library_manager.Library")
    def test_accepts_path_object(self, MockLibrary):
        lib = make_mock_library()
        MockLibrary.load_from_db.return_value = lib

        mgr = LibraryManager()
        mgr.load_library_from_db(Path("/fake/lib.db"))

        MockLibrary.load_from_db.assert_called_once_with(Path("/fake/lib.db"))

    @patch("libviz.core.managers.library_manager.Library")
    def test_converts_string_to_path(self, MockLibrary):
        lib = make_mock_library()
        MockLibrary.load_from_db.return_value = lib

        mgr = LibraryManager()
        mgr.load_library_from_db("/fake/lib.db")

        args, _ = MockLibrary.load_from_db.call_args
        assert isinstance(args[0], Path)

    @patch("libviz.core.managers.library_manager.Library")
    def test_propagates_exceptions(self, MockLibrary):
        MockLibrary.load_from_db.side_effect = FileNotFoundError("DB not found")

        mgr = LibraryManager()
        with pytest.raises(FileNotFoundError):
            mgr.load_library_from_db("/nonexistent.db")


# ---------------------------------------------------------------------------
# save_as_db
# ---------------------------------------------------------------------------

class TestSaveAsDb:
    def test_calls_save_on_selected_library(self):
        lib = make_mock_library()
        mgr = LibraryManager()
        mgr._libraries[str(lib.path)] = lib
        mgr._selected_library = str(lib.path)

        mgr.save_as_db("/output/saved.db")

        lib.save_as_db.assert_called_once_with(Path("/output/saved.db"))

    def test_accepts_path_object(self):
        lib = make_mock_library()
        mgr = LibraryManager()
        mgr._libraries[str(lib.path)] = lib
        mgr._selected_library = str(lib.path)

        mgr.save_as_db(Path("/output/saved.db"))

        lib.save_as_db.assert_called_once_with(Path("/output/saved.db"))

    def test_converts_string_to_path(self):
        lib = make_mock_library()
        mgr = LibraryManager()
        mgr._libraries[str(lib.path)] = lib
        mgr._selected_library = str(lib.path)

        mgr.save_as_db("/output/saved.db")

        args, _ = lib.save_as_db.call_args
        assert isinstance(args[0], Path)

    def test_raises_value_error_when_no_library_selected(self):
        mgr = LibraryManager()
        with pytest.raises(ValueError, match="No library selected"):
            mgr.save_as_db("/output/saved.db")


# ---------------------------------------------------------------------------
# selected_library
# ---------------------------------------------------------------------------

class TestSelectedLibrary:
    def test_returns_none_when_nothing_selected(self):
        mgr = LibraryManager()
        assert mgr.selected_library() is None

    def test_returns_correct_library_when_selected(self):
        lib = make_mock_library(Path("/fake/lib.db"))
        mgr = LibraryManager()
        mgr._libraries[str(lib.path)] = lib
        mgr._selected_library = str(lib.path)

        assert mgr.selected_library() is lib

    def test_returns_none_when_selected_key_not_in_libraries(self):
        # e.g. after a library is removed but _selected_library is not cleared
        mgr = LibraryManager()
        mgr._selected_library = Path("/ghost/lib.db")

        assert mgr.selected_library() is None


# ---------------------------------------------------------------------------
# selected_library_key
# ---------------------------------------------------------------------------

class TestSelectedLibraryKey:
    def test_returns_none_by_default(self):
        mgr = LibraryManager()
        assert mgr.selected_library_key is None

    def test_returns_path_when_set(self):
        path = Path("/fake/lib.db")
        mgr = LibraryManager()
        mgr._selected_library = path

        assert mgr.selected_library_key == path


# ---------------------------------------------------------------------------
# has_libraries
# ---------------------------------------------------------------------------

class TestHasLibraries:
    def test_false_when_empty(self):
        mgr = LibraryManager()
        assert mgr.has_libraries is False

    def test_true_when_library_present(self):
        lib = make_mock_library()
        mgr = LibraryManager()
        mgr._libraries[str(lib.path)] = lib

        assert mgr.has_libraries is True


# ---------------------------------------------------------------------------
# library_count
# ---------------------------------------------------------------------------

class TestLibraryCount:
    def test_zero_on_init(self):
        mgr = LibraryManager()
        assert mgr.library_count == 0

    def test_reflects_number_of_loaded_libraries(self):
        lib_a = make_mock_library(Path("/fake/a.db"))
        lib_b = make_mock_library(Path("/fake/b.db"))
        mgr = LibraryManager()
        mgr._libraries[str(lib_a.path)] = lib_a
        mgr._libraries[str(lib_b.path)] = lib_b

        assert mgr.library_count == 2


# ---------------------------------------------------------------------------
# Unload Library
# ---------------------------------------------------------------------------
class TestUnloadLibrary:
    def test_removes_library_by_string_path(self):
        lib = make_mock_library(Path("/fake/lib.db"))
        mgr = LibraryManager()
        mgr._libraries[str(lib.path)] = lib

        mgr.unload_library("/fake/lib.db")

        assert str(lib.path) not in mgr._libraries

    def test_removes_library_by_path_object(self):
        lib = make_mock_library(Path("/fake/lib.db"))
        mgr = LibraryManager()
        mgr._libraries[str(lib.path)] = lib

        mgr.unload_library(Path("/fake/lib.db"))

        assert str(lib.path) not in mgr._libraries

    def test_no_error_when_path_not_present(self):
        mgr = LibraryManager()
        # should silently do nothing
        mgr.unload_library("/nonexistent.db")

    def test_does_not_remove_other_libraries(self):
        lib_a = make_mock_library(Path("/fake/a.db"))
        lib_b = make_mock_library(Path("/fake/b.db"))
        mgr = LibraryManager()
        mgr._libraries[str(lib_a.path)] = lib_a
        mgr._libraries[str(lib_b.path)] = lib_b

        mgr.unload_library("/fake/a.db")

        assert str(lib_b.path) in mgr._libraries

    def test_library_count_decrements(self):
        lib = make_mock_library(Path("/fake/lib.db"))
        mgr = LibraryManager()
        mgr._libraries[str(lib.path)] = lib

        mgr.unload_library("/fake/lib.db")

        assert mgr.library_count == 0

    def test_has_libraries_false_after_unloading_last(self):
        lib = make_mock_library(Path("/fake/lib.db"))
        mgr = LibraryManager()
        mgr._libraries[str(lib.path)] = lib

        mgr.unload_library("/fake/lib.db")

        assert mgr.has_libraries is False


class TestGetIdenticalSpectra:

    # --- delegation ---

    def test_calls_each_library_with_correct_args(self, mock_manager):
        lib_a = _make_mock_library("/a.db", [])
        lib_b = _make_mock_library("/b.db", [])
        mock_manager._libraries = {"a": lib_a, "b": lib_b}

        mock_manager.get_identical_spectra(PRECURSOR_MZ, POLARITY, HASH_REF, PPM)

        for lib in (lib_a, lib_b):
            lib.get_identical_spectra_compounds_by_spectrum_info.assert_called_once_with(
                precursor_mz=PRECURSOR_MZ,
                polarity=POLARITY,
                hash_ref=HASH_REF,
                ppm_tolerance=PPM,
            )

    # --- aggregation ---

    def test_returns_empty_when_no_libraries(self, mock_manager):
        mock_manager._libraries = {}
        result = mock_manager.get_identical_spectra(PRECURSOR_MZ, POLARITY, HASH_REF, PPM)
        assert result == []

    def test_returns_empty_when_no_matches(self, mock_manager):
        mock_manager._libraries = {"a": _make_mock_library("/a.db", [])}
        result = mock_manager.get_identical_spectra(PRECURSOR_MZ, POLARITY, HASH_REF, PPM)
        assert result == []

    def test_returns_matches_from_single_library(self, mock_manager):
        hits = [{"id": 1, "name": "aspirin", "formula": "C9H8O4",
                 "inchikey": "KEY1", "spectrum_id": 10}]
        mock_manager._libraries = {"a": _make_mock_library("/a.db", hits)}

        result = mock_manager.get_identical_spectra(PRECURSOR_MZ, POLARITY, HASH_REF, PPM)

        assert len(result) == 1

    def test_aggregates_matches_across_libraries(self, mock_manager):
        hits_a = [{"id": 1, "name": "aspirin", "formula": "C9H8O4",
                   "inchikey": "KEY1", "spectrum_id": 10}]
        hits_b = [{"id": 2, "name": "ibuprofen", "formula": "C13H18O2",
                   "inchikey": "KEY2", "spectrum_id": 20},
                  {"id": 3, "name": "caffeine", "formula": "C8H10N4O2",
                   "inchikey": "KEY3", "spectrum_id": 30}]
        mock_manager._libraries = {
            "a": _make_mock_library("/a.db", hits_a),
            "b": _make_mock_library("/b.db", hits_b),
        }

        result = mock_manager.get_identical_spectra(PRECURSOR_MZ, POLARITY, HASH_REF, PPM)

        assert len(result) == 3

    # --- library_path injection ---

    def test_injects_library_path_into_each_result(self, mock_manager):
        hits = [{"id": 1, "name": "aspirin", "formula": "C9H8O4",
                 "inchikey": "KEY1", "spectrum_id": 10}]
        mock_manager._libraries = {"a": _make_mock_library("/a.db", hits)}

        result = mock_manager.get_identical_spectra(PRECURSOR_MZ, POLARITY, HASH_REF, PPM)

        assert result[0]["library_path"] == "/a.db"

    def test_library_path_correct_across_multiple_libraries(self, mock_manager):
        mock_manager._libraries = {
            "a": _make_mock_library("/a.db", [{"id": 1, "name": "x",
                                               "formula": "C1", "inchikey": "K1",
                                               "spectrum_id": 1}]),
            "b": _make_mock_library("/b.db", [{"id": 2, "name": "y",
                                               "formula": "C2", "inchikey": "K2",
                                               "spectrum_id": 2}]),
        }

        result = mock_manager.get_identical_spectra(PRECURSOR_MZ, POLARITY, HASH_REF, PPM)

        by_name = {r["name"]: r for r in result}
        assert by_name["x"]["library_path"] == "/a.db"
        assert by_name["y"]["library_path"] == "/b.db"

    def test_does_not_mutate_original_dicts(self, mock_manager):
        """The loop adds library_path in-place — verify the caller's original list is unchanged
        only if the implementation is ever changed to copy. For now, documents current behaviour."""
        original = {"id": 1, "name": "aspirin", "formula": "C9H8O4",
                    "inchikey": "KEY1", "spectrum_id": 10}
        mock_manager._libraries = {"a": _make_mock_library("/a.db", [original])}

        mock_manager.get_identical_spectra(PRECURSOR_MZ, POLARITY, HASH_REF, PPM)

        # Current implementation mutates in-place — document that it does
        assert "library_path" in original

# ---------------------------------------------------------------------------
# Key normalisation (str from QML vs Path from core)
# ---------------------------------------------------------------------------

class TestKeys:
    def test_select_and_unload_with_mixed_path_types(self, tmp_path):
        mgr = LibraryManager()
        key = mgr.create_library("Lib", tmp_path / "lib.db")

        mgr.select_library(str(tmp_path / "lib.db"))
        assert mgr.selected_library_key == key

        mgr.unload_library(str(tmp_path / "lib.db"))
        assert mgr.library_count == 0
        assert mgr.selected_library_key is None

    def test_select_unknown_raises(self):
        with pytest.raises(KeyError):
            LibraryManager().select_library("/nope.db")

    def test_save_rekeys_temp_library(self, tmp_path, monkeypatch):
        monkeypatch.setattr("libviz.core.readers.msp_reader.parse_msp", lambda *_: [])
        mgr = LibraryManager()
        temp_key = mgr.load_library_from_msp(tmp_path / "x.msp")
        temp_file = Path(temp_key)

        new_key = mgr.save_as_db(tmp_path / "saved.db")

        assert new_key == str((tmp_path / "saved.db").resolve())
        assert list(mgr.libraries) == [new_key]
        assert not temp_file.exists()  # temp DB cleaned up
