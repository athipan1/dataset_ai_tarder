from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import settings from the centralized config file
from ai_trader.config import settings  # Updated import

# DATABASE_URL is now sourced from settings
DATABASE_URL = settings.DATABASE_URL

if DATABASE_URL is None:
    # This check might be redundant if settings.DATABASE_URL already ensures a value or raises an error.
    # However, keeping it for explicitness, or it can be removed if settings guarantees non-None.
    raise EnvironmentError(
        "DATABASE_URL not available from settings. "
        "Ensure it's configured in .env or environment variables and loaded by config.py."
    )

engine_args = {}
if DATABASE_URL.startswith("sqlite"):
    # For SQLite, ensure check_same_thread is False for non-serial access (e.g. web apps)
    # This is also important for Alembic.
    engine_args["connect_args"] = {"check_same_thread": False}
    # Potentially use NullPool for SQLite to avoid issues with some serverless environments or multiprocessing
    # from sqlalchemy.pool import NullPool
    # engine_args["poolclass"] = NullPool
elif DATABASE_URL.startswith("postgresql"):
    # PostgreSQL specific arguments can be added here if needed
    # For example, to set a specific schema:
    # engine_args["connect_args"] = {"options": "-csearch_path=my_schema"}
    pass

engine = create_engine(DATABASE_URL, **engine_args)

# The call to register_audit_listeners() will be moved to a higher-level entry point
# (e.g., ai_trader/__init__.py or main application setup) to break circular dependency.

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Dependency injector for FastAPI or context manager for other uses.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Example of using the session for a standalone script:
# if __name__ == "__main__":
#     db_session = SessionLocal()
#     # You can now use db_session to interact with the database
#     try:
#         # Example: query users (assuming User model is imported)
#         # from ai_trader.models.user import User
#         # users = db_session.query(User).all()
#         # for user in users:
#         #     print(user)
#         print("Database session created successfully.")
#     except Exception as e:
#         print(f"An error occurred: {e}")
#     finally:
#         db_session.close()
#         print("Database session closed.")
