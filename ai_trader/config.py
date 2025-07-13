# ai_trader/core/config.py
import os
from typing import Optional
from urllib.parse import quote_plus  # For safely encoding password in DB URL

from dotenv import load_dotenv

# Load values from .env file for base configuration
# and then from .env.local to override them for local development.
# In production, environment variables should be set directly in the environment.
load_dotenv()  # Load .env first
load_dotenv(
    ".env.local", override=True
)  # Load .env.local and override if variables exist


class Settings:
    PROJECT_NAME: str = "AI Trader"
    PROJECT_VERSION: str = "0.1.0"

    # --- Database settings ---
    # Option 1: Define individual PostgreSQL components
    POSTGRES_SERVER: Optional[str] = os.getenv("POSTGRES_SERVER")
    POSTGRES_USER: Optional[str] = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD: Optional[str] = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_DB: Optional[str] = os.getenv("POSTGRES_DB")
    POSTGRES_PORT: Optional[str] = os.getenv(
        "POSTGRES_PORT", "5432"
    )  # Default PostgreSQL port

    # Option 2: Define a full DATABASE_URL (takes precedence if set)
    # This can be for PostgreSQL, SQLite, or other supported databases
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")

    # Construct DATABASE_URL from PostgreSQL components if DATABASE_URL is not explicitly set
    if not DATABASE_URL and all(
        [POSTGRES_SERVER, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB]
    ):
        encoded_password = quote_plus(POSTGRES_PASSWORD)
        DATABASE_URL = f"postgresql://{POSTGRES_USER}:{encoded_password}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"
    elif not DATABASE_URL:
        # Default to a local SQLite database if no other configuration is found
        # This is useful for quick local setup or testing
        default_sqlite_path = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "ai_trader.db",
        )
        DATABASE_URL = f"sqlite:///{default_sqlite_path}"
        print(
            f"Warning: DATABASE_URL or PostgreSQL environment variables not fully set. Falling back to SQLite: {DATABASE_URL}"
        )

    # --- Application Secrets ---
    # Secret key for JWT, session management, or other security features
    # IMPORTANT: Change this in production to a strong, random key!
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY", "a_very_secret_default_key_for_dev_only_CHANGE_ME"
    )
    if SECRET_KEY == "a_very_secret_default_key_for_dev_only_CHANGE_ME":
        print(
            "Warning: SECRET_KEY is using the default development value. This should be changed for production."
        )

    # --- API Keys / Other Secrets (Example) ---
    # These should always be loaded from environment variables and never hardcoded.
    SOME_EXCHANGE_API_KEY: Optional[str] = os.getenv("SOME_EXCHANGE_API_KEY")
    SOME_EXCHANGE_API_SECRET: Optional[str] = os.getenv("SOME_EXCHANGE_API_SECRET")

    # Binance API Keys (used in scripts/fetch_price_data.py)
    BINANCE_API_KEY: Optional[str] = os.getenv("BINANCE_API_KEY")
    BINANCE_API_SECRET: Optional[str] = os.getenv("BINANCE_API_SECRET")

    # --- Logging Configuration (Example) ---
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    # Ensure LOG_LEVEL is one of the standard levels
    if LOG_LEVEL not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        print(f"Warning: Invalid LOG_LEVEL '{LOG_LEVEL}'. Defaulting to INFO.")
        LOG_LEVEL = "INFO"

    class Config:
        case_sensitive = (
            True  # Ensure environment variable names are treated as case-sensitive
        )


# Create a single instance of the Settings class that can be imported elsewhere
settings = Settings()

# Example of how to use this in other parts of the application:
# from ai_trader.core.config import settings
#
# db_url = settings.DATABASE_URL
# api_key = settings.SOME_EXCHANGE_API_KEY
#
# if api_key:
#     print("Exchange API Key is configured.")
# else:
#     print("Warning: Exchange API Key is not configured.")
