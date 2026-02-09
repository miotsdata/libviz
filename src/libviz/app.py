from PySide6.QtWidgets import QApplication # pylint: disable=no-name-in-module
from libviz.gui.main_window import MainWindow  # relative import inside package
from libviz.utils.logging_utils import configure_logging
import logging
from pathlib import Path

def main():

    configure_logging(
        level=logging.DEBUG,
        log_file=Path("libviz.log"),
    )

    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()

if __name__ == "__main__":
    main()
