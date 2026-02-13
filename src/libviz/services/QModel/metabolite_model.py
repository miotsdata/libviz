from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex, Slot # pylint: disable=no-name-in-module
from PySide6.QtQml import QmlElement, QmlSingleton # pylint: disable=no-name-in-module
from sqlalchemy import select

from libviz.services.classes.library import Library
from libviz.services.db.models.compound import Compound

"""
QML_IMPORT_NAME = "compoundModel"
QML_IMPORT_MAJOR_VERSION = 1

@QmlElement
"""
class CompoundTableModel(QAbstractTableModel):

    def __init__(self, library_service, parent=None):
        """
        library: instance of your Library class
        """
        super().__init__(parent)
        self.library_service = library_service
        self.library: Library = None
        self._headers = ["Name", "Formula", "InChIKey", "Exact Mass", "Added On"]

        # Load initial data (all compounds, can later optimize for lazy loading)
        self._data = []
        print("CompoundTableModel INIT", id(self))

    @Slot()
    def load_compounds(self):
        self.library = self.library_service._library
        print("LOAD CALLED", id(self))
        print("Loading compounds...")
        session = self.library.Session()
        stmt = select(Compound).limit(5)
        results = session.execute(stmt).scalars().all()
        
        self.beginResetModel()
        self._data = results
        self.endResetModel()
        print("Finished")
        print(f"N compounds: {len(self._data)}")

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        print("Loading data")
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None

        compound = self._data[index.row()]
        column = index.column()
        if column == 0:
            return compound.name
        elif column == 1:
            return compound.formula
        elif column == 2:
            return compound.inchikey
        elif column == 3:
            return str(compound.exact_mass)
        elif column == 4:
            return compound.added_on.strftime("%Y-%m-%d %H:%M:%S")
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None
    
    def roleNames(self):
        return {
            Qt.ItemDataRole.DisplayRole: b"display"
        }

    """
    def sort(self, column, order):
        self.layoutAboutToBeChanged.emit()
        reverse = order == Qt.DescendingOrder

        key_map = {
            0: lambda c: c.name or "",
            1: lambda c: c.formula or "",
            2: lambda c: c.inchikey or "",
            3: lambda c: c.exact_mass or 0,
            4: lambda c: c.added_on,
        }

        self._data.sort(key=key_map[column], reverse=reverse)
        self.layoutChanged.emit()
    """



