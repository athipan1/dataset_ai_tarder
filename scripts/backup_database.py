import os
import sys
import shutil
import subprocess
import zipfile
from datetime import datetime

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Ensure .env is loaded for DATABASE_URL
from dotenv import load_dotenv  # noqa: E402

dotenv_path = os.path.join(PROJECT_ROOT, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    print(f".env file loaded from {dotenv_path} for script context.")
else:
    print(
        f"Warning: .env file not found at {dotenv_path}. DATABASE_URL might be missing."
    )

DATABASE_URL = os.getenv(
    "DATABASE_URL", "sqlite:///./ai_trader.db"
)  # Default if not in .env
BACKUP_DIR = os.path.join(PROJECT_ROOT, "database_backups")
os.makedirs(BACKUP_DIR, exist_ok=True)


def backup_sqlite():
    """Backs up an SQLite database file."""
    if not DATABASE_URL.startswith("sqlite:///"):
        print("Error: DATABASE_URL does not specify an SQLite database.")
        return

    db_file_part = DATABASE_URL.split("sqlite:///")[1]
    db_filepath = (
        os.path.join(PROJECT_ROOT, db_file_part)
        if not os.path.isabs(db_file_part)
        else db_file_part
    )

    if not os.path.exists(db_filepath):
        print(f"Error: SQLite database file not found at {db_filepath}")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename_base = f"{os.path.basename(db_filepath)}_{timestamp}"
    backup_filepath_db = os.path.join(BACKUP_DIR, f"{backup_filename_base}.db")
    backup_filepath_zip = os.path.join(BACKUP_DIR, f"{backup_filename_base}.zip")

    try:
        # 1. Copy the database file
        shutil.copy2(db_filepath, backup_filepath_db)
        print(f"SQLite database copied to: {backup_filepath_db}")

        # 2. Compress the copied database file
        with zipfile.ZipFile(backup_filepath_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(backup_filepath_db, arcname=os.path.basename(backup_filepath_db))
        print(f"Compressed backup created: {backup_filepath_zip}")

        # 3. Optionally, remove the uncompressed copy
        os.remove(backup_filepath_db)
        print(f"Removed temporary uncompressed backup: {backup_filepath_db}")

        print("SQLite backup successful.")

    except Exception as e:
        print(f"Error during SQLite backup: {e}")
        import traceback

        traceback.print_exc()


def backup_postgresql():
    """
    Backs up a PostgreSQL database using pg_dump.
    This function assumes pg_dump is in the system's PATH and connection details
    can be inferred from DATABASE_URL or standard PG environment variables (PGHOST, PGUSER, etc.).
    Format of DATABASE_URL for PostgreSQL: postgresql://user:password@host:port/dbname
    """
    if not DATABASE_URL.startswith("postgresql://"):
        print("Error: DATABASE_URL does not specify a PostgreSQL database.")
        return

    print("Attempting PostgreSQL backup using pg_dump...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Try to parse dbname from DATABASE_URL, pg_dump often needs it explicitly
    try:
        from urllib.parse import urlparse

        parsed_url = urlparse(DATABASE_URL)
        db_name = parsed_url.path.lstrip("/")
        if not db_name:
            raise ValueError("Database name not found in DATABASE_URL path.")
    except Exception as e:
        print(
            f"Could not parse database name from DATABASE_URL ('{DATABASE_URL}'): {e}"
        )
        print("PostgreSQL backup might fail without explicit dbname for pg_dump.")
        # Fallback or require db_name to be set as an env var for pg_dump
        db_name = "ai_trader_db"  # Placeholder, this should be accurate
        print(f"Using placeholder db_name: {db_name}. Ensure this is correct.")

    backup_filename = f"{db_name}_backup_{timestamp}.sql"
    # For pg_dumpall (full cluster backup): backup_filename = f"postgres_cluster_backup_{timestamp}.sql"
    # For custom format (allows pg_restore, compression): backup_filename = f"{db_name}_backup_{timestamp}.dump"

    backup_filepath = os.path.join(BACKUP_DIR, backup_filename)

    # Construct the pg_dump command.
    # Using DATABASE_URL directly with pg_dump can be tricky if it contains password.
    # pg_dump relies on PGHOST, PGUSER, PGPASSWORD (via .pgpass or env) environment variables.
    # Or, you can try to pass parts of the URL.
    # For simplicity, we'll assume environment variables are set up for pg_dump,
    # or the user part of DATABASE_URL is sufficient.

    # Example using DATABASE_URL (might expose password in logs if not careful):
    # command = ["pg_dump", "-d", DATABASE_URL, "-f", backup_filepath, "--clean", "--if-exists"]

    # Safer: Rely on env vars (PGHOST, PGPORT, PGUSER, PGDATABASE) or a service file.
    # pg_dump will use PGDATABASE from env if set, or you must specify the dbname.
    command = ["pg_dump", db_name, "-f", backup_filepath, "--clean", "--if-exists"]
    # For custom format compressed backup (recommended):
    # command = ["pg_dump", db_name, "-f", backup_filepath.replace(".sql", ".dump"), "-F", "c", "-Z", "9"]

    print(
        f"Executing command: {' '.join(command)} (ensure DB connection env vars are set for pg_dump)"
    )
    try:
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()

        if process.returncode == 0:
            print(f"PostgreSQL backup successful: {backup_filepath}")
            if stdout:
                print("pg_dump stdout:\n", stdout.decode())
            # stderr might contain progress for pg_dump
            if stderr:
                print("pg_dump stderr (info/warnings):\n", stderr.decode())
        else:
            print(
                f"Error during PostgreSQL backup (pg_dump returned code {process.returncode}):"
            )
            if stdout:
                print("pg_dump stdout:\n", stdout.decode())
            if stderr:
                print("pg_dump stderr:\n", stderr.decode())

    except FileNotFoundError:
        print(
            "Error: 'pg_dump' command not found. Please ensure PostgreSQL client utilities are installed and in your PATH."
        )
    except Exception as e:
        print(f"An unexpected error occurred during PostgreSQL backup: {e}")
        import traceback

        traceback.print_exc()


def main():
    print("Starting database backup script...")
    if DATABASE_URL.startswith("sqlite:///"):
        backup_sqlite()
    elif DATABASE_URL.startswith("postgresql://"):
        backup_postgresql()
    else:
        print(f"Error: Unsupported database type in DATABASE_URL: {DATABASE_URL}")
        print("This script currently supports 'sqlite:///' and 'postgresql://' URLs.")

    print("\n--- CRON Job / Task Scheduler Setup ---")
    print("To automate database backups, set up a CRON job or Task Scheduler.")
    print("Example CRON job (runs daily at 3 AM):")
    # The following f-string was split to avoid E501:
    abs_script_path = os.path.abspath(__file__)
    log_file = "/var/log/ai_trader_backup.log"
    command_part = f"0 3 * * * /usr/bin/python3 {abs_script_path}"
    redirect_part = f">> {log_file} 2>&1"
    cron_command = f"{command_part} {redirect_part}"
    # py_exec = "/usr/bin/python3"
    # schedule = "0 3 * * *"
    # cron_command = f"{schedule} {py_exec} {abs_script_path} {redirect_part}"
    print(cron_command)
    print("\nReplace paths with your actual Python interpreter and script location.")
    print(
        "Ensure the environment (DATABASE_URL, PostgreSQL client tools path, PG env vars) is available."
    )
    print("---------------------------------------\n")


if __name__ == "__main__":
    main()
    print("Database backup script finished.")
