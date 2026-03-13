import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from libviz.core.db.models import LibraryMetadata


class TestLibraryMetadata:
    def test_create_library_metadata(self, session):
        lib_meta = LibraryMetadata(
            name="Test Library",
        )
        session.add(lib_meta)
        session.commit()

        assert lib_meta.id is not None
        assert lib_meta.name == "Test Library"
        assert lib_meta.added_on is not None
        assert lib_meta.last_updated_on is not None

    def test_name_not_nullable(self, session):
        lib_meta = LibraryMetadata(
        )
        session.add(lib_meta)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_added_on_auto_timestamp(self, session):
        lib_meta = LibraryMetadata(
            name="Test",
        )

        session.add(lib_meta)
        session.commit()

        assert abs((datetime.now() - lib_meta.added_on).total_seconds()) < 2

    def test_last_updated_on_auto_timestamp(self, session):
        before = datetime.now()
        lib_meta = LibraryMetadata(
            name="Test",
        )
        session.add(lib_meta)
        session.commit()

        assert abs((datetime.now() - lib_meta.last_updated_on).total_seconds()) < 2


    def test_empty_strings(self, session):
        lib_meta = LibraryMetadata(
            name="",
        )
        session.add(lib_meta)
        session.commit()
        assert lib_meta.name == ""

    def test_unicode_name(self, session):
        lib_meta = LibraryMetadata(
            name="Test Library 中文",
        )
        session.add(lib_meta)
        session.commit()
        assert lib_meta.name == "Test Library 中文"