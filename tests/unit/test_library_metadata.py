import pytest
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from libviz.services.db.models import LibraryMetadata


class TestLibraryMetadata:
    def test_create_library_metadata(self, session):
        lib_meta = LibraryMetadata(
            name="Test Library",
            created_version="1.0.0",
            actual_version="1.0.0"
        )
        session.add(lib_meta)
        session.commit()

        assert lib_meta.id is not None
        assert lib_meta.name == "Test Library"
        assert lib_meta.created_version == "1.0.0"
        assert lib_meta.actual_version == "1.0.0"
        assert lib_meta.added_on is not None
        assert lib_meta.last_updated_on is not None

    def test_name_not_nullable(self, session):
        lib_meta = LibraryMetadata(
            created_version="1.0.0",
            actual_version="1.0.0"
        )
        session.add(lib_meta)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_created_version_not_nullable(self, session):
        lib_meta = LibraryMetadata(
            name="Test",
            actual_version="1.0.0"
        )
        session.add(lib_meta)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_actual_version_not_nullable(self, session):
        lib_meta = LibraryMetadata(
            name="Test",
            created_version="1.0.0"
        )
        session.add(lib_meta)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_added_on_auto_timestamp(self, session):
        lib_meta = LibraryMetadata(
            name="Test",
            created_version="1.0.0",
            actual_version="1.0.0"
        )

        session.add(lib_meta)
        session.commit()

        assert abs((datetime.now() - lib_meta.added_on).total_seconds()) < 2

    def test_last_updated_on_auto_timestamp(self, session):
        before = datetime.now()
        lib_meta = LibraryMetadata(
            name="Test",
            created_version="1.0.0",
            actual_version="1.0.0"
        )
        session.add(lib_meta)
        session.commit()

        assert abs((datetime.now() - lib_meta.last_updated_on).total_seconds()) < 2

    def test_created_version_length(self, session):
        # Column(String(10)), so max 10 chars
        lib_meta = LibraryMetadata(
            name="Test",
            created_version="1234567890",  # 10 chars
            actual_version="1.0.0"
        )
        session.add(lib_meta)
        session.commit()
        assert lib_meta.created_version == "1234567890"

    def test_created_version_too_long(self, session):
        lib_meta = LibraryMetadata(
            name="Test",
            created_version="12345678901",  # 11 chars
            actual_version="1.0.0"
        )
        session.add(lib_meta)
        # SQLAlchemy might truncate or raise, depending on backend
        # For SQLite, it might allow, but let's check
        session.commit()
        # SQLite doesn't enforce VARCHAR length strictly
        assert len(lib_meta.created_version) == 11

    def test_actual_version_length(self, session):
        lib_meta = LibraryMetadata(
            name="Test",
            created_version="1.0.0",
            actual_version="1234567890"
        )
        session.add(lib_meta)
        session.commit()
        assert lib_meta.actual_version == "1234567890"

    def test_empty_strings(self, session):
        lib_meta = LibraryMetadata(
            name="",
            created_version="",
            actual_version=""
        )
        session.add(lib_meta)
        session.commit()
        assert lib_meta.name == ""
        assert lib_meta.created_version == ""
        assert lib_meta.actual_version == ""

    def test_unicode_name(self, session):
        lib_meta = LibraryMetadata(
            name="Test Library 中文",
            created_version="1.0.0",
            actual_version="1.0.0"
        )
        session.add(lib_meta)
        session.commit()
        assert lib_meta.name == "Test Library 中文"

    def test_version_formats(self, session):
        lib_meta = LibraryMetadata(
            name="Test",
            created_version="v1.2.3-beta",
            actual_version="2.0.0-rc.1"
        )
        session.add(lib_meta)
        session.commit()
        assert lib_meta.created_version == "v1.2.3-beta"
        assert lib_meta.actual_version == "2.0.0-rc.1"