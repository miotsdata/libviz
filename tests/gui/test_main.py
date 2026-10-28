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
