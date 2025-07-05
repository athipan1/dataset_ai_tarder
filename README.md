# AI Trader Dataset and Models

This project provides a database schema and SQLAlchemy models for an AI Trader application. It's designed to store information about users, trading strategies, market data (price data), trading signals, orders, and backtest results.

## Project Overview

The core of the project is `models.py`, which defines the database structure using SQLAlchemy. This can be used with SQLite for local development and testing, or with PostgreSQL for more robust deployments.

## Setup and Installation

1.  **Python Version:** Ensure you have Python 3.8+ installed.
2.  **Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```
3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Database Setup:**
    *   **SQLite (Default for local development):** The database file `ai_trader.db` will be automatically created in the project root when `models.py` is run directly (or when tables are created via a script).
    *   **PostgreSQL (Optional):**
        *   Ensure you have PostgreSQL server installed and running.
        *   Create a database and user.
        *   Update the connection string in your application's configuration (see `models.py` for an example placeholder). You might use environment variables for this in a real application.

## Basic Usage

To create the database tables (if they don't exist yet), you should now use the Alembic migration scripts. See the "Database Migrations (Alembic)" section below.

## Project Structure

-   `README.md`: This file.
-   `requirements.txt`: Python dependencies.
-   `models.py`: SQLAlchemy database models. Table creation and schema evolution is now handled by Alembic.
-   `alembic/`: Directory containing Alembic migration scripts and configuration.
-   `alembic.ini`: Alembic configuration file.
-   `scripts/`: Helper scripts for database operations.
    -   `create_db.py`: Script to assist in initial database setup (especially for non-SQLite DBs).
    -   `upgrade_db.py`: Applies all pending database migrations.
    -   `downgrade_db.py`: Reverts database migrations.
    -   `generate_migration.sh`: Generates a new migration file based on model changes.
-   `ai_trader.db`: SQLite database file (created and managed by Alembic migrations).
-   `.github/workflows/ci.yml`: GitHub Actions workflow for CI (linting/testing/migrations).
-   `LICENSE`: Project license.

(Further details on project structure will be added as the project evolves, e.g., for API components, services, tests, etc.)

## Database Migrations (Alembic)

This project uses [Alembic](https://alembic.sqlalchemy.org/) to manage database schema migrations. This allows for evolving the database schema over time without losing data.

### Initial Database Setup

1.  Ensure your `alembic.ini` file has the correct `sqlalchemy.url` for your database. By default, it's configured for `sqlite:///./ai_trader.db`.
2.  Run the `create_db.py` script if you need to perform any pre-migration database setup (e.g., for PostgreSQL, ensuring the database itself exists). For SQLite, this step is often not strictly necessary as the file will be created.
    ```bash
    python scripts/create_db.py
    ```
3.  Apply all migrations to bring the database to the latest schema:
    ```bash
    python scripts/upgrade_db.py
    ```
    This will create the `ai_trader.db` file if it doesn't exist (for SQLite) and apply all migration scripts found in `alembic/versions/`.

### Generating New Migrations

When you make changes to your SQLAlchemy models in `models.py` (e.g., add a new table, add a column, change a column type), you need to generate a new migration script:

1.  Run the `generate_migration.sh` script with a descriptive message for your changes:
    ```bash
    bash scripts/generate_migration.sh "your_descriptive_migration_message"
    ```
    For example:
    ```bash
    bash scripts/generate_migration.sh "add_last_login_to_users_table"
    ```
2.  This will create a new file in the `alembic/versions/` directory.
3.  **Important**: Open the generated migration file and review it carefully. Alembic's autogenerate feature is powerful but not always perfect. You might need to adjust the generated code to ensure it matches your intent, especially for complex changes like constraints, custom types, or data migrations.
4.  Once you are satisfied with the migration script, you can apply it (see below).

### Applying Migrations

To apply any pending migrations (i.e., upgrade the database schema to the latest version):

```bash
python scripts/upgrade_db.py
```

You can also upgrade to a specific revision:

```bash
python scripts/upgrade_db.py <revision_id>
```

### Downgrading Migrations

To revert (downgrade) migrations:

*   To revert the last applied migration:
    ```bash
    python scripts/downgrade_db.py -1
    ```
*   To revert to a specific earlier revision (all subsequent migrations will be undone):
    ```bash
    python scripts/downgrade_db.py <target_revision_id_before_the_ones_to_revert>
    ```
    For example, if you have revisions `A -> B -> C` and want to go back to `A`, you'd downgrade to `A`.
    To revert all migrations (back to an empty database schema, not dropping the database itself):
    ```bash
    python scripts/downgrade_db.py base
    ```

### Viewing Migration History

You can see the history of migrations and the current revision:

```bash
alembic history
alembic current
```
(Ensure your shell is in the project root or that Alembic can find `alembic.ini`.)