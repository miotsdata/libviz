from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.orm import relationship

from libviz.core.db import Base

PROTON = 1.007276466812
ELECTRON = 0.000548579909065  # optional, often ignored

COMMON_ADDUCTS = [
    # Positive mode
    {"formula": "[M+H]+",     "charge": 1, "delta": PROTON, "multiplication_factor": 1},
    {"formula": "[M+Na]+",    "charge": 1, "delta": 22.989218, "multiplication_factor": 1},
    {"formula": "[M+K]+",     "charge": 1, "delta": 38.963158, "multiplication_factor": 1},
    {"formula": "[M+NH4]+",   "charge": 1, "delta": 18.033823, "multiplication_factor": 1},

    {"formula": "[M+2H]2+",   "charge": 2, "delta": 2 * PROTON, "multiplication_factor": 1},

    # Negative mode
    {"formula": "[M-H]-",     "charge": -1, "delta": -PROTON, "multiplication_factor": 1},
    {"formula": "[M+Cl]-",    "charge": -1, "delta": 34.969402, "multiplication_factor": 1},
    {"formula": "[M+FA-H]-",  "charge": -1, "delta": 44.998201, "multiplication_factor": 1},
]

class AdductType(Base):
    __tablename__ = "adduct_type"

    id = Column(Integer, primary_key=True)

    formula = Column(String, unique=True)
    charge = Column(Integer, nullable=False, index=True)
    delta_mass = Column(Float, index=True)
    multiplication_factor = Column(Integer, default=1, nullable=False, index=True)

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
                multiplication_factor=p["multiplication_factor"]
            )
        )

    session.commit()
