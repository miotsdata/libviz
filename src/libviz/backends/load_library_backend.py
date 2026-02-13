from PySide6.QtCore import QObject, Slot, Signal, QThread # pylint: disable=no-name-in-module
from PySide6.QtWidgets import QFileDialog # pylint: disable=no-name-in-module

import logging

from libviz.services.QModel.metabolite_model import CompoundTableModel
from libviz.services.library_service import LibraryService

logger = logging.getLogger(__name__)

class LoadLibraryBackend(QObject):
    libraryLoading = Signal(str)
    errorOccurred = Signal(str)
    successOccurred = Signal()

    def __init__(self, library_service, engine):
        super().__init__()
        self._library_service: LibraryService = library_service
        self._thread = None
        self._worker = None


    @Slot(str)
    def loadLibraryFromDb(self, path: str):
        logger.info("Loading library: %s", path)

        try:
            self._library_service.load(path)
        except FileNotFoundError:
            logger.warning("File not found: %s", path)
            self.errorOccurred.emit("This file does not exists")
            return
        except Exception as e:
            logger.exception("Failed to load library: %s", e)
            self.errorOccurred.emit("Failed to load library")
            return

        logger.info("Library successfully loaded")
        self.successOccurred.emit()

    @Slot(str)
    def loadLibraryFromMsp(self, path: str):
        logger.info("Loading library: %s", path)

        # Tell QML loading started
        self.libraryLoading.emit(path)

        # Create thread + worker
        self._thread = QThread()
        self._worker = LoadFromMspWorker(self._library_service, path)

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
        logger.info("Library successfully loaded")
        self.successOccurred.emit()


    def _on_error(self, message):
        logger.error("Library loading failed: %s", message)
        self.errorOccurred.emit(message)


    @Slot(result=str)
    def selectPathDB(self):
        path, _ = QFileDialog.getOpenFileName(
            None,
            "Load library file",
            "",
            "Database Files (*.db)"
        )
        return path or ""

    @Slot(result=str)
    def selectPathMsp(self):
        path, _ = QFileDialog.getOpenFileName(
            None,
            "Load library file",
            "",
            "MSP Files (*.msp)"
        )
        return path or ""

class LoadFromMspWorker(QObject):
    finished = Signal()
    errorOccurred = Signal(str)

    def __init__(self, library_service, path: str):
        super().__init__()
        self._library_service: LibraryService = library_service
        self._path = path

    @Slot()
    def run(self):
        try:
            self._library_service.loadFromMSP(self._path)
        except FileNotFoundError:
            self.errorOccurred.emit("This file does not exist")
            return
        except Exception:
            self.errorOccurred.emit("Failed to load library")
            return

        self.finished.emit()

