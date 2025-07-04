from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os

# Default to SQLite if DATABASE_URL is not set
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ai_trader.db")

# For PostgreSQL, the DATABASE_URL would be something like:
# DATABASE_URL = "postgresql://user:password@host:port/database"
# e.g., "postgresql://postgres:mysecretpassword@localhost:5432/ai_trader_db"

# For MySQL, the DATABASE_URL would be something like:
# DATABASE_URL = "mysql+mysqlconnector://user:password@host:port/database"
# e.g., "mysql+mysqlconnector://root:mysecretpassword@localhost:3306/ai_trader_db"


# Create the SQLAlchemy engine
# `echo=True` will log all SQL statements executed by SQLAlchemy, useful for debugging.
# `pool_pre_ping=True` enables a feature that tests connections for liveness before handing them out from the pool.
engine_args = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    # connect_args is specific to SQLite to enforce foreign key constraints
    engine_args["connect_args"] = {"check_same_thread": False}
    # For SQLite, echo can be very verbose due to simple operations.
    # engine_args["echo"] = False # Or True for debugging
else:
    # For server-based databases, echo is generally more useful.
    engine_args["echo"] = True


engine = create_engine(DATABASE_URL, **engine_args)

# Create a configured "Session" class
# autocommit=False and autoflush=False are common settings for web applications
# to have more control over transaction boundaries.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    Dependency injector for database sessions.
    This function is a generator that yields a database session.
    It ensures the session is properly closed after use.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Optional: A simple function to test the connection
def test_connection():
    try:
        # Try to connect and execute a simple query
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            for row in result:
                print("Connection test successful:", row)
        return True
    except Exception as e:
        print(f"Connection test failed: {e}")
        return False

if __name__ == "__main__":
    print(f"Database URL: {DATABASE_URL}")
    print("Testing database connection...")
    # Need to import 'text' for the test_connection function
    from sqlalchemy import text
    if test_connection():
        print("Database session management appears to be configured correctly.")
    else:
        print("Please check your DATABASE_URL or database server.")

    # Example of using get_db (more relevant in an application context)
    # db_session_generator = get_db()
    # session = next(db_session_generator)
    # try:
    #     # Perform database operations with 'session'
    #     print("Session obtained successfully.")
    # finally:
    #     try:
    #         next(db_session_generator) # This will close the session
    #     except StopIteration:
    #         pass # Expected
    #     print("Session closed.")
