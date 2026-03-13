from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

from libviz.core.db import Base

class LibraryMetadata(Base):
    __tablename__ = "library_metadata"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    added_on = Column(
        DateTime(timezone=True),
        default=datetime.now,
        nullable=False
    )
    last_updated_on = Column(
        DateTime(timezone=True),
        default=datetime.now,
        onupdate=datetime.now,
        nullable=False
    )
