from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from libviz.services.db.extensions import Base
from libviz.services.db.models import LibraryMetadata
from libviz.services.db.models.compound import Compound
from libviz.services.db.models.spectrum import Spectrum

VERSION = "1"

class Library:
    def __init__(self, name: str, path: Path):
        self.path = path
        self.name = name
        self.engine = create_engine(f"sqlite:///{self.path}", future=True)
        self.Session = sessionmaker(bind=self.engine, future=True)
        self.session = None
        self.n_compounds = 0
        self.n_spectra = 0

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

    @classmethod
    def load_from_db(cls, path: Path):
        """Load a library from an existing database path."""
        if not Path(path).exists():
            raise FileNotFoundError(path)

        # We need the library name from the metadata
        engine = create_engine(f"sqlite:///{path}", future=True)
        Session = sessionmaker(bind=engine, future=True)
        with Session() as session:
            meta = session.query(LibraryMetadata).first()
            if meta is None:
                raise ValueError(f"No metadata found in library at {path}")
            name = meta.name

        # Create instance
        lib = cls(name=name, path=path)
        lib.session = lib.Session()
        lib.n_compounds = lib.session.query(Compound).count()
        lib.n_spectra = lib.session.query(Spectrum).count()
        return lib

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
