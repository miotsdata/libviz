from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.orm import relationship

from libviz.core.db import Base

PROTON = 1.007276466812
ELECTRON = 0.000548579909065  # optional, often ignored

COMMON_ADDUCTS = [
    # Positive mode
    {"formula": "[M+H]+",     "charge": 1, "delta": PROTON},
    {"formula": "[M+Na]+",    "charge": 1, "delta": 22.989218},
    {"formula": "[M+K]+",     "charge": 1, "delta": 38.963158},
    {"formula": "[M+NH4]+",   "charge": 1, "delta": 18.033823},

    {"formula": "[M+2H]2+",   "charge": 2, "delta": 2 * PROTON},

    # Negative mode
    {"formula": "[M-H]-",     "charge": -1, "delta": -PROTON},
    {"formula": "[M+Cl]-",    "charge": -1, "delta": 34.969402},
    {"formula": "[M+FA-H]-",  "charge": -1, "delta": 44.998201},
]

class AdductType(Base):
    __tablename__ = "adduct_type"

    id = Column(Integer, primary_key=True)

    formula = Column(String, unique=True)
    charge = Column(Integer, nullable=False)
    delta_mass = Column(Float, index=True)

    spectra = relationship("Spectrum", back_populates="adduct_type")


def populate_adduct_types(session):

    for p in COMMON_ADDUCTS:
        exists = session.query(AdductType)\
            .filter_by(formula=p["formula"])\
            .one_or_none()

        if exists:
            continue

        session.add(
            AdductType(
                formula=p["formula"],
                charge=p["charge"],
                delta_mass=p["delta"],
            )
        )

    session.commit()
