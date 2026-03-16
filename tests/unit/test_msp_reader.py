from libviz.core.readers.msp_reader import MSPReader
from libviz.core.db.models import AdductType, Compound, Spectrum, SpectrumMetadata
from unittest.mock import patch
import numpy as np

def test_prepare_peaks_sorts_values(session):

    reader = MSPReader(session)

    entry = {
        "peaks": [
            ("200", "5"),
            ("100", "10"),
            ("150", "8")
        ]
    }

    mz, intensity = reader._prepare_peaks(entry)

    assert list(mz) == [100.0, 150.0, 200.0]
    assert list(intensity) == [10.0, 8.0, 5.0]



def test_create_adduct(session):

    reader = MSPReader(session)

    entry = {"PRECURSORTYPE": "[M+H]+"}

    adduct_id = reader._get_or_create_adduct(entry)

    adduct = session.get(AdductType, adduct_id)

    assert adduct.formula == "[M+H]+"
    assert adduct.charge == 1


def test_reuse_existing_adduct(session):

    reader = MSPReader(session)

    entry = {"PRECURSORTYPE": "[M+H]+"}

    a1 = reader._get_or_create_adduct(entry)
    a2 = reader._get_or_create_adduct(entry)

    assert a1 == a2



def test_create_compound(session):

    reader = MSPReader(session)

    entry = {
        "NAME": "benzene",
        "FORMULA": "C6H6",
        "INCHIKEY": "UHOVQNZJYSORNB-UHFFFAOYSA-N",
        "EXACTMASS": "78.04695"
    }

    compound_id = reader._get_or_create_compound(entry)

    compound = session.get(Compound, compound_id)

    assert compound.name == "benzene"
    assert compound.formula == "C6H6"


def test_reuse_existing_compound(session):

    reader = MSPReader(session)

    entry = {
        "NAME": "benzene",
        "FORMULA": "C6H6",
        "INCHIKEY": "TESTKEY"
    }

    c1 = reader._get_or_create_compound(entry)
    c2 = reader._get_or_create_compound(entry)

    assert c1 == c2


def test_insert_spectrum(session):

    reader = MSPReader(session)

    entry = {
        "NAME": "test_compound",
        "FORMULA": "C6H6",
        "INCHIKEY": "UHOVQNZJYSORNB-UHFFFAOYSA-N",
        "EXACTMASS": "78.04695",
        "PRECURSORMZ": "100",
        "IONMODE": "POSITIVE",
        "COLLISIONENERGY": "20",
        "PRECURSORTYPE": "[M+H]+"
    }

    mz = np.array([100.0, 200.0], dtype=np.float32).tobytes()
    intensity = np.array([10.0, 5.0], dtype=np.float32).tobytes()

    c_id = reader._get_or_create_compound(entry)
    adduct_id = reader._get_or_create_adduct(entry)

    spectrum_id = reader._insert_spectrum(
        compound_id=c_id,
        adduct_id=adduct_id,
        entry=entry,
        mz=mz,
        intensity=intensity,
        spectrum_hash="abc"
    )

    spectrum = session.get(Spectrum, spectrum_id)

    assert spectrum is not None
    assert spectrum.precursor_mz == 100.0


def test_duplicate_spectrum_ignored(session):

    reader = MSPReader(session)

    entry = {
        "NAME": "test_compound",
        "FORMULA": "C6H6",
        "INCHIKEY": "UHOVQNZJYSORNB-UHFFFAOYSA-N",
        "EXACTMASS": "78.04695",
        "PRECURSORMZ": "100",
        "IONMODE": "POSITIVE",
        "COLLISIONENERGY": "20",
        "PRECURSORTYPE": "[M+H]+"
    }

    mz = np.array([100.0], dtype=np.float32).tobytes()
    intensity = np.array([10.0], dtype=np.float32).tobytes()

    c_id = reader._get_or_create_compound(entry)
    adduct_id = reader._get_or_create_adduct(entry)

    s1 = reader._insert_spectrum(
        compound_id=c_id,
        adduct_id=adduct_id,
        entry=entry,
        mz=mz,
        intensity=intensity,
        spectrum_hash="samehash"
    )

    s2 = reader._insert_spectrum(
        compound_id=c_id,
        adduct_id=adduct_id,
        entry=entry,
        mz=mz,
        intensity=intensity,
        spectrum_hash="samehash"
    )

    assert s1 is not None
    assert s2 is None


def test_insert_metadata(session):

    reader = MSPReader(session)

    entry = {
        "NAME": "test_compound",
        "FORMULA": "C6H6",
        "INCHIKEY": "UHOVQNZJYSORNB-UHFFFAOYSA-N",
        "EXACTMASS": "78.04695",
        "PRECURSORMZ": "100",
        "IONMODE": "POSITIVE",
        "COLLISIONENERGY": "20",
        "PRECURSORTYPE": "[M+H]+",
        "EXTRA_FIELD": "test"
    }

    mz = np.array([100.0, 200.0], dtype=np.float32).tobytes()
    intensity = np.array([10.0, 5.0], dtype=np.float32).tobytes()

    c_id = reader._get_or_create_compound(entry)
    adduct_id = reader._get_or_create_adduct(entry)

    spectrum_id = reader._insert_spectrum(
        compound_id=c_id,
        adduct_id=adduct_id,
        entry=entry,
        mz=mz,
        intensity=intensity,
        spectrum_hash="abc"
    )

    reader._insert_metadata(spectrum_id, entry)

    rows = session.query(SpectrumMetadata).all()

    assert len(rows) == 1
    assert rows[0].key == "EXTRA_FIELD"
    assert rows[0].value == "test"


def test_insert_entry_full(session):

    reader = MSPReader(session)

    entry = {
        "NAME": "benzene",
        "FORMULA": "C6H6",
        "INCHIKEY": "TESTKEY",
        "PRECURSORTYPE": "[M+H]+",
        "PRECURSORMZ": "79",
        "IONMODE": "POSITIVE",
        "COLLISIONENERGY": "20",
        "peaks": [
            (50, 10),
            (60, 5)
        ]
    }

    reader._insert_entry(entry)

    assert session.query(Compound).count() == 1
    assert session.query(Spectrum).count() == 1


def test_import_file(session):

    reader = MSPReader(session)

    fake_entries = [
        {
            "NAME": "cmpd1",
            "FORMULA": "C6H6",
            "INCHIKEY": "K1",
            "PRECURSORTYPE": "[M+H]+",
            "PRECURSORMZ": "79",
            "IONMODE": "POSITIVE",
            "COLLISIONENERGY": "20",
            "peaks": [(50, 10)]
        },
        {
            "NAME": "cmpd2",
            "FORMULA": "C7H8",
            "INCHIKEY": "K2",
            "PRECURSORTYPE": "[M+H]+",
            "PRECURSORMZ": "93",
            "IONMODE": "POSITIVE",
            "COLLISIONENERGY": "20",
            "peaks": [(60, 5)]
        },
        {
            "NAME": "cmpd3",
            "FORMULA": "C7H81",
            "INCHIKEY": "K22",
            "PRECURSORTYPE": "[M+H]+",
            "PRECURSORMZ": "93",
            "IONMODE": "POSITIVE",
            "COLLISIONENERGY": "20",
            "peaks": [(60, 5)]
        }

    ]

    with patch("libviz.core.readers.msp_reader.parse_msp", return_value=fake_entries):
        reader.import_file("dummy.msp")

    assert session.query(Compound).count() == 3