import asyncio
import os
import sys

# from datetime import datetime # Removed F401

from sqlalchemy.ext.asyncio import AsyncSession  # Third-party
from sqlalchemy.future import select  # Third-party

# from sqlalchemy.orm import sessionmaker # Removed F401
# from sqlalchemy import create_engine # Removed F401


# Add project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Local application imports
from ai_trader.db.session import (  # noqa: E402
    get_db_session_context,  # Removed get_async_engine F401
)  # Assuming this provides async session
from ai_trader.models import (  # noqa: E402
    User,
    Asset,
    Strategy,
    AssetType,
    # Trade, TradeType, Order, OrderStatus, OrderType, OrderSide # For more advanced seeding
)

# from ai_trader.db.base import ( # Removed F401
#     Base,
# )  # To create tables if run standalone on a fresh DB (for testing seed script)

# Basic password hashing - in a real app, use passlib or similar
# For seeding, we might store a known hash or a plain password to be hashed by app logic later
# Here, we'll just put a placeholder for a hashed password.
# A common practice for dev is to have a known weak password like 'password'
# HASHED_DEMO_PASSWORD = "some_pre_hashed_password_for_demo_user"
# Or, if your User model or auth logic handles hashing on create:
DEMO_PASSWORD = "password123"  # This would need to be hashed by user creation logic


async def seed_data(db_session: AsyncSession):
    """
    Populates the database with initial seed data.
    """
    print("Seeding data...")

    # Check if user already exists
    user_exists_stmt = select(User).where(User.username == "demo_user")
    result = await db_session.execute(user_exists_stmt)
    existing_user = result.scalars().first()

    if existing_user:
        print("Demo user already exists. Skipping user creation.")
        demo_user = existing_user
    else:
        print("Creating demo user...")
        # IMPORTANT: In a real application, password should be hashed.
        # This seed script assumes that the application logic (e.g., a user service or model hook)
        # would normally handle hashing. If not, you'd need to hash it here.
        # For simplicity, if User model doesn't auto-hash, this will store plain text if not careful.
        # Assuming User.hashed_password expects a hash:
        # For this script, we'll create a user with a placeholder or a simple hash.
        # If your app has a user creation service that hashes, use that.
        # For now, let's assume we need to provide a 'hashed_password'.
        # A real app would use a proper hashing library like passlib:
        # from passlib.context import CryptContext
        # pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        # hashed_password = pwd_context.hash(DEMO_PASSWORD)

        # Placeholder for hashed password. Replace with actual hashing if model expects it.
        # This is a simplified example.
        demo_user = User(
            username="demo_user",
            email="demo@example.com",
            hashed_password="fake_hashed_password_for_demo",  # Replace with actual hash if needed
        )
        db_session.add(demo_user)
        await db_session.flush()  # To get demo_user.id for strategies
        msg_part1 = "Demo user created with ID: "
        user_creation_message = f"{msg_part1}{demo_user.id}"
        print(user_creation_message)

    # Create Assets
    assets_to_create = [
        {
            "symbol": "BTCUSD",
            "name": "Bitcoin USD",
            "asset_type": AssetType.CRYPTO,
            "exchange": "Various",
        },
        {
            "symbol": "ETHUSD",
            "name": "Ethereum USD",
            "asset_type": AssetType.CRYPTO,
            "exchange": "Various",
        },
        {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "asset_type": AssetType.STOCK,
            "exchange": "NASDAQ",
        },
        {
            "symbol": "EURUSD",
            "name": "Euro US Dollar",
            "asset_type": AssetType.FOREX,
            "exchange": "FXCM",
        },
    ]

    for asset_data in assets_to_create:
        asset_exists_stmt = select(Asset).where(Asset.symbol == asset_data["symbol"])
        result = await db_session.execute(asset_exists_stmt)
        existing_asset = result.scalars().first()
        if existing_asset:
            print(f"Asset {asset_data['symbol']} already exists.")
        else:
            asset = Asset(**asset_data)
            db_session.add(asset)
            print(f"Asset {asset_data['symbol']} created.")

    await db_session.flush()  # Ensure assets are created before strategies that might reference them (though not directly here)

    # Create a Strategy for the demo user
    strategy_exists_stmt = select(Strategy).where(
        Strategy.name == "Demo RSI Strategy", Strategy.user_id == demo_user.id  # noqa: E501 (if this is the reported line)
    )
    result = await db_session.execute(strategy_exists_stmt)
    existing_strategy = result.scalars().first()

    if existing_strategy:
        print("Demo RSI Strategy already exists for demo_user.")
    else:
        if demo_user.id is None:  # Should not happen if flushed
            await db_session.refresh(demo_user, ["id"])

        demo_strategy = Strategy(
            user_id=demo_user.id,
            name="Demo RSI Strategy",
            description="A simple strategy based on Relative Strength Index.",
            model_version="1.0",
            parameters={"rsi_period": 14, "buy_threshold": 30, "sell_threshold": 70},
        )
        db_session.add(demo_strategy)
        print("Demo RSI Strategy created for demo_user.")

    try:
        await db_session.commit()
        print("Data seeding committed successfully.")
    except Exception as e:
        await db_session.rollback()
        print(f"Error during data seeding commit: {e}")
        import traceback

        traceback.print_exc()


async def main():
    # This main function is primarily for running the seed script directly.
    # It can also be called from other parts of your application if needed.

    # In a real app, get DATABASE_URL from environment variables (e.g., .env file)
    # For this script, we assume alembic.ini or environment has the DB URL for get_async_engine
    print("Initializing database for seeding...")

    # Note: get_async_engine might need the actual URL if not configured globally for it
    # For simplicity, if your get_async_engine doesn't read from env/config, you might need:
    # from ai_trader.db.session import DATABASE_URL # if you have this constant
    # engine = get_async_engine(DATABASE_URL)
    # engine = get_async_engine()  # F841 - Removed. Assuming this function can get the URL

    # Optional: Create tables if they don't exist (useful for standalone script run on empty DB)
    # This is not strictly necessary if migrations are always run first.
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)
    # print("Tables ensured (created if not exist).")

    # Use a context manager for the session
    async with get_db_session_context() as db:  # Assuming get_db_session_context is an async context manager
        await seed_data(db)


if __name__ == "__main__":
    print("Running seed_data.py script...")
    # For Windows, event loop policy might be needed if using asyncio.run
    # if sys.platform == "win32":
    # asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
    print("Seed script finished.")
