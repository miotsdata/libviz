from libviz.chore.models import PrecursorType
import pytest

def test_create_precursor_type(session):
    pt = PrecursorType(
        formula="[M+H]+",
        mass=1.007276,
    )
    session.add(pt)
    session.commit()

    assert pt.id is not None

def test_unique_formula(session):
    pt1 = PrecursorType(
        formula="[M+Na]+",
        mass=22.99,
    )
    pt2 = PrecursorType(
        formula="[M+Na]+",
        mass=22.99,
    )

    session.add(pt1)
    session.commit()

    session.add(pt2)
    with pytest.raises(Exception):
        session.commit()