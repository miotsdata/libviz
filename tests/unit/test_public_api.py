"""The libviz surface MSIAnalyzer relies on (see its annotate.py, plotter.py
and tests/core/unit/conftest.py). Breaking this test breaks MSIAnalyzer."""
from pathlib import Path

import numpy as np

from libviz.core.library import Library
from libviz.core.db.models import AdductType, Spectrum, SpectrumMetadata


def test_msianalyzer_usage(tmp_path):
    lib = Library.create(Path(tmp_path / "lib.db"), name="mock")
    adduct_id = next(a["id"] for a in lib.get_adducts() if a["charge"] > 0)
    lib.add_spectra(
        compound_name="TrueCompound",
        compound_formula="C10H15N5O10P2",
        inchikey="AAAAAAAAAAAAAA-BBBBBBBBBB-N",
        spectra_info={
            "precursor_mz": 428.04,
            "polarity": "POSITIVE",
            "collision_energy": 20.0,
            "mz": np.array([100.0, 200.0]),
            "intensity": np.array([1.0, 2.0]),
        },
        adduct_id=adduct_id,
    )

    lib = Library.load_from_db(Path(tmp_path / "lib.db"))
    assert str(lib.path).endswith("lib.db")

    spectra = lib.get_spectra_in_mz_range(428.0, 428.1, "POSITIVE", convert_arrays=False)
    assert spectra[0]["compound_name"] == "TrueCompound"
    assert isinstance(spectra[0]["mz"], np.ndarray)

    with lib.session_scope() as session:
        sid, formula = (
            session.query(Spectrum.id, AdductType.formula)
            .join(AdductType, AdductType.id == Spectrum.adduct_type_id)
            .one()
        )
        assert formula == "[M+H]+"
        assert session.query(SpectrumMetadata).filter(SpectrumMetadata.spectrum_id.in_([sid])).all() == []
        s = session.query(Spectrum).filter_by(id=sid).one()
        np.testing.assert_allclose(np.frombuffer(s.mz_array, dtype=np.float32), [100.0, 200.0])
        np.testing.assert_allclose(s.mz_numpy(), [100.0, 200.0])
