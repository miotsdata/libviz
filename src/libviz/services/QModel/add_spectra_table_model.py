# mock_spectra_model.py

from PySide6.QtCore import Slot, Signal, Property # pylint: disable=no-name-in-module
from PySide6.QtSql import QSqlQueryModel, QSqlQuery, QSqlDatabase # pylint: disable=no-name-in-module

class AddSpectraTableModel(QSqlQueryModel):
    """
    QSqlQueryModel for spectra table.
    Only shows relevant info:
    id, precursor_mz, polarity, collision_energy
    """
    rowCountChanged = Signal()
    queryingChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._connection_name = None
        self._db_path = None
        self._db = None
        self._querying = False

    # ----------------------------
    # Database Initialization
    # ----------------------------
    def _init_database(self):
        if QSqlDatabase.contains(self._connection_name):
            self._db = QSqlDatabase.database(self._connection_name)
        else:
            self._db = QSqlDatabase.addDatabase("QSQLITE", self._connection_name)
            self._db.setDatabaseName(self._db_path)

        if not self._db.open():
            print("Database open failed:", self._db.lastError().text())

    @Slot(str)
    def set_db(self, db_path: str):
        self._db_path = db_path

    # ----------------------------
    # Refresh Model
    # ----------------------------
    @Slot(float, int)
    def refresh(self, mz_value: float, ppm: int):
        self.set_querying(True)
        if mz_value is None:
            self.setQuery("")  # empty
            return

        # Calculate range
        min_mz, max_mz = self._calculate_range(mz_value=mz_value, ppm=ppm)
        print(min_mz, max_mz)

        self._init_database()
        query = QSqlQuery(self._db)

        # Join with precursor_type to get its name
        sql = f"""
            SELECT id,
                   spectrum_index,
                   precursor_mz,
                   retention_time,
                   polarity,
                   collision_energy
            FROM spectrum
            WHERE precursor_mz BETWEEN {min_mz} AND {max_mz}
            ORDER BY spectrum_index
        """

        if not query.prepare(sql):
            print("Prepare failed:", query.lastError().text())
            return


        if not query.exec():
            print("Query failed:", query.lastError().text())
            return

        self.setQuery(query)

        if self.lastError().isValid():
            print("Model error:", self.lastError().text())

        print("Spectra rows loaded:", self.rowCountProperty)

        self.rowCountChanged.emit()
        self.set_querying(False)

    @Property(int, notify=rowCountChanged)
    def rowCountProperty(self):
        return super().rowCount()
    
    @Property(bool, notify=queryingChanged)
    def querying(self):
        return self._querying
    
    def set_querying(self, value):
        if self._querying != value:
            self._querying = value
            print(f"Querying status changed to {value}")
            self.queryingChanged.emit()

    @Slot(int, result=int)
    def idForRow(self, row: int) -> int:
        """Return the spectra ID at a given row index."""
        record = self.record(row)
        return record.value("id")

    @staticmethod
    def _calculate_range(mz_value: float, ppm: int) -> tuple[float, float]:
        delta: float = mz_value * ppm / 1_000_00
        return (mz_value - delta, mz_value + delta)
