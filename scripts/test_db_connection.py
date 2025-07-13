import sqlalchemy
from ai_trader.db.session import engine
from ai_trader.config import settings


def main():
    print("Testing database connection...")
    print(f"Using database URL: {settings.DATABASE_URL}")
    try:
        with engine.connect() as connection:
            print("Connection successful!")
            result = connection.execute(sqlalchemy.text("SELECT 1"))
            for row in result:
                print(f"SELECT 1 result: {row[0]}")
    except Exception as e:
        print(f"Error connecting to the database: {e}")


if __name__ == "__main__":
    main()
