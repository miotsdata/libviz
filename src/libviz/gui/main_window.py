from PySide6.QtWidgets import QMainWindow, QFileDialog # pylint: disable=no-name-in-module
from .ui_mainwindow import Ui_MainWindow
import logging

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.show_home_page()

        # Connect menu actions
        self.ui.actionLoad_library.triggered.connect(lambda _: _)
        self.ui.actionCreate_library.triggered.connect(self.show_create_library)

        # ============== CREATE LIBRARY PAGE ==============
        # Connect buttons
        self.ui.createLibraryBrowse_btn.clicked.connect(self.browse_path)
        self.ui.createLibrarySave_btn.clicked.connect(self.save_library)
        self.ui.createLibraryCancel_btn.clicked.connect(self.cancel_libary_creation)

        # Connect lineEdit
        self.ui.createLibraryName_lineEdit.textChanged.connect(
            self._update_create_library_save_state
        )
        self.ui.createLibraryPath_lineEdit.textChanged.connect(
            self._update_create_library_save_state
        )

    # ---------- navigation ----------
    def show_create_library(self):
        sender = self.sender()
        logger.debug("Clicked from %s", sender.objectName())
        self.ui.stackedWidget.setCurrentWidget(
            self.ui.CreateLibrary_page
        )

    def show_home_page(self):
        sender = self.sender()
        if sender:
            logger.debug("Clicked from %s", sender.objectName())
        self.ui.stackedWidget.setCurrentWidget(
            self.ui.Home_page
        )


    # ---------- UI actions ----------
    def browse_path(self):
        sender = self.sender()
        logger.debug("Clicked from %s", sender.objectName())
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Library As",
            "",
            "Database Files (*.db)"
        )
        if file_path:
            self.ui.createLibraryPath_lineEdit.setText(file_path)

    def save_library(self):
        name = self.ui.createLibraryName_lineEdit.text().strip()
        path = self.ui.createLibraryPath_lineEdit.text()
        print(f"Library name: {name}, path: {path}")

    def _update_create_library_save_state(self):
        name_ok = bool(self.ui.createLibraryName_lineEdit.text().strip())
        path_ok = bool(self.ui.createLibraryPath_lineEdit.text().strip())

        self.ui.createLibrarySave_btn.setEnabled(name_ok and path_ok)

    def cancel_libary_creation(self):
        self.ui.createLibraryPath_lineEdit.clear()
        self.ui.createLibraryPath_lineEdit.clear()
        name = self.ui.createLibraryName_lineEdit.text().strip()
        path = self.ui.createLibraryPath_lineEdit.text()
        print(f"Library name: {name}, path: {path}")
        self.show_home_page()
