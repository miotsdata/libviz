import pytest
from pathlib import Path
from sqlalchemy import inspect

from libviz.chore.services.library import Library
from libviz.chore.models import LibraryMetadata
from libviz.chore.extensions import Base

VERSION = "1"

@pytest.fixture
def tmp_library_path(tmp_path):
    return tmp_path / "test_library.db"


def test_create_library(tmp_library_path):
    lib = Library(name="MyLib", path=tmp_library_path)
    lib.create()

    # DB file is created
    assert tmp_library_path.exists()

    # Tables exist
    inspector = inspect(lib.engine)
    tables = inspector.get_table_names()
    assert "library_metadata" in tables

    # Metadata row exists
    session = lib.Session()
    meta = session.query(LibraryMetadata).first()
    assert meta.name == "MyLib"
    assert meta.created_version == VERSION
    assert meta.actual_version == VERSION
    session.close()


def test_create_existing_library_raises(tmp_library_path):
    lib = Library(name="MyLib", path=tmp_library_path)
    lib.create()

    # Creating again should raise
    lib2 = Library(name="OtherLib", path=tmp_library_path)
    with pytest.raises(FileExistsError):
        lib2.create()


def test_load_library(tmp_library_path):
    lib = Library(name="MyLib", path=tmp_library_path)
    lib.create()

    # load existing library
    loaded = Library(name="MyLib", path=tmp_library_path).load()
    assert loaded.session is not None

    # Metadata still exists
    meta = loaded.session.query(LibraryMetadata).first()
    assert meta.name == "MyLib"

    loaded.close()
    assert loaded.session is None


def test_load_nonexistent_library(tmp_path):
    fake_path = tmp_path / "nonexistent.db"
    lib = Library(name="Fake", path=fake_path)
    with pytest.raises(FileNotFoundError):
        lib.load()


def test_session_scope_commit(tmp_library_path):
    lib = Library(name="MyLib", path=tmp_library_path)
    lib.create()

    with lib.session_scope() as session:
        meta = LibraryMetadata(
            name="Extra",
            created_version=VERSION,
            actual_version=VERSION
        )
        session.add(meta)

    # Check it committed
    session = lib.Session()
    assert session.query(LibraryMetadata).filter_by(name="Extra").count() == 1
    session.close()


def test_session_scope_rollback(tmp_library_path):
    lib = Library(name="MyLib", path=tmp_library_path)
    lib.create()

    try:
        with lib.session_scope() as session:
            meta = LibraryMetadata(
                name="RollbackTest",
                created_version=VERSION,
                actual_version=VERSION
            )
            session.add(meta)
            raise ValueError("force rollback")
    except ValueError:
        pass

    # Row should not exist
    session = lib.Session()
    assert session.query(LibraryMetadata).filter_by(name="RollbackTest").count() == 0
    session.close()


def test_close(tmp_library_path):
    lib = Library(name="MyLib", path=tmp_library_path)
    lib.create()
    lib.load()

    lib.close()
    assert lib.session is None


def test_is_valid(tmp_library_path):
    lib = Library(name="MyLib", path=tmp_library_path)
    assert not lib.is_valid()
    lib.create()
    assert lib.is_valid()
