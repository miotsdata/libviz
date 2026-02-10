from PySide6.QtCore import QObject, Slot, Signal # pylint: disable=no-name-in-module
from PySide6.QtWidgets import QFileDialog # pylint: disable=no-name-in-module

import logging

logger = logging.getLogger(__name__)

class LoadLibraryBackend(QObject):
    errorOccurred = Signal(str)
    successOccurred = Signal()

    def __init__(self, library_service):
        super().__init__()
        self._library_service = library_service
    
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

    @Slot(result=str)
    def selectPath(self):
        path, _ = QFileDialog.getOpenFileName(  
            None,
            "Load library file",
            "",
            "Database Files (*.db)"
        )
        return path or ""
