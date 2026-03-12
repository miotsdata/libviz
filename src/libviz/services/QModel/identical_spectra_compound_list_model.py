from libviz.services.library_service import LibraryService

from PySide6.QtCore import Qt, QAbstractListModel, QModelIndex, Slot # pylint: disable=no-name-in-module

class IdenticalSpectraCompoundListModel(QAbstractListModel):
    IdRole = Qt.UserRole + 1
    NameRole = Qt.UserRole + 2
    FormulaRole = Qt.UserRole + 3

    def __init__(self, library_service: LibraryService, parent=None):
        super().__init__(parent)
        self.library_service: LibraryService = library_service
        self._data = []
    
    @Slot(int)
    def refresh(self, spectrum_id=None):
        print("Refreshing identical spectra compound list model...")
        self.beginResetModel()
        self._data = self.library_service.get_identical_spectra_compounds(spectrum_id) or []
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self._data) if self._data else 0

    def data(self, index, role):
        if not index.isValid() or not self._data:
            return None

        item = self._data[index.row()]

        if role == Qt.DisplayRole:
            return item["name"]
        if role == self.IdRole:
            return item["id"]
        if role == self.NameRole:
            return item["name"]
        if role == self.FormulaRole:
            return item["formula"]

    def roleNames(self):
        return {
            self.IdRole: b"id",
            self.NameRole: b"name",
            self.FormulaRole: b"formula",
        }
    
    @Slot(int, result="int")
    def getId(self, index):
        if 0 <= index < len(self._data):
            id_ = self._data[index]["id"]
            print(f"getId({index}) -> {id_}")
            return id_
        return -1