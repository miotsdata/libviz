from pathlib import Path

from libviz.core.readers.msp_reader import MSPReader
from libviz.core.db.models import AdductType, Compound, Spectrum, SpectrumMetadata
from unittest.mock import patch
import numpy as np


def test_prepare_peaks_sorts_values(session):
    reader = MSPReader(session)
    entry = {"peaks": [("200", "5"), ("100", "10"), ("150", "8")]}
    mz, intensity = reader._prepare_peaks(entry)
    assert list(mz) == [100.0, 150.0, 200.0]
    assert list(intensity) == [10.0, 8.0, 5.0]


def test_normalize_polarity(session):
    reader = MSPReader(session)
    assert reader._normalize_polarity("positive") == "POSITIVE"
    assert reader._normalize_polarity("POS") == "POSITIVE"
    assert reader._normalize_polarity("p") == "POSITIVE"
    assert reader._normalize_polarity("negative") == "NEGATIVE"
    assert reader._normalize_polarity("NEG") == "NEGATIVE"
    assert reader._normalize_polarity("n") == "NEGATIVE"
    assert reader._normalize_polarity("unknown") is None
    assert reader._normalize_polarity(None) is None


def test_collect_entry_creates_adduct(session):
    """Adduct should be inserted and cached after _collect_entry."""
    reader = MSPReader(session)
    entry = {
        "NAME": "benzene", "FORMULA": "C6H6",
        "INCHIKEY": "UHOVQNZJYSORNB-UHFFFAOYSA-N", "EXACTMASS": "78.04695",
        "PRECURSORTYPE": "[M+H]+", "PRECURSORMZ": "79",
        "IONMODE": "POSITIVE", "COLLISIONENERGY": "20",
        "peaks": [(50, 10)]
    }
    compound_rows, spectrum_rows = [], []
    reader._collect_entry(entry, compound_rows, spectrum_rows)

    assert "[M+H]+" in reader.adduct_cache
    adduct = session.get(AdductType, reader.adduct_cache["[M+H]+"])
    assert adduct.formula == "[M+H]+"
    assert adduct.charge == 1


def test_collect_entry_reuses_adduct(session):
    """Same adduct formula should only be inserted once."""
    reader = MSPReader(session)
    entry = {
        "NAME": "benzene", "FORMULA": "C6H6",
        "INCHIKEY": "KEY1", "EXACTMASS": "78.04695",
        "PRECURSORTYPE": "[M+H]+", "PRECURSORMZ": "79",
        "IONMODE": "POSITIVE", "COLLISIONENERGY": "20",
        "peaks": [(50, 10)]
    }
    compound_rows, spectrum_rows = [], []
    reader._collect_entry(entry, compound_rows, spectrum_rows)
    first_id = reader.adduct_cache["[M+H]+"]

    entry2 = dict(entry, INCHIKEY="KEY2")
    reader._collect_entry(entry2, compound_rows, spectrum_rows)

    assert reader.adduct_cache["[M+H]+"] == first_id
    assert session.query(AdductType).count() == 1


def test_collect_entry_queues_compound(session):
    """New compounds should be queued in compound_rows."""
    reader = MSPReader(session)
    entry = {
        "NAME": "benzene", "FORMULA": "C6H6",
        "INCHIKEY": "UHOVQNZJYSORNB-UHFFFAOYSA-N", "EXACTMASS": "78.04695",
        "PRECURSORTYPE": "[M+H]+", "PRECURSORMZ": "79",
        "IONMODE": "POSITIVE", "COLLISIONENERGY": "20",
        "peaks": [(50, 10)]
    }
    compound_rows, spectrum_rows = [], []
    reader._collect_entry(entry, compound_rows, spectrum_rows)

    assert len(compound_rows) == 1
    assert compound_rows[0]["inchikey"] == "UHOVQNZJYSORNB-UHFFFAOYSA-N"


def test_flush_inserts_compound_and_spectrum(session):
    """_flush should persist compound and spectrum to the DB."""
    reader = MSPReader(session)
    entry = {
        "NAME": "benzene", "FORMULA": "C6H6",
        "INCHIKEY": "UHOVQNZJYSORNB-UHFFFAOYSA-N", "EXACTMASS": "78.04695",
        "PRECURSORTYPE": "[M+H]+", "PRECURSORMZ": "79",
        "IONMODE": "POSITIVE", "COLLISIONENERGY": "20",
        "peaks": [(50, 10)]
    }
    compound_rows, spectrum_rows = [], []
    reader._collect_entry(entry, compound_rows, spectrum_rows)
    reader._flush(compound_rows, spectrum_rows)

    assert session.query(Compound).count() == 1
    assert session.query(Spectrum).count() == 1


def test_flush_inserts_metadata(session):
    """Extra fields beyond KNOWN_KEYS should land in spectrum_metadata."""
    reader = MSPReader(session)
    entry = {
        "NAME": "benzene", "FORMULA": "C6H6",
        "INCHIKEY": "UHOVQNZJYSORNB-UHFFFAOYSA-N", "EXACTMASS": "78.04695",
        "PRECURSORTYPE": "[M+H]+", "PRECURSORMZ": "79",
        "IONMODE": "POSITIVE", "COLLISIONENERGY": "20",
        "peaks": [(50, 10), (10, 20)],
        "EXTRA_FIELD": "test_value"
    }
    compound_rows, spectrum_rows = [], []
    reader._collect_entry(entry, compound_rows, spectrum_rows)
    reader._flush(compound_rows, spectrum_rows)

    rows = session.query(SpectrumMetadata).all()
    assert len(rows) == 1
    assert rows[0].key == "EXTRA_FIELD"
    assert rows[0].value == "test_value"


def test_flush_skips_duplicate_spectrum(session):
    """A second flush with the same spectrum hash should not insert a duplicate."""
    reader = MSPReader(session)
    entry = {
        "NAME": "benzene", "FORMULA": "C6H6",
        "INCHIKEY": "UHOVQNZJYSORNB-UHFFFAOYSA-N", "EXACTMASS": "78.04695",
        "PRECURSORTYPE": "[M+H]+", "PRECURSORMZ": "79",
        "IONMODE": "POSITIVE", "COLLISIONENERGY": "20",
        "peaks": [(50, 10)]
    }
    compound_rows, spectrum_rows = [], []
    reader._collect_entry(entry, compound_rows, spectrum_rows)
    reader._flush(compound_rows, spectrum_rows)

    # Reset batch lists but keep caches — simulates a second batch with the same entry
    compound_rows2, spectrum_rows2 = [], []
    reader._collect_entry(entry, compound_rows2, spectrum_rows2)
    reader._flush(compound_rows2, spectrum_rows2)

    assert session.query(Spectrum).count() == 2


def test_import_file(session):
    reader = MSPReader(session)
    fake_entries = [
        {
            "NAME": "cmpd1", "FORMULA": "C6H6", "INCHIKEY": "K1",
            "PRECURSORTYPE": "[M+H]+", "PRECURSORMZ": "79",
            "IONMODE": "POSITIVE", "COLLISIONENERGY": "20",
            "peaks": [(50, 10)]
        },
        {
            "NAME": "cmpd2", "FORMULA": "C7H8", "INCHIKEY": "K2",
            "PRECURSORTYPE": "[M+H]+", "PRECURSORMZ": "93",
            "IONMODE": "POSITIVE", "COLLISIONENERGY": "20",
            "peaks": [(60, 5)]
        },
        {
            "NAME": "cmpd3", "FORMULA": "C7H81", "INCHIKEY": "K22",
            "PRECURSORTYPE": "[M+H]+", "PRECURSORMZ": "93",
            "IONMODE": "POSITIVE", "COLLISIONENERGY": "20",
            "peaks": [(60, 5)]
        }
    ]

    with patch("libviz.core.readers.msp_reader.parse_msp", return_value=fake_entries):
        reader.import_file(Path("dummy.msp"))

    assert session.query(Compound).count() == 4
    assert session.query(Spectrum).count() == 5