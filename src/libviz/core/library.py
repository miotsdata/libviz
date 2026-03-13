from pathlib import Path
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker, Session
import numpy as np
import logging
import tempfile
import sqlite3

from libviz.core.db.extensions import Base
from libviz.core.db.migrations import upgrade_library_schema
from libviz.core.db.models import (
    Compound,
    Spectrum,
    LibraryMetadata,
    SpectrumMetadata,
    AdductType,
    populate_adduct_types,  
    calculate_spectrum_hash
)
from libviz.core.utils import parse_msp, calculate_exact_mass, infer_precursor_delta

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

    @classmethod
    def create(cls, path: str | Path, name: str):
        if not isinstance(path, (str, Path)):
            raise TypeError(f"Path should be either str or Path, found {type(path).__name__}")
        
        if path.exists():
            raise FileExistsError(f"Library already exists at path {str(path)}")

        path = Path(path) if isinstance(path, str) else path
        lib = cls(name = name, path=path)

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

"""
    @classmethod
    def load_from_db(cls, path: Path):
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


    @classmethod
    def loadFromMSP(cls, msp_path: str):

        # Create in-memory SQLite DB
        # Create temporary DB file
        tmp_file = tempfile.NamedTemporaryFile(
            suffix=".db",
            delete=False
        )
        tmp_file.close()

        db_path = tmp_file.name
        logger.debug(f"Temporary database path: {db_path}")

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
        lib.session_maker = Session_db
        lib.n_compounds = session.query(Compound).count()
        lib.n_spectra = session.query(Spectrum).count()
        lib.is_temp = True

        session.close()
        return lib

    # ---------- helpers ----------

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

        
        # ---------- check if spectrum already exists ----------
        existing = session.query(Spectrum).filter_by(
            compound_id=compound.id,
            adduct_type_id=adduct_type.id,
            polarity=entry.get("IONMODE"),
            collision_energy = float(entry.get("COLLISIONENERGY") or 0.0),
            spectrum_hash=spectrum_hash
        ).one_or_none()

        if existing:
            # spectrum already in DB → skip everything
            return existing

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


    def save_as_db(self, path: str):

        if self.name == "NONAME":
            raise ValueError("Name cannot be NONAME. Please rename the library with the rename method.")

        # ensure WAL is flushed
        with self.engine.connect() as conn:
            conn.exec_driver_sql("PRAGMA wal_checkpoint(FULL);")

        # close all pooled connections
        self.engine.dispose()

        src = sqlite3.connect(self.path)
        dest = sqlite3.connect(path)

        try:
            src.backup(dest)
        finally:
            dest.close()
            src.close()

        self.path = Path(path)
        self.is_temp = False
        logger.debug("Saved library to %s", path)


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


    def rename(self, new_name: str):
        logger.debug("Renaming library from %s to %s", self.name, new_name)
        with self.session_scope() as session:
            meta = session.query(LibraryMetadata).first()
            if meta is None:
                raise ValueError("No metadata found in library")
            meta.name = new_name
            session.commit()
            self.name = new_name
"""