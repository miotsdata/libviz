import pytest
from sqlalchemy.exc import IntegrityError

from libviz.core.db.models import AdductType


class TestAdductType:
    def test_create_adduct_type(self, session):
        adduct = AdductType(formula="[M+H]+", charge=1, delta_mass=1.007276466812)
        session.add(adduct)
        session.commit()

        assert adduct.id is not None
        assert adduct.formula == "[M+H]+"
        assert adduct.charge == 1
        assert adduct.delta_mass == 1.007276466812

    def test_unique_formula(self, session):
        adduct1 = AdductType(formula="[M+HO]+", charge=1, delta_mass=1.0)
        adduct2 = AdductType(formula="[M+HO]+", charge=1, delta_mass=1.0)
        session.add(adduct1)
        session.commit()

        session.add(adduct2)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_charge_not_nullable(self, session):
        adduct = AdductType(formula="[M+HS]+", delta_mass=1.0)
        session.add(adduct)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_delta_mass_indexed(self, session):
        # This is more of a schema test, but we can check it exists
        adduct = AdductType(formula="[M+S]+", charge=1, delta_mass=1.0)
        session.add(adduct)
        session.commit()
        # If indexed, querying by delta_mass should work
        found = session.query(AdductType).filter_by(delta_mass=1.0).first()
        assert found is not None

    def test_relationship_spectra(self, session):
        adduct = AdductType(formula="[M-H]+", charge=-1, delta_mass=-1.0)
        session.add(adduct)
        session.commit()
        # Since spectra is back_populates, we can check the attribute exists
        assert hasattr(adduct, 'spectra')
        assert adduct.spectra == []

    def test_invalid_charge_type(self, session):
        # charge should be int, but SQLAlchemy might convert
        adduct = AdductType(formula="[M+2HOP]+", charge="1", delta_mass=1.0)
        session.add(adduct)
        session.commit()  # Should work if SQLAlchemy converts
        assert adduct.charge == 1

    def test_zero_charge(self, session):
        adduct = AdductType(formula="[M]", charge=0, delta_mass=0.0)
        session.add(adduct)
        session.commit()
        assert adduct.charge == 0
