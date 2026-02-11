from PySide6.QtCore import QObject, Slot, Signal # pylint: disable=no-name-in-module
from PySide6.QtWidgets import QFileDialog # pylint: disable=no-name-in-module

import logging

from libviz.services.library_service import LibraryService

logger = logging.getLogger(__name__)

class CreateLibraryBackend(QObject):
    errorOccurred = Signal(str)
    successOccurred = Signal()

    def __init__(self, library_service):
        super().__init__()
        self._library_service: LibraryService = library_service

    @Slot(str, str)
    def createLibrary(self, name: str, path: str):
        logger.info("Creating library: %s at %s", name, path)

        try:
            self._library_service.create(name, path)
        except FileExistsError:
            logger.warning("Library already exists at %s", path)
            self.errorOccurred.emit("This file already exists")
            return
        except Exception as e:
            logger.exception("Failed to create library: %s", e)
            self.errorOccurred.emit("Failed to create library")
            return

        logger.info("Library created successfully")
        self.successOccurred.emit()

    @Slot(result=str)
    def selectPath(self):
        path, _ = QFileDialog.getSaveFileName(
            None,
            "Save Library As",
            "",
            "Database Files (*.db)"
        )
        return path or ""
