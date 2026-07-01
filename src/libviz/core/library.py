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
from libviz.core.utils.mass_calulation_utils import calculate_exact_mass

logger = logging.getLogger(__name__)

class Library:
    def __init__(self, name: str, path: Path):

        # Checks
        if not isinstance(path, (str, Path)):
            raise TypeError(f"Path should be a Path object or str, found {type(path).__name__}")

        if not isinstance(name, str):
            raise TypeError(f"Name should be of type str, found {type(name).__name__}")

        if not name:
            raise ValueError("Name cannot be an empty string.")

        self.path: Path = path
        self.is_temp: bool = True
        self.name: str = name
        self.engine: Engine = create_engine(f"sqlite:///{self.path}", future=True)
        self.session_maker = sessionmaker(bind=self.engine, future=True)
        self._n_compounds = 0
        self._n_spectra = 0

        @event.listens_for(self.engine, "connect")
        def enable_sqlite_fk(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=MEMORY")
            cursor.execute("PRAGMA synchronous=OFF")
            cursor.close()


    @classmethod
    def create(cls, path: Path, name: str):

        logger.debug("Creating new library with name %s at path %s", name, path)

        lib = cls(name = name, path=path)

        if path.exists():
            raise FileExistsError(f"Library already exists at path {str(path)}")

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
    def loadFromMSP(cls, msp_path: Path):

        logger.debug("Loading library from MSP file %s", msp_path)

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

            lib._n_compounds = session.query(Compound).count()
            lib._n_spectra = session.query(Spectrum).count()

        lib.is_temp = True

        logger.debug("Loaded library from MSP file %s with %d compounds and %d spectra", msp_path, lib._n_compounds, lib._n_spectra)

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
        lib._n_compounds = session.query(Compound).count()
        lib._n_spectra = session.query(Spectrum).count()
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
                     "delta_mass": a.delta_mass, "multiplication_factor": a.multiplication_factor} 
                     for a in adducts]


    def get_adduct_delta(self, adduct_id: int):
        with self.session_scope() as session:
            adduct = session.query(AdductType).filter_by(id=adduct_id).one_or_none()
            if adduct is None:
                raise ValueError(f"Adduct with ID {adduct_id} not found")
            return adduct.delta_mass

    @property
    def n_compounds(self):
        return self._n_compounds
    
    @property
    def n_spectra(self):
        return self._n_spectra

    def _get_or_insert_compound_by_inchikey(self, session,  name: str, formula: str, inchikey: str) -> Compound:

        # Checks
        if not isinstance(name, str) or not name:
            raise ValueError("name must be a non-empty string")

        if not isinstance(formula, str) or not formula:
            raise ValueError("formula must be a non-empty string")

        if not isinstance(inchikey, str) or not inchikey:
            raise ValueError("inchikey must be a non-empty string")

        compound = session.query(Compound).filter_by(inchikey=inchikey).one_or_none()
        if compound is not None:
            return compound

        compound = Compound(
            name=name,
            formula=formula,
            inchikey=inchikey,
            exact_mass=calculate_exact_mass(formula),
        )
        session.add(compound)
        session.flush()  # to get the ID assigned

        return compound


    def add_spectra(self, compound_name: str, compound_formula: str, inchikey: str, 
                    spectra_info: dict, adduct_id: int):

        # Checks
        if not isinstance(compound_name, str) or not compound_name:
            raise ValueError("compound_name must be a non-empty string")
        
        if not isinstance(compound_formula, str) or not compound_formula:
            raise ValueError("compound_formula must be a non-empty string")
        
        if not isinstance(inchikey, str) or not inchikey:
            raise ValueError("inchikey must be a non-empty string")
        
        if not isinstance(spectra_info, dict):
            raise ValueError("spectra_info must be a dictionary")

        if not isinstance(adduct_id, int):
            raise ValueError("adduct_id must be an integer")

        # Get or insert compound
        with self.session_scope() as session:
            compound = self._get_or_insert_compound_by_inchikey(session,
                                                                compound_name,
                                                                compound_formula,
                                                                inchikey)
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


    def find_identical_spectra(self, precursor_mz: float, polarity: str, hash_ref: str,
                               ppm_tolerance: float = 5):
        if precursor_mz <= 0:
            raise ValueError("precursor_mz must be a positive number")

        if polarity not in ("POSITIVE", "NEGATIVE"):
            raise ValueError("polarity must be either 'POSITIVE' or 'NEGATIVE'")

        if not isinstance(hash_ref, str) or not hash_ref:
            raise ValueError("hash_ref must be a non-empty string")

        if ppm_tolerance < 0:
            raise ValueError("ppm_tolerance must be a non-negative number")

        matches = []
        with self.session_scope() as session:
            candidates = session.query(Spectrum).filter_by(
                polarity=polarity,
                spectrum_hash=hash_ref
            ).all()

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


    def get_identical_spectra_compounds_by_spectrum_id(self,
                                                       spectrum_id: int,
                                                       ppm_tolerance: float = 5):

        if not isinstance(spectrum_id, int):
            raise ValueError("spectrum_id must be an integer")

        if not isinstance(ppm_tolerance, (int, float)):
            raise ValueError("ppm_tolerance must be a number")

        if ppm_tolerance < 0:
            raise ValueError("ppm_tolerance must be a non-negative number")

        with self.session_scope() as session:
            spectrum = session.query(Spectrum).filter_by(id=spectrum_id).one_or_none()
            if spectrum is None:
                raise ValueError(f"Spectrum with ID {spectrum_id} not found")

            candidates = (
                session.query(Spectrum, Compound)
                .join(Compound, Compound.id == Spectrum.compound_id)
                .filter(
                    Spectrum.polarity == spectrum.polarity,
                    Spectrum.spectrum_hash == spectrum.spectrum_hash,
                    Spectrum.id != spectrum_id
                )
                .all()
            )

            compounds = []
            for candidate_spectrum, comp in candidates:
                ppm_diff = abs(candidate_spectrum.precursor_mz - spectrum.precursor_mz) / spectrum.precursor_mz * 1e6
                if ppm_diff <= ppm_tolerance:
                    compounds.append({"id": comp.id,
                                      "name": comp.name,
                                      "formula": comp.formula, 
                                      "inchikey": comp.inchikey, 
                                      "spectrum_id": candidate_spectrum.id})

            return compounds


    def get_identical_spectra_compounds_by_spectrum_info(self,
                                                         precursor_mz: float,
                                                         polarity: str,
                                                         hash_ref: str,
                                                         ppm_tolerance: float = 5) -> list[dict]:
        if precursor_mz <= 0:
            raise ValueError("precursor_mz must be a positive number")

        if polarity not in ("POSITIVE", "NEGATIVE"):
            raise ValueError("polarity must be either 'POSITIVE' or 'NEGATIVE'")

        if not isinstance(hash_ref, str) or not hash_ref:
            raise ValueError("hash_ref must be a non-empty string")

        if ppm_tolerance < 0:
            raise ValueError("ppm_tolerance must be a non-negative number")

        with self.session_scope() as session:
            spectrum = session.query(Spectrum).filter_by(
                polarity=polarity,
                spectrum_hash=hash_ref
            ).all()

            compounds = []
            for candidate_spectrum in spectrum:
                ppm_diff = abs(candidate_spectrum.precursor_mz - precursor_mz) / precursor_mz * 1e6
                if ppm_diff <= ppm_tolerance:
                    compounds.append({"id": candidate_spectrum.compound_id,
                                      "name": candidate_spectrum.compound.name,
                                      "formula": candidate_spectrum.compound.formula, 
                                      "inchikey": candidate_spectrum.compound.inchikey, 
                                      "spectrum_id": candidate_spectrum.id})

            return compounds

    def get_spectra_in_mz_range(
        self,
        mz_min: float,
        mz_max: float,
        polarity: str | None = None,
    ) -> list[dict]:
        """Return spectra with precursor_mz in [mz_min, mz_max]."""
        with self.session_scope() as session:
            query = session.query(Spectrum, Compound).join(
                Compound, Compound.id == Spectrum.compound_id
            ).filter(
                Spectrum.precursor_mz >= mz_min,
                Spectrum.precursor_mz <= mz_max,
            )
            if polarity is not None:
                query = query.filter(Spectrum.polarity == polarity)

            return [
                {
                    "spectrum_id": s.id,
                    "compound_id": c.id,
                    "compound_name": c.name,
                    "compound_formula": c.formula,
                    "inchikey": c.inchikey,
                    "mz": s.mz,           # however Spectrum stores/exposes the array
                    "intensity": s.intensity,
                }
                for s, c in query.all()
            ]
