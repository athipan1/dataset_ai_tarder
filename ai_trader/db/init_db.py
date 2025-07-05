from sqlalchemy.orm import Session

from ai_trader.db.base import Base
from ai_trader.db.session import engine, SessionLocal
# Import all models here so that Base knows about them.
# These are needed for Base.metadata.create_all() to find the tables.
from ai_trader.models import User, Trade, Strategy, TradeType  # noqa: F401


def init_db(db_engine=engine):
    """
    Initializes the database by creating all tables defined in the models.
    """
    # In a real application, you might want to use Alembic for migrations
    # instead of Base.metadata.create_all(bind=db_engine) directly,
    # especially for production environments.
    print("Initializing database...")
    print(f"Using engine: {db_engine.url}")

    # The following line will create tables.
    # Ensure all models are imported above so Base.metadata contains them.
    Base.metadata.create_all(bind=db_engine)
    print("Database tables created (if they didn't exist).")


def get_db_session() -> Session:
    """Helper to get a new database session."""
    return SessionLocal()

# Example of how to add some initial data (optional)
# def create_initial_data(db: Session):
#     print("Creating initial data...")
#     # Example: Create a test user if none exists
#     user = db.query(User).filter(User.email == "test@example.com").first()
#     if not user:
#         print("Creating test user...")
#         # In a real app, hash the password properly
#         test_user = User(username="testuser", email="test@example.com", hashed_password="fakepassword")
#         db.add(test_user)
#         db.commit()
#         db.refresh(test_user)
#         print(f"User {test_user.username} created.")
#     else:
#         print(f"User {user.username} already exists.")
#     print("Initial data setup complete.")


if __name__ == "__main__":
    print("Running init_db directly.")
    init_db()
    # Example of adding initial data
    # db_session = get_db_session()
    # try:
    #     create_initial_data(db_session)
    # finally:
    #     db_session.close()
    print("Database initialization process finished.")
