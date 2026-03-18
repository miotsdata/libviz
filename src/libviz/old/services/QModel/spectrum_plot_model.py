from PySide6.QtCore import Property, Signal, Slot # pylint: disable=no-name-in-module
from PySide6.QtSql import QSqlQueryModel, QSqlQuery, QSqlDatabase # pylint: disable=no-name-in-module
import numpy as np

class SpectrumPlotModel(QSqlQueryModel):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._db = None
        self._peak_id = None
        self._peaks = None
        self._min_mz = None
        self._max_mz = None

    # ----------------------------
    # Database Initialization
    # ----------------------------
    def init_database(self, connection_name: str, db_path: str):

        if self._db is not None and self._db.databaseName() != db_path:
            self._db.close()
            conn_name_2close = self._db.connectionName()
            del self._db
            self._db = None
            QSqlDatabase.removeDatabase(conn_name_2close)

            self._db = QSqlDatabase.addDatabase("QSQLITE",connection_name)
            self._db.setDatabaseName(db_path)
        elif  QSqlDatabase.contains(connection_name):
            self._db = QSqlDatabase.database(connection_name)
        else:       
            self._db = QSqlDatabase.addDatabase("QSQLITE", connection_name)
            self._db.setDatabaseName(db_path)

        if not self._db.open():
            print("Database open failed:", self._db.lastError().text())
        else:
            print("Database opened successfully:", db_path)

    def _decode_array(self, binary_data: bytes) -> np.ndarray:
        """Convert LargeBinary from SQLite to numpy float32 array."""
        if binary_data is None:
            return np.array([], dtype=np.float32)
        return np.frombuffer(binary_data, dtype=np.float32)

    def _load_spectrum_from_query(self, query: QSqlQuery) -> tuple[np.ndarray, np.ndarray]:
        """
        Given a QSqlQuery positioned at the right record,
        return (mz, intensity) as numpy arrays.
        """
        if not query.isActive() or not query.isSelect():
            return np.array([], dtype=np.float32), np.array([], dtype=np.float32)

        mz_array = query.value(0)  # s.mz_array
        intensity_array = query.value(1)  # s.intensity_array

        mz = self._decode_array(mz_array)
        intensity = self._decode_array(intensity_array)

        return mz, intensity

    @Slot()
    def refresh(self):
        print("Refreshing spectrum plot for peak_id:", self._peak_id)
        if self._peak_id is None:
            self.setQuery("")  # empty
            return

        query = QSqlQuery(self._db)

        sql = f"""
            SELECT mz_array,
                intensity_array
            FROM spectrum
            WHERE id = {self._peak_id}
            LIMIT 1
        """

        if not query.exec(sql):
            print("Query failed:", query.lastError().text())
            return

        if not query.next():
            # No spectrum found
            self._peaks = []
            self._min_mz = 0
            self._max_mz = 1
            self.dataChanged.emit()
            return

        mz, intensity = self._load_spectrum_from_query(query)

        if len(intensity) == 0:
            self._peaks = []
            self._min_mz = 0
            self._max_mz = 1
            self.dataChanged.emit()
            return

        # normalize
        max_int = intensity.max()
        norm = (intensity / max_int) * 100 if max_int > 0 else intensity

        self._peaks = [{"mz": float(m), "intensity": float(i)} for m, i in zip(mz, norm)]
        self._min_mz = float(mz.min())
        self._max_mz = float(mz.max())

        self.dataChanged.emit()

    @Property("QVariantList", notify=dataChanged)
    def peaks(self):
        return self._peaks

    @Property(float, notify=dataChanged)
    def minMz(self):
        return self._min_mz

    @Property(float, notify=dataChanged)
    def maxMz(self):
        return self._max_mz
    
    @Slot(int)
    def setPeakId(self, peak_id: int):
        if self._peak_id != peak_id:
            self._peak_id = peak_id
            self.refresh()

    @Slot()
    def clear(self):
        self._peaks = []
        self._min_mz = 0
        self._max_mz = 0
        self.dataChanged.emit()