import importlib.metadata
import logging
import os
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from libviz.core.utils.logging_utils import configure_logging
from libviz.gui.builder_bridge import BuilderBridge
from libviz.gui.inspector_bridge import InspectorBridge
from libviz.gui.library_bridge import LibraryBridge
from libviz.gui.search_bridge import SearchBridge

# QML is loaded straight from the package directory, not compiled into a
# qrc module: no rcc step, no generated file to keep in sync (ADR 2).
QML_DIR = Path(__file__).parent / "qml"


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
    app = QGuiApplication(sys.argv)
    app.setOrganizationName("LibViz")
    app.setApplicationName("LibViz")
    app.setOrganizationDomain("libviz")

    bridges = make_bridges()
    engine = build_engine(bridges)  # noqa: F841  (must outlive app.exec)
    exit_code = app.exec()
    # Delete temp (unsaved, already confirmed in Main.qml) import DBs.
    for lib in bridges["Libraries"].manager.libraries.values():
        lib.close()
    # A Task still running (e.g. a large import the user quit during) would
    # block interpreter shutdown; nothing is left to flush.
    os._exit(exit_code)


if __name__ == "__main__":
    sys.exit(main())
