import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL is None:
    raise EnvironmentError(
        "DATABASE_URL not set in environment variables. "
        "Please create a .env file with this variable."
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

engine = create_engine(DATABASE_URL, **engine_args) # Synchronous engine

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) # Synchronous sessionmaker


# --- Asynchronous Setup ---
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker # noqa E402
from contextlib import asynccontextmanager # noqa E402

# Construct the async DATABASE_URL. For SQLite, it's often prefixed with 'sqlite+aiosqlite:///'
# For PostgreSQL, 'postgresql+asyncpg://'
ASYNC_DATABASE_URL = None
if DATABASE_URL.startswith("sqlite"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
elif DATABASE_URL.startswith("postgresql"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    # Potentially raise an error or log a warning if the DB type is not supported for async
    print(f"Warning: Async database URL could not be determined for: {DATABASE_URL}")
    # Fallback or error, for now, let's make it None so get_async_engine will fail clearly
    # Or, could try to make it same as DATABASE_URL if some drivers support it directly (unlikely for async)

if ASYNC_DATABASE_URL:
    async_engine_args = {}
    if ASYNC_DATABASE_URL.startswith("sqlite+aiosqlite"):
        # For aiosqlite, connect_args are typically not needed unless specific pragmas are set.
        # check_same_thread is not an issue with aiosqlite's typical async usage.
        pass

    async_engine = create_async_engine(ASYNC_DATABASE_URL, **async_engine_args)
    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False, # Good default for async sessions
        autocommit=False,
        autoflush=False,
    )
else:
    async_engine = None
    AsyncSessionLocal = None


def get_async_engine():
    """Returns the globally configured async engine."""
    if not async_engine:
        raise RuntimeError(f"Async engine not initialized. ASYNC_DATABASE_URL: {ASYNC_DATABASE_URL}")
    return async_engine

@asynccontextmanager
async def get_db_session_context() -> AsyncSession:
    """Provides an async database session via an async context manager."""
    if not AsyncSessionLocal:
        raise RuntimeError("AsyncSessionLocal not initialized. Check ASYNC_DATABASE_URL configuration.")

    session: AsyncSession = AsyncSessionLocal()
    try:
        yield session
        await session.commit() # Default commit on successful exit from context
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


# --- Synchronous get_db ---
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
