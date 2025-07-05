import os
from alembic.config import Config


project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
alembic_ini_path = os.path.join(project_root, "alembic.ini")


def main():
    print("Database creation/preparation script.")

    alembic_cfg = Config(alembic_ini_path)
    db_url = alembic_cfg.get_main_option("sqlalchemy.url")

    if db_url.startswith("sqlite:///"):
        db_path = db_url.replace("sqlite:///", "")
        # For SQLite, the database file is created automatically if it doesn't exist
        # when a connection is made, for example, by `alembic upgrade head`.
        # We can check if the file exists.
        if os.path.exists(os.path.join(project_root, db_path)):
            print(f"SQLite database file '{db_path}' already exists.")
        else:
            print(f"SQLite database file '{db_path}' will be created by the first migration.")
        print("No explicit creation step needed for SQLite, migrations will handle it.")
    elif db_url.startswith("postgresql"):
        print(f"PostgreSQL database URL detected: {db_url}")
        print("For PostgreSQL, ensure the database is created manually or via another script.")
        print("Example: CREATE DATABASE your_db_name;")
        # Here you could add logic to connect to the default 'postgres' db
        # and issue a 'CREATE DATABASE' command if it doesn't exist.
        # This requires database credentials with creation privileges.
        # from sqlalchemy import create_engine
        # from sqlalchemy.exc import OperationalError
        # try:
        #     engine = create_engine(db_url)
        #     with engine.connect() as connection:
        #         print("Database already exists and is connectable.")
        # except OperationalError as e:
        #     if "does not exist" in str(e): # This error message is specific to psycopg2
        #         print(f"Database does not exist. You might need to create it.")
        #         print("Attempting to create database (requires appropriate permissions)...")
        #         # This is a simplified example and might need more robust error handling
        #         # and parsing of the database URL to connect to the default 'postgres' database.
        #         # For instance, connect to 'postgres' db then CREATE DATABASE.
        #     else:
        #         print(f"Could not connect to database: {e}")
    else:
        print(f"Unsupported database type for automatic creation: {db_url}")

    print("If you haven't run migrations yet, run: python scripts/upgrade_db.py")


if __name__ == "__main__":
    main()
