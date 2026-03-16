import logging
import numpy as np

from sqlalchemy.orm import Session
from sqlalchemy import insert, select

from libviz.core.db.models import (
    Compound,
    Spectrum,
    SpectrumMetadata,
    AdductType,
    calculate_spectrum_hash
)

from libviz.core.utils import (
    parse_msp,
    calculate_exact_mass,
    infer_precursor_delta
)

logger = logging.getLogger(__name__)

POLARITY_MAP = {
    "positive": "POSITIVE",
    "pos": "POSITIVE",
    "p": "POSITIVE",
    "negative": "NEGATIVE",
    "neg": "NEGATIVE",
    "n": "NEGATIVE",
}

class MSPReader:

    BATCH_SIZE = 1000

    def __init__(self, session: Session):
        self.session = session
        self._counter = 0
        self.adduct_cache = {}
        self.compound_cache = {}

    # ---------- public API ----------
    def import_file(self, msp_path: str):

        for entry in parse_msp(msp_path):
            self._insert_entry(entry)

            self._counter += 1
            if self._counter % self.BATCH_SIZE == 0:
                self.session.commit()

        self.session.commit()

    # ---------- entry processing ----------
    def _insert_entry(self, entry):

        mz, intensity = self._prepare_peaks(entry)
        mz_bytes = mz.tobytes()
        intensity_bytes = intensity.tobytes()

        spectrum_hash = calculate_spectrum_hash(mz, intensity)

        adduct_id = self._get_or_create_adduct(entry)
        if adduct_id is None:
            return

        compound_id = self._get_or_create_compound(entry)

        spectrum_id = self._insert_spectrum(
            compound_id,
            adduct_id,
            entry,
            mz_bytes,
            intensity_bytes,
            spectrum_hash
        )

        if spectrum_id:
            self._insert_metadata(spectrum_id, entry)

    # ---------- helpers ----------
    def _prepare_peaks(self, entry):

        mz = np.array([float(m) for m, _ in entry.get("peaks", [])], dtype=np.float32)
        intensity = np.array([float(i) for _, i in entry.get("peaks", [])], dtype=np.float32)

        order = np.argsort(mz)

        return mz[order], intensity[order]

    # ---------- adduct ----------
    def _get_or_create_adduct(self, entry):

        formula = entry.get("PRECURSORTYPE")

        if formula in self.adduct_cache:
            return self.adduct_cache[formula]

        try:
            charge, delta = infer_precursor_delta(formula)
        except ValueError:
            logger.warning("Skipping precursor: %s", formula)
            return None

        stmt = insert(AdductType).values(
            formula=formula,
            delta_mass=delta,
            charge=charge
        ).prefix_with("OR IGNORE")

        self.session.execute(stmt)

        stmt = select(AdductType.id).where(AdductType.formula == formula)
        adduct_id = self.session.execute(stmt).scalar()

        self.adduct_cache[formula] = adduct_id

        return adduct_id

    # ---------- compound ----------
    def _get_or_create_compound(self, entry):

        inchikey = entry.get("INCHIKEY")

        if inchikey in self.compound_cache:
            return self.compound_cache[inchikey]

        exact_mass = (
            float(entry["EXACTMASS"])
            if "EXACTMASS" in entry
            else calculate_exact_mass(entry.get("FORMULA"))
        )

        stmt = insert(Compound).values(
            name=entry.get("NAME"),
            formula=entry.get("FORMULA"),
            inchikey=inchikey,
            exact_mass=exact_mass
        ).prefix_with("OR IGNORE")

        self.session.execute(stmt)

        stmt = select(Compound.id).where(Compound.inchikey == inchikey)
        compound_id = self.session.execute(stmt).scalar()

        self.compound_cache[inchikey] = compound_id

        return compound_id

    # ---------- spectrum ----------
    def _insert_spectrum(
        self,
        compound_id: int,
        adduct_id: int,
        entry: dict,
        mz: bytes,
        intensity: bytes,
        spectrum_hash: str
    ):

        stmt = insert(Spectrum).values(
            compound_id=compound_id,
            precursor_mz=float(entry["PRECURSORMZ"]),
            adduct_type_id=adduct_id,
            polarity=self._normalize_polarity(entry.get("IONMODE")),
            collision_energy=float(entry.get("COLLISIONENERGY") or 0.0),
            spectrum_hash=spectrum_hash,
            mz_array=mz,
            intensity_array=intensity
        ).prefix_with("OR IGNORE")

        result = self.session.execute(stmt)

        if result.rowcount == 0:
            return None

        return result.inserted_primary_key[0]

    # ---------- metadata ----------
    def _insert_metadata(self, spectrum_id, entry):

        known_keys = {
            "NAME",
            "FORMULA",
            "INCHIKEY",
            "EXACTMASS",
            "PRECURSORMZ",
            "PRECURSORTYPE",
            "IONMODE",
            "COLLISIONENERGY",
            "peaks"
        }

        rows = []

        for key, value in entry.items():

            if key in known_keys:
                continue

            rows.append(
                {
                    "spectrum_id": spectrum_id,
                    "key": key,
                    "value": str(value)
                }
            )

        if rows:
            self.session.execute(insert(SpectrumMetadata), rows)


    def _normalize_polarity(self, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = POLARITY_MAP.get(value.strip().lower())
        if normalized is None:
            logger.warning("Unrecognized polarity value: %s", value)
        return normalized
