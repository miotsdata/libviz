import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QCoreApplication, QSettings
from PySide6.QtQuickControls2 import QQuickStyle

# Same style as production (gui/main.py), before any QtQuick.Controls loads.
QQuickStyle.setStyle("Fusion")

MSP = """NAME: Caffeine
FORMULA: C8H10N4O2
INCHIKEY: RYYVLZVUVIJVGH-UHFFFAOYSA-N
SMILES: CN1C=NC2=C1C(=O)N(C(=O)N2C)C
PRECURSORTYPE: [M+H]+
PRECURSORMZ: 195.0877
IONMODE: Positive
COLLISIONENERGY: 20
Num Peaks: 3
138.0662 100
110.0713 20
195.0877 50

NAME: Theobromine
FORMULA: C7H8N4O2
INCHIKEY: YAPQBXQYLJRXSA-UHFFFAOYSA-N
PRECURSORTYPE: [M+H]+
PRECURSORMZ: 181.0720
IONMODE: Positive
COLLISIONENERGY: 30
Num Peaks: 2
138.0662 100
163.0614 10
"""


@pytest.fixture(scope="session", autouse=True)
def _isolated_settings(qapp, tmp_path_factory):
    """Never read or write the developer's real LibViz settings."""
    QCoreApplication.setOrganizationName("LibVizTests")
    QCoreApplication.setOrganizationDomain("libviz.test")
    QCoreApplication.setApplicationName("LibVizTests")
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                      str(tmp_path_factory.mktemp("settings")))


@pytest.fixture
def msp_file(tmp_path):
    path = tmp_path / "small.msp"
    path.write_text(MSP)
    return path
