import argparse
import logging

from faker import Faker

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Adjust imports to match project structure
try:
    from ai_trader.db.session import SessionLocal
    from ai_trader.models import User

    # Placeholder for password hashing - replace with actual utility if available
    # from ai_trader.security import get_password_hash
except ImportError:
    logger.error(
        "Failed to import necessary modules. Ensure PYTHONPATH or script execution context is correct."
    )
    logger.info(
        "Attempting relative imports for common project structures (less ideal)."
    )
    import os
    import sys

    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from ai_trader.db.session import SessionLocal
    from ai_trader.models import User

    # from ai_trader.security import get_password_hash # Adjust if path is different


# If no password hashing function is available, we'll use a placeholder.
# Real applications should hash passwords securely.
def get_password_hash_placeholder(password: str) -> str:
    # In a real app, this would use bcrypt, passlib, etc.
    # For seeding, a simple placeholder is often acceptable.
    # logger.warning("Using placeholder password hashing. NOT FOR PRODUCTION.")
    return f"hashed_{password}_placeholder"


def seed_users(session, num_users: int = 10):
    """
    Seeds the database with mock users.
    """
    fake = Faker()
    users_created_count = 0

    logger.info(f"Starting to seed {num_users} users...")

    existing_usernames = {user.username for user in session.query(User.username).all()}
    existing_emails = {user.email for user in session.query(User.email).all()}

    for i in range(num_users):
        username = fake.user_name()
        while username in existing_usernames:  # Ensure username is unique
            username = fake.user_name() + str(i)

        email = fake.email()
        while email in existing_emails:  # Ensure email is unique
            email = f"{i}_{fake.email()}"

        # For seeding, we might use a common password or generate one.
        # The password needs to be hashed before storing.
        # Replace this with your actual password hashing utility.
        password_to_hash = "password123"
        hashed_password = get_password_hash_placeholder(password_to_hash)

        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            # created_at and updated_at usually have defaults in the model
        )
        session.add(user)
        existing_usernames.add(username)
        existing_emails.add(email)
        users_created_count += 1
        logger.debug(f"Prepared user: {username} ({email})")

    try:
        session.commit()
        logger.info(f"Successfully seeded {users_created_count} users.")
    except Exception as e:
        session.rollback()
        logger.error(f"Error seeding users: {e}", exc_info=True)
        logger.info("Rolled back any pending changes for user seeding.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed users into the database.")
    parser.add_argument(
        "--num_users", type=int, default=10, help="Number of mock users to create."
    )
    args = parser.parse_args()

    logger.info(f"Attempting to seed {args.num_users} users...")
    db_session = SessionLocal()
    try:
        seed_users(db_session, args.num_users)
    finally:
        db_session.close()
    logger.info("User seeding process finished.")
