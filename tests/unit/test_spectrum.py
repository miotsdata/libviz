import numpy as np
import pytest
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from libviz.services.db.models import Spectrum, Compound, AdductType, calculate_spectrum_hash


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

# ------------ TESTS
class TestSpectrum:
    def test_create_spectrum(self, session):
        # Create required related objects
        compound = get_or_create_compound(session, "SPECTRUMINCHI")
        adduct = get_or_create_adduct(session)
        session.add_all([compound, adduct])
        session.commit()

        spectrum = Spectrum(
            compound_id=compound.id,
            precursor_mz=181.0,
            adduct_type_id=adduct.id,
            polarity="positive",
            collision_energy=25.0,
            mz_array=b'\x00\x00\x80\x3f\x00\x00\x00\x40',  # 1.0, 2.0
            intensity_array=b'\x00\x00\x80\x3f\x00\x00\x00\x40',  # 1.0, 2.0
            spectrum_hash="testhash123"
        )
        session.add(spectrum)
        session.commit()

        assert spectrum.id is not None
        assert spectrum.compound_id == compound.id
        assert spectrum.precursor_mz == 181.0
        assert spectrum.adduct_type_id == adduct.id
        assert spectrum.polarity == "positive"
        assert spectrum.collision_energy == 25.0
        assert spectrum.added_on is not None

    def test_unique_constraint(self, session):
        compound = get_or_create_compound(session, "SPECTRUMINCHI")
        adduct = get_or_create_adduct(session)
        session.add_all([compound, adduct])
        session.commit()

        spectrum1 = Spectrum(
            compound_id=compound.id,
            precursor_mz=181.0,
            adduct_type_id=adduct.id,
            polarity="positive",
            collision_energy=25.0,
            mz_array=b'\x00\x00\x80\x3f',
            intensity_array=b'\x00\x00\x80\x3f',
            spectrum_hash="samehash"
        )
        spectrum2 = Spectrum(
            compound_id=compound.id,
            precursor_mz=181.0,
            adduct_type_id=adduct.id,
            polarity="positive",
            collision_energy=25.0,
            mz_array=b'\x00\x00\x80\x3f',
            intensity_array=b'\x00\x00\x80\x3f',
            spectrum_hash="samehash"
        )
        session.add(spectrum1)
        session.commit()

        session.add(spectrum2)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_from_arrays_method(self, session):
        compound = get_or_create_compound(session, "SPECTRUMINCHI")
        adduct = get_or_create_adduct(session)
        session.add_all([compound, adduct])
        session.commit()

        mz = np.array([2.0, 1.0, 3.0], dtype=np.float32)  # unsorted
        intensity = np.array([20.0, 10.0, 30.0], dtype=np.float32)

        spectrum = Spectrum.from_arrays(
            compound_id=compound.id,
            precursor_mz=181.0,
            adduct_type_id=adduct.id,
            polarity="positive",
            collision_energy=25.0,
            mz=mz,
            intensity=intensity
        )
        session.add(spectrum)
        session.commit()

        # Check that mz is sorted
        mz_np = spectrum.mz_numpy()
        intensity_np = spectrum.intensity_numpy()
        assert np.allclose(mz_np, [1.0, 2.0, 3.0])
        assert np.allclose(intensity_np, [10.0, 20.0, 30.0])

    def test_mz_numpy_method(self, session):
        compound = get_or_create_compound(session, "SPECTRUMINCHI")
        adduct = get_or_create_adduct(session)
        session.add_all([compound, adduct])
        session.commit()

        mz_data = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        spectrum = Spectrum(
            compound_id=compound.id,
            precursor_mz=181.0,
            adduct_type_id=adduct.id,
            polarity="positive",
            collision_energy=25.0,
            mz_array=mz_data.tobytes(),
            intensity_array=b'\x00\x00\x80\x3f\x00\x00\x00\x40\x00\x00\x40\x40',
            spectrum_hash="testhash"
        )
        session.add(spectrum)
        session.commit()

        mz_np = spectrum.mz_numpy()
        assert np.allclose(mz_np, [1.0, 2.0, 3.0])

    def test_intensity_numpy_method(self, session):
        compound = get_or_create_compound(session, "SPECTRUMINCHI")
        adduct = get_or_create_adduct(session)
        session.add_all([compound, adduct])
        session.commit()

        intensity_data = np.array([100.0, 20.0, 30.0], dtype=np.float32)
        spectrum = Spectrum(
            compound_id=compound.id,
            precursor_mz=181.0,
            adduct_type_id=adduct.id,
            polarity="positive",
            collision_energy=25.0,
            mz_array=b'\x00\x00\x80\x3f\x00\x00\x00\x40\x00\x00\x40\x40',
            intensity_array=intensity_data.tobytes(),
            spectrum_hash="testhash2"
        )
        session.add(spectrum)
        session.commit()

        intensity_np = spectrum.intensity_numpy()
        assert np.allclose(intensity_np, [100.0, 20.0, 30.0])

    def test_calculate_spectrum_hash(self):
        mz = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        intensity = np.array([10.0, 20.0, 30.0], dtype=np.float32)
        hash1 = calculate_spectrum_hash(mz, intensity)
        hash2 = calculate_spectrum_hash(mz, intensity)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex

        # Different data gives different hash
        mz2 = np.array([1.0, 2.0, 4.0], dtype=np.float32)
        hash3 = calculate_spectrum_hash(mz2, intensity)
        assert hash1 != hash3

    def test_relationships(self, session):
        compound = get_or_create_compound(session, "SPECTRUMINCHI")
        adduct = get_or_create_adduct(session)
        session.add_all([compound, adduct])
        session.commit()

        spectrum = Spectrum(
            compound_id=compound.id,
            precursor_mz=181.0,
            adduct_type_id=adduct.id,
            polarity="positive",
            collision_energy=25.0,
            mz_array=b'\x00\x00\x80\x3f',
            intensity_array=b'\x00\x00\x80\x3f',
            spectrum_hash="testhash3"
        )
        session.add(spectrum)
        session.commit()

        assert spectrum.compound == compound
        assert spectrum.adduct_type == adduct
        assert spectrum.spectrum_metadata == []

    def test_polarity_indexed(self, session):
        compound = get_or_create_compound(session, "SPECTRUMINCHI")
        adduct = get_or_create_adduct(session)
        session.add_all([compound, adduct])
        session.commit()

        spectrum = Spectrum(
            compound_id=compound.id,
            precursor_mz=181.0,
            adduct_type_id=adduct.id,
            polarity="negative",
            collision_energy=25.0,
            mz_array=b'\x00\x00\x80\x3f',
            intensity_array=b'\x00\x00\x80\x3f',
            spectrum_hash="testhash"
        )
        session.add(spectrum)
        session.commit()

        found = session.query(Spectrum).filter_by(polarity="negative").first()
        assert found is not None

    def test_collision_energy_indexed(self, session):
        compound = get_or_create_compound(session, "SPECTRUMINCHI")
        adduct = get_or_create_adduct(session)
        session.add_all([compound, adduct])
        session.commit()

        spectrum = Spectrum(
            compound_id=compound.id,
            precursor_mz=181.0,
            adduct_type_id=adduct.id,
            polarity="positive",
            collision_energy=35.0,
            mz_array=b'\x00\x00\x80\x3f',
            intensity_array=b'\x00\x00\x80\x3f',
            spectrum_hash="testhash"
        )
        session.add(spectrum)
        session.commit()

        found = session.query(Spectrum).filter_by(collision_energy=35.0).first()
        assert found is not None

    def test_precursor_mz_indexed(self, session):
        compound = get_or_create_compound(session, "SPECTRUMINCHI")
        adduct = get_or_create_adduct(session)
        session.add_all([compound, adduct])
        session.commit()

        spectrum = Spectrum(
            compound_id=compound.id,
            precursor_mz=200.0,
            adduct_type_id=adduct.id,
            polarity="positive",
            collision_energy=25.0,
            mz_array=b'\x00\x00\x80\x3f',
            intensity_array=b'\x00\x00\x80\x3f',
            spectrum_hash="testhash4"
        )
        session.add(spectrum)
        session.commit()

        found = session.query(Spectrum).filter_by(precursor_mz=200.0).first()
        assert found is not None

    def test_spectrum_hash_indexed(self, session):
        compound = get_or_create_compound(session, "SPECTRUMINCHI")
        adduct = get_or_create_adduct(session)
        session.add_all([compound, adduct])
        session.commit()

        spectrum = Spectrum(
            compound_id=compound.id,
            precursor_mz=181.0,
            adduct_type_id=adduct.id,
            polarity="positive",
            collision_energy=25.0,
            mz_array=b'\x00\x00\x80\x3f',
            intensity_array=b'\x00\x00\x80\x3f',
            spectrum_hash="uniquehash"
        )
        session.add(spectrum)
        session.commit()

        found = session.query(Spectrum).filter_by(spectrum_hash="uniquehash").first()
        assert found is not None

    def test_added_on_auto_timestamp(self, session):
        compound = get_or_create_compound(session, "SPECTRUMINCHI")
        adduct = get_or_create_adduct(session)
        session.add_all([compound, adduct])
        session.commit()

        spectrum = Spectrum(
            compound_id=compound.id,
            precursor_mz=181.0,
            adduct_type_id=adduct.id,
            polarity="positive",
            collision_energy=25.0,
            mz_array=b'\x00\x00\x80\x3f',
            intensity_array=b'\x00\x00\x80\x3f',
            spectrum_hash="testhash5"
        )
        session.add(spectrum)
        session.commit()

        assert abs((datetime.now() - spectrum.added_on).total_seconds()) < 2

    def test_foreign_key_constraints(self, session):
        # Invalid compound_id
        spectrum = Spectrum(
            compound_id=999,
            precursor_mz=181.0,
            adduct_type_id=1,
            polarity="positive",
            collision_energy=25.0,
            mz_array=b'\x00\x00\x80\x3f',
            intensity_array=b'\x00\x00\x80\x3f',
            spectrum_hash="testhash"
        )
        session.add(spectrum)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_not_nullable_fields(self, session):
        compound = get_or_create_compound(session, "SPECTRUMINCHI")
        adduct = get_or_create_adduct(session)
        session.add_all([compound, adduct])
        session.commit()

        # Test precursor_mz not nullable
        spectrum = Spectrum(
            compound_id=compound.id,
            adduct_type_id=adduct.id,
            polarity="positive",
            collision_energy=25.0,
            mz_array=b'\x00\x00\x80\x3f',
            intensity_array=b'\x00\x00\x80\x3f',
            spectrum_hash="testhash"
        )
        session.add(spectrum)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_polarity_values(self, session):
        compound = get_or_create_compound(session, "SPECTRUMINCHI")
        adduct = get_or_create_adduct(session)
        session.add_all([compound, adduct])
        session.commit()

        # Test various polarity values
        for pol in ["positive", "negative", "neutral"]:
            spectrum = Spectrum(
                compound_id=compound.id,
                precursor_mz=181.0,
                adduct_type_id=adduct.id,
                polarity=pol,
                collision_energy=25.0,
                mz_array=b'\x00\x00\x80\x3f',
                intensity_array=b'\x00\x00\x80\x3f',
                spectrum_hash=f"hash{pol}"
            )
            session.add(spectrum)
            session.commit()

    def test_collision_energy_zero(self, session):
        compound = get_or_create_compound(session, "SPECTRUMINCHI")
        adduct = get_or_create_adduct(session)
        session.add_all([compound, adduct])
        session.commit()

        spectrum = Spectrum(
            compound_id=compound.id,
            precursor_mz=181.0,
            adduct_type_id=adduct.id,
            polarity="positive",
            collision_energy=0.0,
            mz_array=b'\x00\x00\x80\x3f',
            intensity_array=b'\x00\x00\x80\x3f',
            spectrum_hash="zerohash"
        )
        session.add(spectrum)
        session.commit()
        assert spectrum.collision_energy == 0.0

    def test_large_arrays(self, session):
        compound = get_or_create_compound(session, "SPECTRUMINCHI")
        adduct = get_or_create_adduct(session)
        session.add_all([compound, adduct])
        session.commit()

        # Large arrays
        mz = np.random.rand(10000).astype(np.float32)
        intensity = np.random.rand(10000).astype(np.float32)

        spectrum = Spectrum.from_arrays(
            compound_id=compound.id,
            precursor_mz=181.0,
            adduct_type_id=adduct.id,
            polarity="positive",
            collision_energy=25.0,
            mz=mz,
            intensity=intensity
        )
        session.add(spectrum)
        session.commit()

        assert len(spectrum.mz_numpy()) == 10000
        assert len(spectrum.intensity_numpy()) == 10000