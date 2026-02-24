from PySide6.QtCore import QObject, Slot, Signal, QThread, QByteArray # pylint: disable=no-name-in-module
from PySide6.QtWidgets import QFileDialog # pylint: disable=no-name-in-module
from PySide6.QtSql import QSqlDatabase, QSqlQuery # pylint: disable=no-name-in-module

import logging
import tempfile
import uuid
from pyteomics import mzml

from pathlib import Path
import numpy as np

logger = logging.getLogger(__name__)

class LoadMzmlBackend(QObject):
    mzmlLoading = Signal(str)
    errorOccurred = Signal(str)
    successOccurred = Signal(str)

    def __init__(self):
        super().__init__()
        self._mzml_path: Path = None
        self._db_path: Path = Path(tempfile.gettempdir()) / f"libviz_import_{uuid.uuid4()}.db"
        self._connection_name = f"mzml_{uuid.uuid4()}"
        self._thread = None
        self._worker = None

    @Slot(str)
    def load(self, mzml_path: str):
        logger.warning("LOAD CALLED")
        logger.info("Loading file: %s", mzml_path)

        # Tell QML loading started
        self.mzmlLoading.emit(mzml_path)
        self._mzml_path = mzml_path

        # Create thread + worker
        self._thread = QThread()
        self._worker = LoadFromMzmlWorker(self._mzml_path, str(self._db_path), self._connection_name)

        # Move worker to thread
        self._worker.moveToThread(self._thread)

        # When thread starts → run worker
        self._thread.started.connect(self._worker.run)

        # When finished → clean up
        self._worker.finished.connect(self._on_success)
        self._worker.errorOccurred.connect(self._on_error)

        # Proper cleanup
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()


    def _on_success(self, db_path):
        main_conn_name = f"{self._connection_name}_main"
        db = QSqlDatabase.addDatabase("QSQLITE", main_conn_name)
        db.setDatabaseName(str(db_path))
        print(str(db_path))

        if not db.open():
            self.errorOccurred.emit("Failed to open temporary DB")
            return

        query = QSqlQuery(db)
        if query.exec("SELECT count(*) FROM spectrum"):
            if query.next():
                row_count = query.value(0)
                logger.info("Number of spectra rows: %s", row_count)
        else:
            logger.error("Failed to execute count query")

        self.successOccurred.emit(db_path)

        db.close()
        del db
        QSqlDatabase.removeDatabase(main_conn_name)


    def _on_error(self, message):
        logger.error("mzml file failed: %s", message)
        self.errorOccurred.emit(message)


    @Slot(result=str)
    def selectPathMzml(self):
        path, _ = QFileDialog.getOpenFileName(
            None,
            "Load library file",
            "",
            "mzML Files (*.mzML)"
        )
        return path or ""


class LoadFromMzmlWorker(QObject):
    finished = Signal(str)
    errorOccurred = Signal(str)

    def __init__(self, mzml_path: str, db_path: str, connection_name: str):
        super().__init__()
        self._mzml_path = mzml_path
        self._db_path = db_path
        self._connection_name = connection_name

    @Slot()
    def run(self):
        try:
            # --- Open thread-local connection ---
            db = QSqlDatabase.addDatabase("QSQLITE", self._connection_name)
            db.setDatabaseName(str(self._db_path))
            if not db.open():
                self.errorOccurred.emit("Failed to open temporary DB")
                return

            # --- Setup table ---
            setup_query = QSqlQuery(db)
            setup_query.exec("""
                CREATE TABLE IF NOT EXISTS spectrum (
                    id INTEGER PRIMARY KEY,
                    spectrum_index INTEGER UNIQUE,
                    precursor_mz REAL,
                    retention_time REAL,
                    collision_energy REAL,
                    polarity TEXT,
                    mz_array BLOB,
                    intensity_array BLOB
                )
            """)
            setup_query.exec("CREATE INDEX IF NOT EXISTS idx_spectrum_precursor_mz ON spectrum(precursor_mz)")
            setup_query.finish()  # destroy setup_query

            db.transaction()  # begin transaction for bulk insert

            seen = set()
            # --- Stream spectra efficiently ---
            for _, spectrum in enumerate(MzMLParser.parse(self._mzml_path)):
                mz = np.round(np.array(spectrum.mz, dtype=np.float32), 4).tobytes()
                intensity = np.round(np.array(spectrum.intensity, dtype=np.float32), 2).tobytes()

                mz_blob = QByteArray(mz)
                intensity_blob = QByteArray(intensity)

                insert_query = QSqlQuery(db)
                insert_query.prepare("""
                    INSERT OR IGNORE INTO spectrum
                    (spectrum_index, precursor_mz, retention_time, collision_energy, polarity, mz_array, intensity_array)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """)
                insert_query.addBindValue(int(spectrum.index))
                insert_query.addBindValue(round(float(spectrum.precursor_mz), 4))
                insert_query.addBindValue(float(spectrum.retention_time))
                insert_query.addBindValue(float(spectrum.collision_energy))
                insert_query.addBindValue(spectrum.polarity)
                insert_query.addBindValue(mz_blob)
                insert_query.addBindValue(intensity_blob)
                insert_query.exec_()
                insert_query.finish()  # destroy query immediately

            db.commit()  # commit transaction
            db.close()
            del db
            QSqlDatabase.removeDatabase(self._connection_name)  # safe now

            self.finished.emit(self._db_path)

        except Exception as e:
            logger.exception("Failed to import mzML")
            self.errorOccurred.emit(str(e))




class MzMLParser:

    class Spectrum:
        __slots__ = (
            "index",
            "precursor_mz",
            "retention_time",
            "collision_energy",
            "polarity",
            "mz",
            "intensity",
        )

        def __init__(self, index, precursor_mz, retention_time, collision_energy, polarity, mz, intensity):
            self.index = index
            self.precursor_mz = precursor_mz
            self.retention_time = retention_time
            self.collision_energy = collision_energy
            self.polarity = polarity
            self.mz = mz              # NumPy array (no copy)
            self.intensity = intensity  # NumPy array (no copy)

    @staticmethod
    def parse(path):
        with mzml.MzML(path) as reader:

            for spec in reader:

                # Fast MS level check
                if spec.get("ms level") != 2:
                    continue

                # Fast polarity detection
                polarity = (
                    "positive" if "positive scan" in spec
                    else "negative" if "negative scan" in spec
                    else None
                )

                retention_time = spec["scanList"]["scan"][0].get("scan start time", 0)

                # Direct array access (NO conversion)
                mz_array = spec.get("m/z array")
                intensity_array = spec.get("intensity array")

                if mz_array is None or intensity_array is None:
                    continue

                # Precursor info (safe + fewer lookups)
                precursor_mz = None
                collision_energy = None
                index = spec.get("index")

                precursor_list = spec.get("precursorList")
                if precursor_list:
                    precursor = precursor_list["precursor"][0]
                    selected_ion = precursor["selectedIonList"]["selectedIon"][0]

                    precursor_mz = selected_ion.get("selected ion m/z")
                    collision_energy = precursor["activation"].get("collision energy")

                yield MzMLParser.Spectrum(
                    index,
                    precursor_mz,
                    retention_time,
                    collision_energy,
                    polarity,
                    mz_array,
                    intensity_array
                )
