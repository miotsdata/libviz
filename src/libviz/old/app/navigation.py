# navigation.py
from PySide6.QtCore import QObject, Signal, Slot # pylint: disable=no-name-in-module

class Navigation(QObject):
    goHome = Signal()
    goCreateLibrary = Signal()
    goLoadLibrary = Signal()
    goLibraryHomePage = Signal()

    @Slot()
    def show_home(self):
        self.goHome.emit()

    @Slot()
    def show_create_library(self):
        self.goCreateLibrary.emit()

    @Slot()
    def show_load_library(self):
        self.goLoadLibrary.emit()

    @Slot()
    def show_library_page(self):
        self.goLibraryHomePage.emit()
