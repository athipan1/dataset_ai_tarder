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

To create the database tables (if they don't exist yet), you can run the `models.py` script directly:

```bash
python models.py
```
This will output: "Database tables created successfully."

## Project Structure

-   `README.md`: This file.
-   `requirements.txt`: Python dependencies.
-   `models.py`: SQLAlchemy database models and table creation logic.
-   `ai_trader.db`: SQLite database file (created automatically).
-   `.github/workflows/ci.yml`: GitHub Actions workflow for CI (linting/testing).
-   `LICENSE`: Project license.

(Further details on project structure will be added as the project evolves, e.g., for API components, services, tests, etc.)