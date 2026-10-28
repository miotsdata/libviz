from PySide6.QtCore import QAbstractListModel, QByteArray, QModelIndex, Property, Qt, Signal


class DictListModel(QAbstractListModel):
    """Rows of same-keyed dicts, one role per key, for QML views that must
    keep their scroll position when a single row changes (``set_row``)."""

    countChanged = Signal()

    def __init__(self, keys: list[str], parent=None):
        super().__init__(parent)
        self._keys = keys
        self._rows: list[dict] = []

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def roleNames(self):
        return {Qt.ItemDataRole.UserRole + i: QByteArray(k.encode()) for i, k in enumerate(self._keys)}

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        i = role - Qt.ItemDataRole.UserRole
        return self._rows[index.row()].get(self._keys[i]) if 0 <= i < len(self._keys) else None

    def set_rows(self, rows: list[dict]):
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()
        self.countChanged.emit()

    def set_row(self, row: int, values: dict):
        self._rows[row] = values
        self.dataChanged.emit(self.index(row), self.index(row))

    def row(self, row: int) -> dict:
        return self._rows[row]

    @Property(int, notify=countChanged)
    def count(self) -> int:
        return len(self._rows)
