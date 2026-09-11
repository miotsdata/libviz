import pytest
from unittest.mock import patch, MagicMock
from libviz.core.db.extensions import Base
from libviz.core.library import Library
from libviz.core.db.models import LibraryMetadata, Compound, Spectrum
from sqlalchemy import create_engine, inspect
import sqlite3
from pathlib import Path
import numpy as np

# pylint: disable=redefined-outer-name, protected-access, unused-argument, unused-variable

# ---- helpers ----

def _spectra_info(precursor_mz: float, mz=None, intensity=None) -> dict:
    return {
        "precursor_mz": precursor_mz,
        "polarity": "POSITIVE",
        "collision_energy": 20.0,
        "mz": mz if mz is not None else np.array([50.0, 60.0], dtype=np.float32),
        "intensity": intensity if intensity is not None else np.array([100.0, 50.0], dtype=np.float32),
    }



# ---- fixtures ----

@pytest.fixture
def saved_library(tmp_path, monkeypatch) -> Path:
    """A real on-disk library with two compounds/spectra."""

    fake_entries = [
        {
            "NAME": "cmpd1",
            "FORMULA": "C6H6",
            "INCHIKEY": "K1",
            "PRECURSORTYPE": "[M+H]+",
            "PRECURSORMZ": "79",
            "IONMODE": "POSITIVE",
            "COLLISIONENERGY": "20",
            "peaks": [(50, 10)]
        },
        {
            "NAME": "cmpd2",
            "FORMULA": "C7H8",
            "INCHIKEY": "K2",
            "PRECURSORTYPE": "[M+H]+",
            "PRECURSORMZ": "93",
            "IONMODE": "POSITIVE",
            "COLLISIONENERGY": "20",
            "peaks": [(60, 5)]
        },
        {
            "NAME": "cmpd3",
            "FORMULA": "C7H81",
            "INCHIKEY": "K22",
            "PRECURSORTYPE": "[M+H]+",
            "PRECURSORMZ": "93",
            "IONMODE": "POSITIVE",
            "COLLISIONENERGY": "20",
            "peaks": [(60, 5)]
        }

    ]

    monkeypatch.setattr("libviz.core.readers.msp_reader.parse_msp", lambda _: fake_entries)

    loaded_library = Library.loadFromMSP(Path("dummy.msp"))
    db_path = Path(tmp_path / "test.db")
    loaded_library.save_as_db(db_path)

    return db_path

@pytest.fixture
def loaded_library(saved_library) -> Library:
    """A Library instance loaded from the saved db, ready to query."""
    return Library.load_from_db(saved_library)


@pytest.fixture
def empty_library(tmp_path, monkeypatch):
    monkeypatch.setattr("libviz.core.readers.msp_reader.parse_msp", lambda _: [])

    db_path = tmp_path / "empty.db"
    loaded_library = Library.loadFromMSP(Path("dummy.msp"))
    loaded_library.save_as_db(db_path)

    return db_path

@pytest.fixture
def adduct_id(loaded_library) -> int:
    return loaded_library.get_adducts()[0]["id"] 


@pytest.fixture
def spectra_info():
    return {
        "precursor_mz": 100.0,
        "polarity": "POSITIVE",
        "collision_energy": 20.0,
        "mz": np.array([50.0, 60.0], dtype=np.float32),
        "intensity": np.array([100.0, 50.0], dtype=np.float32),
    }

@pytest.fixture
def two_identical_spectra(loaded_library, adduct_id) -> dict:
    """Two compounds with identical peaks and precursor_mz — should match each other."""
    mz = np.array([50.0, 60.0], dtype=np.float32)
    intensity = np.array([100.0, 50.0], dtype=np.float32)

    loaded_library.add_spectra("aspirin", "C9H8O4", "INCHI-ASPIRIN", _spectra_info(100.0, mz, intensity), adduct_id)
    loaded_library.add_spectra("ibuprofen", "C13H18O2", "INCHI-IBUPROFEN", _spectra_info(100.0, mz, intensity), adduct_id)

    with loaded_library.session_scope() as session:
        s1 = session.query(Spectrum).filter_by(precursor_mz=100.0).first()
        s2 = session.query(Spectrum).filter_by(precursor_mz=100.0).offset(1).first()
        return {"s1_id": s1.id, "s2_id": s2.id}


@pytest.fixture
def unique_spectrum(loaded_library, adduct_id) -> int:
    """One spectrum with unique peaks — no matches."""
    loaded_library.add_spectra(
        "unique_cmpd", "C2H6O", "INCHI-UNIQUE",
        _spectra_info(200.0, np.array([99.0], dtype=np.float32), np.array([999.0], dtype=np.float32)),
        adduct_id
    )
    with loaded_library.session_scope() as session:
        return session.query(Spectrum).filter_by(precursor_mz=200.0).one().id
    

@pytest.fixture
def known_spectrum(loaded_library, adduct_id) -> dict:
    """
    Inserts one spectrum and returns the raw values needed to call
    get_identical_spectra_compounds_by_spectrum_info.
    """
    mz = np.array([55.0, 77.0], dtype=np.float32)
    intensity = np.array([200.0, 100.0], dtype=np.float32)
    loaded_library.add_spectra(
        "known_cmpd", "C6H6", "INCHI-KNOWN",
        _spectra_info(150.0, mz, intensity),
        adduct_id,
    )
    with loaded_library.session_scope() as session:
        s = session.query(Spectrum).filter_by(precursor_mz=150.0).one()
        return {
            "precursor_mz": s.precursor_mz,
            "polarity": s.polarity,
            "hash": s.spectrum_hash,
            "spectrum_id": s.id,
            "compound_name": "known_cmpd",
        }


@pytest.fixture
def two_info_spectra(loaded_library, adduct_id) -> dict:
    """
    Two compounds with identical peaks and precursor_mz — both should appear
    in results when queried by either one's spectrum info.
    """
    mz = np.array([40.0, 80.0], dtype=np.float32)
    intensity = np.array([300.0, 150.0], dtype=np.float32)
    loaded_library.add_spectra(
        "alpha", "C2H6O", "INCHI-ALPHA",
        _spectra_info(120.0, mz, intensity),
        adduct_id,
    )
    loaded_library.add_spectra(
        "beta", "C3H8O", "INCHI-BETA",
        _spectra_info(120.0, mz, intensity),
        adduct_id,
    )
    with loaded_library.session_scope() as session:
        s = session.query(Spectrum).filter_by(precursor_mz=120.0).first()
        return {
            "precursor_mz": s.precursor_mz,
            "polarity": s.polarity,
            "hash": s.spectrum_hash,
        }




# --------------------------------------------
#
# TESTS
#
# --------------------------------------------

def test_library_init(tmp_path):
    lib_path = tmp_path / "test.db"
    loaded_library = Library(name="TestLib", path=lib_path)

    assert loaded_library.name == "TestLib"
    assert loaded_library.path == lib_path
    assert loaded_library.is_temp is True
    assert loaded_library.n_compounds == 0
    assert loaded_library.n_spectra == 0
    assert loaded_library.engine is not None
    assert callable(loaded_library.session_maker)


def test_create_library_full(tmp_path):
    lib_path = tmp_path / "integration_test.db"

    # Create library (runs actual schema upgrade and adduct population)
    loaded_library = Library.create(path=lib_path, name="MyIntegrationLib")

    # Ensure the library object is returned and DB file exists
    assert isinstance(loaded_library, Library)
    assert loaded_library.path.exists()
    assert loaded_library.name == "MyIntegrationLib"

    # Check LibraryMetadata table has the entry
    with loaded_library.session_scope() as session:
        meta = session.query(LibraryMetadata).filter_by(name="MyIntegrationLib").first()
        assert meta is not None
        assert meta.name == "MyIntegrationLib"

    # Optionally check that expected tables exist (adduct types, etc.)
    inspector = inspect(loaded_library.engine)
    expected_tables = ["library_metadata", "adduct_type", "compound", "spectrum", "spectrum_metadata"]
    for table in expected_tables:
        assert table in inspector.get_table_names()


def test_create_existing_library(tmp_path):
    lib_path = tmp_path / "exists.db"
    lib_path.touch()  # create file to simulate existing library

    with pytest.raises(FileExistsError):
        Library.create(path=lib_path, name="ExistsLib")


def test_create_invalid_path():
    with pytest.raises(TypeError):
        Library.create(path=12345, name="InvalidPath")


def test_session_scope_commit(tmp_path):
    lib_path = tmp_path / "session_test.db"
    loaded_library = Library(name="TestSession", path=lib_path)

    # Use session_scope context to simulate commit
    # Patch the Library's Session to return a dummy session with commit/rollback
    with patch.object(loaded_library, "session_maker", return_value=MagicMock(commit=MagicMock(), rollback=MagicMock(), close=MagicMock())) as mock_session:
        with loaded_library.session_scope() as session:
            assert session is not None
        # Ensure commit and close called
        session.commit.assert_called_once()
        session.close.assert_called_once()


def test_save_as_db_type_error(tmp_path):
    loaded_library = Library(name="TestLib", path=tmp_path / "src.db")

    with pytest.raises(TypeError):
        loaded_library.save_as_db(123)


def test_save_as_db_noname_error(tmp_path):
    loaded_library = Library(name="NONAME", path=tmp_path / "src.db")

    with pytest.raises(ValueError):
        loaded_library.save_as_db(tmp_path / "dest.db")


def test_save_as_db_success(tmp_path):
    src_path = tmp_path / "src.db"
    dest_path = tmp_path / "dest.db"

    # create library and a real sqlite file
    loaded_library = Library.create(name="TestLib", path=src_path)

    with sqlite3.connect(src_path) as conn:
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.execute("INSERT INTO test VALUES (1)")
        conn.commit()

    loaded_library.save_as_db(dest_path)

    # destination file exists
    assert dest_path.exists()

    # library internal state updated
    assert loaded_library.path == dest_path
    assert loaded_library.is_temp is False

    # ensure DB content was copied
    with sqlite3.connect(dest_path) as conn:
        result = conn.execute("SELECT id FROM test").fetchone()
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"

    assert result[0] == 1


def test_save_as_db_flushes_engine(tmp_path):
    src_path = tmp_path / "src.db"
    dest_path = tmp_path / "dest2.db"

    loaded_library = Library.create(name="TestLib", path=src_path)

    with sqlite3.connect(src_path) as conn:
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()

    # open a SQLAlchemy connection to ensure engine exists
    with loaded_library.engine.connect() as conn:
        conn.exec_driver_sql("SELECT 1")

    loaded_library.save_as_db(dest_path)

    assert dest_path.exists()


def test_save_as_db_creates_missing_parent_directories(tmp_path):
    """save_as_db no longer goes through sqlite3's backup() API (it hangs
    indefinitely on some network filesystems); the replacement plain-copy
    path also creates the destination's parent directory, which a raw
    sqlite3.connect() to a nonexistent directory could never do."""
    src_path = tmp_path / "src.db"
    dest_path = tmp_path / "nested" / "does" / "not" / "exist" / "dest.db"

    loaded_library = Library.create(name="TestLib", path=src_path)
    loaded_library.save_as_db(dest_path)

    assert dest_path.exists()
    assert loaded_library.path == dest_path


def test_save_as_db_no_leftover_tmp_file(tmp_path):
    """The copy-then-rename should leave no .tmp file behind."""
    src_path = tmp_path / "src.db"
    dest_path = tmp_path / "dest3.db"

    loaded_library = Library.create(name="TestLib", path=src_path)
    loaded_library.save_as_db(dest_path)

    assert not dest_path.with_name(dest_path.name + ".tmp").exists()


def test_load_from_db_returns_library(saved_library):
    loaded_library = Library.load_from_db(saved_library)
    assert isinstance(loaded_library, Library)


def test_load_from_db_is_not_temp(saved_library):
    loaded_library = Library.load_from_db(saved_library)
    assert loaded_library.is_temp is False


def test_load_from_db_counts(saved_library):
    loaded_library = Library.load_from_db(saved_library)
    assert loaded_library.n_compounds == 3
    assert loaded_library.n_spectra == 3


def test_load_from_db_name(saved_library):
    loaded_library = Library.load_from_db(saved_library)
    assert loaded_library.name == "In-memory MSP Library"


def test_load_from_db_path(saved_library):
    loaded_library = Library.load_from_db(saved_library)
    assert loaded_library.path == saved_library


def test_load_from_db_empty_library(empty_library):
    loaded_library = Library.load_from_db(empty_library)
    assert loaded_library.n_compounds == 0
    assert loaded_library.n_spectra == 0


def test_load_from_db_wrong_type_raises():
    with pytest.raises(TypeError):
        Library.load_from_db(123)


def test_load_from_db_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        Library.load_from_db(tmp_path / "nonexistent.db")


def test_load_from_db_no_metadata_raises(tmp_path):
    # A valid SQLite file but with no LibraryMetadata row
    db_path = tmp_path / "bare.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    Base.metadata.create_all(engine)  # creates tables but inserts nothing

    with pytest.raises(ValueError, match="No metadata found"):
        Library.load_from_db(db_path)


def test_get_adducts_returns_list(loaded_library):
    adducts = loaded_library.get_adducts()
    assert isinstance(adducts, list)


def test_get_adducts_returns_dicts(loaded_library):
    adducts = loaded_library.get_adducts()
    assert all(isinstance(a, dict) for a in adducts)


def test_get_adducts_dict_keys(loaded_library):
    adducts = loaded_library.get_adducts()
    expected_keys = {"id", "formula", "charge", "delta_mass", "multiplication_factor"}
    assert all(expected_keys == a.keys() for a in adducts)


def test_get_adducts_contains_mh_plus(loaded_library):
    formulas = [a["formula"] for a in loaded_library.get_adducts()]
    assert "[M+H]+" in formulas


def test_get_adduct_delta_returns_float(loaded_library):
    adduct_id = loaded_library.get_adducts()[0]["id"]
    delta = loaded_library.get_adduct_delta(adduct_id)
    assert isinstance(delta, float)


def test_get_adduct_delta_correct_value(loaded_library):
    adducts = loaded_library.get_adducts()
    mh = next(a for a in adducts if a["formula"] == "[M+H]+")
    delta = loaded_library.get_adduct_delta(mh["id"])
    assert delta == pytest.approx(mh["delta_mass"])


def test_get_adduct_delta_invalid_id_raises(loaded_library):
    with pytest.raises(ValueError, match="not found"):
        loaded_library.get_adduct_delta(99999)


def test_rename_library_changes_name(loaded_library):
    old_name = loaded_library.name
    new_name = "RenamedLib"
    loaded_library.rename_library(new_name)

    assert loaded_library.name == new_name

    # Reload library to check name persisted in DB
    reloaded = Library.load_from_db(loaded_library.path)
    assert reloaded.name == new_name


def test_get_or_insert_creates_new_compound(loaded_library):
    with loaded_library.session_scope() as session:
        compound = loaded_library._get_or_insert_compound_by_inchikey(session, "aspirin", "C9H8O4", "UNIQUE-KEY-001")
        session.flush()
        assert compound.id is not None


def test_get_or_insert_compound_fields(loaded_library):
    with loaded_library.session_scope() as session:
        compound = loaded_library._get_or_insert_compound_by_inchikey(session, "aspirin", "C9H8O4", "UNIQUE-KEY-001")
        assert compound.name == "aspirin"
        assert compound.formula == "C9H8O4"
        assert compound.inchikey == "UNIQUE-KEY-001"


def test_get_or_insert_reuses_existing_compound(loaded_library):
    with loaded_library.session_scope() as session:
        c1 = loaded_library._get_or_insert_compound_by_inchikey(session, "aspirin", "C9H8O4", "UNIQUE-KEY-001")
        session.flush()
        c2 = loaded_library._get_or_insert_compound_by_inchikey(session, "aspirin", "C9H8O4", "UNIQUE-KEY-001")
        assert c1.id == c2.id


def test_get_or_insert_calculates_exact_mass(loaded_library):
    with loaded_library.session_scope() as session:
        compound = loaded_library._get_or_insert_compound_by_inchikey(session, "benzene", "C6H6", "UNIQUE-KEY-002")
        assert compound.exact_mass == pytest.approx(78.04695, abs=1e-4)


def test_get_or_insert_none_inchikey_raises(loaded_library):
    with loaded_library.session_scope() as session:
        with pytest.raises(ValueError, match="inchikey"):
            loaded_library._get_or_insert_compound_by_inchikey(session, "unknown", "C6H6", None)


def test_get_or_insert_empty_inchikey_raises(loaded_library):
    with loaded_library.session_scope() as session:
        with pytest.raises(ValueError, match="inchikey"):
            loaded_library._get_or_insert_compound_by_inchikey(session, "unknown", "C6H6", "")


def test_get_or_insert_none_name_raises(loaded_library):
    with loaded_library.session_scope() as session:
        with pytest.raises(ValueError, match="name"):
            loaded_library._get_or_insert_compound_by_inchikey(session, None, "C6H6", "SOME-KEY")


def test_get_or_insert_empty_name_raises(loaded_library):
    with loaded_library.session_scope() as session:
        with pytest.raises(ValueError, match="name"):
            loaded_library._get_or_insert_compound_by_inchikey(session, "", "C6H6", "SOME-KEY")


def test_get_or_insert_none_formula_raises(loaded_library):
    with loaded_library.session_scope() as session:
        with pytest.raises(ValueError, match="formula"):
            loaded_library._get_or_insert_compound_by_inchikey(session, "unknown", None, "SOME-KEY")


def test_get_or_insert_empty_formula_raises(loaded_library):
    with loaded_library.session_scope() as session:
        with pytest.raises(ValueError, match="formula"):
            loaded_library._get_or_insert_compound_by_inchikey(session, "unknown", "", "SOME-KEY")


def test_add_spectra_creates_compound(loaded_library, adduct_id, spectra_info):
    initial = loaded_library.n_compounds
    loaded_library.add_spectra("aspirin", "C9H8O4", "BSYNRYMUTXBXSQ-UHFFFAOYSA-N", spectra_info, adduct_id)

    with loaded_library.session_scope() as session:
        assert session.query(Compound).count() == initial + 1


def test_add_spectra_creates_spectrum(loaded_library, adduct_id, spectra_info):
    initial = loaded_library.n_spectra
    loaded_library.add_spectra("aspirin", "C9H8O4", "BSYNRYMUTXBXSQ-UHFFFAOYSA-N", spectra_info, adduct_id)

    with loaded_library.session_scope() as session:
        assert session.query(Spectrum).count() == initial + 1


def test_add_spectra_compound_fields(loaded_library, adduct_id, spectra_info):
    loaded_library.add_spectra("aspirin", "C9H8O4", "BSYNRYMUTXBXSQ-UHFFFAOYSA-N", spectra_info, adduct_id)

    with loaded_library.session_scope() as session:
        compound = session.query(Compound).filter_by(inchikey="BSYNRYMUTXBXSQ-UHFFFAOYSA-N").one()
        assert compound.name == "aspirin"
        assert compound.formula == "C9H8O4"


def test_add_spectra_spectrum_fields(loaded_library, adduct_id, spectra_info):
    loaded_library.add_spectra("aspirin", "C9H8O4", "BSYNRYMUTXBXSQ-UHFFFAOYSA-N", spectra_info, adduct_id)

    with loaded_library.session_scope() as session:
        spectrum = session.query(Spectrum).filter_by(precursor_mz=100.0).first()
        assert spectrum.polarity == "POSITIVE"
        assert spectrum.collision_energy == pytest.approx(20.0)


def test_add_spectra_reuses_existing_compound(loaded_library, adduct_id, spectra_info):
    loaded_library.add_spectra("aspirin", "C9H8O4", "BSYNRYMUTXBXSQ-UHFFFAOYSA-N", spectra_info, adduct_id)

    with loaded_library.session_scope() as session:
        count = session.query(Compound).filter_by(inchikey="BSYNRYMUTXBXSQ-UHFFFAOYSA-N").count()
        assert count == 1


# ---- error cases ----

def test_add_spectra_none_adduct_id_raises(loaded_library, spectra_info):
    with pytest.raises(ValueError, match="adduct_id must be an integer"):
        loaded_library.add_spectra("aspirin", "C9H8O4", "BSYNRYMUTXBXSQ-UHFFFAOYSA-N", spectra_info, None)


def test_add_spectra_none_adduct_does_not_create_compound(loaded_library, spectra_info):
    initial_count = None
    with loaded_library.session_scope() as session:
        initial_count = session.query(Compound).count()

    with pytest.raises(ValueError, match="adduct_id must be an integer"):
        loaded_library.add_spectra("aspirin", "C9H8O4", "BSYNRYMUTXBXSQ-UHFFFAOYSA-N", spectra_info, None)

    with loaded_library.session_scope() as session:
        assert session.query(Compound).count() == initial_count


def test_get_compound_id_returns_int(loaded_library, two_identical_spectra):
    compound_id = loaded_library.get_compound_id_from_spectrum_id(two_identical_spectra["s1_id"])
    assert isinstance(compound_id, int)


def test_get_compound_id_correct_value(loaded_library, two_identical_spectra):
    with loaded_library.session_scope() as session:
        spectrum = session.query(Spectrum).filter_by(id=two_identical_spectra["s1_id"]).one()
        expected = spectrum.compound_id

    result = loaded_library.get_compound_id_from_spectrum_id(two_identical_spectra["s1_id"])
    assert result == expected


def test_get_compound_id_invalid_id_raises(loaded_library):
    with pytest.raises(ValueError, match="not found"):
        loaded_library.get_compound_id_from_spectrum_id(99999)


def test_get_identical_spectra_compounds_by_spectrum_id_returns_list(loaded_library, two_identical_spectra):
    result = loaded_library.get_identical_spectra_compounds_by_spectrum_id(two_identical_spectra["s1_id"])
    assert isinstance(result, list)


def test_get_identical_spectra_compounds_by_spectrum_id_finds_match(loaded_library, two_identical_spectra):
    result = loaded_library.get_identical_spectra_compounds_by_spectrum_id(two_identical_spectra["s1_id"])
    assert len(result) == 1


def test_get_identical_spectra_compounds_by_spectrum_id_dict_keys(loaded_library, two_identical_spectra):
    result = loaded_library.get_identical_spectra_compounds_by_spectrum_id(two_identical_spectra["s1_id"])
    assert set(result[0].keys()) == {"id", "name", "formula", "inchikey", "spectrum_id"}


def test_get_identical_spectra_compounds_by_spectrum_id_correct_compound(loaded_library, two_identical_spectra):
    result = loaded_library.get_identical_spectra_compounds_by_spectrum_id(two_identical_spectra["s1_id"])
    names = [c["name"] for c in result]
    assert "ibuprofen" in names


def test_get_identical_spectra_compounds_by_spectrum_id_excludes_self(loaded_library, two_identical_spectra):
    s1_compound_id = loaded_library.get_compound_id_from_spectrum_id(two_identical_spectra["s1_id"])
    result = loaded_library.get_identical_spectra_compounds_by_spectrum_id(two_identical_spectra["s1_id"])
    compound_ids = [c["id"] for c in result]
    assert s1_compound_id not in compound_ids


def test_get_identical_spectra_compounds_by_spectrum_id_no_match(loaded_library, unique_spectrum):
    result = loaded_library.get_identical_spectra_compounds_by_spectrum_id(unique_spectrum)
    assert result == []


def test_get_identical_spectra_compounds_by_spectrum_id_invalid_id_raises(loaded_library):
    with pytest.raises(ValueError, match="not found"):
        loaded_library.get_identical_spectra_compounds_by_spectrum_id(99999)


def test_get_identical_spectra_compounds_by_spectrum_id_symmetry(loaded_library, two_identical_spectra):
    """If s1 matches s2, then s2 should also match s1."""
    from_s1 = loaded_library.get_identical_spectra_compounds_by_spectrum_id(two_identical_spectra["s1_id"])
    from_s2 = loaded_library.get_identical_spectra_compounds_by_spectrum_id(two_identical_spectra["s2_id"])

    ids_from_s1 = {c["id"] for c in from_s1}
    ids_from_s2 = {c["id"] for c in from_s2}

    s1_compound = loaded_library.get_compound_id_from_spectrum_id(two_identical_spectra["s1_id"])
    s2_compound = loaded_library.get_compound_id_from_spectrum_id(two_identical_spectra["s2_id"])

    assert s2_compound in ids_from_s1
    assert s1_compound in ids_from_s2



# ---- get_identical_spectra_compounds_by_spectrum_info ----

class TestGetIdenticalSpectraCompoundsBySpectrumInfo:

    # --- return type / shape ---

    def test_returns_list(self, loaded_library, known_spectrum):
        result = loaded_library.get_identical_spectra_compounds_by_spectrum_info(
            known_spectrum["precursor_mz"],
            known_spectrum["polarity"],
            known_spectrum["hash"],
        )
        assert isinstance(result, list)

    def test_result_items_are_dicts(self, loaded_library, known_spectrum):
        result = loaded_library.get_identical_spectra_compounds_by_spectrum_info(
            known_spectrum["precursor_mz"],
            known_spectrum["polarity"],
            known_spectrum["hash"],
        )
        assert all(isinstance(item, dict) for item in result)

    def test_dict_keys(self, loaded_library, known_spectrum):
        result = loaded_library.get_identical_spectra_compounds_by_spectrum_info(
            known_spectrum["precursor_mz"],
            known_spectrum["polarity"],
            known_spectrum["hash"],
        )
        assert set(result[0].keys()) == {"id", "name", "formula", "inchikey", "spectrum_id"}

    # --- correct content ---

    def test_finds_matching_compound(self, loaded_library, known_spectrum):
        result = loaded_library.get_identical_spectra_compounds_by_spectrum_info(
            known_spectrum["precursor_mz"],
            known_spectrum["polarity"],
            known_spectrum["hash"],
        )
        assert any(c["name"] == known_spectrum["compound_name"] for c in result)

    def test_returns_both_when_two_identical(self, loaded_library, two_info_spectra):
        result = loaded_library.get_identical_spectra_compounds_by_spectrum_info(
            two_info_spectra["precursor_mz"],
            two_info_spectra["polarity"],
            two_info_spectra["hash"],
        )
        names = {c["name"] for c in result}
        assert {"alpha", "beta"} == names

    def test_compound_fields_are_correct(self, loaded_library, known_spectrum):
        result = loaded_library.get_identical_spectra_compounds_by_spectrum_info(
            known_spectrum["precursor_mz"],
            known_spectrum["polarity"],
            known_spectrum["hash"],
        )
        hit = next(c for c in result if c["name"] == known_spectrum["compound_name"])
        assert hit["formula"] == "C6H6"
        assert hit["inchikey"] == "INCHI-KNOWN"
        assert isinstance(hit["spectrum_id"], int)

    def test_includes_self(self, loaded_library, known_spectrum):
        """Unlike get_by_spectrum_id, this method has no self-exclusion."""
        result = loaded_library.get_identical_spectra_compounds_by_spectrum_info(
            known_spectrum["precursor_mz"],
            known_spectrum["polarity"],
            known_spectrum["hash"],
        )
        spectrum_ids = [c["spectrum_id"] for c in result]
        assert known_spectrum["spectrum_id"] in spectrum_ids

    # --- no match → empty list (not ValueError) ---

    def test_wrong_hash_returns_empty(self, loaded_library, known_spectrum):
        result = loaded_library.get_identical_spectra_compounds_by_spectrum_info(
            known_spectrum["precursor_mz"],
            known_spectrum["polarity"],
            "NONEXISTENT-HASH",
        )
        assert result == []

    def test_wrong_polarity_returns_empty(self, loaded_library, known_spectrum):
        wrong_polarity = "NEGATIVE" if known_spectrum["polarity"] == "POSITIVE" else "POSITIVE"
        result = loaded_library.get_identical_spectra_compounds_by_spectrum_info(
            known_spectrum["precursor_mz"],
            wrong_polarity,
            known_spectrum["hash"],
        )
        assert result == []

    def test_precursor_mz_outside_ppm_window_returns_empty(self, loaded_library, known_spectrum):
        """Same hash/polarity but precursor_mz far enough away to fail the ppm filter."""
        result = loaded_library.get_identical_spectra_compounds_by_spectrum_info(
            known_spectrum["precursor_mz"] * 1.1,  # 10% shift — well outside 5 ppm
            known_spectrum["polarity"],
            known_spectrum["hash"],
        )
        assert result == []

    # --- ppm tolerance boundary ---

    def test_zero_ppm_tolerance_matches_exact_mz(self, loaded_library, known_spectrum):
        result = loaded_library.get_identical_spectra_compounds_by_spectrum_info(
            known_spectrum["precursor_mz"],
            known_spectrum["polarity"],
            known_spectrum["hash"],
            ppm_tolerance=0.0,
        )
        assert any(c["name"] == known_spectrum["compound_name"] for c in result)

    # --- input validation ---

    def test_precursor_mz_zero_raises(self, loaded_library, known_spectrum):
        with pytest.raises(ValueError, match="precursor_mz"):
            loaded_library.get_identical_spectra_compounds_by_spectrum_info(
                0.0, known_spectrum["polarity"], known_spectrum["hash"]
            )

    def test_precursor_mz_negative_raises(self, loaded_library, known_spectrum):
        with pytest.raises(ValueError, match="precursor_mz"):
            loaded_library.get_identical_spectra_compounds_by_spectrum_info(
                -1.0, known_spectrum["polarity"], known_spectrum["hash"]
            )

    def test_invalid_polarity_raises(self, loaded_library, known_spectrum):
        with pytest.raises(ValueError, match="polarity"):
            loaded_library.get_identical_spectra_compounds_by_spectrum_info(
                known_spectrum["precursor_mz"], "INVALID", known_spectrum["hash"]
            )

    def test_empty_hash_raises(self, loaded_library, known_spectrum):
        with pytest.raises(ValueError, match="hash_ref"):
            loaded_library.get_identical_spectra_compounds_by_spectrum_info(
                known_spectrum["precursor_mz"], known_spectrum["polarity"], ""
            )

    def test_none_hash_raises(self, loaded_library, known_spectrum):
        with pytest.raises(ValueError, match="hash_ref"):
            loaded_library.get_identical_spectra_compounds_by_spectrum_info(
                known_spectrum["precursor_mz"], known_spectrum["polarity"], None
            )

    def test_negative_ppm_tolerance_raises(self, loaded_library, known_spectrum):
        with pytest.raises(ValueError, match="ppm_tolerance"):
            loaded_library.get_identical_spectra_compounds_by_spectrum_info(
                known_spectrum["precursor_mz"],
                known_spectrum["polarity"],
                known_spectrum["hash"],
                ppm_tolerance=-1.0,
            )