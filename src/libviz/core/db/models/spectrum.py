import hashlib
import numpy as np

from sqlalchemy import CheckConstraint, Column, Integer, String, Float, DateTime, ForeignKey, LargeBinary, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime

from libviz.core.db import Base

class Spectrum(Base):
    __tablename__ = "spectrum"

    id = Column(Integer, primary_key=True)
    compound_id = Column(Integer, ForeignKey("compound.id"), nullable=False, index=True)
    precursor_mz = Column(Float, index=True, nullable=False)
    adduct_type_id = Column(Integer, ForeignKey("adduct_type.id"), nullable=False, index=True)
    polarity = Column(String, CheckConstraint("polarity IN ('POSITIVE', 'NEGATIVE')"), nullable=True, index=True)
    collision_energy = Column(Float, index=True, nullable=False)
    rt = Column(Float, index=True, nullable=True)  # retention time, minutes; NULL = unknown
    mz_array = Column(LargeBinary, nullable=False)
    intensity_array = Column(LargeBinary, nullable=False)
    added_on = Column(
        DateTime(timezone=True),
        default=datetime.now,
        nullable=False
    )
    spectrum_hash = Column(String(64), nullable=False, index=True)

    compound = relationship("Compound", back_populates="spectra")
    adduct_type = relationship("AdductType", back_populates="spectra")
    spectrum_metadata = relationship(
        "SpectrumMetadata",
        back_populates="spectrum",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "compound_id",
            "adduct_type_id",
            "polarity",
            "collision_energy",
            "spectrum_hash",
            name="uq_spectrum_identity"
        ),
    )

    @classmethod
    def from_arrays(
        cls,
        *,
        compound_id: int,
        precursor_mz: float,
        adduct_type_id: int,
        polarity: str,
        collision_energy: float,
        mz: np.ndarray,
        intensity: np.ndarray,
        rt: float | None = None,
    ):
        
        mz = np.asarray(mz, dtype="<f4")
        intensity = np.asarray(intensity, dtype="<f4")
        order = np.argsort(mz)
        mz = np.round(mz[order], 4)
        intensity = np.round(intensity[order], 2)


        return cls(
            compound_id=compound_id,
            precursor_mz=precursor_mz,
            adduct_type_id=adduct_type_id,
            polarity=polarity,
            collision_energy=collision_energy,
            rt=rt,
            mz_array=mz.tobytes(),
            intensity_array=intensity.tobytes(),
            spectrum_hash=calculate_spectrum_hash(mz, intensity),
        )

    def mz_numpy(self) -> np.ndarray:
        return np.frombuffer(self.mz_array, dtype="<f4")

    def intensity_numpy(self) -> np.ndarray:
        return np.frombuffer(self.intensity_array, dtype="<f4")


def calculate_spectrum_hash(mz: np.ndarray, intensity: np.ndarray) -> str:
    h = hashlib.sha256()
    h.update(np.asarray(mz, dtype="<f4").tobytes())
    h.update(np.asarray(intensity, dtype="<f4").tobytes())
    return h.hexdigest()
