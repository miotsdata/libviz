import pytest
import os
import subprocess
import sys

from PySide6.QtCore import QObject

from libviz.gui.main import build_engine, make_bridges


def test_main_qml_loads_without_warnings(qtbot):
    bridges = make_bridges()
    warnings = []
    engine = build_engine(bridges)
    engine.warnings.connect(warnings.extend)
    window = engine.rootObjects()[0]
    assert window.objectName() == "mainWindow"
    assert window.findChild(QObject, "librariesList") is not None
    qtbot.wait(50)
    assert warnings == []


def test_window_follows_selected_library(qtbot, msp_file):
    bridges = make_bridges()
    engine = build_engine(bridges)
    window = engine.rootObjects()[0]
    libs = bridges["Libraries"]

    with qtbot.waitSignal(libs.libraryOpened, timeout=10_000):
        libs.importMsp(str(msp_file))
    qtbot.waitUntil(lambda: window.property("title") == "small — LibViz")
    libs.closeLibrary(libs.selectedKey)
    qtbot.waitUntil(lambda: window.property("title") == "LibViz")


def test_every_page_loads_without_warnings(qtbot, msp_file):
    bridges = make_bridges()
    engine = build_engine(bridges)
    warnings = []
    engine.warnings.connect(warnings.extend)
    window = engine.rootObjects()[0]
    libs = bridges["Libraries"]

    with qtbot.waitSignal(libs.libraryOpened, timeout=10_000):  # library page
        libs.importMsp(str(msp_file))
    qtbot.waitUntil(lambda: bridges["Inspector"].compounds.rowCount() > 0)
    with qtbot.waitSignal(bridges["Inspector"].spectrumChanged, timeout=10_000):
        bridges["Inspector"].selectCompoundRow(0)
    window.setProperty("page", "builder")  # builder page
    qtbot.wait(100)
    window.setProperty("page", "search")  # search page
    qtbot.wait(100)
    window.setProperty("page", "")
    qtbot.wait(100)
    assert [w.toString() for w in warnings] == []


def test_smoke_test_mode_exits_cleanly(tmp_path):
    """What the release builds run on the frozen app (ADR 7)."""
    env = {**os.environ, "LIBVIZ_SMOKE_TEST": "1", "QT_QPA_PLATFORM": "offscreen",
           "XDG_CONFIG_HOME": str(tmp_path)}
    run = subprocess.run([sys.executable, "-m", "libviz.gui.main"], env=env,
                         capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stderr[-2000:]
    assert "LIBVIZ_SMOKE_TEST ok" in run.stdout


def test_peaks_dialog_lists_and_sorts_the_selected_spectrum(qtbot, msp_file):
    bridges = make_bridges()
    engine = build_engine(bridges)
    window = engine.rootObjects()[0]
    libs, insp = bridges["Libraries"], bridges["Inspector"]
    with qtbot.waitSignal(libs.libraryOpened, timeout=10_000):
        libs.importMsp(str(msp_file))
    qtbot.waitUntil(lambda: insp.compounds.rowCount() > 0)
    with qtbot.waitSignal(insp.spectrumChanged, timeout=10_000):
        insp.selectCompoundRow(0)
    qtbot.waitUntil(lambda: bool(insp.spectrum.get("mz")))

    dialog = window.findChild(QObject, "peaksDialog")
    dialog.open()
    qtbot.waitUntil(lambda: dialog.property("opened"))
    spectrum = insp.spectrum
    rows = dialog.property("rows").toVariant()
    assert [r[0] for r in rows] == pytest.approx(sorted(spectrum["mz"]))
    assert max(r[2] for r in rows) == pytest.approx(100)

    dialog.setProperty("sortColumn", 1)
    dialog.setProperty("ascending", False)
    intensities = [r[1] for r in dialog.property("rows").toVariant()]
    assert intensities == sorted(intensities, reverse=True)
