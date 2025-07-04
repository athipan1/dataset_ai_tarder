import os
import sys

# --- DEBUGGING PATH ISSUES ---
print(f"--- DEBUG: Initial sys.path in env.py: {sys.path}")
print(f"--- DEBUG: Initial CWD in env.py: {os.getcwd()}")
project_root = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..'))
print(f"--- DEBUG: Calculated project_root: {project_root}")
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    print(f"--- DEBUG: sys.path after inserting project_root: {sys.path}")
else:
    print(f"--- DEBUG: project_root already in sys.path.")
# --- END DEBUGGING ---

from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line needs to be positioned at the top of the file to ensure that
# the logger is configured before any other operations try to use it.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add the project's root directory to the Python path (handled by debug block above)
# This allows alembic to find your models.py file
# The actual path to your models.py might need adjustment
# depending on your project structure.
# Assuming alembic.ini is in the root and this env.py is in db/migrations/
# sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..'))) # Moved to debug block
# The prepend_sys_path = . in alembic.ini should handle this.

# Import your Base model.
# Adjust the import according to your project structure.
# This assumes your models are defined in 'db.models.Base'
from db.models import Base  # Updated import path
from db.session import DATABASE_URL # Import DATABASE_URL for direct use if needed

# Set target_metadata for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def get_url():
    # Prioritize DATABASE_URL environment variable
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        print(f"--- DEBUG: Using DATABASE_URL from environment: '{db_url}'")
        return db_url

    # Fallback to the value from alembic.ini's sqlalchemy.url
    ini_url = config.get_main_option("sqlalchemy.url") # This was returning the raw string e.g. "${DATABASE_URL:sqlite:///./ai_trader.db}"

    # Manually parse the ini_url if it contains the known pattern ${VAR:default}
    if ini_url and ini_url.startswith("${") and ":" in ini_url and ini_url.endswith("}"):
        # Extract the default part, e.g. "sqlite:///./ai_trader.db" from "${DATABASE_URL:sqlite:///./ai_trader.db}"
        try:
            # Simple parse: find first ':', take rest up to last '}'
            default_url_candidate = ini_url.split(":", 1)[1][:-1]
            # Check if this looks like a valid URL scheme (optional, but good practice)
            if "://" in default_url_candidate:
                print(f"--- DEBUG: Using default URL from parsed alembic.ini string: '{default_url_candidate}'")
                return default_url_candidate
            else:
                print(f"--- DEBUG: Parsed default URL '{default_url_candidate}' from alembic.ini seems invalid, proceeding to next fallback.")
        except IndexError:
            print(f"--- DEBUG: Could not parse default URL from alembic.ini string: '{ini_url}', proceeding to next fallback.")

    # If ini_url is a direct URL (not the pattern) or parsing failed, and it's not None or empty
    if ini_url and "://" in ini_url: # Check if it looks like a valid URL
        print(f"--- DEBUG: Using sqlalchemy.url directly from alembic.ini (not an env var pattern or successfully parsed): '{ini_url}'")
        return ini_url

    # Final hardcoded fallback if all else fails or DATABASE_URL was empty
    final_default_url = "sqlite:///./ai_trader.db"
    print(f"--- DEBUG: Falling back to hardcoded default URL: '{final_default_url}' because previous attempts failed or DATABASE_URL was empty/invalid.")
    print(f"--- DEBUG: (Original ini_url was: '{ini_url}', os.getenv('DATABASE_URL') was: '{os.getenv('DATABASE_URL')}')")
    return final_default_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url()
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
    # configuration = config.get_section(config.config_ini_section, {})
    # configuration["sqlalchemy.url"] = get_url()
    # connectable = engine_from_config(
    #     configuration,
    #     prefix="sqlalchemy.",
    #     poolclass=pool.NullPool,
    # )

    # Use the engine from db.session.py if possible, or construct as alembic expects
    # This ensures consistency if your app has specific engine configurations
    from db.session import engine as app_engine

    # If using the app's engine, make sure its URL is what Alembic expects
    # Alembic's config object (config.get_main_option("sqlalchemy.url")) should be the source of truth for migrations
    # However, if your app_engine is already configured with the correct URL (e.g. from DATABASE_URL env var),
    # you might be able to use it directly.
    # For simplicity and to ensure Alembic controls the DB connection for migrations:
    actual_url = get_url()
    print(f"--- DEBUG: URL obtained by get_url(): '{actual_url}'")
    connectable_config = config.get_section(config.config_ini_section, {})
    connectable_config['sqlalchemy.url'] = actual_url # Use the fetched and printed URL
    connectable = engine_from_config(
        connectable_config,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )


    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True # For SQLite compatibility
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
