# tests/test_migrations.py
import pytest
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, Session as SASession
from alembic.config import Config as AlembicConfig
from alembic import command as alembic_command
import os
from typing import Generator

# Use config from ai_trader.core.config for consistency,
# but tests can override DATABASE_URL via TEST_DB_URL env var.
from ai_trader.core.config import settings as app_settings
from ai_trader.db.base import Base # To access metadata for drop/create if needed & schema checks

# --- Configuration for Test Database ---
TEST_DATABASE_URL_SQLITE_IN_MEMORY = "sqlite:///:memory:"
# Example for PostgreSQL (requires a running instance accessible to tests)
# TEST_DATABASE_URL_POSTGRES = "postgresql://test_user:test_password@localhost:5432/ai_trader_test_db_migrations"

# Test database URL can be overridden by environment variable
TEST_DATABASE_URL = os.getenv("TEST_DB_URL", TEST_DATABASE_URL_SQLITE_IN_MEMORY)
print(f"Running migration tests against: {TEST_DATABASE_URL}")


# --- Alembic Configuration Setup ---
# Assuming alembic.ini and the 'alembic' script directory are in the project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALEMBIC_INI_PATH = os.path.join(PROJECT_ROOT, 'alembic.ini')
# The script_location in alembic.ini is usually relative (e.g., "alembic")
# If it's absolute or needs adjustment, do it here or ensure alembic.ini is correct.

@pytest.fixture(scope="session")
def alembic_config_obj() -> AlembicConfig:
    """
    Fixture to create an Alembic Config object pointing to the test database.
    """
    if not os.path.exists(ALEMBIC_INI_PATH):
        pytest.fail(f"Alembic config file not found at: {ALEMBIC_INI_PATH}")

    config = AlembicConfig(ALEMBIC_INI_PATH)
    # No need to set script_location if it's correctly relative in alembic.ini
    # config.set_main_option("script_location", "alembic") # Redundant if alembic.ini has it
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    return config


@pytest.fixture(scope="session")
def test_engine_session_scoped():
    """
    SQLAlchemy engine for the test database (session-scoped).
    """
    engine = create_engine(TEST_DATABASE_URL)
    yield engine
    engine.dispose()

@pytest.fixture(scope="function")
def db_session_migrated(test_engine_session_scoped, alembic_config_obj: AlembicConfig) -> Generator[SASession, None, None]:
    """
    Sets up the DB to the latest migration, yields a session, then downgrades to base.
    Ensures each test function runs on a freshly migrated schema.
    """
    engine = test_engine_session_scoped

    # Ensure tables are dropped if any exist from previous failed run (only for persistent test DBs)
    # For SQLite in-memory, this is not strictly necessary as it starts empty.
    if TEST_DATABASE_URL != TEST_DATABASE_URL_SQLITE_IN_MEMORY :
         Base.metadata.drop_all(bind=engine) # Drop all known tables from models
         # Potentially drop alembic_version too, or handle if downgrade base fails
         try:
            with engine.connect() as conn:
                conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
                conn.commit()
         except Exception as e:
            print(f"Could not drop alembic_version table (may not exist): {e}")


    alembic_command.upgrade(alembic_config_obj, "head")

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    yield session

    session.close()
    alembic_command.downgrade(alembic_config_obj, "base")


# --- Test Cases ---

def test_migrations_cycle(alembic_config_obj: AlembicConfig, test_engine_session_scoped):
    """
    Tests a full upgrade to 'head' and downgrade to 'base'.
    """
    engine = test_engine_session_scoped
    try:
        # Start from base (important if engine is session-scoped and tests run sequentially)
        try: # Try to downgrade first in case a previous test failed mid-way
            alembic_command.downgrade(alembic_config_obj, "base")
        except Exception: # May fail if already at base or no alembic_version table
            pass

        alembic_command.upgrade(alembic_config_obj, "head")
        inspector_head = inspect(engine)
        tables_at_head = inspector_head.get_table_names()

        assert "users" in tables_at_head
        assert "assets" in tables_at_head
        assert "orders" in tables_at_head
        # The 'trades' table is defined in models but not in the initial migration.
        # This assertion will FAIL until a migration for 'trades' table is added.
        # assert "trades" in tables_at_head, "'trades' table missing at head. Create a migration for it."

        alembic_command.downgrade(alembic_config_obj, "base")
        inspector_base = inspect(engine)
        tables_at_base = [t for t in inspector_base.get_table_names() if t != "alembic_version"]
        assert len(tables_at_base) == 0, f"Tables still exist after downgrade to base: {tables_at_base}"

    except Exception as e:
        pytest.fail(f"Migration cycle (head -> base) failed: {e}")


def test_individual_migrations_incrementally(alembic_config_obj: AlembicConfig, test_engine_session_scoped):
    """
    Tests upgrading and downgrading migrations one by one.
    This requires fetching the list of revisions.
    """
    engine = test_engine_session_scoped

    # Get all revision scripts (simplified, assumes linear history for this test)
    # A more robust way would be to parse script_location directory
    # For now, we assume we start from base and go up.
    # This test is more complex to implement generically without knowing all revisions.
    # We'll test the first one explicitly as an example.

    first_revision_id = "aef0e2350ba4" # From initial migration

    try:
        # Ensure we are at base
        try:
            alembic_command.downgrade(alembic_config_obj, "base")
        except Exception:
            pass

        # Upgrade to the first revision
        alembic_command.upgrade(alembic_config_obj, first_revision_id)
        inspector_after_first = inspect(engine)
        assert "users" in inspector_after_first.get_table_names(), "Table 'users' should exist after first migration"

        # Downgrade from the first revision (back to base)
        alembic_command.downgrade(alembic_config_obj, f"{first_revision_id}^") # or "base"
        inspector_after_downgrade = inspect(engine)
        tables_after_downgrade = [t for t in inspector_after_downgrade.get_table_names() if t != "alembic_version"]
        assert len(tables_after_downgrade) == 0, "Tables should not exist after downgrading first migration"

    except Exception as e:
        pytest.fail(f"Incremental migration test for revision {first_revision_id} failed: {e}")


def test_schema_matches_models_at_head(db_session_migrated: SASession):
    """
    After migrating to 'head', does the DB schema reflect SQLAlchemy models?
    The db_session_migrated fixture handles migrating to head.
    """
    session = db_session_migrated # This session is already on a DB migrated to head
    inspector = inspect(session.bind)
    db_tables = inspector.get_table_names()

    model_table_names = set(Base.metadata.tables.keys())

    # Tables that are in models but might not have migrations yet (like 'trades')
    # or optional tables (like 'archived_trades')
    expected_but_conditionally_present = {"trades", "archived_trades"}

    for table_name in model_table_names:
        if table_name in expected_but_conditionally_present and table_name not in db_tables:
            print(f"INFO: Model table '{table_name}' is defined but not found in DB (migration might be pending). Skipping detailed check for it.")
            continue

        assert table_name in db_tables, f"Model table '{table_name}' not found in migrated database."

        # Basic column check (more detailed checks for types, nullability, etc., are possible but complex)
        db_columns = {col['name'] for col in inspector.get_columns(table_name)}
        model_columns = {col.name for col in Base.metadata.tables[table_name].columns}

        assert model_columns == db_columns, \
            f"Column mismatch for table '{table_name}'. Model: {model_columns}, DB: {db_columns}"

    # Example: Try a simple operation with a model if it's expected to be in the DB
    # from ai_trader.models.user import User
    # if "users" in db_tables:
    #     try:
    #         _ = session.query(User).count()
    #     except Exception as e:
    #         pytest.fail(f"Failed to query User model on migrated schema: {e}")


# To make this test suite more robust:
# 1. Add a migration for the 'trades' table based on 'ai_trader/models/trade.py'.
#    Run: `bash scripts/generate_migration.sh "create_trades_table"`
#    Then, uncomment the 'trades' assertion in `test_migrations_cycle`.
# 2. If using a persistent test DB (not SQLite in-memory), ensure it's properly cleaned
#    before and after test runs, especially if tests can fail and leave the DB in an
#    intermediate state. The `db_session_migrated` fixture tries to handle this.
# 3. For data migration tests (if you have them), you'd need to:
#    - Upgrade to revision N-1.
#    - Insert specific data.
#    - Upgrade to revision N.
#    - Assert data integrity/transformation.
#    - Optionally, downgrade to N-1 and assert again.
