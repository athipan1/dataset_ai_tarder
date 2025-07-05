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

### Initial Database Setup with Alembic

1.  **Configure Database URL**: Ensure your `alembic.ini` file (and your `.env` file, which `alembic/env.py` might read) has the correct `sqlalchemy.url` for your database. By default, it's configured for `sqlite:///./ai_trader.db`.
2.  **Create Database (if needed)**:
    *   For **SQLite**, Alembic will create the database file automatically if it doesn't exist when you run the upgrade command.
    *   For **PostgreSQL** or other server-based databases, ensure the database itself (e.g., `ai_trader_db`) and the necessary user/permissions are created on the server. The `scripts/create_db.py` *used to* call `init_db()` which could create tables directly; it no longer does this by default to prevent conflicts with Alembic. Its main purpose now would be for any potential pre-Alembic setup if required by your DB server, or for non-Alembic development.
3.  **Apply Migrations**: To create all tables and bring the database schema to the latest version, run:
    ```bash
    python scripts/upgrade_db.py
    ```
    This command executes `alembic upgrade head`, which applies all migrations found in `alembic/versions/`. For SQLite, this will create the `ai_trader.db` file if it doesn't exist.

### Important Considerations for Alembic Usage

*   **Avoid Mixing Schema Creation Methods**:
    **CRITICAL**: Do **NOT** use SQLAlchemy's `Base.metadata.create_all()` (which was previously called by `init_db()` in `scripts/create_db.py`) and Alembic (`python scripts/upgrade_db.py` or `alembic upgrade head`) together on the *same live database instance*.
    *   `Base.metadata.create_all()` directly creates tables based on your current models, bypassing Alembic's versioning.
    *   Alembic creates tables based on its migration scripts and tracks schema versions in the `alembic_version` table.
    *   Using both can lead to errors like "table already exists" when running migrations, or an inconsistent database state.
    *   **Rule of thumb**: Once you start using Alembic for a database, Alembic should be the *only* tool used to modify that database's schema.

*   **Resetting the Database (Especially for SQLite Development)**:
    If you encounter issues like "table already exists" during an `alembic upgrade` and you're using SQLite for local development (and don't need to preserve data), the simplest solution is often to reset:
    1.  **Delete the SQLite database file**:
        ```bash
        rm ai_trader.db  # Or the name specified in your DATABASE_URL
        ```
    2.  **Re-apply all migrations**:
        ```bash
        python scripts/upgrade_db.py
        ```
    For other database systems, resetting might involve dropping and recreating the database or its tables, then running migrations. Always ensure you understand the implications before deleting data.

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