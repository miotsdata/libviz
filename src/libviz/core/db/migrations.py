import sys
from pathlib import Path
from alembic.config import Config
from alembic import command

def get_bundle_dir():
    """Get the path to the app directory, even if frozen by PyInstaller."""
    if getattr(sys, 'frozen', False):
        # Running in a bundle (.exe / .app)
        return Path(sys._MEIPASS)
    # Running in normal Python environment
    return Path(__file__).parent.parent.parent.parent.parent

def upgrade_library_schema(db_path: Path):
    bundle_dir = get_bundle_dir()
    ini_path = bundle_dir / "alembic.ini"
    
    alembic_cfg = Config(str(ini_path))
    
    # CRITICAL: Tell Alembic where the versions folder is inside the bundle
    # This overrides the 'script_location' in alembic.ini
    script_location = bundle_dir / "migrations"
    alembic_cfg.set_main_option("script_location", str(script_location))
    
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    
    command.upgrade(alembic_cfg, "head")