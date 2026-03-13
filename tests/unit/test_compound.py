import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from libviz.core.db.models import Compound


class TestCompound:
    def test_create_compound(self, session):
        compound = Compound(
            name="Test Compound",
            formula="C6H12O6",
            inchikey="TESTINCHIKEY1234567890",
            exact_mass=180.0634
        )
        session.add(compound)
        session.commit()

        assert compound.id is not None
        assert compound.name == "Test Compound"
        assert compound.formula == "C6H12O6"
        assert compound.inchikey == "TESTINCHIKEY1234567890"
        assert compound.exact_mass == 180.0634
        assert compound.added_on is not None

    def test_unique_inchikey(self, session):
        compound1 = Compound(
            name="Compound1",
            formula="C6H12O6",
            inchikey="UNIQUEINCHIKEY",
            exact_mass=180.0
        )
        compound2 = Compound(
            name="Compound2",
            formula="C7H14O7",
            inchikey="UNIQUEINCHIKEY",
            exact_mass=190.0
        )
        session.add(compound1)
        session.commit()

        session.add(compound2)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_name_case_insensitive_index(self, session):
        compound = Compound(
            name="glucose",
            formula="C6H12O6",
            inchikey="GLUCOSEINCHI",
            exact_mass=180.0
        )
        session.add(compound)
        session.commit()

        # Test that case-insensitive search works (assuming NOCASE collation)
        found = session.query(Compound).filter(Compound.name.ilike("GLUCOSE")).first()
        assert found is not None

    def test_formula_index(self, session):
        compound = Compound(
            name="Test",
            formula="C6H12O6",
            inchikey="FORMULAINCHI",
            exact_mass=180.0
        )
        session.add(compound)
        session.commit()

        found = session.query(Compound).filter_by(formula="C6H12O6").first()
        assert found is not None

    def test_exact_mass_index(self, session):
        compound = Compound(
            name="Test",
            formula="C6H12O6",
            inchikey="MASSINCHI",
            exact_mass=180.0634
        )
        session.add(compound)
        session.commit()

        found = session.query(Compound).filter_by(exact_mass=180.0634).first()
        assert found is not None

    def test_added_on_auto_timestamp(self, session):
        compound = Compound(
            name="Test",
            formula="C6H12O6",
            inchikey="TIMESTAMPINCHI",
            exact_mass=180.0
        )
        session.add(compound)
        session.commit()

        assert abs((datetime.now() - compound.added_on).total_seconds()) < 2

    def test_relationship_spectra(self, session):
        compound = Compound(
            name="Test",
            formula="C6H12O6",
            inchikey="RELATIONINCHI",
            exact_mass=180.0
        )
        session.add(compound)
        session.commit()

        assert hasattr(compound, 'spectra')
        assert compound.spectra == []

    def test_name_nullable(self, session):
        # name is nullable
        compound = Compound(
            formula="C6H12O6",
            inchikey="NULLNAMEINCHI",
            exact_mass=180.0
        )
        session.add(compound)
        session.commit()
        assert compound.name is None

    def test_formula_nullable(self, session):
        compound = Compound(
            name="Test",
            inchikey="NULLFORMINCHI",
            exact_mass=180.0
        )
        session.add(compound)
        session.commit()
        assert compound.formula is None

    def test_exact_mass_nullable(self, session):
        compound = Compound(
            name="Test",
            formula="C6H12O6",
            inchikey="NULLMASSINCHI"
        )
        session.add(compound)
        session.commit()
        assert compound.exact_mass is None

    def test_inchikey_not_nullable(self, session):
        compound = Compound(
            name="Test",
            formula="C6H12O6",
            exact_mass=180.0
        )
        session.add(compound)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_empty_strings(self, session):
        compound = Compound(
            name="",
            formula="",
            inchikey="EMPTYINCHI",
            exact_mass=0.0
        )
        session.add(compound)
        session.commit()
        assert compound.name == ""
        assert compound.formula == ""

    def test_large_exact_mass(self, session):
        compound = Compound(
            name="Large",
            formula="C100H200O100",
            inchikey="LARGEINCHI",
            exact_mass=10000.0
        )
        session.add(compound)
        session.commit()
        assert compound.exact_mass == 10000.0

    def test_negative_exact_mass(self, session):
        compound = Compound(
            name="Negative",
            formula="C",
            inchikey="NEGATIVEINCHI",
            exact_mass=-1.0
        )
        session.add(compound)
        session.commit()
        assert compound.exact_mass == -1.0