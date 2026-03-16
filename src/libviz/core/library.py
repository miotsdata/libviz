from pathlib import Path
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import sessionmaker
import logging
import tempfile
import sqlite3

from libviz.core.db.migrations import upgrade_library_schema
from libviz.core.readers import MSPReader

from libviz.core.db.models import (
    Compound,
    Spectrum,
    LibraryMetadata,
    AdductType,
    populate_adduct_types
)

logger = logging.getLogger(__name__)

class Library:
    def __init__(self, name: str, path: Path):
        self.path: Path = path
        self.is_temp: bool = True
        self.name: str = name
        self.engine: Engine = create_engine(f"sqlite:///{self.path}", future=True)
        self.session_maker = sessionmaker(bind=self.engine, future=True)
        self.n_compounds = 0
        self.n_spectra = 0

        @event.listens_for(self.engine, "connect")
        def enable_sqlite_fk(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=MEMORY")
            cursor.execute("PRAGMA synchronous=OFF")
            cursor.close()

    @classmethod
    def create(cls, path: Path, name: str):
        if not isinstance(path, Path):
            raise TypeError(f"Path should be a Path object, found {type(path).__name__}")

        if path.exists():
            raise FileExistsError(f"Library already exists at path {str(path)}")

        lib = cls(name = name, path=path)

        # upgrade schema (creates tables if DB is new, applies migrations if existing)
        upgrade_library_schema(lib.path)

        with lib.session_scope() as session:
            meta = LibraryMetadata(
                name = name
            )
            session.add(meta)
            session.commit()

            populate_adduct_types(session)
        return lib


    # ---------- session handling ----------
    def session_scope(self):
        class _SessionContext:
            def __init__(self, lib):
                self.lib = lib
                self.session = None

            def __enter__(self):
                self.session = self.lib.session_maker()
                return self.session

            def __exit__(self, exc_type, exc, tb):
                if exc:
                    self.session.rollback()
                else:
                    self.session.commit()
                self.session.close()

        return _SessionContext(self)


    # ---------- Saving ----------
    def save_as_db(self, path: Path):
        logger.debug("Saving library to %s", path)

        if not isinstance(path, Path):
            raise TypeError(f"Path should be a Path object, found {type(path).__name__}")

        if self.name == "NONAME":
            raise ValueError("Name cannot be NONAME. Please rename the library with the rename method.")

        # ensure WAL is flushed
        with self.engine.connect() as conn:
            conn.exec_driver_sql("PRAGMA wal_checkpoint(FULL);")

        # close all pooled connections
        self.engine.dispose()

        src = sqlite3.connect(self.path)
        dest = sqlite3.connect(str(path))

        try:
            src.backup(dest)
        finally:
            dest.close()
            src.close()

        self.path = Path(path)
        self.is_temp = False
        logger.debug("Saved library to %s", path)


    # ---------- Loading ----------
    @classmethod
    def loadFromMSP(cls, msp_path: str):

        tmp_file = tempfile.NamedTemporaryFile(
            suffix=".db",
            delete=True
        )
        tmp_file.close()

        db_path = Path(tmp_file.name)

        lib = cls.create(name="In-memory MSP Library", path=db_path)

        with lib.session_scope() as session:

            reader = MSPReader(session)
            reader.import_file(msp_path)

            lib.n_compounds = session.query(Compound).count()
            lib.n_spectra = session.query(Spectrum).count()

        lib.is_temp = True

        return lib


    @classmethod
    def load_from_db(cls, path: Path):
        if not isinstance(path, Path):
            raise TypeError(f"Path should be a Path object, found {type(path).__name__}")

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
        lib = cls(name=name, path=Path(path))
        session = lib.session_maker()
        lib.n_compounds = session.query(Compound).count()
        lib.n_spectra = session.query(Spectrum).count()
        lib.is_temp = False
        return lib
    
    # ---------- Setters ----------
    def rename_library(self, new_name: str):
        logger.debug("Renaming library from %s to %s", self.name, new_name)
        with self.session_scope() as session:
            meta = session.query(LibraryMetadata).first()
            if meta is None:
                raise ValueError("No metadata found in library")
            meta.name = new_name
            session.commit()
        self.name = new_name
    
    # ---------- Getters ----------

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







    """

    def add_spectra(self, compound_name: str, compound_formula: str, inchikey: str, spectra_info: dict, adduct_id: float):
        with self.session_scope() as session:
            # Check if compound already exists
            compound = None
            if inchikey:
                compound = session.query(Compound).filter_by(inchikey=inchikey).one_or_none()

            if compound is None:
                compound = Compound(
                    name=compound_name,
                    formula=compound_formula,
                    inchikey=inchikey,
                    exact_mass=calculate_exact_mass(compound_formula),
                )
                session.add(compound)
                session.flush()  # get compound.id

            # Add spectrum
            if adduct_id is None:
                raise ValueError("adduct_id is required in spectra_info")

            spectrum = Spectrum.from_arrays(
                compound_id=compound.id,
                precursor_mz=spectra_info["precursor_mz"],
                adduct_type_id=adduct_id,
                polarity=spectra_info["polarity"],
                collision_energy=spectra_info["collision_energy"],
                mz=spectra_info["mz"],
                intensity=spectra_info["intensity"]
            )

            session.add(spectrum)
            session.commit()  # commit to get spectrum.id


    def find_identical_spectra(self, precursor_mz: float, polarity: str, hash_ref: str,
                               ppm_tolerance: float = 5):
        matches = []
        with self.session_scope() as session:
            candidates = session.query(Spectrum).filter_by(
                polarity=polarity,
                spectrum_hash=hash_ref
            ).all()

            if not candidates:
                return matches

            for spectrum in candidates:
                ppm_diff = abs(spectrum.precursor_mz - precursor_mz) / precursor_mz * 1e6
                if ppm_diff <= ppm_tolerance:
                    matches.append(spectrum.id)

            return matches


    def get_compound_id_from_spectrum_id(self, spectrum_id: int):
        with self.session_scope() as session:
            spectrum = session.query(Spectrum).filter_by(id=spectrum_id).one_or_none()
            if spectrum is None:
                raise ValueError(f"Spectrum with ID {spectrum_id} not found")
            return spectrum.compound_id


    def get_identical_spectra_compounds(self, spectrum_id: int):
        with self.session_scope() as session:
            spectrum = session.query(Spectrum).filter_by(id=spectrum_id).one_or_none()
            if spectrum is None:
                raise ValueError(f"Spectrum with ID {spectrum_id} not found")

            identical_spectra_ids = self.find_identical_spectra(
                precursor_mz=spectrum.precursor_mz,
                polarity=spectrum.polarity,
                hash_ref=spectrum.spectrum_hash
            )

            identical_spectra_ids = [sid for sid in identical_spectra_ids if sid != spectrum_id]

            logger.debug("Found %d identical spectra for spectrum ID %d", len(identical_spectra_ids), spectrum_id)

            compounds = []
            for spec_id in identical_spectra_ids:
                spec = session.query(Spectrum).filter_by(id=spec_id).one()
                comp = session.query(Compound).filter_by(id=spec.compound_id).one()
                compounds.append({
                    "id": comp.id,
                    "name": comp.name,
                    "formula": comp.formula
                })

            return compounds



"""