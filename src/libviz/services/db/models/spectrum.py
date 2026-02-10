import hashlib
import numpy as np

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, LargeBinary, UniqueConstraint, text
from sqlalchemy.orm import relationship

from libviz.chore.extensions import Base

class Spectrum(Base):
    __tablename__ = "spectrum"

    id = Column(Integer, primary_key=True)
    compound_id = Column(Integer, ForeignKey("compound.id"), nullable=False)
    precursor_mz = Column(Float, index=True, nullable=False)
    precursor_type_id = Column(Integer, ForeignKey("precursor_type.id"), nullable=False)
    polarity = Column(String, index=True, nullable=False)
    collision_energy = Column(Float, index=True, nullable=False)
    mz_array = Column(LargeBinary, nullable=False)
    intensity_array = Column(LargeBinary, nullable=False)
    added_on = Column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False
    )
    spectrum_hash = Column(String(64), nullable=False)

    compound = relationship("Compound", back_populates="spectra")
    precursor_type = relationship("PrecursorType", back_populates="spectra")
    spectrum_metadata = relationship(
        "SpectrumMetadata",
        back_populates="spectrum",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "precursor_type_id",
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
        precursor_type_id: int,
        polarity: str,
        collision_energy: float,
        mz: np.ndarray,
        intensity: np.ndarray,
    ):
        mz = np.asarray(mz, dtype=np.float32)
        intensity = np.asarray(intensity, dtype=np.float32)

        return cls(
            compound_id=compound_id,
            precursor_mz=precursor_mz,
            precursor_type_id=precursor_type_id,
            polarity=polarity,
            collision_energy=collision_energy,
            mz_array=mz.tobytes(),
            intensity_array=intensity.tobytes(),
            spectrum_hash=calculate_spectrum_hash(mz, intensity),
        )

    def mz_numpy(self) -> np.ndarray:
        return np.frombuffer(self.mz_array, dtype=np.float32)

    def intensity_numpy(self) -> np.ndarray:
        return np.frombuffer(self.intensity_array, dtype=np.float32)


def calculate_spectrum_hash(mz: np.ndarray, intensity: np.ndarray) -> str:
    h = hashlib.sha256()
    h.update(np.asarray(mz, dtype=np.float32).tobytes())
    h.update(np.asarray(intensity, dtype=np.float32).tobytes())
    return h.hexdigest()
