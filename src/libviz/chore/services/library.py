from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from libviz.chore.extensions import Base
from libviz.chore.models import LibraryMetadata

VERSION = "1"

class Library:
    def __init__(self, name: str, path: Path):
        self.path = Path(path)
        self.name = name
        self.engine = create_engine(f"sqlite:///{self.path}", future=True)
        self.Session = sessionmaker(bind=self.engine, future=True)
        self.session = None

    # ---------- lifecycle ----------

    def create(self):
        if self.path.exists():
            raise FileExistsError(f"Library already exists: {self.path}")

        Base.metadata.create_all(self.engine)

        with self.session_scope() as session:
            meta = LibraryMetadata(
                name = self.name,
                created_version=VERSION,
                actual_version=VERSION,
            )
            session.add(meta)

    def load(self):
        if not self.path.exists():
            raise FileNotFoundError(self.path)

        self.session = self.Session()
        return self

    def close(self):
        if self.session:
            self.session.close()
            self.session = None

    # ---------- session handling ----------

    def session_scope(self):
        class _SessionContext:
            def __init__(self, lib):
                self.lib = lib
                self.session = None

            def __enter__(self):
                self.session = self.lib.Session()
                return self.session

            def __exit__(self, exc_type, exc, tb):
                if exc:
                    self.session.rollback()
                else:
                    self.session.commit()
                self.session.close()

        return _SessionContext(self)

    # ---------- helpers ----------

    def is_valid(self) -> bool:
        return self.path.exists()
