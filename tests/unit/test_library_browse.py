from pathlib import Path

import numpy as np
import pytest

from libviz.core.library import Library


def _info(mz, polarity="POSITIVE", ce=20.0, peaks=(50.0, 60.0)):
    return {"precursor_mz": mz, "polarity": polarity, "collision_energy": ce,
            "mz": np.array(peaks), "intensity": np.array([100.0, 50.0][:len(peaks)])}


@pytest.fixture
def lib(tmp_path):
    lib = Library.create(Path(tmp_path / "b.db"), name="browse")
    adducts = {a["formula"]: a["id"] for a in lib.get_adducts()}
    lib.add_spectra("Caffeine", "C8H10N4O2", "RYYVLZVUVIJVGH-UHFFFAOYSA-N", _info(195.0877, ce=20.0), adducts["[M+H]+"])
    lib.add_spectra("Caffeine", "C8H10N4O2", "RYYVLZVUVIJVGH-UHFFFAOYSA-N", _info(195.0877, ce=40.0, peaks=(138.0,)), adducts["[M+H]+"])
    lib.add_spectra("Theobromine", "C7H8N4O2", "YAPQBXQYLJRXSA-UHFFFAOYSA-N", _info(179.0574, "NEGATIVE"), adducts["[M-H]-"])
    lib.add_spectra("100%_weird_name", "C6H6", "UHOVQNZJYSORNB-UHFFFAOYSA-N", _info(79.0542), adducts["[M+Na]+"])
    return lib


def names(rows):
    return [r["name"] for r in rows]


def test_default_page_sorted_by_name(lib):
    rows = lib.search_compounds()
    assert names(rows) == ["100%_weird_name", "Caffeine", "Theobromine"]
    caffeine = rows[1]
    assert caffeine["n_spectra"] == 2
    assert caffeine["exact_mass"] == pytest.approx(194.0804, abs=1e-3)


def test_text_matches_name_case_insensitive_inchikey_prefix_and_formula(lib):
    assert names(lib.search_compounds(text="caff")) == ["Caffeine"]
    assert names(lib.search_compounds(text="yapq")) == ["Theobromine"]
    assert names(lib.search_compounds(text="C6H6")) == ["100%_weird_name"]


def test_like_wildcards_are_literal(lib):
    assert names(lib.search_compounds(text="%")) == ["100%_weird_name"]
    assert names(lib.search_compounds(text="_")) == ["100%_weird_name"]


def test_mass_matches_neutral_mass_or_precursor(lib):
    assert names(lib.search_compounds(mass=194.0804, ppm=5)) == ["Caffeine"]
    assert names(lib.search_compounds(mass=179.0574, ppm=5)) == ["Theobromine"]
    assert lib.search_compounds(mass=500.0, ppm=5) == []


def test_spectrum_filters(lib):
    assert names(lib.search_compounds(polarity="NEGATIVE")) == ["Theobromine"]
    assert names(lib.search_compounds(adduct="[M+Na]+")) == ["100%_weird_name"]
    assert names(lib.search_compounds(collision_energy=40.0)) == ["Caffeine"]
    assert lib.count_compounds(polarity="POSITIVE") == 2


def test_sort_and_paging(lib):
    assert names(lib.search_compounds(sort="exact_mass", descending=True)) == ["Caffeine", "Theobromine", "100%_weird_name"]
    assert names(lib.search_compounds(offset=1, limit=1)) == ["Caffeine"]
    with pytest.raises(ValueError):
        lib.search_compounds(sort="id; DROP TABLE compound")


def test_filter_options_only_used_values(lib):
    opts = lib.filter_options()
    assert opts["polarities"] == ["NEGATIVE", "POSITIVE"]
    assert opts["adducts"] == ["[M+H]+", "[M+Na]+", "[M-H]-"]
    assert opts["collision_energies"] == [20.0, 40.0]


def test_compound_spectra_and_spectrum(lib):
    cid = lib.search_compounds(text="Caffeine")[0]["id"]
    assert lib.get_compound(cid)["inchikey"] == "RYYVLZVUVIJVGH-UHFFFAOYSA-N"

    spectra = lib.get_compound_spectra(cid)
    assert [(s["collision_energy"], s["n_peaks"], s["adduct"]) for s in spectra] == [(20.0, 2, "[M+H]+"), (40.0, 1, "[M+H]+")]

    spectrum = lib.get_spectrum(spectra[0]["id"])
    assert spectrum["mz"] == [50.0, 60.0]
    assert spectrum["intensity"] == [100.0, 50.0]
    assert spectrum["metadata"] == {}
    with pytest.raises(ValueError):
        lib.get_spectrum(999)
