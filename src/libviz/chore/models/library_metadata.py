from sqlalchemy import Column, Integer, String, DateTime, text

from libviz.chore.extensions import Base

class LibraryMetadata(Base):
    __tablename__ = "library_metadata"

    id = Column(Integer, primary_key=True)
    added_on = Column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False
    )
    created_version = Column(String(10), nullable=False)
    last_updated_on = Column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False
    )
    actual_version = Column(String(10), nullable=False)
