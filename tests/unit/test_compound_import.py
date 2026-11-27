import pandas as pd
import pytest

from libviz.core.compound_import import check_rows, guess_mapping, import_compounds, read_table, sheet_names
from libviz.core.library import Library
from libviz.core.utils.mass_utils import calculate_exact_mass

CAFFEINE_KEY = "RYYVLZVUVIJVGH-UHFFFAOYSA-N"


@pytest.fixture
def workbook(tmp_path):
    """Two sheets, Italian headers, a title-free header row after a blank row."""
    path = tmp_path / "compounds.xlsx"
    compounds = pd.DataFrame([
        # Nome, formula, Massa, InChIKey, PubChem CID
        ["Caffeine", "C8H10N4O2", "194.0804", CAFFEINE_KEY, 2519],
        ["Cholic acid-d4", "C24​H36​D4​O5", "", "", None],  # zero-width spaces, deuterium
        ["Lys-CA", "C30H52N2O6", "536.7", "FTOTVNJFGHCOCZ-PJGKWPCRSA-N", None],  # mass ≠ formula
        ["TRYPT-CA", "C34H50N2O4", "", "TRYPT-CA", None],  # invalid key
        ["Typo", "C26H40NNaO6s", "500.1", "", None],  # bad formula, mass used
        ["Nothing", "", "", "", None],  # neither formula nor mass
        ["Caffeine again", "C8H10N4O2", "", CAFFEINE_KEY.lower(), None],  # same key
    ], columns=["Nome", "formula", "Massa", "InChIKey", "PubChem CID"])
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame([["ignore me"]]).to_excel(writer, sheet_name="Notes", index=False, header=False)
        compounds.to_excel(writer, sheet_name="Library", index=False, startrow=1)
    return path


def test_deuterium_and_invisible_characters():
    assert calculate_exact_mass("C24H36D4O5", 6) == pytest.approx(408.287574 + 4 * 1.006277, abs=1e-5)
    assert calculate_exact_mass("C24​H36 D4O5", 6) == calculate_exact_mass("C24H36D4O5", 6)
    assert calculate_exact_mass("DyCl3") is not None  # dysprosium stays dysprosium


def test_check_and_import(tmp_path, workbook):
    assert sheet_names(workbook) == ["Notes", "Library"]
    header, rows = read_table(workbook, "Library")
    assert rows[0][0] == 3  # blank first row skipped; line numbers are the sheet's
    mapping = guess_mapping(header)
    assert mapping == {"name": "Nome", "formula": "formula", "mass": "Massa", "inchikey": "InChIKey",
                       "smiles": "", "pubchem_id": "PubChem CID"}

    checked = {row.name: row for row in check_rows(header, rows, mapping)}
    assert checked["Caffeine"].status == "ok" and checked["Caffeine"].pubchem_id == 2519
    deuterated = checked["Cholic acid-d4"]
    assert deuterated.formula == "C24H36D4O5" and deuterated.inchikey == "NOKEY:Cholic acid-d4"
    assert deuterated.warnings == ["no InChIKey"]
    assert "differs from the formula" in checked["Lys-CA"].warnings[0]
    assert checked["Lys-CA"].exact_mass == pytest.approx(536.3825, abs=1e-4)
    assert checked["TRYPT-CA"].inchikey == "TRYPT-CA" and checked["TRYPT-CA"].status == "warning"
    assert checked["Typo"].formula is None and checked["Typo"].exact_mass == 500.1
    assert checked["Nothing"].error == "no formula and no mass"
    assert checked["Caffeine again"].error == "same key as line 3"

    lib = Library.create(tmp_path / "lib.db", name="Bile acids")
    assert import_compounds(lib, list(checked.values())) == {"added": 5, "existing": 0, "filled": 0}
    issues = {issue["key"]: issue["count"] for issue in lib.overview()["issues"]}
    assert issues["bad_inchikey"] == 3 and issues["no_spectra"] == 5
    assert {c["name"] for c in lib.search_compounds(issue="bad_inchikey")} == {"Cholic acid-d4", "TRYPT-CA", "Typo"}

    # Again with SMILES: nothing added, the existing compound is completed.
    header, rows = ["name", "formula", "inchikey", "smiles"], [(2, ["Caffeine", "C8H10N4O2", CAFFEINE_KEY, "CN1C=NC2"])]
    assert import_compounds(lib, check_rows(header, rows, guess_mapping(header))) == {"added": 0, "existing": 1, "filled": 1}
    [caffeine] = lib.search_compounds(text="Caffeine")
    assert lib.get_compound(caffeine["id"])["smiles"] == "CN1C=NC2"


def test_csv(tmp_path):
    path = tmp_path / "c.csv"
    path.write_text("name;formula\nCaffeine;C8H10N4O2\n")
    header, rows = read_table(path)
    assert sheet_names(path) == [] and [row.status for row in check_rows(header, rows, guess_mapping(header))] == ["warning"]
