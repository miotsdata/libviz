import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from libviz.chore.extensions import Base

@pytest.fixture(scope="module")
def engine():
    db_engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(db_engine)
    return db_engine


@pytest.fixture()
def session(engine):
    Session = sessionmaker(bind=engine, future=True)
    db_session = Session()
    yield db_session
    db_session.rollback()
    db_session.close()
