from alembic.config import Config
from alembic import command
import os
import sys

# Construct the path to alembic.ini relative to this script
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
alembic_ini_path = os.path.join(project_root, "alembic.ini")

alembic_cfg = Config(alembic_ini_path)
alembic_cfg.set_main_option("script_location", os.path.join(project_root, "alembic"))


def main():
    revision = "-1"
    if len(sys.argv) > 1:
        revision = sys.argv[1]

    print(f"Downgrading database by {revision} revision(s).")
    print(f"Using migrations from: {alembic_cfg.get_main_option('script_location')}")
    print(f"Using database URL: {alembic_cfg.get_main_option('sqlalchemy.url')}")
    command.downgrade(alembic_cfg, revision)
    print("Database downgrade completed.")


if __name__ == "__main__":
    main()
