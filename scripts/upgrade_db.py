import sys
import os
import subprocess  # To call alembic command
from sqlalchemy.exc import OperationalError  # To catch specific DB errors

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Ensure .env is loaded for Alembic to pick up DATABASE_URL from alembic.ini's script.py.mako
# or if alembic env.py directly loads it.
from dotenv import load_dotenv  # noqa: E402
dotenv_path = os.path.join(PROJECT_ROOT, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    print(f".env file loaded from {dotenv_path} for Alembic context.")
else:
    print(f"Warning: .env file not found at {dotenv_path}. "
          "Alembic might not find DATABASE_URL if not set globally.")


def run_alembic_upgrade():
    """
    Runs the 'alembic upgrade head' command.
    Includes error handling for common issues like pre-existing tables with SQLite.
    """
    print("Attempting to upgrade database to the latest revision using Alembic...")
    try:
        alembic_ini_path = os.path.join(PROJECT_ROOT, "alembic.ini")
        if not os.path.exists(alembic_ini_path):
            print(f"Error: alembic.ini not found at {alembic_ini_path}")
            print("Please ensure Alembic is initialized and alembic.ini is in the project root.")
            return

        # Using '-c' to specify the config path is good practice
        command = ["alembic", "-c", alembic_ini_path, "upgrade", "head"]
        print(f"Executing command: {' '.join(command)}")

        # Run the command from the project root
        result = subprocess.run(command, capture_output=True, text=True, check=False, cwd=PROJECT_ROOT)

        if result.returncode == 0:
            print("Alembic upgrade successful.")
            if result.stdout:
                print("Output:\n", result.stdout)
            if result.stderr:  # Sometimes alembic info goes to stderr
                print("Info/Warnings from Alembic (stderr):\n", result.stderr)

        else:
            print("Error during Alembic upgrade.")
            print("Return Code:", result.returncode)
            if result.stdout:
                print("Standard Output:\n", result.stdout)
            if result.stderr:
                print("Standard Error:\n", result.stderr)

            output_combined = result.stdout.lower() + result.stderr.lower()
            if "already exists" in output_combined:
                db_url = os.getenv("DATABASE_URL", "")
                print("\n--------------------------------------------------------------------")
                print("ERROR: It appears one or more tables Alembic tried to create already exist.")
                if db_url.startswith("sqlite:///"):
                    db_file_part = db_url.split(":///")[1]
                    abs_db_file = os.path.join(PROJECT_ROOT, db_file_part) \
                        if not os.path.isabs(db_file_part) else db_file_part
                    db_name = os.path.basename(abs_db_file)
                    print(
                        f"This is common if the SQLite database ('{db_name}') had been "
                        "previously initialized using a method other than Alembic "
                        "(e.g., SQLAlchemy's create_all)."
                    )
                    print("\nTo resolve this for a new Alembic setup with SQLite:")
                    print(f"  1. Ensure no critical data is in '{db_name}'.")
                    print(
                        f"  2. Delete the SQLite database file: rm \"{abs_db_file}\""
                    )
                    script_name = os.path.basename(__file__)
                    print(f"  3. Re-run this script: python {script_name}")
                else:
                    print(
                        "This can happen if the database was previously initialized "
                        "by other means."
                    )
                    print(
                        "For non-SQLite databases, you might need to manually drop "
                        "tables or use `alembic stamp head` if schema matches "
                        "the latest revision."
                    )
                print("-----------------------------\n")
            elif "can't locate revision identified by" in output_combined:
                print("\n--------------------------------------------------------------------")
                print("ERROR: Alembic - Can't locate revision.")
                print(
                    "This might mean the `alembic_version` table is missing/corrupt, "
                    "or contains an unknown revision ID."
                )
                print(
                    "If this is a new database, ensure it's empty before "
                    "the first `upgrade head`."
                )
                print(
                    "If the schema is supposedly up-to-date but Alembic is "
                    "unaware, you might need `alembic stamp head`."
                )
                print("--------------------------------------------------------------------\n")

    except FileNotFoundError:
        print("Error: The 'alembic' command was not found.")
        print("Please ensure Alembic is installed and in your system's PATH.")
        print("You can install it with: pip install alembic")
    except OperationalError as oe:  # This specific exception might be rare here due to subprocess
        print(f"A SQLAlchemy OperationalError occurred directly in the script (unexpected): {oe}")
        # This part of error handling might be more relevant if we used Alembic's Python API directly
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback  # noqa: E402
        traceback.print_exc()


if __name__ == "__main__":
    run_alembic_upgrade()
