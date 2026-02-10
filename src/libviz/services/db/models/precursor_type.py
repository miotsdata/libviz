from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.orm import relationship

from libviz.services.db.extensions import Base

class PrecursorType(Base):
    __tablename__ = "precursor_type"

    id = Column(Integer, primary_key=True)

    formula = Column(String, unique=True)
    mass = Column(Float, index=True)

    spectra = relationship("Spectrum", back_populates="precursor_type")
