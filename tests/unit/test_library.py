import pytest
from unittest.mock import patch, MagicMock
from libviz.core.db.extensions import Base
from libviz.core.library import Library
from libviz.core.db.models import LibraryMetadata
from sqlalchemy import create_engine, inspect
import sqlite3
from pathlib import Path


# ---- fixtures ----

@pytest.fixture
def saved_library(tmp_path, monkeypatch) -> Path:
    """A real on-disk library with two compounds/spectra."""

    fake_entries = [
        {
            "NAME": "cmpd1",
            "FORMULA": "C6H6",
            "INCHIKEY": "K1",
            "PRECURSORTYPE": "[M+H]+",
            "PRECURSORMZ": "79",
            "IONMODE": "POSITIVE",
            "COLLISIONENERGY": "20",
            "peaks": [(50, 10)]
        },
        {
            "NAME": "cmpd2",
            "FORMULA": "C7H8",
            "INCHIKEY": "K2",
            "PRECURSORTYPE": "[M+H]+",
            "PRECURSORMZ": "93",
            "IONMODE": "POSITIVE",
            "COLLISIONENERGY": "20",
            "peaks": [(60, 5)]
        },
        {
            "NAME": "cmpd3",
            "FORMULA": "C7H81",
            "INCHIKEY": "K22",
            "PRECURSORTYPE": "[M+H]+",
            "PRECURSORMZ": "93",
            "IONMODE": "POSITIVE",
            "COLLISIONENERGY": "20",
            "peaks": [(60, 5)]
        }

    ]

    monkeypatch.setattr("libviz.core.readers.msp_reader.parse_msp", lambda _: fake_entries)

    lib = Library.loadFromMSP(Path("dummy.msp"))
    db_path = Path(tmp_path / "test.db")
    lib.save_as_db(db_path)

    return db_path

@pytest.fixture
def loaded_library(saved_library) -> Library:
    """A Library instance loaded from the saved db, ready to query."""
    return Library.load_from_db(saved_library)


@pytest.fixture
def empty_library(tmp_path, monkeypatch):
    monkeypatch.setattr("libviz.core.readers.msp_reader.parse_msp", lambda _: [])

    db_path = tmp_path / "empty.db"
    lib = Library.loadFromMSP(Path("dummy.msp"))
    lib.save_as_db(db_path)

    return db_path


# ---- TESTS ----
def test_library_init(tmp_path):
    lib_path = tmp_path / "test.db"
    lib = Library(name="TestLib", path=lib_path)

    assert lib.name == "TestLib"
    assert lib.path == lib_path
    assert lib.is_temp is True
    assert lib.n_compounds == 0
    assert lib.n_spectra == 0
    assert lib.engine is not None
    assert callable(lib.session_maker)


def test_create_library_full(tmp_path):
    lib_path = tmp_path / "integration_test.db"

    # Create library (runs actual schema upgrade and adduct population)
    lib = Library.create(path=lib_path, name="MyIntegrationLib")

    # Ensure the library object is returned and DB file exists
    assert isinstance(lib, Library)
    assert lib.path.exists()
    assert lib.name == "MyIntegrationLib"

    # Check LibraryMetadata table has the entry
    with lib.session_scope() as session:
        meta = session.query(LibraryMetadata).filter_by(name="MyIntegrationLib").first()
        assert meta is not None
        assert meta.name == "MyIntegrationLib"

    # Optionally check that expected tables exist (adduct types, etc.)
    inspector = inspect(lib.engine)
    expected_tables = ["library_metadata", "adduct_type", "compound", "spectrum", "spectrum_metadata"]
    for table in expected_tables:
        assert table in inspector.get_table_names()


def test_create_existing_library(tmp_path):
    lib_path = tmp_path / "exists.db"
    lib_path.touch()  # create file to simulate existing library

    with pytest.raises(FileExistsError):
        Library.create(path=lib_path, name="ExistsLib")


def test_create_invalid_path():
    with pytest.raises(TypeError):
        Library.create(path=12345, name="InvalidPath")


def test_session_scope_commit(tmp_path):
    lib_path = tmp_path / "session_test.db"
    lib = Library(name="TestSession", path=lib_path)

    # Use session_scope context to simulate commit
    # Patch the Library's Session to return a dummy session with commit/rollback
    with patch.object(lib, "session_maker", return_value=MagicMock(commit=MagicMock(), rollback=MagicMock(), close=MagicMock())) as mock_session:
        with lib.session_scope() as session:
            assert session is not None
        # Ensure commit and close called
        session.commit.assert_called_once()
        session.close.assert_called_once()


def test_save_as_db_type_error(tmp_path):
    lib = Library(name="TestLib", path=tmp_path / "src.db")

    with pytest.raises(TypeError):
        lib.save_as_db(123)


def test_save_as_db_noname_error(tmp_path):
    lib = Library(name="NONAME", path=tmp_path / "src.db")

    with pytest.raises(ValueError):
        lib.save_as_db(tmp_path / "dest.db")


def test_save_as_db_success(tmp_path):
    src_path = tmp_path / "src.db"
    dest_path = tmp_path / "dest.db"

    # create library and a real sqlite file
    lib = Library.create(name="TestLib", path=src_path)

    with sqlite3.connect(src_path) as conn:
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.execute("INSERT INTO test VALUES (1)")
        conn.commit()

    lib.save_as_db(dest_path)

    # destination file exists
    assert dest_path.exists()

    # library internal state updated
    assert lib.path == dest_path
    assert lib.is_temp is False

    # ensure DB content was copied
    with sqlite3.connect(dest_path) as conn:
        result = conn.execute("SELECT id FROM test").fetchone()
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"

    assert result[0] == 1


def test_save_as_db_flushes_engine(tmp_path):
    src_path = tmp_path / "src.db"
    dest_path = tmp_path / "dest2.db"

    lib = Library.create(name="TestLib", path=src_path)

    with sqlite3.connect(src_path) as conn:
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()

    # open a SQLAlchemy connection to ensure engine exists
    with lib.engine.connect() as conn:
        conn.exec_driver_sql("SELECT 1")

    lib.save_as_db(dest_path)

    assert dest_path.exists()


def test_load_from_db_returns_library(saved_library):
    lib = Library.load_from_db(saved_library)
    assert isinstance(lib, Library)


def test_load_from_db_is_not_temp(saved_library):
    lib = Library.load_from_db(saved_library)
    assert lib.is_temp is False


def test_load_from_db_counts(saved_library):
    lib = Library.load_from_db(saved_library)
    assert lib.n_compounds == 3
    assert lib.n_spectra == 3


def test_load_from_db_name(saved_library):
    lib = Library.load_from_db(saved_library)
    assert lib.name == "In-memory MSP Library"


def test_load_from_db_path(saved_library):
    lib = Library.load_from_db(saved_library)
    assert lib.path == saved_library


def test_load_from_db_empty_library(empty_library):
    lib = Library.load_from_db(empty_library)
    assert lib.n_compounds == 0
    assert lib.n_spectra == 0


def test_load_from_db_wrong_type_raises():
    with pytest.raises(TypeError):
        Library.load_from_db(123)


def test_load_from_db_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        Library.load_from_db(tmp_path / "nonexistent.db")


def test_load_from_db_no_metadata_raises(tmp_path):
    # A valid SQLite file but with no LibraryMetadata row
    db_path = tmp_path / "bare.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    Base.metadata.create_all(engine)  # creates tables but inserts nothing

    with pytest.raises(ValueError, match="No metadata found"):
        Library.load_from_db(db_path)


def test_get_adducts_returns_list(loaded_library):
    adducts = loaded_library.get_adducts()
    assert isinstance(adducts, list)


def test_get_adducts_returns_dicts(loaded_library):
    adducts = loaded_library.get_adducts()
    assert all(isinstance(a, dict) for a in adducts)


def test_get_adducts_dict_keys(loaded_library):
    adducts = loaded_library.get_adducts()
    expected_keys = {"id", "formula", "charge", "delta_mass"}
    assert all(expected_keys == a.keys() for a in adducts)


def test_get_adducts_contains_mh_plus(loaded_library):
    formulas = [a["formula"] for a in loaded_library.get_adducts()]
    assert "[M+H]+" in formulas


def test_get_adduct_delta_returns_float(loaded_library):
    adduct_id = loaded_library.get_adducts()[0]["id"]
    delta = loaded_library.get_adduct_delta(adduct_id)
    assert isinstance(delta, float)


def test_get_adduct_delta_correct_value(loaded_library):
    adducts = loaded_library.get_adducts()
    mh = next(a for a in adducts if a["formula"] == "[M+H]+")
    delta = loaded_library.get_adduct_delta(mh["id"])
    assert delta == pytest.approx(mh["delta_mass"])


def test_get_adduct_delta_invalid_id_raises(loaded_library):
    with pytest.raises(ValueError, match="not found"):
        loaded_library.get_adduct_delta(99999)


def test_rename_library_changes_name(loaded_library):
    old_name = loaded_library.name
    new_name = "RenamedLib"
    loaded_library.rename_library(new_name)

    assert loaded_library.name == new_name

    # Reload library to check name persisted in DB
    reloaded = Library.load_from_db(loaded_library.path)
    assert reloaded.name == new_name