import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from libviz.core.db import Base


@pytest.fixture(scope="module")
def engine():
    db_engine = create_engine("sqlite:///:memory:", future=True)

    # Enable SQLite foreign key enforcement
    @event.listens_for(db_engine, "connect")
    def enable_sqlite_fk(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=MEMORY")
        cursor.execute("PRAGMA synchronous=OFF")
        cursor.close()

    Base.metadata.create_all(db_engine)
    return db_engine


@pytest.fixture()
def session(engine):
    Session = sessionmaker(bind=engine, future=True)
    db_session = Session()
    yield db_session
    db_session.rollback()
    db_session.close()

@pytest.fixture(scope="module")
def reader_session(tmp_path):
    db = tmp_path / "test.db"

    engine = create_engine(f"sqlite:///{db}", future=True)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)

    with Session() as s:
        yield s
