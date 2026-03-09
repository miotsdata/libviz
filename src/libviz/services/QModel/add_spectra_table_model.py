# mock_spectra_model.py

import time
import uuid

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
    dbChanged = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._connection_name = None
        self._db_path = None
        self._db = None
        self._querying = False

    # ----------------------------
    # Database Initialization
    # ----------------------------
    @Slot(str)
    def set_db(self, db_path: str):
        self._db_path = db_path
        self.setQuery("")
        self.set_querying(False)
        self._connection_name = f"spectra_model_{uuid.uuid4()}"


        if QSqlDatabase.contains(self._connection_name):
            self._db = QSqlDatabase.database(self._connection_name)
        else:
            self._db = QSqlDatabase.addDatabase("QSQLITE", self._connection_name)
            self._db.setDatabaseName(self._db_path)

        if not self._db.open():
            print("Database open failed:", self._db.lastError().text())
        else:
            print("Database opened successfully:", self._db_path)
            self.dbChanged.emit(self._connection_name, self._db_path)


    # ----------------------------
    # Refresh Model
    # ----------------------------
    @Slot(float, int)
    def refresh(self, mz_value: float, ppm: int):
        if self._querying:
            print("Already querying — ignoring new request.")
            return
        self.set_querying(True)

        if mz_value is None or not isinstance(mz_value, (int, float)):
            print("Invalid m/z value:", mz_value)
            self.setQuery("")  # empty
            self.set_querying(False)
            return

        # Calculate range
        min_mz, max_mz = self._calculate_range(mz_value=mz_value, ppm=ppm)
        print(min_mz, max_mz)

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

        print("Spectra rows loaded:", super().rowCount())
        self.set_querying(False)
        self.rowCountChanged.emit()

    @Property(bool, notify=rowCountChanged)
    def hasRows(self):
        return super().rowCount() > 0
    
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
        delta: float = mz_value * ppm / 1_000_000
        return (mz_value - delta, mz_value + delta)
    
    @Slot(int, result="QVariantMap")
    def getSpectraInfoById(self, peak_id: int):
        query = QSqlQuery(self._db)

        sql = f"""
            SELECT precursor_mz,
                   retention_time,
                   polarity,
                   collision_energy
            FROM spectrum
            WHERE id = {peak_id}
            LIMIT 1
        """

        if not query.exec(sql):
            print("Query failed:", query.lastError().text())
            return None

        if not query.next():
            print("No spectrum found with id:", peak_id)
            return None

        precursor_mz = query.value(0)
        retention_time = query.value(1)
        polarity = query.value(2)
        collision_energy = query.value(3)

        return {
            "precursor_mz": precursor_mz,
            "retention_time": retention_time,
            "polarity": polarity,
            "collision_energy": collision_energy
        }
