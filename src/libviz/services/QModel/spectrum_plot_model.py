from PySide6.QtCore import Property, Signal, Slot # pylint: disable=no-name-in-module
from PySide6.QtSql import QSqlQueryModel, QSqlQuery, QSqlDatabase # pylint: disable=no-name-in-module
from libviz.services import LibraryService
import numpy as np

class SpectrumPlotModel(QSqlQueryModel):
    dataChanged = Signal()

    def __init__(self, library_service, parent=None):
        super().__init__(parent)
        self.library_service: LibraryService = library_service
        self._db = None
        self._peak_id = None
        self._peaks = None
        self._min_mz = None
        self._max_mz = None

    # ----------------------------
    # Database Initialization
    # ----------------------------
    def _init_database(self):
        if QSqlDatabase.contains(self.library_service.connection_name):
            self._db = QSqlDatabase.database(self.library_service.connection_name)
        else:
            self._db = QSqlDatabase.addDatabase("QSQLITE", self.library_service.connection_name)
            self._db.setDatabaseName(self.library_service.db_path)

        if not self._db.open():
            print("Database open failed:", self._db.lastError().text())

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

        self._init_database()
        query = QSqlQuery(self._db)

        sql = f"""
            SELECT s.mz_array,
                s.intensity_array
            FROM spectrum s
            WHERE compound_id = {self._peak_id}
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
