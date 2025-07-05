import sys
import os

# Add the project root to the Python path to allow for absolute imports
# This assumes 'scripts/' is one level down from the project root.
# If 'ai_trader' and 'scripts' are sibling directories, this path needs adjustment.
# Current assumption:
# project_root/
#  ├── ai_trader/
#  ├── scripts/
#  └── .env
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, PROJECT_ROOT)

# Ensure ai_trader is in path if it's not directly in PROJECT_ROOT
# For example, if structure is project_root/src/ai_trader
# and scripts is project_root/scripts, then you might need:
# sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))

from ai_trader.db.init_db import init_db
from ai_trader.db.session import engine # engine is already configured in session.py
from dotenv import load_dotenv

def main():
    print("Attempting to create database tables...")

    # Load .env file from the project root.
    # session.py also loads .env, but doing it here ensures that any script-specific
    # configurations or checks can happen early.
    dotenv_path = os.path.join(PROJECT_ROOT, '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
        print(f".env file loaded from {dotenv_path}")
    else:
        # If .env is not in PROJECT_ROOT, try one level up from PROJECT_ROOT
        # This handles cases where PWD is 'scripts' and .env is in parent of 'scripts'
        dotenv_path_alt = os.path.join(PROJECT_ROOT, '..', '.env')
        if os.path.exists(dotenv_path_alt):
            load_dotenv(dotenv_path_alt)
            print(f".env file loaded from {dotenv_path_alt}")
        else:
            print(f".env file not found at {dotenv_path} or {dotenv_path_alt}. Make sure it exists and DATABASE_URL is set.")
            # Proceeding, as session.py will raise an error if DATABASE_URL is truly missing.

    # The engine is imported from session.py, where it's already configured with DATABASE_URL.
    # init_db will use this engine.
    try:
        init_db(engine)
        print("Database tables process completed.")
        print(f"Database configured at: {engine.url}")

        # Check for SQLite file existence specifically
        if str(engine.url).startswith("sqlite"):
            # Relative paths for sqlite:///./file.db are relative to where the script is run.
            # If DATABASE_URL=sqlite:///./ai_trader.db and script is run from PROJECT_ROOT,
            # it will be PROJECT_ROOT/ai_trader.db
            # If DATABASE_URL=sqlite:///ai_trader.db (no dot), it's often treated as an absolute path in some contexts
            # or relative to CWD. SQLAlchemy usually handles this as relative to CWD.

            db_file_path_str = str(engine.url).replace("sqlite:///", "")

            # If .env is in PROJECT_ROOT and defines sqlite:///./file.db
            # and create_db.py is in PROJECT_ROOT/scripts/
            # The path ./ai_trader.db would be relative to PROJECT_ROOT if python is run from there.
            # Let's try to construct the expected path relative to PROJECT_ROOT
            if db_file_path_str.startswith('./'):
                db_file_path_abs = os.path.join(PROJECT_ROOT, db_file_path_str[2:])
            elif not os.path.isabs(db_file_path_str): # relative path not starting with ./
                db_file_path_abs = os.path.join(PROJECT_ROOT, db_file_path_str)
            else: # absolute path
                db_file_path_abs = db_file_path_str

            if os.path.exists(db_file_path_abs):
                print(f"SQLite database file confirmed at: {os.path.abspath(db_file_path_abs)}")
            else:
                print(f"Warning: SQLite database file NOT found at expected location: {os.path.abspath(db_file_path_abs)}")
                print("Ensure the DATABASE_URL in .env points to the correct relative or absolute path.")
                print(f"Current working directory: {os.getcwd()}")
                print(f"Project root (calculated): {PROJECT_ROOT}")


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
        import traceback
        traceback.print_exc()
        print("Further suggestions:")
        print("- Check database server status if using PostgreSQL/MySQL etc.")
        print("- Verify connection string details (user, password, host, dbname).")

if __name__ == "__main__":
    main()
