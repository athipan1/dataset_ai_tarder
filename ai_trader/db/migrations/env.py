from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
import os
import sys

# Ensure the project root (containing the 'ai_trader' package) is in the path.
# alembic.ini's prepend_sys_path = . also helps if alembic is run from project root.
# The path from env.py (in alembic/env.py) to project root is one level up.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Ensure all models are imported so Base.metadata is populated before it's assigned to target_metadata
# This is crucial for Alembic autogenerate and for ensuring migrations have the correct context.
# All models are now defined in ai_trader.models.py and use the Base from there.
# Importing Base from ai_trader.models will make its metadata available.
from ai_trader.models import (Asset, AuditLog,  # noqa: E402, F401
                              BacktestResult, Base, MarketEvent, Order,
                              PriceData, Signal, Strategy, Trade,
                              TradeAnalytics, User, UserBehaviorLog)

target_metadata = Base.metadata

# Import settings from the new config module
from ai_trader.config import settings  # noqa: E402

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def get_url():
    """Helper function to get the database URL from settings."""
    return settings.DATABASE_URL


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # url = config.get_main_option("sqlalchemy.url") # Original line
    url = get_url() # Use the new settings
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # Also enable batch mode for offline context
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Check if an engine is passed directly via config attributes (e.g., from tests)
    connectable = config.attributes.get('connection_engine_for_tests')

    if connectable is None:
        # No direct engine passed, so configure one based on URL (normal CLI flow)
        db_url = config.get_main_option("sqlalchemy.url")
        if not db_url:
            db_url = get_url() # Fallback to settings from ai_trader.config

        engine_config_dict = config.get_section(config.config_ini_section, {})
        engine_config_dict["sqlalchemy.url"] = db_url

        connectable = engine_from_config(
            engine_config_dict,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
    # else: Engine was passed directly from tests, use it.

    # Now connectable is either the test_engine or the newly created engine
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True  # Enable batch mode for SQLite
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
