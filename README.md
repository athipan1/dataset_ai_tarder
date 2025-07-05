# AI Trader Project

This repository contains the codebase for an AI-powered trading bot. The system is designed to analyze market data, economic news, and technical indicators to make automated trading decisions.

## Features (Planned/Implemented)
- Data ingestion for market prices (OHLCV)
- Storage and processing of economic news and events (conceptualized with MongoDB)
- Calculation of various technical indicators
- AI model training and prediction for trading signals (Buy/Sell/Hold)
- Order execution (simulated and/or live)
- Backtesting capabilities for strategies
- Database schema defined with SQLAlchemy for structured data (market data, signals, orders, etc.)

## Project Structure
- `models.py`: Defines the database schema using SQLAlchemy.
- `requirements.txt`: Lists Python dependencies.
- `.github/workflows/ci.yml`: GitHub Actions workflow for Continuous Integration.
- `schema.sql`: A reference SQL DDL schema (SQLAlchemy in `models.py` is the source of truth).
- `.gitignore`: Specifies intentionally untracked files that Git should ignore.
- `data/` (suggested, not yet created): Directory for storing raw data, processed data, etc.
- `src/` (suggested, not yet created): Directory for main source code (e.g., data processing, AI models, trading logic).
- `tests/` (suggested, not yet created): Directory for unit and integration tests.

## Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/athipan1/ai-trader.git
   cd ai-trader
   ```
2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. **Environment Variables (Important for Database Connection):**
   - For local development using SQLite (default for `models.py` script), no specific `DATABASE_URL` is needed initially as it defaults to `sqlite:///./ai_trader_v2.db`.
   - If you want to use PostgreSQL or another database, or specify a different SQLite path, create a `.env` file in the root directory:
     ```env
     # Example for PostgreSQL
     # DATABASE_URL=postgresql://user:password@host:port/mydatabase

     # Example for a different SQLite path
     # DATABASE_URL=sqlite:///./my_custom_trader.db
     ```
   - The `models.py` script (when run directly) and your application code should be configured to read this `DATABASE_URL`. The `python-dotenv` library is included in `requirements.txt` to help load `.env` files.

5. Set up the database schema:
   - The `models.py` script can be run to create/update the schema based on the `DATABASE_URL` (or its default SQLite path):
     ```bash
     python models.py
     ```
   - This will create an SQLite file (e.g., `ai_trader_v2.db`) if using the default.

## Usage
(Details to be added on how to run specific components of the AI Trader system, such as:
- Data ingestion scripts
- AI model training process
- Running live trading predictions
- Performing backtests)

## Running Tests
(Details to be added. Placeholder for `pytest` in `ci.yml` exists.)
```bash
# Example (once tests are written):
# pytest
```

## Flake8 Linting
To check code style:
```bash
flake8 .
```
Note: There have been some persistent E501 (line too long) issues in `models.py` within the GitHub Actions CI environment that may require specific `flake8` configuration in this repository (e.g., a `.flake8` file) or investigation of line endings if they differ from local checks.

## Contributing
(To be added: Guidelines for contributing to the project, if open to contributions.)

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.