from alembic.config import Config
from alembic import command
import os

# Construct the path to alembic.ini relative to this script
# This script is in /scripts, alembic.ini is in /
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
alembic_ini_path = os.path.join(project_root, "alembic.ini")

alembic_cfg = Config(alembic_ini_path)
alembic_cfg.set_main_option("script_location", os.path.join(project_root, "alembic"))


def main():
    print(f"Applying migrations from: {alembic_cfg.get_main_option('script_location')}")
    print(f"Using database URL: {alembic_cfg.get_main_option('sqlalchemy.url')}")
    command.upgrade(alembic_cfg, "head")
    print("Database upgrade completed.")


if __name__ == "__main__":
    main()
