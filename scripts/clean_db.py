import argparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Adjust imports to match project structure
# Assuming models are in ai_trader.models and db session components are in ai_trader.db.session
try:
    from ai_trader.db.session import engine  # Using engine directly
    from ai_trader.models import Base
except ImportError as e:
    logger.error(
        f"Failed to import necessary modules. Ensure your PYTHONPATH is set correctly and modules are accessible: {e}"
    )
    logger.error(
        "Attempting to use relative imports for common project structures as a fallback (less ideal)."
    )
    # This is a fallback, direct imports as above are preferred if PYTHONPATH is correctly configured
    # or if the script is run as a module (e.g., python -m scripts.clean_db)
    import os
    import sys

    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from ai_trader.db.session import engine
    from ai_trader.models import Base


def clean_all_data(db_engine, force=False):
    """
    Drops all tables defined in Base.metadata and recreates them.
    Effectively resets the database to an empty state according to the current models.
    """
    if not force:
        confirmation = input(
            "Are you sure you want to drop and recreate all tables? "
            "This will delete ALL data. (yes/no): "
        )
        if confirmation.lower() != "yes":
            logger.info("Database cleanup aborted by user.")
            return

    logger.info("Starting database cleanup: Dropping all tables...")
    try:
        # Drop all tables defined in the metadata
        Base.metadata.drop_all(bind=db_engine)
        logger.info("All tables dropped successfully.")

        # Recreate all tables defined in the metadata
        logger.info("Recreating all tables...")
        Base.metadata.create_all(bind=db_engine)
        logger.info("All tables recreated successfully.")
        logger.info(
            "Database has been reset to an empty state based on current models."
        )

    except Exception as e:
        logger.error(f"An error occurred during database cleanup: {e}", exc_info=True)
        # Depending on the DB and ORM setup, a rollback might be needed if a transaction was implicitly started.
        # However, drop_all/create_all are usually DDL operations that auto-commit or don't run in a transaction
        # in the same way as DML. For SQLAlchemy, explicit transaction management for these is less common.


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Clean Database Script: Drops and recreates all tables."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force delete all data without prompting for confirmation.",
    )
    args = parser.parse_args()

    logger.info("Attempting to connect to the database and clean it...")
    # 'engine' is imported from ai_trader.db.session
    # No need to create a new session for DDL operations like drop_all/create_all,
    # as they operate on the engine level.
    clean_all_data(engine, args.force)
    logger.info("Database cleaning process finished.")
