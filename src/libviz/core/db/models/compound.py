from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from libviz.core.db import Base

class Compound(Base):
    __tablename__ = "compound"

    id = Column(Integer, primary_key=True)

    name = Column(String(collation="NOCASE"), index=True)
    formula = Column(String, index=True)
    exact_mass = Column(Float, index=True)
    inchikey = Column(String, unique=True, nullable=False)
    smiles = Column(String, index=True)
    pubchem_id = Column(Integer, index=True)
    added_on = Column(
        DateTime(timezone=True),
        default=datetime.now,
        nullable=False
    )


    spectra = relationship("Spectrum", back_populates="compound")
