# scripts/cleanup_database.py
import argparse
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import csv
from pathlib import Path

# ควรจะใช้ settings จาก core.config เพื่อความสอดคล้อง
from ai_trader.core.config import settings
# สมมติว่า models ของคุณสามารถ import ได้โดยตรง (อาจจะต้องปรับ PYTHONPATH หรือโครงสร้างเล็กน้อย)
# หรือจะ import Base และ model ที่ต้องการโดยตรง
from ai_trader.db.base import Base
from ai_trader.models.trade import Trade # ตัวอย่าง
# from ai_trader.models.signal import Signal # ตัวอย่างจาก migration (ถ้ามี model)
# from ai_trader.models.price_data import PriceData # ตัวอย่างจาก migration (ถ้ามี model)
# from ai_trader.models.order import Order # ตัวอย่างจาก migration (ถ้ามี model)

# ตั้งค่า logging
logging.basicConfig(level=settings.LOG_LEVEL.upper(), format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# สร้าง SQLAlchemy engine และ session
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def archive_data_to_csv(session, data_to_archive: list, model_name: str, timestamp_column_name: str, table_columns: list):
    """
    ตัวอย่างฟังก์ชันสำหรับ archive ข้อมูลไปยังไฟล์ CSV
    ใน production อาจจะเปลี่ยนเป็นการ upload ไปยัง S3 หรือ data lake
    """
    if not data_to_archive:
        logger.info(f"No data to archive for {model_name}.")
        return

    archive_dir = Path("archived_data")
    archive_dir.mkdir(exist_ok=True)

    first_item_timestamp_val = None
    if hasattr(data_to_archive[0], timestamp_column_name):
        first_item_timestamp_val = getattr(data_to_archive[0], timestamp_column_name)

    if isinstance(first_item_timestamp_val, datetime):
        filename_ts = first_item_timestamp_val.strftime("%Y%m%d_%H%M%S")
    else: # fallback if not a datetime object or not found
        filename_ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        logger.warning(f"Timestamp for filename not found or not datetime for {model_name}, using current time.")


    filename = archive_dir / f"{model_name}_archive_{filename_ts}.csv"

    try:
        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=table_columns, extrasaction='ignore')
            writer.writeheader()
            for item in data_to_archive:
                row_dict = {col: getattr(item, col, None) for col in table_columns}
                writer.writerow(row_dict)
        logger.info(f"Archived {len(data_to_archive)} rows from {model_name} to {filename}")
    except Exception as e:
        logger.error(f"Error archiving {model_name} to CSV: {e}")


def cleanup_table(
    session,
    model_name: str,
    table_name: str,
    timestamp_column: str,
    older_than_days: int,
    archive: bool = False,
    orm_model_class=None, # Pass the ORM model class if available for ORM-based query
    dry_run: bool = False
):
    """
    Generic function to cleanup data from a table older than specified days.
    """
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    logger.info(f"Processing cleanup for table '{table_name}' for data older than {cutoff_date} ({older_than_days} days ago). Archive: {archive}, Dry Run: {dry_run}")

    # Check if table exists in metadata (basic check)
    if not Base.metadata.tables.get(table_name):
        logger.warning(f"Table '{table_name}' not found in SQLAlchemy metadata. Skipping cleanup for this table.")
        return

    try:
        # Determine columns for CSV archiving if needed (can be improved)
        table_meta = Base.metadata.tables.get(table_name)
        if table_meta is None: # Should not happen if previous check passed
             logger.error(f"Could not get metadata for table {table_name} after initial check.")
             return
        csv_columns = [c.name for c in table_meta.columns]


        if archive:
            logger.info(f"Archiving data for {table_name}...")
            # Fetch data to archive. Use ORM if model is provided, otherwise raw SQL.
            data_to_archive = []
            if orm_model_class and hasattr(orm_model_class, timestamp_column):
                data_to_archive = session.query(orm_model_class).filter(getattr(orm_model_class, timestamp_column) < cutoff_date).all()
            else: # Fallback to raw SQL if ORM model not suitable or not provided
                stmt_select = text(f"SELECT * FROM {table_name} WHERE {timestamp_column} < :cutoff_date")
                result_proxy = session.execute(stmt_select, {"cutoff_date": cutoff_date})
                # Convert RowProxy to objects that getattr can work with for archive_data_to_csv
                # This is a simplified conversion; you might need a more robust way or pass raw dicts
                class DynamicRow: pass
                for row in result_proxy:
                    obj = DynamicRow()
                    for col_name, val in zip(result_proxy.keys(), row): # Use keys() from result_proxy
                        setattr(obj, col_name, val)
                    data_to_archive.append(obj)

            if data_to_archive:
                if not dry_run:
                    archive_data_to_csv(session, data_to_archive, table_name, timestamp_column, csv_columns)
                else:
                    logger.info(f"[DRY RUN] Would archive {len(data_to_archive)} rows from {table_name}.")
            else:
                logger.info(f"No data found older than specified date to archive for {table_name}.")

        # Deleting data
        if not dry_run:
            logger.info(f"Deleting data from {table_name}...")
            stmt_delete = text(f"DELETE FROM {table_name} WHERE {timestamp_column} < :cutoff_date")
            result = session.execute(stmt_delete, {"cutoff_date": cutoff_date})
            deleted_count = result.rowcount
            session.commit()
            logger.info(f"Successfully deleted {deleted_count} old rows from {table_name}.")
        else:
            # In dry run, query how many rows would be deleted
            stmt_count = text(f"SELECT COUNT(*) FROM {table_name} WHERE {timestamp_column} < :cutoff_date")
            count_result = session.execute(stmt_count, {"cutoff_date": cutoff_date}).scalar_one()
            logger.info(f"[DRY RUN] Would delete {count_result} rows from {table_name}.")

    except Exception as e:
        if not dry_run: # only rollback if not dry run, as dry run doesn't change db
            session.rollback()
        logger.error(f"Error cleaning up {table_name}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Database cleanup script.")
    parser.add_argument(
        "--entity",
        type=str,
        required=True,
        choices=["trades", "signals", "orders", "price_data", "all"], # Add more entities as needed
        help="The type of data to cleanup (e.g., 'trades', 'signals'). 'all' will attempt to clean all configured entities."
    )
    parser.add_argument(
        "--days",
        type=int,
        required=True,
        help="Cleanup data older than this many days."
    )
    parser.add_argument(
        "--archive",
        action="store_true",
        help="Archive data before deleting. (Currently archives to local CSV)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate cleanup without actually deleting or archiving data."
    )

    args = parser.parse_args()

    logger.info(f"Starting database cleanup: entity='{args.entity}', days={args.days}, archive={args.archive}, dry_run={args.dry_run}")

    db_session = SessionLocal()

    # Define entities to clean. This could be more dynamic or configuration-driven.
    # (table_name, timestamp_column_name, ORM_Class_if_any)
    entities_to_process = {
        "trades": ("trades", "timestamp", Trade),
        "signals": ("signals", "timestamp", None), # Assuming 'signals' table and 'timestamp' column, no ORM model provided for now
        "orders": ("orders", "created_at", None),   # Assuming 'orders' table and 'created_at' column
        "price_data": ("price_data", "timestamp", None) # Assuming 'price_data' and 'timestamp'
    }

    try:
        if args.entity == "all":
            for entity_name, (table_name, ts_col, model_class) in entities_to_process.items():
                logger.info(f"Processing 'all': cleaning up {entity_name}")
                cleanup_table(db_session, entity_name, table_name, ts_col, args.days, args.archive, model_class, args.dry_run)
        elif args.entity in entities_to_process:
            entity_name = args.entity
            table_name, ts_col, model_class = entities_to_process[entity_name]
            cleanup_table(db_session, entity_name, table_name, ts_col, args.days, args.archive, model_class, args.dry_run)
        else:
            logger.error(f"Unknown entity: {args.entity}. Please choose from {list(entities_to_process.keys())} or 'all'.")

    finally:
        db_session.close()

    logger.info("Database cleanup process finished.")

if __name__ == "__main__":
    # This allows running the script with `python -m scripts.cleanup_database ...` from the project root
    main()
```
