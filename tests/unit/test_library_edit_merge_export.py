from pathlib import Path

import numpy as np
import pytest

from libviz.core.library import Library
from libviz.core.writers import write_msp


def add(lib, name, key, mz=79.05, ce=20.0, peaks=(50.0, 60.0), adduct="[M+H]+", polarity="POSITIVE"):
    adduct_id = next(a["id"] for a in lib.get_adducts() if a["formula"] == adduct)
    lib.add_spectra(name, "C6H6", key, {"precursor_mz": mz, "polarity": polarity, "collision_energy": ce,
                                         "mz": np.array(peaks), "intensity": np.array([100.0, 50.0][:len(peaks)])},
                    adduct_id)
    return lib.get_compound_spectra(lib.search_compounds(text=key)[0]["id"])[-1]["id"]


@pytest.fixture
def lib(tmp_path):
    lib = Library.create(tmp_path / "a.db", name="A")
    sid = add(lib, "Benzene", "UHOVQNZJYSORNB-UHFFFAOYSA-N")
    lib.set_spectrum_metadata(sid, "INSTRUMENT", "Orbitrap")
    add(lib, "Benzene", "UHOVQNZJYSORNB-UHFFFAOYSA-N", ce=40.0, peaks=(51.0,))
    add(lib, "Toluene", "YXFVVABEGXRONW-UHFFFAOYSA-N", mz=93.07, adduct="[M-H]-", polarity="NEGATIVE")
    return lib


# ---- editing ----

def test_update_compound(lib):
    cid = lib.search_compounds(text="Toluene")[0]["id"]
    lib.update_compound(cid, name="Methylbenzene", formula="C7H8", smiles="Cc1ccccc1", pubchem_id=1140)
    c = lib.get_compound(cid)
    assert (c["name"], c["formula"], c["smiles"], c["pubchem_id"]) == ("Methylbenzene", "C7H8", "Cc1ccccc1", 1140)
    assert c["exact_mass"] == pytest.approx(92.0626, abs=1e-4)
    with pytest.raises(ValueError, match="invalid formula"):
        lib.update_compound(cid, formula="Qq")
    with pytest.raises(ValueError):
        lib.update_compound(cid, name=" ")


def test_metadata_set_overwrite_delete(lib):
    sid = lib.get_compound_spectra(lib.search_compounds(text="Benzene")[0]["id"])[0]["id"]
    lib.set_spectrum_metadata(sid, "INSTRUMENT", "QTOF")
    lib.set_spectrum_metadata(sid, "note", "checked")
    assert lib.get_spectrum(sid)["metadata"] == {"INSTRUMENT": "QTOF", "note": "checked"}
    lib.delete_spectrum_metadata(sid, "note")
    assert lib.get_spectrum(sid)["metadata"] == {"INSTRUMENT": "QTOF"}


def test_delete_spectra_and_compounds(lib):
    benzene = lib.search_compounds(text="Benzene")[0]["id"]
    first = lib.get_compound_spectra(benzene)[0]["id"]
    assert lib.delete_spectra([first]) == 1
    assert lib.n_spectra == 2 and lib.n_compounds == 2
    assert lib.delete_compounds([benzene]) == 1
    assert lib.n_spectra == 1 and lib.n_compounds == 1
    with lib.engine.connect() as conn:
        assert conn.exec_driver_sql("SELECT COUNT(*) FROM spectrum_metadata").scalar() == 0


# ---- export ----

def test_msp_round_trip(lib, tmp_path):
    assert write_msp(lib, tmp_path / "out.msp") == 3
    text = (tmp_path / "out.msp").read_text()
    assert "INSTRUMENT: Orbitrap" in text and "IONMODE: Negative" in text and "PRECURSORTYPE: [M-H]-" in text

    back = Library.load_from_msp(tmp_path / "out.msp")
    assert (back.n_compounds, back.n_spectra) == (2, 3)
    benzene = back.search_compounds(text="Benzene")[0]["id"]
    spectra = back.get_compound_spectra(benzene)
    assert [s["collision_energy"] for s in spectra] == [20.0, 40.0]
    first = back.get_spectrum(spectra[0]["id"])
    assert first["mz"] == [50.0, 60.0] and first["metadata"]["INSTRUMENT"] == "Orbitrap"
    back.close()


def test_export_selected_compounds(lib, tmp_path):
    toluene = lib.search_compounds(text="Toluene")[0]["id"]
    steps = []
    assert write_msp(lib, tmp_path / "t.msp", compound_ids=[toluene], progress=lambda d, t: steps.append((d, t))) == 1
    assert steps[-1] == (1, 1)
    assert "NAME: Toluene" in (tmp_path / "t.msp").read_text()


# ---- merge ----

def test_merge(lib, tmp_path):
    other = Library.create(tmp_path / "b.db", name="B")
    add(other, "Benzene (other name)", "UHOVQNZJYSORNB-UHFFFAOYSA-N")  # identical spectrum: skipped
    sid = add(other, "Benzene (other name)", "UHOVQNZJYSORNB-UHFFFAOYSA-N", ce=60.0)
    other.set_spectrum_metadata(sid, "SOURCE", "B")
    add(other, "Phenol", "ISWSIDIOOBJBQZ-UHFFFAOYSA-N", mz=95.05, adduct="[M+Na]+")

    assert lib.merge_from(other.path) == {"compounds_added": 1, "spectra_added": 2, "spectra_skipped": 1}
    assert lib.n_compounds == 3 and lib.n_spectra == 5
    benzene = lib.search_compounds(text="UHOVQNZJYSORNB")[0]
    assert benzene["name"] == "Benzene"  # existing compound wins
    spectra = {s["collision_energy"]: s["id"] for s in lib.get_compound_spectra(benzene["id"])}
    assert lib.get_spectrum(spectra[60.0])["metadata"] == {"SOURCE": "B"}
    assert lib.get_spectrum(spectra[20.0])["metadata"] == {"INSTRUMENT": "Orbitrap"}  # not duplicated

    assert lib.merge_from(other.path)["spectra_added"] == 0  # idempotent
    with pytest.raises(ValueError, match="itself"):
        lib.merge_from(lib.path)
    (tmp_path / "junk.db").write_bytes(b"")
    with pytest.raises(ValueError, match="not a LibViz library"):
        lib.merge_from(tmp_path / "junk.db")


def test_merge_dedupes_spectra_without_polarity(tmp_path):
    a = Library.create(tmp_path / "a.db", name="A")
    add(a, "Benzene", "UHOVQNZJYSORNB-UHFFFAOYSA-N", polarity=None)
    target = Library.create(tmp_path / "t.db", name="T")
    assert target.merge_from(a.path)["spectra_added"] == 1
    assert target.merge_from(a.path)["spectra_added"] == 0


def test_msp_import_skips_bad_entries_and_summarises(tmp_path):
    def entry(name, inchikey="", mz="100.1", adduct="[M+H]+", peaks="50 10"):
        lines = [f"NAME: {name}", f"PRECURSORMZ: {mz}", f"PRECURSORTYPE: {adduct}"]
        if inchikey:
            lines.append(f"INCHIKEY: {inchikey}")
        return "\n".join(lines + ["Num Peaks: 1", peaks])
    msp = tmp_path / "in.msp"
    msp.write_text("\n\n".join([
        entry("ok", "AAAAAAAAAAAAAA-BBBBBBBBBB-N"),
        entry("ok2", "CCCCCCCCCCCCCC-DDDDDDDDDD-N", peaks="60 5"),
        entry("dup", "AAAAAAAAAAAAAA-BBBBBBBBBB-N"),
        entry("no key"),
        entry("no key 2"),
        entry("bad mz", "EEEEEEEEEEEEEE-FFFFFFFFFF-N", mz="abc"),
        entry("bad adduct", "GGGGGGGGGGGGGG-HHHHHHHHHH-N", adduct="[M+Xx]+"),
    ]) + "\n")

    lib = Library.load_from_msp(msp)

    assert lib.n_spectra == 2
    assert lib.import_summary == (
        "7 entries, 2 imported, 5 skipped (no InChIKey: 2, duplicate spectrum: 1, "
        "missing/invalid precursor m/z: 1, unknown adduct: 1)")
    lib.close()
