import sys

from PySide6.QtGui import QGuiApplication # pylint: disable=no-name-in-module
from PySide6.QtQml import QQmlApplicationEngine # pylint: disable=no-name-in-module
from PySide6.QtQuickControls2 import QQuickStyle # pylint: disable=no-name-in-module

from libviz.gui import libviz_resources # pylint: disable=unused-import


def main():
    app = QGuiApplication(sys.argv)

    QQuickStyle.setStyle("Material")

    engine = QQmlApplicationEngine()

    # qml/ is mounted at qrc:/qml — add it as import path for qmldir modules
    engine.addImportPath("qrc:/gui")

    engine.load("qrc:/gui/main.qml")

    if not engine.rootObjects():
        sys.exit(-1)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()