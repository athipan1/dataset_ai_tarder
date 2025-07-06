# AI Trader Dataset and Models

This project provides a database schema and SQLAlchemy models for an AI Trader application. It's designed to store information about users, trading strategies, market data (price data), trading signals, orders, and backtest results.

## Project Overview

The core of the project is `ai_trader/models.py`, which defines the database structure using SQLAlchemy. Configuration is managed in `ai_trader/config.py`. This setup can be used with SQLite for local development and testing, or with PostgreSQL for more robust deployments.

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
    *   **SQLite (Default for local development):** The database file (e.g., `ai_trader.db`) will be created in the project root when Alembic migrations are run.
    *   **PostgreSQL (Optional):**
        *   Ensure you have PostgreSQL server installed and running.
        *   Create a database and user.
        *   Update the connection string in your `.env` file (see `ai_trader/config.py` for how `DATABASE_URL` is loaded).

## Basic Usage

To create the database tables (if they don't exist yet), you should use the Alembic migration scripts. See the "Database Migrations (Alembic)" section below.

## Project Structure

-   `README.md`: This file.
-   `requirements.txt`: Python dependencies (includes `SQLAlchemy`, `alembic`, `psycopg2-binary`, `python-dotenv`, `flake8`, `black`, `isort`, `pytest`).
-   `ai_trader/`: Main application package.
    -   `models.py`: Consolidated SQLAlchemy database models.
    -   `config.py`: Application configuration settings (loads from `.env`).
    -   `db/`: Database-related modules.
        -   `session.py`: SQLAlchemy engine and session setup.
        -   `init_db.py`: Utility for (non-Alembic) database initialization (use with caution).
-   `alembic/`: Directory containing Alembic migration scripts and configuration.
-   `alembic.ini`: Alembic configuration file.
-   `scripts/`: Helper scripts for database operations and development.
    -   `create_db.py`: Script to assist in initial database setup (primarily for non-Alembic or pre-Alembic scenarios).
    -   `upgrade_db.py`: Applies all pending database migrations.
    -   `downgrade_db.py`: Reverts database migrations.
    -   `generate_migration.sh`: Generates a new migration file based on model changes in `ai_trader/models.py`.
-   `tests/`: Directory for unit and integration tests.
-   `ai_trader.db`: Example SQLite database file (created and managed by Alembic migrations if SQLite is used).
-   `.env`: Local environment variables (e.g., `DATABASE_URL`). **Ignored by Git.**
-   `.env.example`: Example environment file.
-   `.gitignore`: Specifies intentionally untracked files that Git should ignore.
-   `.flake8`: Configuration for flake8 linter.
-   `.github/workflows/ci.yml`: GitHub Actions workflow for CI (linting/testing/migrations).
-   `LICENSE`: Project license.

(Further details on project structure will be added as the project evolves, e.g., for API components, services, etc.)

## Code Quality and Linting

This project uses `flake8` for linting, and `black` and `isort` for code formatting to maintain consistency.
-   `flake8`: Checks for PEP 8 compliance and other code style issues. Configured in `.flake8`.
-   `black`: The uncompromising Python code formatter.
-   `isort`: Sorts imports alphabetically and automatically separates them into sections.

You can run these tools locally:
```bash
flake8 .
black .
isort .
```
**Note:** Due to current limitations with the automated tooling environment, these tools might not have been run automatically during recent refactoring. It is recommended to run them manually to ensure code consistency.

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
    **CRITICAL**: Do **NOT** use SQLAlchemy's `Base.metadata.create_all()` (which can be called by `ai_trader/db/init_db.py` if manually uncommented, or by `scripts/create_db.py` if modified) and Alembic (`python scripts/upgrade_db.py` or `alembic upgrade head`) together on the *same live database instance*.
    *   `Base.metadata.create_all()` directly creates tables based on your current models in `ai_trader/models.py`, bypassing Alembic's versioning.
    *   Alembic creates tables based on its migration scripts and tracks schema versions in the `alembic_version` table.
    *   Using both can lead to errors like "table already exists" when running migrations, or an inconsistent database state.
    *   **Rule of thumb**: Once you start using Alembic for a database, Alembic should be the *only* tool used to modify that database's schema. The `init_db.py` and `create_db.py` utilities are primarily for initial, non-Alembic setups or specific development/testing scenarios where Alembic is not being used.

*   **Resetting the Database (Especially for SQLite Development)**:
    If you encounter issues like "table already exists" during an `alembic upgrade` and you're using SQLite for local development (and don't need to preserve data), the simplest solution is often to reset:
    1.  **Delete the SQLite database file**:
        ```bash
        rm ai_trader.db  # Or the name specified in your DATABASE_URL in .env
        ```
    2.  **Re-apply all migrations**:
        ```bash
        python scripts/upgrade_db.py
        ```
    For other database systems, resetting might involve dropping and recreating the database or its tables, then running migrations. Always ensure you understand the implications before deleting data.

### Generating New Migrations

When you make changes to your SQLAlchemy models in `ai_trader/models.py` (e.g., add a new table, add a column, change a column type), you need to generate a new migration script:

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

### Alembic Best Practices and Automated Checks

To ensure robust and maintainable database migrations, this project incorporates several best practices and automated checks:

1.  **Generating Revisions**:
    *   Always use the `scripts/generate_migration.sh` script to create new revision files:
        ```bash
        bash scripts/generate_migration.sh "Descriptive message about changes"
        ```
    *   This script automatically uses `alembic revision --autogenerate -m "message"`.
    *   Provide a clear and concise message that explains the purpose of the migration (e.g., "add_user_email_verification_table", "add_index_to_orders_created_at").

2.  **Review Autogenerated Migrations**:
    *   Alembic's autogenerate feature is powerful but not infallible. **Always open and review the generated migration script** in `alembic/versions/`.
    *   Verify that the `upgrade()` and `downgrade()` functions accurately reflect the intended schema changes.
    *   Pay close attention to:
        *   Detection of new tables, columns, indexes, and constraints.
        *   Changes to column types, nullability, or default values.
        *   Correct handling of complex types or custom constraints (these might require manual adjustments).
        *   Ensure that the `downgrade` path correctly reverts all changes made in the `upgrade` path.
    *   Autogenerate might not detect all changes, such as server defaults or some types of constraint modifications. These may need to be added manually to the script.

3.  **SQLAlchemy Models as Source of Truth**:
    *   Define your database schema (tables, columns, relationships, indexes, constraints) primarily within your SQLAlchemy models (`ai_trader/models.py`).
    *   Alembic's autogenerate should then derive migrations from these model definitions. Avoid writing raw `CREATE TABLE` or `ALTER TABLE` SQL directly in migration scripts unless absolutely necessary for operations not supported by Alembic's `op` module or for complex data migrations.

4.  **Migration Testing (`tests/test_migrations.py`)**:
    *   This project includes a test suite for migrations (`tests/test_migrations.py`) that is run as part of the CI pipeline. These tests aim to:
        *   **Verify Schema Consistency**: Creates an in-memory SQLite database, applies all migrations, and compares the resulting schema against the schema derived directly from your SQLAlchemy models. This helps detect "database drift" where the live schema might diverge from the model definitions.
        *   **Discourage Raw SQL for Schema Definition**: Checks for raw `CREATE TABLE` statements in migration files, encouraging the use of `op.create_table()` (usually generated from models).
        *   **Detect Empty Migrations**: Flags migration scripts where both `upgrade()` and `downgrade()` functions are empty (e.g., just contain `pass`), which could indicate an error during generation or manual editing.
    *   Ensure these tests pass before merging changes that include new migrations.

5.  **Handling Migration Conflicts (Branching & Merging)**:
    *   When multiple developers work on features that involve database changes, migration conflicts can occur. Alembic creates a linear history, but Git branches can diverge.
    *   **Scenario**: Developer A creates migration `X` on `feature-A`, and Developer B creates migration `Y` on `feature-B`. Both branch from `main`.
        *   If `feature-A` merges first, `main` has `... -> X`.
        *   When `feature-B` is rebased/merged, migration `Y` might now depend on a different "base" revision.
    *   **Resolution**:
        1.  **Rebase Regularly**: Keep your feature branch updated with `main` (`git rebase main`).
        2.  **Resolve Conflicts Manually**: If a conflict occurs (e.g., two migration files have the same `down_revision` or there are merge conflicts within `env.py` or model files):
            *   Alembic provides guidance on merging branches: `alembic merge <rev1> <rev2> -m "merge message"`. This creates a new merge revision file.
            *   Alternatively, you might need to manually adjust the `down_revision` identifier in one of the conflicting migration files to ensure a linear history. For example, if `Y` was based on `OriginalBase` and `X` is now the head, `Y`'s `down_revision` should point to `X`'s revision ID.
            *   Carefully review the changes to ensure the migration history remains consistent and all schema changes are correctly ordered.
        3.  **Communicate**: Coordinate with other developers when making schema changes.

6.  **Batch Mode for SQLite**:
    *   When modifying existing tables in SQLite (e.g., adding/dropping columns, constraints), Alembic operations often need to be performed in "batch mode" because SQLite has limited `ALTER TABLE` support.
    *   The `alembic/env.py` is configured with `render_as_batch=True`.
    *   When manually editing migrations, ensure you use `with op.batch_alter_table('table_name', schema=None) as batch_op:` for such operations. Autogenerate usually handles this correctly.

7.  **Idempotency**:
    *   Migration steps should ideally be idempotent, meaning running them multiple times has the same effect as running them once. While Alembic manages versioning, writing idempotent operations (e.g., `op.create_table_comment` if it doesn't exist) can be safer, though often Alembic's structure makes this less of a direct concern for schema changes. Data migrations, however, should strongly consider idempotency.

8.  **Data Migrations**:
    *   For changes that involve transforming existing data (not just schema), create a separate migration script or include data manipulation logic within a schema migration script.
    *   Use `op.execute()` for raw SQL or use SQLAlchemy Core/ORM within the migration to interact with data.
    *   **Important**: Data migrations can be risky. Test them thoroughly. Ensure the `downgrade` path can correctly revert data changes if possible, or clearly document if it's a one-way transformation.

By following these practices and leveraging the automated checks, we can maintain a more reliable and understandable database migration history.