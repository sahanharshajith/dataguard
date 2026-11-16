from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "backend" / "migrations"


def test_migration_history_has_a_single_head():
    # Two heads means two migrations branched from the same parent and must be merged.
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    assert len(ScriptDirectory.from_config(config).get_heads()) == 1