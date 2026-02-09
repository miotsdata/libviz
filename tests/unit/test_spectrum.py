import numpy as np
import pytest

from libviz.chore.models import (
    Compound,
    PrecursorType,
    Spectrum,
    calculate_spectrum_hash,
)

def test_spectrum_from_arrays_roundtrip(session):
    compound = Compound(
        name="Test",
        formula="C",
        inchikey="TESTKEY",
        exact_mass=12.0,
    )
    pt = PrecursorType(formula="[M+H]+", mass=1.007276)

    session.add_all([compound, pt])
    session.commit()

    mz = np.array([100.0, 101.0, 102.0])
    intensity = np.array([10.0, 20.0, 5.0])

    spectrum = Spectrum.from_arrays(
        compound_id=compound.id,
        precursor_mz=101.0,
        precursor_type_id=pt.id,
        polarity="Positive",
        collision_energy=35.0,
        mz=mz,
        intensity=intensity,
    )

    session.add(spectrum)
    session.commit()

    assert spectrum.id is not None
    np.testing.assert_allclose(spectrum.mz_numpy(), mz)
    np.testing.assert_allclose(spectrum.intensity_numpy(), intensity)


def test_spectrum_hash_stable():
    mz = np.array([1.0, 2.0, 3.0])
    intensity = np.array([10, 20, 30])

    h1 = calculate_spectrum_hash(mz, intensity)
    h2 = calculate_spectrum_hash(mz.copy(), intensity.copy())

    assert h1 == h2


def test_unique_spectrum_identity(session):
    compound = Compound(
        name="Test",
        formula="C",
        inchikey="KEY2",
        exact_mass=12.0,
    )
    pt = PrecursorType(formula="[M-H]-", mass=-1.007276)

    session.add_all([compound, pt])
    session.commit()

    mz = np.array([100.0])
    intensity = np.array([50.0])

    s1 = Spectrum.from_arrays(
        compound_id=compound.id,
        precursor_mz=100.0,
        precursor_type_id=pt.id,
        polarity="Negative",
        collision_energy=20.0,
        mz=mz,
        intensity=intensity,
    )

    s2 = Spectrum.from_arrays(
        compound_id=compound.id,
        precursor_mz=100.0,
        precursor_type_id=pt.id,
        polarity="Negative",
        collision_energy=20.0,
        mz=mz,
        intensity=intensity,
    )

    session.add(s1)
    session.commit()

    session.add(s2)
    with pytest.raises(Exception):
        session.commit()
