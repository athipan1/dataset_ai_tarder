import logging
import os
from typing import Optional
from urllib.parse import quote_plus

from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load .env files
load_dotenv()
load_dotenv(".env.local", override=True)

class Settings:
    PROJECT_NAME: str = "AI Trader"
    PROJECT_VERSION: str = "0.1.0"

    # --- Database settings ---
    POSTGRES_SERVER: Optional[str] = os.getenv("POSTGRES_SERVER")
    POSTGRES_USER: Optional[str] = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD: Optional[str] = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_DB: Optional[str] = os.getenv("POSTGRES_DB")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))

    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")

    if not DATABASE_URL:
        if all([POSTGRES_SERVER, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB]):
            encoded_password = quote_plus(POSTGRES_PASSWORD)
            DATABASE_URL = f"postgresql://{POSTGRES_USER}:{encoded_password}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"
        else:
            default_sqlite_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "ai_trader.db")
            DATABASE_URL = f"sqlite:///{default_sqlite_path}"
            logger.warning(f"DATABASE_URL or PostgreSQL environment variables not fully set. Falling back to SQLite: {DATABASE_URL}")

    # --- Application Secrets ---
    SECRET_KEY: str = os.getenv("SECRET_KEY", "a_very_secret_default_key_for_dev_only_CHANGE_ME")
    if SECRET_KEY == "a_very_secret_default_key_for_dev_only_CHANGE_ME":
        logger.warning("SECRET_KEY is using the default development value. This should be changed for production.")

    # --- API Keys ---
    BINANCE_API_KEY: Optional[str] = os.getenv("BINANCE_API_KEY")
    BINANCE_API_SECRET: Optional[str] = os.getenv("BINANCE_API_SECRET")

    # --- Logging Configuration ---
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    if LOG_LEVEL not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        logger.warning(f"Invalid LOG_LEVEL '{LOG_LEVEL}'. Defaulting to INFO.")
        LOG_LEVEL = "INFO"

    class Config:
        case_sensitive = True

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
