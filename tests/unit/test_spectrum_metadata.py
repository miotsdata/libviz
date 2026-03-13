import pytest
from sqlalchemy.exc import IntegrityError

from libviz.core.db.models import SpectrumMetadata, Spectrum, Compound, AdductType

# ------------ HELPERS
def get_or_create_compound(session, inchikey="TESTINCHI"):
    compound = session.query(Compound).filter_by(inchikey=inchikey).first()
    if compound is None:
        compound = Compound(
            name="Test Compound",
            formula="C6H12O6",
            inchikey=inchikey,
            exact_mass=180.0
        )
        session.add(compound)
        session.commit()
    return compound


def get_or_create_adduct(session, formula="[M+H]+"):
    adduct = session.query(AdductType).filter_by(formula=formula).first()
    if adduct is None:
        adduct = AdductType(
            formula=formula,
            charge=1,
            delta_mass=1.0
        )
        session.add(adduct)
        session.commit()
    return adduct

def get_or_create_spectrum(session, spectrum_hash = "testhash"):
    spectrum = session.query(Spectrum).filter_by(spectrum_hash=spectrum_hash).first()
    if spectrum is None:
        compound = get_or_create_compound(session, "SPECTRUMINCHI")
        adduct = get_or_create_adduct(session)
        spectrum = Spectrum(
            compound_id=compound.id,
            precursor_mz=100.0,
            adduct_type_id=adduct.id,
            polarity="positive",
            collision_energy=25.0,
            mz_array=b'\x00\x00\x80?',  # float32 for 1.0
            intensity_array=b'\x00\x00\x80?',  # float32 for 1.0
            spectrum_hash="testhash"
        )
        session.add(spectrum)
        session.commit()
    return spectrum

class TestSpectrumMetadata:
    def test_create_spectrum_metadata(self, session):
        spectrum = get_or_create_spectrum(session)

        meta = SpectrumMetadata(
            spectrum_id=spectrum.id,
            key="instrument",
            value="Orbitrap"
        )
        session.add(meta)
        session.commit()

        assert meta.id is not None
        assert meta.spectrum_id == spectrum.id
        assert meta.key == "instrument"
        assert meta.value == "Orbitrap"

    def test_spectrum_id_not_nullable(self, session):
        meta = SpectrumMetadata(
            key="test",
            value="value"
        )
        session.add(meta)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_key_not_nullable(self, session):
        spectrum = get_or_create_spectrum(session)

        meta = SpectrumMetadata(
            spectrum_id=spectrum.id,
            value="value"
        )
        session.add(meta)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_value_not_nullable(self, session):
        spectrum = get_or_create_spectrum(session)

        meta = SpectrumMetadata(
            spectrum_id=spectrum.id,
            key="test"
        )
        session.add(meta)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_key_indexed(self, session):
        spectrum = get_or_create_spectrum(session)

        meta = SpectrumMetadata(
            spectrum_id=spectrum.id,
            key="indexed_key",
            value="value"
        )
        session.add(meta)
        session.commit()

        found = session.query(SpectrumMetadata).filter_by(key="indexed_key").first()
        assert found is not None

    def test_relationship_spectrum(self, session):
        spectrum = get_or_create_spectrum(session)

        meta = SpectrumMetadata(
            spectrum_id=spectrum.id,
            key="test",
            value="value"
        )
        session.add(meta)
        session.commit()

        assert meta.spectrum == spectrum

    def test_cascade_delete_orphan(self, session):
        spectrum = get_or_create_spectrum(session)

        meta = SpectrumMetadata(
            spectrum_id=spectrum.id,
            key="test",
            value="value"
        )
        session.add(meta)
        session.commit()

        # Delete spectrum, metadata should be deleted too
        session.delete(spectrum)
        session.commit()

        found = session.query(SpectrumMetadata).filter_by(id=meta.id).first()
        assert found is None

    def test_multiple_metadata_per_spectrum(self, session):
        spectrum = get_or_create_spectrum(session)

        meta1 = SpectrumMetadata(
            spectrum_id=spectrum.id,
            key="key1",
            value="value1"
        )
        meta2 = SpectrumMetadata(
            spectrum_id=spectrum.id,
            key="key2",
            value="value2"
        )
        session.add_all([meta1, meta2])
        session.commit()

        assert len(spectrum.spectrum_metadata) == 2

    def test_empty_key_value(self, session):
        spectrum = get_or_create_spectrum(session)

        meta = SpectrumMetadata(
            spectrum_id=spectrum.id,
            key="",
            value=""
        )
        session.add(meta)
        session.commit()
        assert meta.key == ""
        assert meta.value == ""

    def test_long_key_value(self, session):
        spectrum = get_or_create_spectrum(session)

        long_string = "a" * 1000
        meta = SpectrumMetadata(
            spectrum_id=spectrum.id,
            key=long_string,
            value=long_string
        )
        session.add(meta)
        session.commit()
        assert meta.key == long_string
        assert meta.value == long_string

    def test_foreign_key_constraint(self, session):
        meta = SpectrumMetadata(
            spectrum_id=999,  # Non-existent spectrum
            key="test",
            value="value"
        )
        session.add(meta)
        with pytest.raises(IntegrityError):
            session.commit()