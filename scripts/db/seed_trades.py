import argparse
import logging
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal, getcontext

from faker import Faker

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set precision for Decimal
getcontext().prec = 28 # Standard precision

# Adjust imports to match project structure
try:
    from ai_trader.db.session import SessionLocal
    from ai_trader.models import (Asset, Order, OrderSide,  # Enums
                                  OrderStatus, OrderType, Strategy, Trade,
                                  TradeType, User)
except ImportError:
    logger.error("Failed to import necessary modules. Ensure PYTHONPATH or script execution context is correct.")
    logger.info("Attempting relative imports for common project structures (less ideal).")
    import os
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from ai_trader.db.session import SessionLocal
    from ai_trader.models import (Asset, Order, OrderSide, OrderStatus,
                                  OrderType, Strategy, Trade, TradeType, User)


def get_random_decimal(min_val, max_val, d_places=2):
    """Generates a random Decimal between min_val and max_val with d_places decimal places."""
    return Decimal(random.uniform(min_val, max_val)).quantize(Decimal('1e-{}'.format(d_places)))


def seed_trades(session, num_trades: int = 50):
    """
    Seeds the database with mock trades.
    Each trade is associated with an order, user, asset, and optionally a strategy.
    """
    fake = Faker()
    trades_created_count = 0
    orders_created_count = 0

    logger.info(f"Starting to seed {num_trades} trades (each with an associated order)...")

    users = session.query(User).all()
    assets = session.query(Asset).all()
    strategies = session.query(Strategy).all() # Optional for a trade

    if not users:
        logger.error("No users found. Please run seed_users.py first. Cannot create trades.")
        return
    if not assets:
        logger.error("No assets found. Please run seed_assets.py first. Cannot create trades.")
        return
    # Strategies are optional, so we can proceed without them, but log a warning.
    if not strategies:
        logger.warning("No strategies found. Trades will be created without strategy associations.")

    for _ in range(num_trades):
        selected_user = random.choice(users)
        selected_asset = random.choice(assets)
        selected_strategy = random.choice(strategies) if strategies else None

        # 1. Create an Order first
        order_side = random.choice(list(OrderSide))
        order_quantity = get_random_decimal(1, 1000, d_places=min(8, random.randint(0,4))) # Asset quantity

        # Simulate price based on asset type (very rough simulation)
        if selected_asset.asset_type == "CRYPTO":
            order_price = get_random_decimal(10, 70000, d_places=min(8, random.randint(2,6)))
        elif selected_asset.asset_type == "STOCK":
            order_price = get_random_decimal(10, 2000, d_places=2)
        elif selected_asset.asset_type == "FOREX":
            order_price = get_random_decimal(0.5, 2.0, d_places=4)
        else: # COMMODITY, ETF etc.
            order_price = get_random_decimal(1, 1000, d_places=2)

        order_created_at = fake.date_time_between(start_date="-1y", end_date="now", tzinfo=timezone.utc)

        new_order = Order(
            user_id=selected_user.id,
            asset_id=selected_asset.id,
            strategy_id=selected_strategy.id if selected_strategy else None,
            signal_id=None, # Assuming no direct signal seeding for now
            order_type=random.choice(list(OrderType)), # e.g., MARKET, LIMIT
            order_side=order_side,
            status=OrderStatus.FILLED, # For a trade to exist, order must be filled
            quantity=order_quantity,
            price=order_price if random.choice([True, False]) else None, # Price may be null for MARKET orders until filled
            filled_quantity=order_quantity, # Assuming fully filled for simplicity
            average_fill_price=order_price, # Assuming filled at specified/market price
            commission=get_random_decimal(0.01, 5, d_places=2),
            exchange_order_id=fake.uuid4(),
            is_simulated=random.choice([0,1]),
            created_at=order_created_at,
            updated_at=order_created_at + timedelta(seconds=random.randint(1, 300)) # Simulate fill time
        )
        session.add(new_order)
        orders_created_count += 1

        # Must commit or flush to get order.id if DB is not configured for return_defaults
        # For simplicity here, let's commit per trade/order pair. In bulk, would do larger batches.
        try:
            session.flush() # Flush to get the new_order.id
        except Exception as e:
            session.rollback()
            logger.error(f"Error flushing session for order: {e}", exc_info=True)
            logger.warning("Skipping this trade due to order creation error.")
            continue


        # 2. Create a Trade linked to this Order
        trade_timestamp = new_order.updated_at # Trade occurs when order is filled

        # Trade quantity and price should match the filled order details
        trade_quantity = new_order.filled_quantity
        trade_price = new_order.average_fill_price

        trade_type = TradeType.BUY if new_order.order_side == OrderSide.BUY else TradeType.SELL

        new_trade = Trade(
            user_id=selected_user.id, # user_id is also on Trade model
            order_id=new_order.id,
            symbol=selected_asset.symbol, # Denormalized for querying, or could be joined
            quantity=trade_quantity,
            price=trade_price,
            timestamp=trade_timestamp,
            trade_type=trade_type,
            commission=new_order.commission, # Can be same or split if needed
            commission_asset=selected_asset.symbol if random.random() < 0.1 else "USD" # Example
            # is_deleted/deleted_at from SoftDeleteMixin (default to False/None)
        )
        session.add(new_trade)
        trades_created_count += 1
        logger.debug(f"Prepared Order ID {new_order.id} and Trade ID {new_trade.id} for User {selected_user.username}, Asset {selected_asset.symbol}")

    try:
        session.commit()
        logger.info(f"Successfully seeded {orders_created_count} orders and {trades_created_count} trades.")
    except Exception as e:
        session.rollback()
        logger.error(f"Error committing trades and orders: {e}", exc_info=True)
        logger.info("Rolled back any pending changes for trade/order seeding.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed trades (and their associated orders) into the database.")
    parser.add_argument(
        "--num_trades",
        type=int,
        default=50,
        help="Number of mock trades to create."
    )
    args = parser.parse_args()

    logger.info(f"Attempting to seed {args.num_trades} trades...")
    db_session = SessionLocal()
    try:
        seed_trades(db_session, args.num_trades)
    finally:
        db_session.close()
    logger.info("Trade seeding process finished.")
