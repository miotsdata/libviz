from PySide6.QtCore import QObject, Slot, Signal, QThread # pylint: disable=no-name-in-module
from PySide6.QtWidgets import QFileDialog # pylint: disable=no-name-in-module
from PySide6.QtSql import QSqlDatabase, QSqlQuery # pylint: disable=no-name-in-module

import logging
import tempfile
import uuid

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
        self._connection_name = f"mzml_{id(self)}"
        self._thread = None
        self._worker = None

    @Slot(str)
    def load(self, mzml_path: str):
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


    def _on_success(self):
        logger.info("mzml file successfully loaded")
        db = QSqlDatabase.addDatabase("QSQLITE", self._connection_name)
        db.setDatabaseName(str(self._db_path))
        if not db.open():
            self.errorOccurred.emit("Failed to open temporary DB")
            return

        query = QSqlQuery(db)
        if query.exec("SELECT count(*) FROM spectra"):
            if query.next():  # move to the first (and only) row
                row_count = query.value(0)  # first column
                logger.info("Number of spectra rows: %s", row_count)
        else:
            logger.error("Failed to execute count query")

        self.successOccurred.emit(self._db_path)


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
            db = QSqlDatabase.addDatabase("QSQLITE", self._connection_name)
            db.setDatabaseName(str(self._db_path))
            if not db.open():
                self.errorOccurred.emit("Failed to open temporary DB")
                return

            query = QSqlQuery(db)
            query.exec("""
                CREATE TABLE IF NOT EXISTS spectra (
                    id INTEGER PRIMARY KEY,
                    spectrum_index INTEGER,
                    precursor_mz REAL,
                    collision_energy REAL,
                    polarity TEXT,
                    mz_array BLOB,
                    intensity_array BLOB
                )
            """)

            for idx, spectrum in enumerate(MzMLParser.parse(self._mzml_path)):
                mz = np.array(spectrum.mz, dtype=np.float32)
                intensity = np.array(spectrum.intensity, dtype=np.float32)

                # sort to make hash deterministic
                order = np.argsort(mz)
                mz = mz[order]
                intensity = intensity[order]
                mz = np.round(mz[order], 4).tobytes()
                intensity = np.round(intensity[order], 2).tobytes()

                query.prepare("""
                    INSERT INTO spectra
                    (spectrum_index, precursor_mz, collision_energy, polarity, mz_array, intensity_array)
                    VALUES (?, ?, ?, ?, ?, ?)
                """)
                query.addBindValue(idx)
                query.addBindValue(spectrum.precursor_mz)
                query.addBindValue(spectrum.collision_energy)
                query.addBindValue(spectrum.polarity)
                query.addBindValue(mz)
                query.addBindValue(intensity)
                query.exec()

            db.close()
            self.finished.emit(self._db_path)

        except FileNotFoundError:
            self.errorOccurred.emit("File not found")
        except Exception as e:
            logger.exception("Failed to import mzML")
            self.errorOccurred.emit(str(e))


class MzMLParser:
    class Spectrum:
        def __init__(self, precursor_mz, collision_energy, polarity, mz, intensity):
            self.precursor_mz = precursor_mz
            self.collision_energy = collision_energy
            self.polarity = polarity
            self.mz = mz
            self.intensity = intensity

    @staticmethod
    def parse(path):
        # Replace with actual mzML parsing
        for i in range(10):
            yield MzMLParser.Spectrum(
                precursor_mz=500.0 + i,
                collision_energy=20.0 + i,
                polarity="positive",
                mz=[100.0, 200.0, 300.0],
                intensity=[10.0, 20.0, 30.0]
            )