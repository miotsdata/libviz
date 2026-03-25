import sys

from PySide6.QtGui import QGuiApplication # pylint: disable=no-name-in-module
from PySide6.QtQml import QQmlApplicationEngine # pylint: disable=no-name-in-module
from PySide6.QtQuickControls2 import QQuickStyle # pylint: disable=no-name-in-module

from libviz.gui import libviz_resources # pylint: disable=unused-import
from libviz.core import LibraryManager
from libviz.bridge import LibraryManagerBridge

from libviz.core.utils.logging_utils import configure_logging

import logging
configure_logging(level=logging.DEBUG)


def main():
    app = QGuiApplication(sys.argv)

    QQuickStyle.setStyle("Material")

    # 1. Create the core manager
    manager = LibraryManager()

    # 2. Wrap it in the bridge
    bridge = LibraryManagerBridge(manager)
    

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("libraryManagerBridge", bridge)

    # qml/ is mounted at qrc:/qml — add it as import path for qmldir modules
    engine.addImportPath("qrc:/gui")

    engine.load("qrc:/gui/main.qml")

    if not engine.rootObjects():
        sys.exit(-1)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()