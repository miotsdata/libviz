from PySide6.QtCore import QObject, Signal, Property # pylint: disable=no-name-in-module


class AppState(QObject):
    libraryChanged = Signal()

    def __init__(self):
        super().__init__()
        self._library = None

    def set_library(self, library):
        self._library = library
        self.libraryChanged.emit()

    @Property(bool, notify=libraryChanged)
    def hasLibrary(self):
        return self._library is not None

    @Property(str, notify=libraryChanged)
    def libraryName(self):
        return self._library.name if self._library else ""
