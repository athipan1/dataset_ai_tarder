import sys
import os
import traceback  # Standard library

from dotenv import load_dotenv  # Third-party library

# Project path configuration
# This block needs to be before local application imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Local application imports
from ai_trader.db.init_db import init_db  # noqa: E402
from ai_trader.db.session import engine  # noqa: E402, engine is already configured in session.py


def load_environment_variables():
    """Loads .env file from project root or one level up."""
    dotenv_path = os.path.join(PROJECT_ROOT, '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
        print(f".env file loaded from {dotenv_path}")
        return True

    dotenv_path_alt = os.path.join(PROJECT_ROOT, '..', '.env')
    if os.path.exists(dotenv_path_alt):
        load_dotenv(dotenv_path_alt)
        print(f".env file loaded from {dotenv_path_alt}")
        return True

    print(f".env file not found at {dotenv_path} or {dotenv_path_alt}. "
          "Ensure it exists and DATABASE_URL is set.")
    return False


def check_sqlite_file(db_engine):
    """Checks for SQLite database file existence and logs information."""
    if not str(db_engine.url).startswith("sqlite"):
        return

    db_file_path_str = str(db_engine.url).replace("sqlite:///", "")

    if db_file_path_str.startswith('./'):
        db_file_path_abs = os.path.join(PROJECT_ROOT, db_file_path_str[2:])
    elif not os.path.isabs(db_file_path_str):  # relative path not starting with ./
        db_file_path_abs = os.path.join(PROJECT_ROOT, db_file_path_str)
    else:  # absolute path
        db_file_path_abs = db_file_path_str

    if os.path.exists(db_file_path_abs):
        print(f"SQLite database file confirmed at: {os.path.abspath(db_file_path_abs)}")
    else:
        print(f"Warning: SQLite database file NOT found at expected location: {os.path.abspath(db_file_path_abs)}")
        print("Ensure the DATABASE_URL in .env points to the correct relative or absolute path.")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Project root (calculated): {PROJECT_ROOT}")


def main():
    """
    Main function to initialize the database.
    Loads environment variables, then attempts to create database tables.
    """
    print("Attempting to create database tables...")
    load_environment_variables()

    # The engine is imported from session.py, where it's already configured with DATABASE_URL.
    # init_db will use this engine.

    # IMPORTANT: If using Alembic for database migrations, the `init_db(engine)`
    # call below should typically be commented out or removed after the initial
    # setup, or used only for development databases not managed by Alembic.
    # Alembic will handle table creation and schema management.
    # Running both `init_db` (which calls Base.metadata.create_all) and
    # `alembic upgrade` can lead to conflicts or errors if tables already exist.

    # To initialize a database using SQLAlchemy's create_all (e.g., for a quick dev setup
    # WITHOUT Alembic, or if you are generating the very first Alembic migration from these tables):
    # try:
    #     print("Attempting to initialize database using direct SQLAlchemy Base.metadata.create_all()...")
    #     init_db(engine)
    #     print("Database tables process completed via create_all.")
    #     print(f"Database configured at: {engine.url}")
    #     check_sqlite_file(engine)
    # except EnvironmentError as ee:

    # For Alembic-managed databases, rely on `alembic upgrade head` (e.g., via `scripts/upgrade_db.py`).
    print("Script `create_db.py` executed. If you intend to use Alembic,")
    print("ensure you run `python scripts/upgrade_db.py` or `alembic upgrade head` ")
    print("to manage your database schema. This script's `init_db()` call is primarily for non-Alembic setups,")
    print("or for an initial table setup before Alembic takes over.")
    # Dummy try-except to maintain structure if uncommenting above lines.
    try:
        pass
    except EnvironmentError as ee:
        print(f"Configuration error: {ee}")
        print("Please ensure your .env file is correctly set up with DATABASE_URL.")
    except ImportError as ie:
        print(f"Import error: {ie}")
        print("Ensure all dependencies are installed and the project structure is correct.")
        print(f"PROJECT_ROOT is: {PROJECT_ROOT}")
        print(f"sys.path includes: {sys.path}")
    except Exception as e:
        print(f"An error occurred during database initialization: {e}")
        traceback.print_exc()
        print("Further suggestions:")
        print("- Check database server status if using PostgreSQL/MySQL etc.")
        print("- Verify connection string details (user, password, host, dbname).")


if __name__ == "__main__":
    main()
