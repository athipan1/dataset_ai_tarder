from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

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
import ai_trader.models.user  # noqa: E402, F401
import ai_trader.models.strategy  # noqa: E402, F401
import ai_trader.models.trade  # noqa: E402, F401
# Add other models here if they define tables that Alembic should be aware of for autogenerate
# e.g., if you create models for assets, orders, signals, etc.
# import ai_trader.models.asset # noqa
# import ai_trader.models.order # noqa

from ai_trader.db.base import Base  # noqa: E402
target_metadata = Base.metadata

# Import settings from the new config module
from ai_trader.core.config import settings # noqa: E402

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
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Use a dictionary for engine_from_config to set the URL programmatically
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url() # Use the new settings

    connectable = engine_from_config(
        configuration, # Pass the modified configuration
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
