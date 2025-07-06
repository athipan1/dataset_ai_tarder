# scripts/archive_old_trades.py
import argparse
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, text, event, inspect
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession # Renamed to avoid conflict
from sqlalchemy.exc import OperationalError, IntegrityError
import time

from ai_trader.core.config import settings
from ai_trader.db.base import Base
from ai_trader.models.trade import Trade, TradeType # Assuming TradeType is in trade.py

logging.basicConfig(level=settings.LOG_LEVEL.upper(), format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

engine = create_engine(settings.DATABASE_URL, pool_recycle=3600, echo=False) # Set echo=True for debugging SQL
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

ARCHIVED_TRADES_TABLE_NAME = "archived_trades"

def check_archived_trades_table_exists(session: SQLAlchemySession) -> bool:
    """Checks if the archived_trades table exists using SQLAlchemy inspector."""
    inspector = inspect(session.bind)
    if ARCHIVED_TRADES_TABLE_NAME in inspector.get_table_names():
        logger.info(f"Table '{ARCHIVED_TRADES_TABLE_NAME}' exists.")
        return True
    else:
        logger.warning(f"Table '{ARCHIVED_TRADES_TABLE_NAME}' does not exist. Archiving to DB table will be skipped.")
        logger.warning("Please create this table using an Alembic migration.")
        return False

def archive_trades_to_db_table(session: SQLAlchemySession, trades_to_archive: list[Trade]) -> int:
    """
    Archives a list of Trade objects to the ARCHIVED_TRADES_TABLE_NAME table using raw SQL.
    Returns the number of successfully inserted rows.
    """
    if not trades_to_archive:
        return 0

    archived_count = 0
    insert_stmt = text(f"""
        INSERT INTO {ARCHIVED_TRADES_TABLE_NAME} (id, user_id, symbol, quantity, price, "timestamp", trade_type, archived_at)
        VALUES (:id, :user_id, :symbol, :quantity, :price, :timestamp, :trade_type, :archived_at)
        ON CONFLICT (id) DO NOTHING; -- Assumes 'id' is primary key and you want to skip if already archived
    """)

    for trade in trades_to_archive:
        try:
            trade_type_value = trade.trade_type.value if isinstance(trade.trade_type, TradeType) else str(trade.trade_type)

            session.execute(insert_stmt, {
                "id": trade.id,
                "user_id": trade.user_id,
                "symbol": trade.symbol,
                "quantity": trade.quantity,
                "price": trade.price,
                "timestamp": trade.timestamp,
                "trade_type": trade_type_value,
                "archived_at": datetime.now(timezone.utc)
            })
            archived_count += 1
        except IntegrityError as ie:
            logger.warning(f"Integrity error archiving trade ID {trade.id} (possibly already archived): {ie}")
        except Exception as e:
            logger.error(f"Error inserting trade ID {trade.id} into {ARCHIVED_TRADES_TABLE_NAME}: {e}")
            raise

    if archived_count > 0:
        logger.info(f"Successfully prepared {archived_count} trades for archiving to table '{ARCHIVED_TRADES_TABLE_NAME}'.")
    return archived_count


def archive_and_delete_old_trades(
    session: SQLAlchemySession,
    older_than_days: int,
    batch_size: int = 1000,
    archive_to_db: bool = True,
    max_retries: int = 3,
    retry_delay_seconds: int = 5,
    dry_run: bool = False
):
    """
    Archives and then deletes old trades in batches.
    Handles potential locking issues with retries.
    """
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    logger.info(
        f"Processing trades older than {cutoff_date} ({older_than_days} days). "
        f"Batch: {batch_size}, ArchiveToDB: {archive_to_db}, DryRun: {dry_run}"
    )

    if dry_run:
        logger.warning("DRY RUN mode enabled. No data will be archived or deleted.")

    can_archive_to_db = False
    if archive_to_db:
        can_archive_to_db = check_archived_trades_table_exists(session)
        if not can_archive_to_db:
            logger.warning(f"Cannot archive to DB table '{ARCHIVED_TRADES_TABLE_NAME}' as it does not exist or is not accessible.")

    total_archived_count = 0
    total_deleted_count = 0
    running = True

    while running:
        trades_in_batch = []
        attempt = 0

        while attempt < max_retries:
            try:
                # Query trades including those already soft-deleted, as the script's purpose is to archive them
                # based on age, and then they are soft-deleted again (which is idempotent).
                trade_query = Trade.query_with_deleted(session)\
                    .filter(Trade.timestamp < cutoff_date)\
                    .order_by(Trade.id)

                if session.bind.dialect.name == 'postgresql' and not dry_run:
                    trade_query = trade_query.with_for_update(skip_locked=True)

                trades_in_batch = trade_query.limit(batch_size).all()

                if not trades_in_batch:
                    logger.info("No more old trades found to process.")
                    running = False
                    break

                logger.info(f"Fetched {len(trades_in_batch)} trades for current batch (Attempt {attempt + 1}).")

                archived_in_batch = 0
                if archive_to_db and can_archive_to_db and not dry_run:
                    archived_in_batch = archive_trades_to_db_table(session, trades_in_batch)
                elif archive_to_db and can_archive_to_db and dry_run:
                    logger.info(f"[DRY RUN] Would attempt to archive {len(trades_in_batch)} trades to DB table.")
                    archived_in_batch = len(trades_in_batch)

                deleted_in_batch = 0
                if not dry_run:
                    if trades_in_batch:
                        for trade_to_delete in trades_in_batch:
                            # Use soft_delete instead of hard delete
                            trade_to_delete.soft_delete(session)
                        deleted_in_batch = len(trades_in_batch)
                else:
                    deleted_in_batch = len(trades_in_batch)
                    logger.info(f"[DRY RUN] Would delete {deleted_in_batch} trades from the original table.")

                if not dry_run:
                    session.commit()

                total_archived_count += archived_in_batch
                total_deleted_count += deleted_in_batch

                logger.info(
                    f"Batch processed: Archived={archived_in_batch}, Deleted={deleted_in_batch}. "
                    f"Total cumulative: Archived={total_archived_count}, Deleted={total_deleted_count}."
                )
                break

            except OperationalError as oe:
                logger.warning(f"OperationalError (e.g., lock timeout) on attempt {attempt + 1}/{max_retries}: {oe}")
                if not dry_run: session.rollback()
                attempt += 1
                if attempt < max_retries:
                    logger.info(f"Retrying batch in {retry_delay_seconds}s...")
                    time.sleep(retry_delay_seconds)
                else:
                    logger.error("Max retries reached for the current batch due to OperationalError. Skipping this batch.")
                    running = False
                    break
            except Exception as e:
                logger.error(f"Unexpected error processing batch: {e}", exc_info=True)
                if not dry_run: session.rollback()
                running = False
                break

        if not trades_in_batch and attempt < max_retries :
            running = False


    logger.info(f"Trade archiving and deletion finished. Total Archived: {total_archived_count}, Total Deleted: {total_deleted_count}.")


def main():
    parser = argparse.ArgumentParser(description="Archive and optionally delete old trade data from the 'trades' table.")
    parser.add_argument(
        "--days", type=int, required=True,
        help="Process trades older than this many days."
    )
    parser.add_argument(
        "--batch-size", type=int, default=500,
        help="Number of trades to process in each transaction batch."
    )
    parser.add_argument(
        "--no-db-archive", action="store_true",
        help=f"Do not archive trades to the '{ARCHIVED_TRADES_TABLE_NAME}' table. If not set, archiving is attempted."
    )
    parser.add_argument(
        "--max-retries", type=int, default=3,
        help="Maximum retries for a batch if an OperationalError (like a lock) occurs."
    )
    parser.add_argument(
        "--retry-delay", type=int, default=10, dest="retry_delay_seconds",
        help="Delay in seconds between retries for a failing batch."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Simulate the process: show what would be done without modifying data."
    )

    args = parser.parse_args()

    db_session = SessionLocal()
    try:
        archive_and_delete_old_trades(
            session=db_session,
            older_than_days=args.days,
            batch_size=args.batch_size,
            archive_to_db=not args.no_db_archive,
            max_retries=args.max_retries,
            retry_delay_seconds=args.retry_delay_seconds,
            dry_run=args.dry_run
        )
    finally:
        db_session.close()

    logger.info("Trade archiving script finished.")

if __name__ == "__main__":
    main()
