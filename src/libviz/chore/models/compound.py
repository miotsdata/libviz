from sqlalchemy import Column, Integer, String, Float, DateTime, text
from sqlalchemy.orm import relationship

from libviz.chore.extensions import Base

class Compound(Base):
    __tablename__ = "compound"

    id = Column(Integer, primary_key=True)

    name = Column(String(collation="NOCASE"), index=True)
    formula = Column(String, index=True)
    inchikey = Column(String, unique=True)
    exact_mass = Column(Float, index=True)
    added_on = Column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False
    )

    spectra = relationship("Spectrum", back_populates="compound")
