import logging
from pathlib import Path
import numpy as np
import re
from datetime import datetime, UTC

from sqlalchemy.orm import Session
from pyteomics.auxiliary.structures import PyteomicsError

from libviz.core.db.models import calculate_spectrum_hash
from libviz.core.utils import parse_msp, calculate_exact_mass, infer_precursor_delta

POLARITY_MAP = {
    "positive": "POSITIVE", "pos": "POSITIVE", "p": "POSITIVE",
    "negative": "NEGATIVE", "neg": "NEGATIVE", "n": "NEGATIVE",
}

KNOWN_KEYS = {
    "NAME", "FORMULA", "INCHIKEY", "EXACTMASS",
    "PRECURSORMZ", "PRECURSORTYPE", "IONMODE", "COLLISIONENERGY", "peaks",
    "SMILES",
}

# Some exporters (e.g. MoNA) don't expose SMILES/PubChem CID as top-level
# MSP keys; they bury them as quoted "key=value" segments inside COMMENT(S).
_COMMENT_FIELD_RE = re.compile(r'"([^"]*)"')

logger = logging.getLogger(__name__)


class MSPReader:

    BATCH_SIZE = 2500

    def __init__(self, session: Session, default_precursor_type: str = "[M+H]+"):
        self.session = session
        self.adduct_cache: dict[str, int] = {}
        self.compound_cache: dict[str, int] = {}
        self.default_precursor_type: str = default_precursor_type

    # ---------- public API ----------
    def import_file(self, msp_path: Path):
        if not isinstance(msp_path, Path):
            raise TypeError(f"Msp_path should be a Path object. Found {type(msp_path).__name__}")

        logger.debug("Starting import of MSP file: %s", msp_path)

        compound_rows: list[dict] = []
        spectrum_rows: list[dict] = []

        for i, entry in enumerate(parse_msp(msp_path), start=1):
            self._collect_entry(entry, compound_rows, spectrum_rows)

            if i % self.BATCH_SIZE == 0:
                self._flush(compound_rows, spectrum_rows)
                compound_rows.clear()
                spectrum_rows.clear()

        self._flush(compound_rows, spectrum_rows)
        self.session.commit()
        logger.debug("Import complete.")

    # ---------- collect ----------
    def _collect_entry(self, entry, compound_rows, spectrum_rows):
        precursor_mz = self._parse_precursor_mz(entry)
        if precursor_mz is None:
            logger.warning(
                "Skipping entry with missing/invalid PRECURSORMZ: %r",
                entry.get("PRECURSORMZ") or entry.get("PRECURSOR_MZ"),
            )
            return

        formula = entry.get("PRECURSORTYPE") or entry.get("PRECURSOR_TYPE")

        if not formula:
            logger.warning("Entry missing PRECURSORTYPE, using default: %s", self.default_precursor_type)
            formula = self.default_precursor_type

        if formula not in self.adduct_cache:
            conn = self.session.connection()
            try:
                charge, delta, multiplication_factor = infer_precursor_delta(formula)
            except (ValueError, PyteomicsError):
                logger.warning("Skipping unknown precursor type: %s", formula)
                return

            conn.exec_driver_sql(
                "INSERT OR IGNORE INTO adduct_type (formula, delta_mass, charge, multiplication_factor) "
                "VALUES (?, ?, ?, ?)",
                (formula, delta, charge, multiplication_factor)
            )
            row = conn.exec_driver_sql(
                "SELECT id FROM adduct_type WHERE formula = ?", (formula,)
            ).fetchone()
            self.adduct_cache[formula] = row[0]

        adduct_id = self.adduct_cache[formula]
        inchikey = entry.get("INCHIKEY", "").strip().upper() or None

        if inchikey not in self.compound_cache:
            exact_mass = (
                float(entry["EXACTMASS"])
                if "EXACTMASS" in entry
                else calculate_exact_mass(entry.get("FORMULA"))
            )
            smiles, pubchem_id = self._parse_smiles_and_pubchem(entry)

            compound_rows.append({
                "name":       entry.get("NAME"),
                "formula":    entry.get("FORMULA"),
                "inchikey":   inchikey,
                "exact_mass": exact_mass,
                "smiles":     smiles,
                "pubchem_id": pubchem_id,
            })
            self.compound_cache[inchikey] = None

        mz, intensity = self._prepare_peaks(entry)
        spectrum_hash = calculate_spectrum_hash(mz, intensity)
        extra = {k: v for k, v in entry.items() if k not in KNOWN_KEYS}

        spectrum_rows.append({
            "_inchikey":     inchikey,
            "_adduct_id":    adduct_id,
            "_precursor_mz": precursor_mz,
            "_mz":           mz,
            "_intensity":    intensity,
            "_hash":         spectrum_hash,
            "_entry":        entry,
            "_metadata":     extra,
        })

    # ---------- flush ----------
    def _flush(self, compound_rows, spectrum_rows):
        if not spectrum_rows:
            return

        now = datetime.now(UTC).isoformat()
        conn = self.session.connection()

        # 1. Bulk insert compounds
        if compound_rows:
            conn.exec_driver_sql(
                "INSERT OR IGNORE INTO compound "
                "(name, formula, inchikey, exact_mass, smiles, pubchem_id, added_on) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                [(r["name"], r["formula"], r["inchikey"], r["exact_mass"],
                  r["smiles"], r["pubchem_id"], now)
                 for r in compound_rows]
            )
            inchikeys = tuple(r["inchikey"] for r in compound_rows)
            placeholders = ",".join("?" * len(inchikeys))
            rows = conn.exec_driver_sql(
                f"SELECT id, inchikey FROM compound WHERE inchikey IN ({placeholders})",
                inchikeys
            ).fetchall()
            for compound_id, inchikey in rows:
                self.compound_cache[inchikey] = compound_id

        # 2. Split by metadata presence
        needs_meta = [r for r in spectrum_rows if r["_metadata"]]
        no_meta    = [r for r in spectrum_rows if not r["_metadata"]]

        # 2a. Bulk insert spectra without metadata
        if no_meta:
            conn.exec_driver_sql(
                "INSERT OR IGNORE INTO spectrum "
                "(compound_id, precursor_mz, adduct_type_id, polarity, "
                " collision_energy, spectrum_hash, mz_array, intensity_array, added_on) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [self._build_spectrum_tuple(r, now) for r in no_meta]
            )

        # 2b. Insert spectra with metadata one by one to capture rowid
        meta_rows = []
        for row in needs_meta:
            cursor = conn.exec_driver_sql(
                "INSERT OR IGNORE INTO spectrum "
                "(compound_id, precursor_mz, adduct_type_id, polarity, "
                " collision_energy, spectrum_hash, mz_array, intensity_array, added_on) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                self._build_spectrum_tuple(row, now)
            )
            if cursor.rowcount == 0:
                continue
            sid = cursor.lastrowid
            for k, v in row["_metadata"].items():
                meta_rows.append((sid, k, str(v)))

        if meta_rows:
            conn.exec_driver_sql(
                "INSERT OR IGNORE INTO spectrum_metadata (spectrum_id, key, value) "
                "VALUES (?, ?, ?)",
                meta_rows
            )

        self.session.commit()

    # ---------- helpers ----------
    def _build_spectrum_tuple(self, row, now: str) -> tuple:
        entry = row["_entry"]
        return (
            self.compound_cache[row["_inchikey"]],
            row["_precursor_mz"],
            row["_adduct_id"],
            self._normalize_polarity(entry.get("IONMODE") or entry.get("ION_MODE")),
            parse_collision_energy(entry.get("COLLISIONENERGY") or entry.get("COLLISION_ENERGY")),
            row["_hash"],
            row["_mz"].tobytes(),
            row["_intensity"].tobytes(),
            now,
        )

    def _prepare_peaks(self, entry):
        mz = np.array([float(m) for m, _ in entry.get("peaks", [])], dtype=np.float32)
        intensity = np.array([float(i) for _, i in entry.get("peaks", [])], dtype=np.float32)
        order = np.argsort(mz)
        return mz[order], intensity[order]

    def _parse_precursor_mz(self, entry: dict) -> float | None:
        """Parse PRECURSORMZ (or the PRECURSOR_MZ key variant some
        exporters use), tolerating a locale comma-decimal like "197,9867".

        Returns ``None`` when the field is missing, unparseable, or not a
        positive number -- callers should skip the entry entirely rather
        than store a nonsensical precursor mass (the column is NOT NULL,
        so a bad value would otherwise crash the batch insert, not just
        this one entry).
        """
        raw = entry.get("PRECURSORMZ") or entry.get("PRECURSOR_MZ")
        if raw is None:
            return None
        raw = str(raw).strip()
        if "," in raw and "." not in raw:
            raw = raw.replace(",", ".")
        try:
            value = float(raw)
        except ValueError:
            return None
        return value if value > 0 else None

    def _parse_smiles_and_pubchem(self, entry: dict) -> tuple[str | None, int | None]:
        """Extract SMILES / PubChem CID.

        Most MSP exporters expose these as top-level keys. MoNA instead
        buries them as quoted ``"key=value"`` segments inside COMMENT(S),
        so fall back to parsing that field when the top-level key is
        missing or blank.
        """
        smiles = (entry.get("SMILES") or "").strip() or None
        pubchem_raw = entry.get("PUBCHEM") or entry.get("PUBCHEMID") or entry.get("PUBCHEM_CID")

        if smiles is None or pubchem_raw is None:
            comment = entry.get("COMMENTS") or entry.get("COMMENT") or ""
            comment_fields = self._parse_comment_fields(comment)
            if smiles is None:
                smiles = comment_fields.get("smiles")
            if pubchem_raw is None:
                pubchem_raw = comment_fields.get("pubchem cid") or comment_fields.get("pubchem")

        pubchem_id = None
        if pubchem_raw is not None:
            digits = str(pubchem_raw).strip()
            if digits.isdigit():
                pubchem_id = int(digits)

        return smiles, pubchem_id

    @staticmethod
    def _parse_comment_fields(comment: str) -> dict[str, str]:
        fields: dict[str, str] = {}
        for segment in _COMMENT_FIELD_RE.findall(comment):
            if "=" not in segment:
                continue
            key, value = segment.split("=", 1)
            key = key.strip().lower()
            if key not in fields:
                fields[key] = value.strip()
        return fields

    def _normalize_polarity(self, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = POLARITY_MAP.get(value.strip().lower())
        if normalized is None:
            logger.warning("Unrecognized polarity value: %s", value)
        return normalized

def parse_collision_energy(value):
    if not value:
        return 0.0
    match = re.search(r"[\d.]+", str(value))
    return float(match.group()) if match else 0.0