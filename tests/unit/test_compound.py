from libviz.chore.models import Compound
import pytest

def test_create_compound(session):
    c = Compound(
        name="Glucose",
        formula="C6H12O6",
        inchikey="WQZGKKKJIJFFOK-GASJEMHNSA-N",
        exact_mass=180.0634,
    )
    session.add(c)
    session.commit()

    assert c.id is not None
    assert c.added_on is not None


def test_unique_inchikey(session):
    c1 = Compound(
        name="A",
        formula="X",
        inchikey="UNIQUE",
        exact_mass=1.0,
    )
    c2 = Compound(
        name="B",
        formula="Y",
        inchikey="UNIQUE",
        exact_mass=2.0,
    )

    session.add(c1)
    session.commit()

    session.add(c2)
    with pytest.raises(Exception):
        session.commit()
