import asyncio
import asyncio
import os
import sys
from datetime import datetime, timedelta
from sqlalchemy.future import select # Not strictly needed for this update-only script
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession # Import AsyncSession

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_trader.db.session import get_async_engine, get_db_session_context
from ai_trader.models import Trade

DEFAULT_RETENTION_DAYS = 365

async def soft_delete_old_trades(db_session: AsyncSession, retention_days: int = DEFAULT_RETENTION_DAYS):
    """
    Soft-deletes trades older than the specified retention period.
    It sets the 'deleted_at' field to the current time for qualifying records.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

    print(f"Soft-deleting trades executed before: {cutoff_date.isoformat()} (older than {retention_days} days)...")

    stmt = (
        update(Trade)
        .where(Trade.executed_at < cutoff_date)
        .where(Trade.deleted_at == None)  # Only update those not already soft-deleted
        .values(deleted_at=datetime.utcnow())
    )

    result = await db_session.execute(stmt)
    await db_session.commit()

    print(f"Soft-delete process complete. {result.rowcount} trades were marked as deleted.")
    return result.rowcount

async def main():
    print("Starting archive_old_trades.py script...")

    retention_param = os.getenv("TRADE_RETENTION_DAYS")
    try:
        retention_days = int(retention_param) if retention_param else DEFAULT_RETENTION_DAYS
    except ValueError:
        print(f"Warning: Invalid TRADE_RETENTION_DAYS value '{retention_param}'. Using default: {DEFAULT_RETENTION_DAYS} days.")
        retention_days = DEFAULT_RETENTION_DAYS

    engine = get_async_engine()
    async with get_db_session_context() as db:
        await soft_delete_old_trades(db, retention_days)

    print("Archive old trades script finished.")
    print("\n--- CRON Job / Task Scheduler Setup ---")
    print("To automate this script, you can set up a CRON job or a task scheduler.")
    print("Example CRON job (runs daily at 2 AM):")
    print(f"0 2 * * * /usr/bin/python3 {os.path.abspath(__file__)} >> /var/log/ai_trader_archive.log 2>&1")
    print("\nReplace paths with your actual Python interpreter and script location.")
    print("Ensure the environment (like DATABASE_URL, TRADE_RETENTION_DAYS) is available to the cron job.")
    print("For Windows Task Scheduler, you would create a new task to run this script daily.")
    print("---------------------------------------\n")


if __name__ == "__main__":
    # Ensure .env is loaded if script uses os.getenv and is run directly
    from dotenv import load_dotenv
    dotenv_path = os.path.join(PROJECT_ROOT, '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
        print(f".env file loaded from {dotenv_path} for script context.")
    else:
        print(f"Warning: .env file not found at {dotenv_path}. Environment variables might be missing.")

    asyncio.run(main())
