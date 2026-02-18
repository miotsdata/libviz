
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication # pylint: disable=no-name-in-module
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonInstance # pylint: disable=no-name-in-module
from PySide6.QtCore import QUrl # pylint: disable=no-name-in-module
from PySide6.QtQuickControls2 import QQuickStyle # pylint: disable=no-name-in-module

from libviz.app import AppState, Navigation
#from libviz.services.QModel.mock_model import MockCompoundModel
from libviz.services.QModel import CompoundTableModel, SpectraTableModel, SpectrumPlotModel
from libviz.utils import configure_logging
from libviz.backends import CreateLibraryBackend, LoadLibraryBackend
from libviz.services import LibraryService

def main():
    configure_logging()
    app = QApplication(sys.argv)

    QQuickStyle.setStyle("Material")
    
    library_service = LibraryService()
    create_library_backend = CreateLibraryBackend(library_service)
    
    compound_model = CompoundTableModel(library_service)
    spectra_table_model = SpectraTableModel(library_service)

    spectrum_plot_model = SpectrumPlotModel(library_service)

    qmlRegisterSingletonInstance(CompoundTableModel, "Metabolomics.Models", 1, 0, "CompoundTableModel", compound_model)
    qmlRegisterSingletonInstance(SpectraTableModel, "Metabolomics.Models", 1, 0, "SpectraTableModel", spectra_table_model)
    qmlRegisterSingletonInstance(SpectrumPlotModel, "Metabolomics.Models", 1, 0, "SpectrumPlotModel", spectrum_plot_model)
    library_service.libraryChanged.connect(compound_model.refresh)
    """
    mock_compound_model = MockCompoundModel()

    qmlRegisterSingletonInstance(
        MockCompoundModel,
        "Metabolomics.Models",
        1, 0,
        "MockCompoundModel",
        mock_compound_model
    )
    """

    engine = QQmlApplicationEngine()
    load_library_backend = LoadLibraryBackend(library_service, engine)
    app_state = AppState()
    navigation = Navigation()

    engine.rootContext().setContextProperty("appState", app_state)
    engine.rootContext().setContextProperty("nav", navigation)

    # Create library service + backend
    # Expose backend to QML
    engine.rootContext().setContextProperty("createLibBackend", create_library_backend)
    engine.rootContext().setContextProperty("loadLibBackend", load_library_backend)

    engine.rootContext().setContextProperty("libraryService", library_service)

    qml_dir = Path(__file__).parent / "qml"
    main_qml = qml_dir / "main.qml"

    engine.load(QUrl.fromLocalFile(main_qml.resolve().as_posix()))

    if not engine.rootObjects():
        sys.exit(1)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
