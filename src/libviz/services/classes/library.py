from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import numpy as np
import logging
import tempfile

from libviz.services.db.extensions import Base
from libviz.services.db.models import Compound, Spectrum, LibraryMetadata, SpectrumMetadata, AdductType
from libviz.services.db.models.adducts_type import populate_adduct_types
from libviz.services.db.models.spectrum import calculate_spectrum_hash
from libviz.utils import parse_msp, calculate_exact_mass, infer_precursor_delta

logger = logging.getLogger(__name__)

VERSION = "1"

class Library:
    def __init__(self, name: str, path: Path):
        self.path = path
        self.name = name
        self.engine = create_engine(f"sqlite:///{self.path}", future=True)
        self.Session = sessionmaker(bind=self.engine, future=True)
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

            populate_adduct_types(session)


    @classmethod
    def load_from_db(cls, path: Path):
        """Load a library from an existing database path."""
        if not Path(path).exists():
            raise FileNotFoundError(path)

        # We need the library name from the metadata
        engine = create_engine(f"sqlite:///{path}", future=True)
        session_made = sessionmaker(bind=engine, future=True)
        with session_made() as session:
            meta = session.query(LibraryMetadata).first()
            if meta is None:
                raise ValueError(f"No metadata found in library at {path}")
            name = meta.name

        # Create instance
        lib = cls(name=name, path=path)
        session = lib.Session()
        lib.n_compounds = session.query(Compound).count()
        lib.n_spectra = session.query(Spectrum).count()
        return lib

    @classmethod
    def loadFromMSP(cls, msp_path: str):
        """
        Load a library from an MSP file into an in-memory SQLite database.
        Returns a Library instance.
        """

        # Create in-memory SQLite DB
        # Create temporary DB file
        tmp_file = tempfile.NamedTemporaryFile(
            suffix=".db",
            delete=False
        )
        tmp_file.close()

        db_path = tmp_file.name
        print(db_path)

        engine = create_engine(
            f"sqlite:///{db_path}",
            future=True
        )

        Session_db = sessionmaker(
            bind=engine,
            expire_on_commit=False
        )
        Base.metadata.create_all(engine)  # create tables

        session = Session_db()

        # Create metadata entry
        meta = LibraryMetadata(name="In-memory MSP Library", created_version=VERSION, actual_version=VERSION)
        session.add(meta)
        session.commit()

        populate_adduct_types(session)

        # Parse MSP file
        parse_msp_generator = parse_msp(msp_path)

        for i, compound_data in enumerate(parse_msp_generator, 1):
            cls._insert_msp_entry(session, compound_data)
            if i % 500 == 0:
                session.commit()
        session.commit()

        # Create Library instance
        lib = cls(name="NONAME", path=db_path)
        lib.engine = engine
        lib.Session = Session_db
        lib.n_compounds = session.query(Compound).count()
        lib.n_spectra = session.query(Spectrum).count()

        session.close()

        return lib

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

    @staticmethod
    def _insert_msp_entry(session: Session, entry):
        
        # ---------- prepare mz/intensity ----------
        mz = np.array([float(m) for m, _ in entry.get("peaks", [])], dtype=np.float32)
        intensity = np.array([float(i) for _, i in entry.get("peaks", [])], dtype=np.float32)

        # sort to make hash deterministic
        order = np.argsort(mz)
        mz = mz[order]
        intensity = intensity[order]

        spectrum_hash = calculate_spectrum_hash(mz, intensity)

        # ---------- precursor type ----------
        adduct_type_formula = entry.get("PRECURSORTYPE")
        adduct_type = session.query(AdductType).filter_by(
            formula=adduct_type_formula
        ).one_or_none()

        if adduct_type is None:
            try:
                charge, delta = infer_precursor_delta(adduct_type_formula)
            except ValueError:
                # Skip unusual precursors
                logger.warning("Skipping precursor: %s", adduct_type_formula)
                return
            adduct_type = AdductType(
                formula=adduct_type_formula,
                delta_mass=delta,
                charge=charge
            )
            session.add(adduct_type)
            session.flush()
        

        # ---------- check if spectrum already exists ----------
        existing = session.query(Spectrum).filter_by(
            adduct_type_id=adduct_type.id,
            polarity=entry.get("IONMODE"),
            collision_energy = float(entry.get("COLLISIONENERGY") or 0.0),
            spectrum_hash=spectrum_hash
        ).one_or_none()

        if existing:
            # spectrum already in DB → skip everything
            return existing

        # ---------- compound ----------
        inchikey = entry.get("INCHIKEY")
        compound = None
        if inchikey:
            compound = session.query(Compound).filter_by(inchikey=inchikey).one_or_none()


        if compound is None:
            compound = Compound(
                name=entry.get("NAME"),
                formula=entry.get("FORMULA"),
                inchikey=inchikey,
                exact_mass=float(entry["EXACTMASS"]) if "EXACTMASS" in entry else calculate_exact_mass(entry.get("FORMULA")),
            )
            session.add(compound)
            session.flush()  # get compound.id

        # ---------- peaks / spectrum ----------
        spectrum = Spectrum.from_arrays(
            compound_id=compound.id,
            precursor_mz=float(entry["PRECURSORMZ"]),
            adduct_type_id=adduct_type.id,
            polarity=entry.get("IONMODE"),
            collision_energy=float(entry.get("COLLISIONENERGY") or 0.0),
            mz=mz,
            intensity=intensity,
        )

        session.add(spectrum)
        session.flush()

        # ---------- spectrum metadata ----------
        known_keys = {
            "NAME", "FORMULA", "INCHIKEY", "EXACTMASS",
            "PRECURSORMZ", "PRECURSORTYPE",
            "IONMODE", "COLLISIONENERGY", "peaks"
        }

        for key, value in entry.items():
            if key not in known_keys:
                session.add(
                    SpectrumMetadata(
                        spectrum_id=spectrum.id,
                        key=key,
                        value=str(value)
                    )
                )

        return spectrum

    def get_adducts(self):
        with self.session_scope() as session:
            adducts = session.query(AdductType).all()
            return [{"id": a.id, "formula": a.formula, "charge": a.charge, 
                     "delta_mass": a.delta_mass} for a in adducts]

    def get_adduct_delta(self, adduct_id: int):
        with self.session_scope() as session:
            adduct = session.query(AdductType).filter_by(id=adduct_id).one_or_none()
            if adduct is None:
                raise ValueError(f"Adduct with ID {adduct_id} not found")
            return adduct.delta_mass
