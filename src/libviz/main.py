
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication # pylint: disable=no-name-in-module
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonInstance # pylint: disable=no-name-in-module
from PySide6.QtCore import QUrl # pylint: disable=no-name-in-module
from PySide6.QtQuickControls2 import QQuickStyle # pylint: disable=no-name-in-module

from libviz.app import AppState, Navigation
from libviz.services.QModel.mock_model import MockCompoundTableModel
from libviz.services.QModel import CompoundTableModel
from libviz.utils import configure_logging
from libviz.backends import CreateLibraryBackend, LoadLibraryBackend
from libviz.services import LibraryService

def main():
    configure_logging()
    app = QApplication(sys.argv)

    QQuickStyle.setStyle("Material")
    mock_model = MockCompoundTableModel()
    qmlRegisterSingletonInstance(MockCompoundTableModel, "Metabolomics.Models", 1, 0, "MockCompoundTableModel", mock_model)

    engine = QQmlApplicationEngine()

    app_state = AppState()
    navigation = Navigation()

    engine.rootContext().setContextProperty("appState", app_state)
    engine.rootContext().setContextProperty("nav", navigation)

    # Create library service + backend
    library_service = LibraryService()
    create_library_backend = CreateLibraryBackend(library_service)
    load_library_backend = LoadLibraryBackend(library_service, engine)
    compound_model = CompoundTableModel(library_service._library)


    # Expose backend to QML
    engine.rootContext().setContextProperty("createLibBackend", create_library_backend)
    engine.rootContext().setContextProperty("loadLibBackend", load_library_backend)

    engine.rootContext().setContextProperty("libraryService", library_service)
    engine.rootContext().setContextProperty("compoundModel", compound_model)

    qml_dir = Path(__file__).parent / "qml"
    main_qml = qml_dir / "main.qml"

    engine.load(QUrl.fromLocalFile(main_qml.resolve().as_posix()))

    if not engine.rootObjects():
        sys.exit(1)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
