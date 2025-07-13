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
    from ai_trader.models import Asset
except ImportError:
    logger.error("Failed to import necessary modules. Ensure PYTHONPATH or script execution context is correct.")
    logger.info("Attempting relative imports for common project structures (less ideal).")
    import os
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from ai_trader.db.session import SessionLocal
    from ai_trader.models import Asset

PREDEFINED_ASSETS = [
    {"symbol": "BTC", "name": "Bitcoin", "asset_type": "CRYPTO"},
    {"symbol": "ETH", "name": "Ethereum", "asset_type": "CRYPTO"},
    {"symbol": "ADA", "name": "Cardano", "asset_type": "CRYPTO"},
    {"symbol": "SOL", "name": "Solana", "asset_type": "CRYPTO"},
    {"symbol": "AAPL", "name": "Apple Inc.", "asset_type": "STOCK"},
    {"symbol": "MSFT", "name": "Microsoft Corp.", "asset_type": "STOCK"},
    {"symbol": "GOOGL", "name": "Alphabet Inc. (Class A)", "asset_type": "STOCK"},
    {"symbol": "AMZN", "name": "Amazon.com Inc.", "asset_type": "STOCK"},
    {"symbol": "TSLA", "name": "Tesla Inc.", "asset_type": "STOCK"},
    {"symbol": "EURUSD", "name": "Euro to US Dollar", "asset_type": "FOREX"},
    {"symbol": "GBPUSD", "name": "British Pound to US Dollar", "asset_type": "FOREX"},
]

def seed_assets(session, num_assets: int = 10):
    """
    Seeds the database with mock assets.
    Uses a predefined list first, then Faker for additional assets if num_assets is larger.
    """
    fake = Faker()
    assets_created_count = 0

    logger.info(f"Starting to seed {num_assets} assets...")

    existing_symbols = {asset.symbol for asset in session.query(Asset.symbol).all()}

    # Seed from predefined list first
    for asset_data in PREDEFINED_ASSETS:
        if assets_created_count >= num_assets:
            break
        if asset_data["symbol"] not in existing_symbols:
            asset = Asset(
                symbol=asset_data["symbol"],
                name=asset_data["name"],
                asset_type=asset_data["asset_type"]
                # created_at usually has a default in the model
            )
            session.add(asset)
            existing_symbols.add(asset_data["symbol"])
            assets_created_count += 1
            logger.debug(f"Prepared predefined asset: {asset_data['symbol']}")

    # Seed remaining with Faker if needed
    while assets_created_count < num_assets:
        # Generate a plausible, unique stock-like or crypto-like symbol
        symbol_prefix = random.choice(["FC", "TK", "ST", "CX", "FX"]) # FC=FakeCoin, TK=Ticker, ST=Stock
        symbol_suffix = "".join(fake.random_letters(length=random.randint(2,3))).upper()
        symbol = f"{symbol_prefix}{symbol_suffix}"

        # Ensure symbol uniqueness
        loop_guard = 0 # safety break for very high num_assets / unlikely collisions
        while symbol in existing_symbols and loop_guard < 100:
            symbol_suffix = "".join(fake.random_letters(length=random.randint(2,4))).upper()
            symbol = f"{symbol_prefix}{symbol_suffix}"
            loop_guard +=1
        if symbol in existing_symbols: # If still colliding after attempts, skip or error
            logger.warning(f"Could not generate a unique symbol after {loop_guard} attempts for a Faker asset. Skipping one asset.")
            num_assets -=1 # reduce target as we skip one
            if num_assets <= assets_created_count: break
            continue


        asset_type = random.choice(["STOCK", "CRYPTO", "FOREX", "COMMODITY", "ETF"])
        name = fake.company() if asset_type == "STOCK" else f"{fake.word().capitalize()} Coin" if asset_type == "CRYPTO" else f"{fake.currency_code()}/{fake.currency_code()}" if asset_type == "FOREX" else f"{fake.word().capitalize()} {asset_type.lower().capitalize()}"

        asset = Asset(
            symbol=symbol,
            name=name,
            asset_type=asset_type
        )
        session.add(asset)
        existing_symbols.add(symbol)
        assets_created_count += 1
        logger.debug(f"Prepared Faker asset: {symbol} ({name})")

    try:
        session.commit()
        logger.info(f"Successfully seeded {assets_created_count} assets.")
    except Exception as e:
        session.rollback()
        logger.error(f"Error seeding assets: {e}", exc_info=True)
        logger.info("Rolled back any pending changes for asset seeding.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed assets into the database.")
    parser.add_argument(
        "--num_assets",
        type=int,
        default=10, # Default to a number that covers some predefined and some Faker
        help="Number of mock assets to create."
    )
    args = parser.parse_args()

    logger.info(f"Attempting to seed {args.num_assets} assets...")
    db_session = SessionLocal()
    try:
        seed_assets(db_session, args.num_assets)
    finally:
        db_session.close()
    logger.info("Asset seeding process finished.")
