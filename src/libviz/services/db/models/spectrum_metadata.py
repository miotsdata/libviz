from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from libviz.services.db.extensions import Base

class SpectrumMetadata(Base):
    __tablename__ = "spectrum_metadata"

    id = Column(Integer, primary_key=True)
    spectrum_id = Column(Integer, ForeignKey("spectrum.id"), nullable=False)
    key = Column(String, nullable=False, index=True)
    value = Column(String, nullable=False)

    spectrum = relationship("Spectrum", back_populates="spectrum_metadata")
