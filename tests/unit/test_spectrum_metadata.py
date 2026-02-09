from libviz.chore.models import (
    Compound,
    PrecursorType,
    Spectrum,
    SpectrumMetadata,
)
import numpy as np

def test_metadata_relationship(session):
    compound = Compound(
        name="X",
        formula="C",
        inchikey="METAKEY",
        exact_mass=12.0,
    )
    pt = PrecursorType(formula="[M+H]+", mass=1.0)

    session.add_all([compound, pt])
    session.commit()

    spectrum = Spectrum.from_arrays(
        compound_id=compound.id,
        precursor_mz=100.0,
        precursor_type_id=pt.id,
        polarity="Positive",
        collision_energy=30.0,
        mz=np.array([100.0]),
        intensity=np.array([10.0]),
    )

    meta = SpectrumMetadata(
        key="instrument",
        value="Orbitrap",
        spectrum=spectrum,
    )

    session.add(meta)
    session.commit()

    assert spectrum.spectrum_metadata[0].key == "instrument"
    assert spectrum.spectrum_metadata[0].value == "Orbitrap"


def test_metadata_cascade_delete(session):
    compound = Compound(
        name="Y",
        formula="C",
        inchikey="DELKEY",
        exact_mass=12.0,
    )
    pt = PrecursorType(formula="[M+H]-", mass=1.0)

    session.add_all([compound, pt])
    session.commit()

    spectrum = Spectrum.from_arrays(
        compound_id=compound.id,
        precursor_mz=100.0,
        precursor_type_id=pt.id,
        polarity="Positive",
        collision_energy=30.0,
        mz=np.array([100.0]),
        intensity=np.array([10.0]),
    )

    meta = SpectrumMetadata(key="source", value="DDA", spectrum=spectrum)

    session.add_all([spectrum, meta])
    session.commit()

    pre_n_spec_meta = session.query(SpectrumMetadata).count()

    session.delete(spectrum)
    session.commit()

    post_n_spec_meta = session.query(SpectrumMetadata).count()

    assert pre_n_spec_meta == post_n_spec_meta + 1
