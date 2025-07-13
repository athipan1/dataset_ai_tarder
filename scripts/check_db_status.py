import os
import sqlalchemy
from sqlalchemy import inspect

import os
import sqlalchemy
from sqlalchemy import create_engine, inspect
from ai_trader.config import settings

def main():
    # Determine database URL, giving precedence to DATABASE_URL
    db_url = os.environ.get("DATABASE_URL", settings.DATABASE_URL)

    print("🚀 Starting database status check...")
    print(f"🔗 Connecting to database: {db_url}")

    if not db_url or db_url.startswith('sqlite'):
        print("❌ Error: PostgreSQL database URL is not configured.")
        print("  Please set the `DATABASE_URL` environment variable.")
        return

    try:
        engine = create_engine(db_url)
        with engine.connect() as connection:
            print("✅ Connection successful!")

            inspector = inspect(engine)

            print("\n📊 Available tables:")
            tables = inspector.get_table_names()
            if not tables:
                print("  No tables found in the database.")
            else:
                for table in tables:
                    print(f"  - {table}")

            print("\n📦 Checking tables for data...")
            for table_name in tables:
                try:
                    query = sqlalchemy.text(f'SELECT COUNT(*) FROM "{table_name}"')
                    result = connection.execute(query)
                    row_count = result.scalar()
                    if row_count > 0:
                        print(f"  - ✅ Table '{table_name}' contains {row_count} rows.")
                    else:
                        print(f"  - 텅 비어있는 Table '{table_name}' is empty.")
                except Exception as e:
                    print(f"  - ❌ Could not count rows in table '{table_name}': {e}")

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\n🤔 Suggestions:")
        print("  - Verify that the `DATABASE_URL` environment variable is set correctly.")
        print("  - Check if the database server is running and accessible.")
        print("  - Ensure that the necessary database drivers are installed.")

    print("\n🏁 Database status check finished.")

if __name__ == "__main__":
    main()
