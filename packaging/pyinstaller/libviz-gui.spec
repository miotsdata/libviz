# packaging/pyinstaller/libviz-gui.spec
#
# Build: pdm run pyinstaller packaging/pyinstaller/libviz-gui.spec --noconfirm
# (run from the repo root). Copied from MSIAnalyzer's spec (ADR 7).
#
# onedir, not onefile: onefile unpacks the whole bundle to a temp dir on
# every launch, which costs seconds of startup.
import re
import sys
from pathlib import Path

from PyInstaller.depend import bindepend

REPO_ROOT = Path(SPECPATH).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
PKG = SRC_ROOT / "libviz"

sys.path.insert(0, str(SRC_ROOT))

# Qt Graphs' 2D internals (the `QtGraphs2D.impl` QML module, embedded in
# Qt6Graphs2DImpl) are linked by libQt6Graphs on Linux, but no Windows DLL
# imports Qt6Graphs2DImpl.dll. PyInstaller's import walk never collects it,
# and without it every Qt Graphs plot crashes (access violation in Qt6Core).
# Collected by hand here and loaded by gui/main.py (load_qt_graphs_2d_impl).
# Same fix as MSIAnalyzer (commit 94074b3).
import PySide6  # noqa: E402

_GRAPHS_2D_IMPL = Path(PySide6.__file__).parent / "Qt6Graphs2DImpl.dll"
EXTRA_BINARIES = [(str(_GRAPHS_2D_IMPL), "PySide6")] if _GRAPHS_2D_IMPL.exists() else []
# Kept by the pruning below although nothing imports them (see above).
ALWAYS_KEEP_LIBS = {"qt6graphs2dimpl.dll"}

excludes = [
    "pytest", "_pytest", "pytestqt", "pylint", "astroid", "hupper",
    "archunitpython", "IPython", "jedi", "parso", "PyInstaller",
]

a = Analysis(
    [str(PKG / "gui" / "main.py")],
    pathex=[str(SRC_ROOT)],
    binaries=EXTRA_BINARIES,
    datas=[
        # gui/main.py loads QML from files next to itself (ADR 2); as the
        # entry script it runs from the bundle root, so qml/ goes there.
        (str(PKG / "gui" / "qml"), "qml"),
        # core/db/migrations.py looks for these at sys._MEIPASS when frozen.
        (str(PKG / "migrations"), "migrations"),
        (str(PKG / "alembic.ini"), "."),
    ],
    # Imported only by the migration scripts, which Alembic loads from files.
    hiddenimports=["alembic.op", "alembic.context", "logging.config",
                   "openpyxl"],  # pandas imports it by name for read_excel (ADR 10)
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)


# --- Trim what PySide6's own hooks add unconditionally (they rglob the
# whole Qt tree regardless of `datas`); filtering a.datas/a.binaries
# after Analysis() is the only point that has an effect. Same approach
# and lists as MSIAnalyzer.
#
# QML modules: only those our .qml files import
# (`grep -rhoE "^import [A-Za-z0-9_.]+" src/libviz/gui/qml`) plus the
# always-needed core ones.
KEEP_TOP_LEVEL_QML_DIRS = {"qt", "qtcore", "qtqml", "qtquick", "qtgraphs"}
# Fusion is the only Controls style used (QQuickStyle.setStyle in main.py).
DROP_QTQUICK_PATH_FRAGMENTS = [
    "qtquick/pdf",
    "qtquick/virtualkeyboard",
    "controls/material",
    "controls/universal",
    "controls/imagine",
    "controls/fluentwinui3",
    "controls/designer",
]
# Qt/FFmpeg libs left orphaned once those QML plugins are gone: computed
# by following real link-time imports from everything kept, never a
# hand-written list (one once dropped a lib that was linked directly and
# the app crashed at startup). Only Qt6*/FFmpeg names are ever pruned:
# Qt loads a few other DLLs at runtime without linking them.
PRUNABLE_LIB = re.compile(
    r"^(lib)?(qt6[\w-]*|avcodec|avformat|avutil|swresample|swscale)([.-][\w.-]*)?\.(so[\d.]*|dll)$"
)


def _unreachable_qt_libs(binaries) -> set[str]:
    candidates = {
        Path(dest).name.lower(): src
        for dest, src, _ in binaries
        if PRUNABLE_LIB.match(Path(dest).name.lower())
    }
    todo = [src for dest, src, _ in binaries if Path(dest).name.lower() not in candidates]
    seen_src, reached = set(), set()
    while todo:
        src = todo.pop()
        if src in seen_src:
            continue
        seen_src.add(src)
        for name, _path in bindepend.get_imports(src):
            key = Path(name).name.lower()
            if key in candidates and key not in reached:
                reached.add(key)
                todo.append(candidates[key])
    return set(candidates) - reached - ALWAYS_KEEP_LIBS


def _is_unwanted(path: str) -> bool:
    lowered = path.replace("\\", "/").lower()
    # Linux wheels nest Qt's tree under PySide6/Qt/, Windows wheels don't.
    lowered = lowered.replace("pyside6/qt/", "pyside6/")

    if "pyside6/translations/" in lowered:
        return True  # no QTranslator anywhere in libviz

    if "pyside6/qml/" in lowered:
        module = lowered.split("pyside6/qml/", 1)[1].split("/", 1)[0]
        if module not in KEEP_TOP_LEVEL_QML_DIRS:
            return True
        if any(frag in lowered for frag in DROP_QTQUICK_PATH_FRAGMENTS):
            return True

    return False


a.datas = [d for d in a.datas if not (_is_unwanted(d[0]) or _is_unwanted(d[1]))]
a.binaries = [b for b in a.binaries if not (_is_unwanted(b[0]) or _is_unwanted(b[1]))]
_unreachable = _unreachable_qt_libs(a.binaries)
print(f"libviz-gui.spec: pruning {len(_unreachable)} unreachable Qt libs: {sorted(_unreachable)}")
a.binaries = [b for b in a.binaries if Path(b[0]).name.lower() not in _unreachable]

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="libviz-gui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    # No icon=: PyInstaller needs Pillow to turn the .png into an .ico and
    # libviz doesn't depend on it, so the .exe keeps the default icon.
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="libviz-gui",
)
