import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from libviz.core.library import Library
from libviz.core.db.models import LibraryMetadata
from sqlalchemy import inspect
import sqlite3


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