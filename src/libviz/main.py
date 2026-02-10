
import sys
from pathlib import Path
from PySide6.QtGui import QGuiApplication # pylint: disable=no-name-in-module
from PySide6.QtQml import QQmlApplicationEngine # pylint: disable=no-name-in-module
from PySide6.QtCore import QUrl # pylint: disable=no-name-in-module

from libviz.app import AppState, Navigation
from libviz.utils import configure_logging

def main():
    configure_logging()
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    app_state = AppState()
    navigation = Navigation()

    engine.rootContext().setContextProperty("appState", app_state)
    engine.rootContext().setContextProperty("nav", navigation)

    qml_dir = Path(__file__).parent / "qml"
    main_qml = qml_dir / "main.qml"

    engine.load(QUrl.fromLocalFile(main_qml.resolve().as_posix()))

    if not engine.rootObjects():
        sys.exit(1)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
