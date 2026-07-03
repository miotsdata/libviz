import sys
from pathlib import Path
from alembic.config import Config
from alembic import command
from importlib.resources import files


def _get_migrations_dir() -> Path:
    """
    Locate the migrations directory regardless of how the package is running:
    - normal pip install  → inside site-packages/libviz
    - PyInstaller bundle  → extracted to sys._MEIPASS/migrations
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller bundle — files are extracted to _MEIPASS
        return Path(sys._MEIPASS) / "migrations"

    # Installed package — use importlib.resources to find the data
    # This works whether installed as a wheel, editable install, or zipapp
    ref = files("libviz") / "migrations"
    return Path(str(ref))


def _get_alembic_ini() -> Path:
    """Locate alembic.ini using the same strategy."""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS) / "alembic.ini"
    ref = files("libviz") / "alembic.ini"
    return Path(str(ref))


def upgrade_library_schema(db_path: Path) -> None:
    migrations_dir = _get_migrations_dir()
    ini_path       = _get_alembic_ini()

    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option("script_location", str(migrations_dir))
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

    command.upgrade(alembic_cfg, "head")