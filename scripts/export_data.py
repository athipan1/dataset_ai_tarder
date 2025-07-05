import asyncio
import csv
import json
import os
import sys
from datetime import date, datetime
from decimal import Decimal
import enum  # Import enum module

from sqlalchemy.future import select  # Third-party import

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Local application imports
from ai_trader.db.session import get_db_session_context  # noqa: E402; removed get_async_engine F401
from ai_trader.models import (  # noqa: E402
    User,
    Asset,
    Strategy,
    Trade,
    Order,
    DailyProfit,
    MonthlySummary,
)

OUTPUT_DIR = os.path.join(PROJECT_ROOT, "exports")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def alchemy_encoder(obj):
    """JSON encoder for SQLAlchemy objects and other types."""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)  # Or str(obj) for exact precision string
    if isinstance(obj, enum.Enum):  # Handle Enums
        return obj.value

    # For SQLAlchemy models, only include column properties to avoid lazy loading issues
    # This relies on Base being imported in the main execution scope of this script for the isinstance check to work
    # or more generically checking for __table__ attribute.
    if (
        hasattr(obj, "__table__") and hasattr(obj, "__class__") and hasattr(obj.__class__, "metadata")
    ):  # More specific check for SA model

        data = {}
        for c in obj.__table__.columns:
            value = getattr(obj, c.key)
            if isinstance(value, enum.Enum):
                data[c.key] = value.value
            else:
                data[c.key] = value
        return data

    # If you still want to try __dict__ for other objects, do it cautiously:
    # if hasattr(obj, '__dict__'):
    #     return {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}

    raise TypeError(f"Type {type(obj)} not serializable for JSON")


async def export_table_to_csv(db_session, model_cls, filename_prefix):
    """Exports all data from a given SQLAlchemy model to a CSV file."""
    filepath = os.path.join(OUTPUT_DIR, f"{filename_prefix}_{date.today().isoformat()}.csv")
    print(f"Exporting {model_cls.__tablename__} to {filepath}...")

    stmt = select(model_cls)
    result = await db_session.execute(stmt)
    records = result.scalars().all()

    if not records:
        print(f"No data found for {model_cls.__tablename__}.")
        return

    # Get headers from the first record's columns (requires model introspection or fixed list)
    # A more robust way is to use model_cls.__table__.columns.keys()
    headers = model_cls.__table__.columns.keys()

    with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        for record in records:
            row_data = {header: getattr(record, header) for header in headers}
            writer.writerow(row_data)
    print(f"Successfully exported {len(records)} records to {filepath}")


async def export_table_to_json(db_session, model_cls, filename_prefix):
    """Exports all data from a given SQLAlchemy model to a JSON file."""
    filepath = os.path.join(OUTPUT_DIR, f"{filename_prefix}_{date.today().isoformat()}.json")
    print(f"Exporting {model_cls.__tablename__} to {filepath}...")

    stmt = select(model_cls)
    # Example of eager loading if relationships were needed (adjust per model)
    # if model_cls == User:
    #     stmt = stmt.options(selectinload(User.strategies))

    result = await db_session.execute(stmt)
    records = result.scalars().all()

    if not records:
        print(f"No data found for {model_cls.__tablename__}.")
        return

    data_to_export = [record for record in records]  # Convert to list for JSON dump

    with open(filepath, "w", encoding="utf-8") as jsonfile:
        json.dump(data_to_export, jsonfile, indent=4, default=alchemy_encoder)

    print(f"Successfully exported {len(records)} records to {filepath}")


async def main():
    # engine = get_async_engine() # F841 - Removed
    async with get_db_session_context() as db:
        # Export Users
        await export_table_to_csv(db, User, "users_export")
        await export_table_to_json(db, User, "users_export")

        # Export Assets
        await export_table_to_csv(db, Asset, "assets_export")
        await export_table_to_json(db, Asset, "assets_export")

        # Export Strategies
        await export_table_to_csv(db, Strategy, "strategies_export")
        await export_table_to_json(db, Strategy, "strategies_export")

        # Export Trades
        await export_table_to_csv(db, Trade, "trades_export")
        await export_table_to_json(db, Trade, "trades_export")

        # Export Orders
        await export_table_to_csv(db, Order, "orders_export")
        await export_table_to_json(db, Order, "orders_export")

        # Export Daily Profits
        await export_table_to_csv(db, DailyProfit, "daily_profits_export")
        await export_table_to_json(db, DailyProfit, "daily_profits_export")

        # Export Monthly Summaries
        await export_table_to_csv(db, MonthlySummary, "monthly_summaries_export")
        await export_table_to_json(db, MonthlySummary, "monthly_summaries_export")


if __name__ == "__main__":
    # Need to import Base for the alchemy_encoder if it's used there.
    # This is a bit of a circular dependency if not careful.
    # A better encoder would not rely on Base directly.
    # For now, let's ensure Base is available in the global scope for the encoder.
    # from ai_trader.db.base import Base # Removed F401 as encoder was changed

    print("Running export_data.py script...")
    asyncio.run(main())
    print(f"Export script finished. Files are in {OUTPUT_DIR}")
