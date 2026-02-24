from libviz.services.library_service import LibraryService

from PySide6.QtCore import Qt, QAbstractListModel, QModelIndex, Slot # pylint: disable=no-name-in-module

class AdductListModel(QAbstractListModel):
    IdRole = Qt.UserRole + 1
    FormulaRole = Qt.UserRole + 2
    ChargeRole = Qt.UserRole + 3
    DeltaMassRole = Qt.UserRole + 4

    def __init__(self, library_service: LibraryService, parent=None):
        super().__init__(parent)
        self.library_service = library_service
        self._data = None
    
    @Slot()
    def refresh(self):
        self._data = self.library_service.get_adducts()

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def data(self, index, role):
        if not index.isValid():
            return None

        item = self._data[index.row()]

        if role == self.IdRole:
            return item["id"]
        if role == self.FormulaRole:
            return item["formula"]
        if role == self.ChargeRole:
            return item["charge"]
        if role == self.DeltaMassRole:
            return item["delta_mass"]

    def roleNames(self):
        return {
            self.IdRole: b"id",
            self.FormulaRole: b"formula",
            self.ChargeRole: b"charge",
            self.DeltaMassRole: b"delta_mass",
        }
    
    @Slot(int, result="int")
    def getId(self, index):
        print(f"getId called with index: {index}")
        if 0 <= index < len(self._data):
            id = self._data[index]["id"]
            print(f"Returning id: {id} for index: {index}")
            print(f"Current data: {self._data}")
            return id
        return -1