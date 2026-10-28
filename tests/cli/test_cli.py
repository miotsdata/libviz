import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from mzml_factory import write_mzml  # noqa: E402

from libviz.cli.main import main
from libviz.core.library import Library

MSP = "NAME: A\nFORMULA: C6H6\nINCHIKEY: UHOVQNZJYSORNB-UHFFFAOYSA-N\nPRECURSORMZ: 79.05\nNum Peaks: 1\n50 100\n"


def test_convert_and_info(tmp_path, capsys):
    (tmp_path / "a.msp").write_text(MSP)
    assert main(["convert", str(tmp_path / "a.msp"), "--name", "Mine"]) == 0
    assert Library.load_from_db(tmp_path / "a.db").name == "Mine"
    assert main(["convert", str(tmp_path / "a.msp")]) == 1  # exists, no --force
    assert main(["info", str(tmp_path / "a.db")]) == 0
    assert "1 compounds, 1 spectra" in capsys.readouterr().out


def test_build(tmp_path, capsys):
    (tmp_path / "t.csv").write_text("name,formula,inchikey\nCaffeine,C8H10N4O2,RYYVLZVUVIJVGH-UHFFFAOYSA-N\n"
                                    "Benzene,C6H6,UHOVQNZJYSORNB-UHFFFAOYSA-N\n")
    mzml = write_mzml(tmp_path / "a.mzML", [dict(precursor_mz=195.0877, mz=(138.0, 110.0), intensity=(100.0, 50.0)),
                                           dict(precursor_mz=205.0, isolation=(10, 10), mz=(1.0,), intensity=(1.0,))])
    out = tmp_path / "lib.db"
    assert main(["build", str(tmp_path / "t.csv"), str(mzml), "-o", str(out), "--name", "Std"]) == 0
    text = capsys.readouterr().out
    assert "1 spectra for 1/2 targets" in text and "no MS2: Benzene" in text
    lib = Library.load_from_db(out)
    assert (lib.name, lib.n_spectra) == ("Std", 1)

    assert main(["build", str(tmp_path / "t.csv"), str(mzml), "-o", str(out)]) == 0
    assert "skipped 1" in capsys.readouterr().out


def test_errors_are_one_line(tmp_path, capsys):
    (tmp_path / "t.csv").write_text("name\nx\n")
    assert main(["build", str(tmp_path / "t.csv"), "x.mzML", "-o", str(tmp_path / "o.db")]) == 1
    assert capsys.readouterr().err.startswith("error: missing column")


def test_export_and_merge(tmp_path, capsys):
    (tmp_path / "a.msp").write_text(MSP)
    assert main(["convert", str(tmp_path / "a.msp")]) == 0
    assert main(["export", str(tmp_path / "a.db"), "-o", str(tmp_path / "back.msp")]) == 0
    assert "INCHIKEY: UHOVQNZJYSORNB-UHFFFAOYSA-N" in (tmp_path / "back.msp").read_text()

    assert main(["merge", str(tmp_path / "all.db"), str(tmp_path / "a.db"), str(tmp_path / "a.db")]) == 0
    out = capsys.readouterr().out
    assert "+1 spectra" in out and "+0 spectra" in out and "1 compounds, 1 spectra" in out
