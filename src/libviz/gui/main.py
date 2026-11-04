import importlib.metadata
import logging
import os
import sys
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtQuickControls2 import QQuickStyle

from libviz.core.library import Library
from libviz.core.utils.logging_utils import configure_logging
from libviz.gui.builder_bridge import BuilderBridge
from libviz.gui.inspector_bridge import InspectorBridge
from libviz.gui.library_bridge import LibraryBridge
from libviz.gui.search_bridge import SearchBridge

# QML is loaded straight from the package directory, not compiled into a
# qrc module: no rcc step, no generated file to keep in sync (ADR 2).
QML_DIR = Path(__file__).parent / "qml"


def load_qt_graphs_2d_impl() -> None:
    """Load Qt6Graphs2DImpl.dll on Windows, before any QML.

    It holds Qt Graphs' `QtGraphs2D.impl` QML module, which registers itself
    when the DLL loads. On Linux libQt6Graphs links it, but no Windows DLL
    imports it, so nothing ever loaded it: every Qt Graphs plot (spectrum,
    mirror, EIC) then crashed the app ("QtGraphs2D.impl module's qmldir file
    not found", then an access violation in Qt6Core). Same fix as MSIAnalyzer.
    """
    if sys.platform != "win32":
        return
    import ctypes

    import PySide6

    dll = Path(PySide6.__file__).parent / "Qt6Graphs2DImpl.dll"
    if dll.exists():
        ctypes.WinDLL(str(dll))
    else:
        logging.getLogger(__name__).warning("%s is missing: Qt Graphs plots will crash", dll)


# Smoke test: one real plot, created and rendered (compiling the views is not
# enough: the Windows Qt Graphs crash happened only when a plot was made).
_SMOKE_PLOT_QML = b"""
import QtQuick
import "Views"
Window {
    width: 400; height: 300; visible: true
    StickPlot { anchors.fill: parent; groups: [{ key: "a", name: "a", peaks: [[100, 1000], [150, 500]] }] }
}
"""


def build_engine(bridges: dict[str, object]) -> QQmlApplicationEngine:
    """Construct the QML engine with ``bridges`` as context properties and
    load Main.qml. Raises with the QML warnings if loading fails. Reused by
    tests."""
    engine = QQmlApplicationEngine()
    context = engine.rootContext()
    for name, obj in bridges.items():
        # Owned by the engine, so they outlive the QML that binds to them
        # (Python could otherwise free a bridge first -> crash on teardown).
        obj.setParent(engine)
        context.setContextProperty(name, obj)
    try:
        version = importlib.metadata.version("LibViz")
    except importlib.metadata.PackageNotFoundError:
        version = "dev"
    context.setContextProperty("AppVersion", version)

    errors = []
    engine.warnings.connect(errors.extend)
    engine.load(QUrl.fromLocalFile(str(QML_DIR / "Main.qml")))
    if not engine.rootObjects():
        details = "\n".join(str(w) for w in errors) or "(no warnings captured)"
        raise RuntimeError(f"Failed to load Main.qml:\n{details}")
    return engine


def make_bridges() -> dict[str, object]:
    libraries = LibraryBridge()
    return {"Libraries": libraries, "Inspector": InspectorBridge(libraries),
            "Builder": BuilderBridge(libraries), "Search": SearchBridge(libraries)}


def main() -> int:
    configure_logging(level=logging.INFO)
    # Fusion, not Material: Material + the native FileDialog froze the app on
    # GNOME in MSIAnalyzer; Fusion follows our explicit palette (Theme.qml).
    QQuickStyle.setStyle(os.environ.get("LIBVIZ_QT_STYLE", "Fusion"))
    load_qt_graphs_2d_impl()
    app = QGuiApplication(sys.argv)
    app.setOrganizationName("LibViz")
    app.setApplicationName("LibViz")
    app.setOrganizationDomain("libviz")

    bridges = make_bridges()
    engine = build_engine(bridges)  # noqa: F841  (must outlive app.exec)
    if os.environ.get("LIBVIZ_SMOKE_TEST"):
        # Release builds: prove every view compiles (pages load lazily, so a
        # missing QML module would otherwise only show up later) and the
        # bundled migrations run.
        for qml in sorted((QML_DIR / "Views").glob("*.qml")):
            component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml)))
            if component.isError():
                raise RuntimeError(f"{qml.name}: {component.errorString()}")
        plot = QQmlComponent(engine)
        plot.setData(_SMOKE_PLOT_QML, QUrl.fromLocalFile(str(QML_DIR / "smoke.qml")))
        window = plot.create()
        if window is None:
            raise RuntimeError(f"plot: {plot.errorString()}")
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:  # let it render a few frames
            app.processEvents()
            time.sleep(0.02)
        with tempfile.TemporaryDirectory() as tmp:
            Library.create(Path(tmp) / "smoke.db", name="smoke").close()
        print("LIBVIZ_SMOKE_TEST ok", flush=True)
        os._exit(0)
    exit_code = app.exec()
    # Delete temp (unsaved, already confirmed in Main.qml) import DBs.
    for lib in bridges["Libraries"].manager.libraries.values():
        lib.close()
    # A Task still running (e.g. a large import the user quit during) would
    # block interpreter shutdown; nothing is left to flush.
    os._exit(exit_code)


if __name__ == "__main__":
    sys.exit(main())
