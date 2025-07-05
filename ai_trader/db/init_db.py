from sqlalchemy.orm import Session

# Base is now imported from ai_trader.models where all models are defined
from ai_trader.models import Base
from ai_trader.db.session import engine, SessionLocal
# Importing specific models is only needed if directly used in this file (e.g. for initial data)
# For Base.metadata.create_all() to work, Base just needs to be the one all models are registered with.
# from ai_trader.models import User, Trade, Strategy, TradeType # noqa: F401 - Keep if create_initial_data is used


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
    # Base.metadata.create_all(bind=db_engine) # <<< IMPORTANT: Commented out by default
    print("Database tables created (if they didn't exist). --- Call to create_all() is COMMENTED OUT.")
    print("--- To use this function, uncomment the Base.metadata.create_all() line.")
    print("--- WARNING: This should NOT be used on a database managed by Alembic.")


def get_db_session() -> Session:
    """Helper to get a new database session."""
    return SessionLocal()

# Example of how to add some initial data (optional)
# from ai_trader.models import User # Ensure User is imported if using this example
# def create_initial_data(db: Session):
#     print("Creating initial data...")
#     # Example: Create a test user if none exists
#     user = db.query(User).filter(User.email == "test@example.com").first()
#     if not user:
#         print("Creating test user...")
#         # In a real app, hash the password properly
#         test_user = User(username="testuser", email="test@example.com", hashed_password="fakepassword") # Ensure User model is imported
#         db.add(test_user)
#         db.commit()
#         db.refresh(test_user)
#         print(f"User {test_user.username} created.")
#     else:
#         print(f"User {user.username} already exists.")
#     print("Initial data setup complete.")


if __name__ == "__main__":
    # print("Running init_db directly.")
    # init_db() # <<< IMPORTANT: Commented out by default
    # Example of adding initial data
    # db_session = get_db_session()
    # try:
    #     create_initial_data(db_session)
    # finally:
    #     db_session.close()
    # print("Database initialization process finished.")
    print("The if __name__ == '__main__' block in init_db.py is commented out by default.")
    print("This is to prevent accidental direct execution of Base.metadata.create_all().")
    print("For database schema management, please use Alembic migrations (e.g., scripts/upgrade_db.py).")
