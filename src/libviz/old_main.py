
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication # pylint: disable=no-name-in-module
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonInstance # pylint: disable=no-name-in-module
from PySide6.QtCore import QUrl # pylint: disable=no-name-in-module
from PySide6.QtQuickControls2 import QQuickStyle # pylint: disable=no-name-in-module

from libviz.app import AppState, Navigation
#from libviz.services.QModel.mock_model import MockCompoundModel
from libviz.services.QModel import CompoundTableModel, SpectraTableModel, SpectrumPlotModel, AddSpectraTableModel, AdductListModel, IdenticalSpectraCompoundListModel
from libviz.utils import configure_logging
from libviz.backends import CreateLibraryBackend, LoadLibraryBackend, LoadMzmlBackend, AddSpectraBackend
from libviz.services import LibraryService

import libviz.resources_rc

def main():
    configure_logging()
    app = QApplication(sys.argv)

    QQuickStyle.setStyle("Material")
    
    library_service = LibraryService()
    create_library_backend = CreateLibraryBackend(library_service)
    
    compound_model = CompoundTableModel(library_service)
    spectra_table_model = SpectraTableModel(library_service)

    spectrum_plot_model_library_home = SpectrumPlotModel()
    spectrum_plot_model_add_spectra = SpectrumPlotModel()
    

    load_mzml_backend = LoadMzmlBackend()

    add_spectra_table_model = AddSpectraTableModel()

    adduct_list_model = AdductListModel(library_service)

    add_spectra_backend = AddSpectraBackend(library_service)

    load_library_backend = LoadLibraryBackend(library_service)
    identical_spectra_compound_list_model = IdenticalSpectraCompoundListModel(library_service)


    qmlRegisterSingletonInstance(CompoundTableModel, "Metabolomics.Models", 1, 0, "CompoundTableModel", compound_model)
    qmlRegisterSingletonInstance(SpectraTableModel, "Metabolomics.Models", 1, 0, "SpectraTableModel", spectra_table_model)
    qmlRegisterSingletonInstance(SpectrumPlotModel, "Metabolomics.Models", 1, 0, "SpectrumPlotModelLibraryHome", spectrum_plot_model_library_home)
    qmlRegisterSingletonInstance(SpectrumPlotModel, "Metabolomics.Models", 1, 0, "SpectrumPlotModelAddSpectra", spectrum_plot_model_add_spectra)
    qmlRegisterSingletonInstance(LoadMzmlBackend, "Metabolomics.Models", 1, 0, "LoadMzmlBackend", load_mzml_backend)
    qmlRegisterSingletonInstance(AddSpectraTableModel, "Metabolomics.Models", 1, 0, "AddSpectraTableModel", add_spectra_table_model)
    qmlRegisterSingletonInstance(AdductListModel, "Metabolomics.Models", 1, 0, "AdductListModel", adduct_list_model)
    qmlRegisterSingletonInstance(AddSpectraBackend, "Metabolomics.Models", 1, 0, "AddSpectraBackend", add_spectra_backend)
    qmlRegisterSingletonInstance(LoadLibraryBackend, "Metabolomics.Models", 1, 0, "LoadLibraryBackend", load_library_backend)
    qmlRegisterSingletonInstance(CreateLibraryBackend, "Metabolomics.Models", 1, 0, "CreateLibraryBackend", create_library_backend)
    qmlRegisterSingletonInstance(IdenticalSpectraCompoundListModel, "Metabolomics.Models", 1, 0, "IdenticalSpectraCompoundListModel", identical_spectra_compound_list_model)


    library_service.libraryChanged.connect(compound_model.refresh)
    load_mzml_backend.successOccurred.connect(add_spectra_table_model.set_db)
    add_spectra_table_model.dbChanged.connect(spectrum_plot_model_add_spectra.init_database)
    library_service.libraryChanged.connect(adduct_list_model.refresh)
    load_library_backend.loadedLibrarySuccessfully.connect(spectrum_plot_model_library_home.init_database)

    engine = QQmlApplicationEngine()
    
    app_state = AppState()
    navigation = Navigation()

    engine.rootContext().setContextProperty("appState", app_state)
    engine.rootContext().setContextProperty("nav", navigation)

    # Create library service + backend
    # Expose backend to QML
    engine.rootContext().setContextProperty("createLibBackend", create_library_backend)

    engine.rootContext().setContextProperty("libraryService", library_service)

    engine.load(QUrl("qrc:/qml/main.qml"))

    if not engine.rootObjects():
        sys.exit(1)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
