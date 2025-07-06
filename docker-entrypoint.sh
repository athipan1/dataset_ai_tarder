#!/bin/bash
set -e

# Variables from environment (or defaults)
DB_HOST="${DB_HOST:-db}" # Default to 'db' which is the service name in docker-compose
DB_PORT="${DB_PORT:-5432}"
DB_USER="${POSTGRES_USER:-user}" # Use POSTGRES_USER from .env.dev.docker
DB_NAME="${POSTGRES_DB:-ai_trader_db}" # Use POSTGRES_DB from .env.dev.docker

# Wait for the database to be ready
# Attempt to connect to the database using pg_isready.
# The check is for the 'db' service using the credentials provided.
echo "Waiting for database at $DB_HOST:$DB_PORT..."
# Note: pg_isready might not be available in the backend container by default.
# We'll use a simple Python script to check DB readiness if pg_isready is not present.

# Check if pg_isready is available
if command -v pg_isready &> /dev/null; then
    while ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -q; do
      echo "PostgreSQL is unavailable - sleeping"
      sleep 1
    done
else
    echo "pg_isready not found. Using Python script to check DB connection."
    # Python script to check DB connection (relies on psycopg2 being installed)
    # The DATABASE_URL should be set in the environment for this to work
    # This is a fallback and might need adjustment based on exact DB driver/availability
    PY_DB_CHECK_COMMAND="python -c \"
import os
import sys
import time
import sqlalchemy
from sqlalchemy.exc import OperationalError

retries = 30
wait_seconds = 2
db_url = os.getenv('DATABASE_URL')

if not db_url:
    print('DATABASE_URL environment variable not set. Cannot check DB status.')
    sys.exit(1)

print(f'Attempting to connect to database at {db_url} (retrying for {retries*wait_seconds}s)...')
for i in range(retries):
    try:
        engine = sqlalchemy.create_engine(db_url)
        with engine.connect() as connection:
            print('Database connection successful.')
            sys.exit(0)
    except OperationalError as e:
        print(f'Attempt {i+1}/{retries}: Database connection failed: {e}. Retrying in {wait_seconds}s...')
        time.sleep(wait_seconds)
    except Exception as e:
        print(f'Attempt {i+1}/{retries}: An unexpected error occurred: {e}. Retrying in {wait_seconds}s...')
        time.sleep(wait_seconds)
print('Database connection failed after multiple retries.')
sys.exit(1)
\""
    # Execute the Python database check
    eval "$PY_DB_CHECK_COMMAND"
fi

echo "Database is up - proceeding..."

# Run database migrations
echo "Running database migrations..."
python scripts/upgrade_db.py

echo "Database migrations complete."

# Execute the command passed to this script (e.g., CMD from Dockerfile or command from docker-compose)
exec "$@"
