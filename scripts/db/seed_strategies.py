import argparse
import logging
import random

from faker import Faker

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Adjust imports to match project structure
try:
    from ai_trader.db.session import SessionLocal
    from ai_trader.models import Strategy, User
except ImportError:
    logger.error("Failed to import necessary modules. Ensure PYTHONPATH or script execution context is correct.")
    logger.info("Attempting relative imports for common project structures (less ideal).")
    import os
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from ai_trader.db.session import SessionLocal
    from ai_trader.models import Strategy, User

def seed_strategies(session, strategies_per_user: int = 2):
    """
    Seeds the database with mock strategies, associated with existing users.
    """
    fake = Faker()
    strategies_created_count = 0

    logger.info(f"Starting to seed strategies ({strategies_per_user} per user)...")

    users = session.query(User).all()
    if not users:
        logger.warning("No users found in the database. Please seed users first (e.g., run seed_users.py). Strategies will not be created.")
        return

    for user in users:
        user_strategies_created = 0
        # Check existing strategy names for this user to avoid duplicates if script is run multiple times
        existing_strategy_names_for_user = {
            s.name for s in session.query(Strategy.name).filter(Strategy.user_id == user.id).all()
        }

        for i in range(strategies_per_user):
            strategy_name_base = f"{fake.word().capitalize()} {fake.word().capitalize()} Strategy"
            strategy_name = strategy_name_base
            # Ensure strategy name is unique for the user
            name_suffix_counter = 0
            while strategy_name in existing_strategy_names_for_user:
                name_suffix_counter += 1
                strategy_name = f"{strategy_name_base} v{name_suffix_counter + 1}"

            description = fake.sentence(nb_words=10)
            model_version = f"v{random.randint(1, 3)}.{random.randint(0, 9)}"
            parameters = {
                "param1": fake.random_int(min=1, max=100),
                "param2": round(random.uniform(0.1, 5.0), 2),
                "mode": random.choice(["aggressive", "conservative", "balanced"])
            }
            # api_key might be nullable or not set for mock strategies

            strategy = Strategy(
                name=strategy_name,
                description=description,
                model_version=model_version,
                parameters=parameters,
                user_id=user.id
                # created_at and updated_at usually have defaults
            )
            session.add(strategy)
            existing_strategy_names_for_user.add(strategy_name) # Add to set for current user
            strategies_created_count += 1
            user_strategies_created +=1
            logger.debug(f"Prepared strategy '{strategy_name}' for user '{user.username}'")
        logger.info(f"Prepared {user_strategies_created} strategies for user ID {user.id} ({user.username}).")


    try:
        session.commit()
        logger.info(f"Successfully seeded a total of {strategies_created_count} strategies across all users.")
    except Exception as e:
        session.rollback()
        logger.error(f"Error seeding strategies: {e}", exc_info=True)
        logger.info("Rolled back any pending changes for strategy seeding.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed strategies into the database, associated with existing users.")
    parser.add_argument(
        "--strategies_per_user",
        type=int,
        default=2,
        help="Number of mock strategies to create per user."
    )
    args = parser.parse_args()

    logger.info(f"Attempting to seed {args.strategies_per_user} strategies per user...")
    db_session = SessionLocal()
    try:
        seed_strategies(db_session, args.strategies_per_user)
    finally:
        db_session.close()
    logger.info("Strategy seeding process finished.")
