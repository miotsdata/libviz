from contextlib import contextmanager
from pathlib import Path
from sqlalchemy import Engine, create_engine, event, exists, func, or_, select
from sqlalchemy.orm import sessionmaker
import numpy as np
import logging
import os
import shutil
import tempfile

from libviz.core.db.migrations import upgrade_library_schema
from libviz.core.readers import MSPReader

from libviz.core.db.models import (
    SpectrumMetadata,
    Compound,
    Spectrum,
    LibraryMetadata,
    AdductType,
    populate_adduct_types
)
from libviz.core.utils.mass_utils import calculate_exact_mass

logger = logging.getLogger(__name__)

class Library:
    def __init__(self, name: str, path: Path, *, fast_writes: bool = False):

        # Checks
        if not isinstance(path, (str, Path)):
            raise TypeError(f"Path should be a Path object or str, found {type(path).__name__}")

        if not isinstance(name, str):
            raise TypeError(f"Name should be of type str, found {type(name).__name__}")

        if not name:
            raise ValueError("Name cannot be an empty string.")

        self.path: Path = Path(path)
        self.is_temp: bool = True
        self.name: str = name
        self._open_engine(fast_writes)

    def _open_engine(self, fast_writes: bool):
        """(Re)open the engine on ``self.path``.

        ``fast_writes`` turns off the rollback journal and fsync — only for
        the disposable temp DB a bulk import writes into, never for a library
        the user keeps (a crash there would corrupt it, see ADR 1). No WAL
        either: libraries live on network shares, where WAL is unsafe.
        """
        self.engine: Engine = create_engine(f"sqlite:///{self.path}", future=True)
        self.session_maker = sessionmaker(bind=self.engine, future=True)

        @event.listens_for(self.engine, "connect")
        def _pragmas(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            if fast_writes:
                cursor.execute("PRAGMA journal_mode=MEMORY")
                cursor.execute("PRAGMA synchronous=OFF")
            cursor.close()


    @classmethod
    def create(cls, path: Path, name: str, *, fast_writes: bool = False):

        logger.debug("Creating new library with name %s at path %s", name, path)

        lib = cls(name=name, path=path, fast_writes=fast_writes)

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
    @contextmanager
    def session_scope(self):
        session = self.session_maker()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def close(self):
        """Release the DB; a temp (unsaved) library's file is deleted."""
        self.engine.dispose()
        if self.is_temp:
            self.path.unlink(missing_ok=True)


    # ---------- Saving ----------
    def save_as_db(self, path: Path):
        logger.debug("Saving library to %s", path)

        if not isinstance(path, Path):
            raise TypeError(f"Path should be a Path object, found {type(path).__name__}")

        if self.name == "NONAME":
            raise ValueError("Name cannot be NONAME. Please rename the library with the rename method.")

        # close all pooled connections -- every session has committed, so
        # self.path is now a complete, consistent, single-file snapshot
        self.engine.dispose()

        # A plain file copy rather than sqlite3's backup() API: backup()
        # needs a real file lock on the destination, which some network
        # filesystems (SMB/CIFS) don't honour -- the call can then hang
        # indefinitely instead of erroring. The dispose above already
        # makes self.path a complete, static file, so a straight sequential
        # copy is correct and safe everywhere. Copy-then-rename keeps the
        # write atomic -- a crash mid-copy never leaves a partial `path`.
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_name(path.name + ".tmp")
        shutil.copy2(self.path, tmp_path)
        tmp_path.replace(path)

        old_path, was_temp = self.path, self.is_temp
        self.path = Path(path)
        self.is_temp = False
        # Later edits must go to the saved file, with safe pragmas.
        self._open_engine(fast_writes=False)
        if was_temp and old_path != self.path:
            old_path.unlink(missing_ok=True)
        logger.debug("Saved library to %s", path)


    # ---------- Loading ----------
    @classmethod
    def load_from_msp(cls, msp_path: Path, default_precursor_type: str = "[M+H]+", progress=None):
        """Import an MSP file into a new temp library (``is_temp``)."""
        logger.debug("Loading library from MSP file %s", msp_path)

        fd, tmp_name = tempfile.mkstemp(suffix=".db", prefix="libviz_")
        os.close(fd)
        db_path = Path(tmp_name)
        db_path.unlink()  # create() refuses an existing file

        lib = cls.create(name=Path(msp_path).stem or "MSP library", path=db_path, fast_writes=True)

        with lib.session_scope() as session:
            reader = MSPReader(session, default_precursor_type=default_precursor_type)
            reader.import_file(msp_path, progress)

        lib.is_temp = True

        logger.debug("Loaded library from MSP file %s with %d compounds and %d spectra",
                     msp_path, lib.n_compounds, lib.n_spectra)

        return lib


    @classmethod
    def load_from_db(cls, path: Path):
        if not isinstance(path, Path):
            raise TypeError(f"Path should be a Path object, found {type(path).__name__}")

        if not Path(path).exists():
            raise FileNotFoundError(path)

        lib = cls(name="unnamed", path=path)
        with lib.session_scope() as session:
            meta = session.query(LibraryMetadata).first()
            if meta is None:
                lib.engine.dispose()
                raise ValueError(f"No metadata found in library at {path}")
            lib.name = meta.name
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
    def n_compounds(self) -> int:
        with self.session_scope() as session:
            return session.query(Compound).count()

    @property
    def n_spectra(self) -> int:
        with self.session_scope() as session:
            return session.query(Spectrum).count()

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


    def get_compound_id_from_spectrum_id(self, spectrum_id: int):
        with self.session_scope() as session:
            spectrum = session.query(Spectrum).filter_by(id=spectrum_id).one_or_none()
            if spectrum is None:
                raise ValueError(f"Spectrum with ID {spectrum_id} not found")
            return spectrum.compound_id


    def get_identical_spectra_compounds_by_spectrum_id(self,
                                                       spectrum_id: int,
                                                       ppm_tolerance: float = 5):
        """Other spectra identical to ``spectrum_id`` (same hash, polarity,
        precursor within ppm), with their compound."""
        if not isinstance(spectrum_id, int):
            raise ValueError("spectrum_id must be an integer")

        with self.session_scope() as session:
            spectrum = session.query(Spectrum).filter_by(id=spectrum_id).one_or_none()
            if spectrum is None:
                raise ValueError(f"Spectrum with ID {spectrum_id} not found")
            ref = (spectrum.precursor_mz, spectrum.polarity, spectrum.spectrum_hash)

        return [
            c for c in self.get_identical_spectra_compounds_by_spectrum_info(*ref, ppm_tolerance=ppm_tolerance)
            if c["spectrum_id"] != spectrum_id
        ]


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
        convert_arrays: bool = True
    ) -> list[dict]:
        """Return spectra with precursor_mz in [mz_min, mz_max]."""
        with self.session_scope() as session:
            query = session.query(Spectrum, Compound).join(
                Compound, Compound.id == Spectrum.compound_id
            ).filter(
                Spectrum.precursor_mz >= mz_min,
                Spectrum.precursor_mz <= mz_max,
            )
            def _to_numpy_array(value):
                if isinstance(value, (bytes, bytearray)):
                    return np.frombuffer(value, dtype=np.float32).copy()
                return value

            if polarity is not None:
                query = query.filter(Spectrum.polarity == polarity)

            return [
                {
                    "spectrum_id": s.id,
                    "compound_id": c.id,
                    "compound_name": c.name,
                    "compound_formula": c.formula,
                    "inchikey": c.inchikey,
                    "mz": _to_numpy_array(s.mz_array).tolist() if convert_arrays else _to_numpy_array(s.mz_array),
                    "intensity": _to_numpy_array(s.intensity_array).tolist() if convert_arrays else _to_numpy_array(s.intensity_array),
                }
                for s, c in query.all()
            ]


    # ---------- Browsing (inspector) ----------
    # Everything below is paged/filtered in SQL so it stays fast on
    # MoNA-sized libraries (500k+ spectra); see ADR 3.

    COMPOUND_SORT_KEYS = ("name", "formula", "exact_mass", "inchikey")

    def _compound_filters(self, text: str = "", mass: float | None = None, ppm: float = 10.0,
                          polarity: str | None = None, adduct: str | None = None,
                          collision_energy: float | None = None) -> list:
        conditions = []
        text = (text or "").strip()
        if text:
            like = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            conditions.append(or_(
                Compound.name.like(f"%{like}%", escape="\\"),
                Compound.inchikey.like(f"{like.upper()}%", escape="\\"),
                Compound.formula == text,
            ))
        if mass is not None and mass > 0:
            tol = mass * ppm / 1e6
            conditions.append(or_(
                Compound.exact_mass.between(mass - tol, mass + tol),
                exists().where(Spectrum.compound_id == Compound.id,
                               Spectrum.precursor_mz.between(mass - tol, mass + tol)),
            ))
        spectrum_conditions = []
        if polarity:
            spectrum_conditions.append(Spectrum.polarity == polarity)
        if adduct:
            spectrum_conditions.append(Spectrum.adduct_type_id.in_(
                select(AdductType.id).where(AdductType.formula == adduct)))
        if collision_energy is not None:
            spectrum_conditions.append(Spectrum.collision_energy == collision_energy)
        if spectrum_conditions:
            conditions.append(exists().where(Spectrum.compound_id == Compound.id, *spectrum_conditions))
        return conditions

    def count_compounds(self, **filters) -> int:
        with self.session_scope() as session:
            return session.query(func.count(Compound.id)).filter(*self._compound_filters(**filters)).scalar()

    def search_compounds(self, *, sort: str = "name", descending: bool = False,
                         offset: int = 0, limit: int = 200, **filters) -> list[dict]:
        """One page of compounds matching ``filters`` (see ``_compound_filters``)."""
        if sort not in self.COMPOUND_SORT_KEYS:
            raise ValueError(f"sort must be one of {self.COMPOUND_SORT_KEYS}")
        column = getattr(Compound, sort)
        n_spectra = (select(func.count(Spectrum.id)).where(Spectrum.compound_id == Compound.id)
                     .correlate(Compound).scalar_subquery())
        with self.session_scope() as session:
            rows = (
                session.query(Compound.id, Compound.name, Compound.formula, Compound.exact_mass,
                              Compound.inchikey, n_spectra)
                .filter(*self._compound_filters(**filters))
                .order_by(column.desc() if descending else column.asc(), Compound.id)
                .offset(offset).limit(limit)
                .all()
            )
        return [{"id": r[0], "name": r[1] or "", "formula": r[2] or "", "exact_mass": r[3],
                 "inchikey": r[4] or "", "n_spectra": r[5]} for r in rows]

    def filter_options(self) -> dict:
        """Distinct polarities, adducts and collision energies actually used."""
        with self.session_scope() as session:
            polarities = [p for (p,) in session.query(Spectrum.polarity).distinct() if p]
            adducts = [a for (a,) in session.query(AdductType.formula)
                       .filter(exists().where(Spectrum.adduct_type_id == AdductType.id))
                       .order_by(AdductType.formula)]
            energies = [e for (e,) in session.query(Spectrum.collision_energy).distinct()
                        .order_by(Spectrum.collision_energy) if e is not None]
        return {"polarities": sorted(polarities), "adducts": adducts, "collision_energies": energies}

    def get_compound(self, compound_id: int) -> dict:
        with self.session_scope() as session:
            c = session.get(Compound, compound_id)
            if c is None:
                raise ValueError(f"Compound with ID {compound_id} not found")
            return {"id": c.id, "name": c.name or "", "formula": c.formula or "",
                    "exact_mass": c.exact_mass, "inchikey": c.inchikey or "",
                    "smiles": c.smiles or "", "pubchem_id": c.pubchem_id}

    def get_compound_spectra(self, compound_id: int) -> list[dict]:
        """Spectrum summaries (no peak arrays) of one compound."""
        with self.session_scope() as session:
            rows = (
                session.query(Spectrum.id, Spectrum.precursor_mz, AdductType.formula, Spectrum.polarity,
                              Spectrum.collision_energy, func.length(Spectrum.mz_array) / 4, Spectrum.added_on)
                .join(AdductType, AdductType.id == Spectrum.adduct_type_id)
                .filter(Spectrum.compound_id == compound_id)
                .order_by(Spectrum.polarity, AdductType.formula, Spectrum.collision_energy, Spectrum.id)
                .all()
            )
        return [{"id": r[0], "precursor_mz": r[1], "adduct": r[2] or "", "polarity": r[3] or "",
                 "collision_energy": r[4], "n_peaks": int(r[5] or 0),
                 "added_on": r[6].isoformat(timespec="seconds") if r[6] else ""} for r in rows]

    def get_spectrum(self, spectrum_id: int) -> dict:
        """One spectrum with peaks (plain lists) and its key/value metadata."""
        with self.session_scope() as session:
            s = session.get(Spectrum, spectrum_id)
            if s is None:
                raise ValueError(f"Spectrum with ID {spectrum_id} not found")
            return {
                "id": s.id,
                "compound_id": s.compound_id,
                "precursor_mz": s.precursor_mz,
                "adduct": s.adduct_type.formula if s.adduct_type else "",
                "polarity": s.polarity or "",
                "collision_energy": s.collision_energy,
                "mz": s.mz_numpy().astype(float).tolist(),
                "intensity": s.intensity_numpy().astype(float).tolist(),
                "metadata": {m.key: m.value for m in s.spectrum_metadata},
                "added_on": s.added_on.isoformat(timespec="seconds") if s.added_on else "",
            }

    # ---------- Editing ----------

    def update_compound(self, compound_id: int, *, name: str | None = None, formula: str | None = None,
                        smiles: str | None = None, pubchem_id: int | None = None):
        """Change compound fields (``None`` = unchanged; ``""`` clears SMILES).
        A new formula recomputes the exact mass; the InChIKey is the
        compound's identity and is not editable."""
        with self.session_scope() as session:
            c = session.get(Compound, compound_id)
            if c is None:
                raise ValueError(f"Compound with ID {compound_id} not found")
            if name is not None:
                if not name.strip():
                    raise ValueError("name cannot be empty")
                c.name = name.strip()
            if formula is not None and formula.strip() != c.formula:
                mass = calculate_exact_mass(formula.strip())
                if mass is None:
                    raise ValueError(f"invalid formula {formula!r}")
                c.formula, c.exact_mass = formula.strip(), mass
            if smiles is not None:
                c.smiles = smiles.strip() or None
            if pubchem_id is not None:
                c.pubchem_id = pubchem_id or None

    def delete_spectra(self, spectrum_ids: list[int]) -> int:
        """Delete spectra and their metadata; compounds are kept."""
        with self.session_scope() as session:
            session.query(SpectrumMetadata).filter(SpectrumMetadata.spectrum_id.in_(spectrum_ids)).delete()
            return session.query(Spectrum).filter(Spectrum.id.in_(spectrum_ids)).delete()

    def delete_compounds(self, compound_ids: list[int]) -> int:
        """Delete compounds with all their spectra and metadata."""
        with self.session_scope() as session:
            spectra = select(Spectrum.id).where(Spectrum.compound_id.in_(compound_ids))
            session.query(SpectrumMetadata).filter(SpectrumMetadata.spectrum_id.in_(spectra)).delete()
            session.query(Spectrum).filter(Spectrum.compound_id.in_(compound_ids)).delete()
            return session.query(Compound).filter(Compound.id.in_(compound_ids)).delete()

    def set_spectrum_metadata(self, spectrum_id: int, key: str, value: str):
        """Set (add or overwrite) one metadata field of a spectrum."""
        key = key.strip()
        if not key:
            raise ValueError("metadata key cannot be empty")
        with self.session_scope() as session:
            if session.get(Spectrum, spectrum_id) is None:
                raise ValueError(f"Spectrum with ID {spectrum_id} not found")
            rows = session.query(SpectrumMetadata).filter_by(spectrum_id=spectrum_id, key=key).all()
            if rows:
                rows[0].value = str(value)
                for extra in rows[1:]:
                    session.delete(extra)
            else:
                session.add(SpectrumMetadata(spectrum_id=spectrum_id, key=key, value=str(value)))

    def delete_spectrum_metadata(self, spectrum_id: int, key: str):
        with self.session_scope() as session:
            session.query(SpectrumMetadata).filter_by(spectrum_id=spectrum_id, key=key).delete()

    # ---------- Merging ----------

    def merge_from(self, source: Path) -> dict[str, int]:
        """Copy every compound, adduct type and spectrum (with metadata) of
        the library file ``source`` into this one, in SQL (ATTACH).

        Compounds are matched by InChIKey (the existing one wins), adduct
        types by formula. A spectrum identical to one already here (same
        compound, adduct, polarity, CE and peaks) is skipped.
        """
        source = Path(source).resolve()
        if source == self.path.resolve():
            raise ValueError("cannot merge a library into itself")
        if not source.exists():
            raise FileNotFoundError(source)
        conn = self.engine.raw_connection()
        try:
            cur = conn.cursor()
            cur.execute("ATTACH DATABASE ? AS src", (str(source),))
            try:
                if cur.execute("SELECT name FROM src.sqlite_master WHERE name = 'spectrum'").fetchone() is None:
                    raise ValueError(f"{source.name} is not a LibViz library")
                n_compounds = cur.execute("SELECT COUNT(*) FROM compound").fetchone()[0]
                n_src = cur.execute("SELECT COUNT(*) FROM src.spectrum").fetchone()[0]
                max_id = cur.execute("SELECT COALESCE(MAX(id), 0) FROM spectrum").fetchone()[0]
                cur.execute(
                    "INSERT OR IGNORE INTO compound (name, formula, exact_mass, inchikey, smiles, pubchem_id, added_on)"
                    " SELECT name, formula, exact_mass, inchikey, smiles, pubchem_id, added_on FROM src.compound")
                cur.execute(
                    "INSERT INTO adduct_type (formula, charge, delta_mass, multiplication_factor)"
                    " SELECT formula, charge, delta_mass, multiplication_factor FROM src.adduct_type sa"
                    " WHERE NOT EXISTS (SELECT 1 FROM adduct_type a WHERE a.formula IS sa.formula)")
                cur.execute(
                    "INSERT OR IGNORE INTO spectrum (compound_id, precursor_mz, adduct_type_id, polarity,"
                    " collision_energy, mz_array, intensity_array, added_on, spectrum_hash)"
                    " SELECT c.id, s.precursor_mz, a.id, s.polarity, s.collision_energy, s.mz_array,"
                    " s.intensity_array, s.added_on, s.spectrum_hash"
                    " FROM src.spectrum s"
                    " JOIN src.compound sc ON sc.id = s.compound_id JOIN compound c ON c.inchikey = sc.inchikey"
                    " JOIN src.adduct_type sa ON sa.id = s.adduct_type_id JOIN adduct_type a ON a.formula IS sa.formula"
                    # Explicit, not just OR IGNORE: the UNIQUE constraint
                    # treats NULL polarities as distinct.
                    " WHERE NOT EXISTS (SELECT 1 FROM spectrum m WHERE m.spectrum_hash = s.spectrum_hash"
                    "  AND m.compound_id = c.id AND m.adduct_type_id = a.id AND m.polarity IS s.polarity"
                    "  AND m.collision_energy = s.collision_energy)"
                    " ORDER BY s.id")
                added = cur.execute("SELECT COUNT(*) FROM spectrum WHERE id > ?", (max_id,)).fetchone()[0]
                # Metadata only for the spectra just inserted, found by identity.
                cur.execute(
                    "INSERT INTO spectrum_metadata (spectrum_id, key, value)"
                    " SELECT m.id, sm.key, sm.value FROM src.spectrum_metadata sm"
                    " JOIN src.spectrum s ON s.id = sm.spectrum_id"
                    " JOIN src.compound sc ON sc.id = s.compound_id JOIN compound c ON c.inchikey = sc.inchikey"
                    " JOIN src.adduct_type sa ON sa.id = s.adduct_type_id JOIN adduct_type a ON a.formula IS sa.formula"
                    " JOIN spectrum m ON m.id > ? AND m.compound_id = c.id AND m.adduct_type_id = a.id"
                    "  AND m.polarity IS s.polarity AND m.collision_energy = s.collision_energy"
                    "  AND m.spectrum_hash = s.spectrum_hash", (max_id,))
                new_compounds = cur.execute("SELECT COUNT(*) FROM compound").fetchone()[0] - n_compounds
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cur.execute("DETACH DATABASE src")
        finally:
            conn.close()
        return {"compounds_added": new_compounds, "spectra_added": added, "spectra_skipped": n_src - added}

