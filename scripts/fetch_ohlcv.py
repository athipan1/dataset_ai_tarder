import os
import sys
import argparse
from datetime import datetime, timedelta
import logging

import yfinance as yf
from binance.client import Client # For Binance
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

# Add project root to Python path to allow importing project modules
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_trader.models import Base, PriceData
from ai_trader.db.session import SessionLocal # SessionLocal is a configured sessionmaker
from ai_trader.config import settings # For DATABASE_URL, though SessionLocal already uses it via its engine

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_session():
    """Returns a new SQLAlchemy DB session from the configured SessionLocal."""
    return SessionLocal()


def fetch_yfinance_data(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """
    Fetches historical OHLCV data from Yahoo Finance.

    Args:
        symbol (str): The stock/crypto symbol (e.g., "AAPL", "BTC-USD").
        period (str): The period for which to fetch data (e.g., "1y", "2y", "max").
        interval (str): The data interval (e.g., "1d", "1h", "15m").

    Returns:
        pd.DataFrame: A DataFrame with OHLCV data, or an empty DataFrame if an error occurs.
                      Columns: Datetime (index), Open, High, Low, Close, Volume.
    """
    logger.info(f"Fetching data for {symbol} from Yahoo Finance (period: {period}, interval: {interval})")
    try:
        ticker = yf.Ticker(symbol)
        # Adjusting start/end based on period for more control if needed, yfinance handles "period" well.
        # For "1y", "2y", yfinance's period is sufficient.
        # If specific dates are needed:
        # end_date = datetime.now()
        # if period == "1y":
        #     start_date = end_date - timedelta(days=365)
        # elif period == "2y":
        #     start_date = end_date - timedelta(days=365 * 2)
        # else: # Default to period string
        #     start_date = None
        # history = ticker.history(period=period, interval=interval, start=start_date, end=end_date)

        history = ticker.history(period=period, interval=interval)

        if history.empty:
            logger.warning(f"No data found for {symbol} with period {period} and interval {interval} from Yahoo Finance.")
            return pd.DataFrame()

        history.reset_index(inplace=True)
        # Ensure 'Datetime' or 'Date' column is timezone-naive for SQLite compatibility if it's timezone-aware
        ts_column = None
        if 'Datetime' in history.columns:
            ts_column = 'Datetime'
        elif 'Date' in history.columns:
            ts_column = 'Date'
        else:
            logger.error(f"Timestamp column not found in yfinance data for {symbol}.")
            return pd.DataFrame()

        if pd.api.types.is_datetime64_any_dtype(history[ts_column]):
            if history[ts_column].dt.tz is not None:
                history[ts_column] = history[ts_column].dt.tz_localize(None)

        logger.info(f"Successfully fetched {len(history)} records for {symbol} from Yahoo Finance.")
        return history

    except Exception as e:
        logger.error(f"Error fetching data for {symbol} from Yahoo Finance: {e}")
        return pd.DataFrame()


def fetch_binance_data(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """
    Fetches historical OHLCV data from Binance.

    Args:
        symbol (str): The trading pair symbol (e.g., "BTCUSDT", "ETHBTC").
        period (str): The period for which to fetch data (e.g., "1y", "6M", "1d").
                      Binance API uses a start_str, so this will be converted.
        interval (str): The data interval (e.g., "1d", "1h", "15m").

    Returns:
        pd.DataFrame: A DataFrame with OHLCV data, or an empty DataFrame if an error occurs.
                      Columns: Datetime, Open, High, Low, Close, Volume.
    """
    logger.info(f"Fetching data for {symbol} from Binance (period: {period}, interval: {interval})")

    # Initialize Binance client (assuming no API key/secret needed for public klines)
    # If keys are needed: client = Client(api_key=settings.BINANCE_API_KEY, api_secret=settings.BINANCE_API_SECRET)
    # For now, let's assume they are in settings if needed, or public access works.
    try:
        api_key = getattr(settings, 'BINANCE_API_KEY', None)
        api_secret = getattr(settings, 'BINANCE_API_SECRET', None)
        if api_key and api_secret:
            client = Client(api_key, api_secret)
            logger.info("Using Binance API key from settings.")
        else:
            client = Client() # Public access
            logger.info("Attempting public Binance API access (no key found in settings).")

    except Exception as e:
        logger.error(f"Error initializing Binance client: {e}. Ensure python-binance is installed and settings are correct if using API keys.")
        return pd.DataFrame()

    # Map user-friendly interval to Binance KLINE_INTERVAL constants
    interval_map = {
        "1m": Client.KLINE_INTERVAL_1MINUTE,
        "3m": Client.KLINE_INTERVAL_3MINUTE,
        "5m": Client.KLINE_INTERVAL_5MINUTE,
        "15m": Client.KLINE_INTERVAL_15MINUTE,
        "30m": Client.KLINE_INTERVAL_30MINUTE,
        "1h": Client.KLINE_INTERVAL_1HOUR,
        "2h": Client.KLINE_INTERVAL_2HOUR,
        "4h": Client.KLINE_INTERVAL_4HOUR,
        "6h": Client.KLINE_INTERVAL_6HOUR,
        "8h": Client.KLINE_INTERVAL_8HOUR,
        "12h": Client.KLINE_INTERVAL_12HOUR,
        "1d": Client.KLINE_INTERVAL_1DAY,
        "3d": Client.KLINE_INTERVAL_3DAY,
        "1w": Client.KLINE_INTERVAL_1WEEK,
        "1M": Client.KLINE_INTERVAL_1MONTH, # Note: 'M' for month vs 'm' for minute
    }
    binance_interval = interval_map.get(interval)
    if not binance_interval:
        logger.error(f"Unsupported interval for Binance: {interval}. Supported: {list(interval_map.keys())}")
        return pd.DataFrame()

    # Convert period string to a start_str for Binance API
    # Examples: "1y ago UTC", "6 months ago UTC", "1 day ago UTC"
    # The get_historical_klines function takes start_str.
    # We need to calculate the start time based on the 'period'.
    end_dt = datetime.utcnow()
    if period.endswith("y"):
        years = int(period[:-1])
        start_dt = end_dt - timedelta(days=365 * years)
    elif period.endswith("M"): # Assuming 'M' for Month, consistent with yfinance
        months = int(period[:-1])
        start_dt = end_dt - timedelta(days=30 * months) # Approximate
    elif period.endswith("w"):
        weeks = int(period[:-1])
        start_dt = end_dt - timedelta(days=7 * weeks)
    elif period.endswith("d"):
        days = int(period[:-1])
        start_dt = end_dt - timedelta(days=days)
    elif period.endswith("h"): # Less common for period, but possible
        hours = int(period[:-1])
        start_dt = end_dt - timedelta(hours=hours)
    elif period == "max": # Binance doesn't have a simple "max" like yfinance period.
                          # Fetch since a very early date or a defined project start.
                          # For this example, let's default to a few years back or handle as error.
        logger.warning("Binance 'max' period is not directly supported by start_str; fetching last 5 years as default for 'max'.")
        start_dt = end_dt - timedelta(days=365 * 5) # Default to 5 years for "max"
    else:
        logger.error(f"Unsupported period format for Binance: {period}. Use formats like '1y', '6M', '30d'.")
        return pd.DataFrame()

    start_str = start_dt.strftime("%d %b, %Y %H:%M:%S")

    try:
        logger.info(f"Fetching klines for {symbol} from {start_str} with interval {binance_interval}")
        klines = client.get_historical_klines(symbol, binance_interval, start_str)

        if not klines:
            logger.warning(f"No data found for {symbol} with period {period} (from {start_str}) and interval {interval} from Binance.")
            return pd.DataFrame()

        # Convert to DataFrame
        columns = ['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume',
                   'CloseTime', 'QuoteAssetVolume', 'NumberofTrades',
                   'TakerBuyBaseAssetVolume', 'TakerBuyQuoteAssetVolume', 'Ignore']
        df = pd.DataFrame(klines, columns=columns)

        # Convert timestamp to datetime (Binance returns ms) and make it timezone-naive
        df['Datetime'] = pd.to_datetime(df['Datetime'], unit='ms')
        if df['Datetime'].dt.tz is not None:
            df['Datetime'] = df['Datetime'].dt.tz_localize(None)

        # Select and typecast necessary columns
        df = df[['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume']]
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            df[col] = pd.to_numeric(df[col])

        logger.info(f"Successfully fetched {len(df)} records for {symbol} from Binance.")
        return df

    except Exception as e:
        logger.error(f"Error fetching data for {symbol} from Binance: {e}")
        return pd.DataFrame()


def save_data_to_db(session, data: pd.DataFrame, symbol: str, exchange_name: str):
    """
    Saves OHLCV data to the PriceData table in the database.
    Skips entries if a record with the same symbol and timestamp already exists.

    Args:
        session: SQLAlchemy session object.
        data (pd.DataFrame): DataFrame containing OHLCV data. Expected columns:
                             'Datetime' or 'Date', 'Open', 'High', 'Low', 'Close', 'Volume'.
        symbol (str): The symbol for which data is being saved.
        exchange_name (str): The name of the exchange (e.g., "Yahoo Finance", "Binance").
    """
    if data.empty:
        logger.info(f"No data to save for {symbol} from {exchange_name}.")
        return

    added_count = 0
    skipped_count = 0

    ts_column = 'Datetime' if 'Datetime' in data.columns else 'Date'

    for _, row in data.iterrows():
        timestamp = pd.to_datetime(row[ts_column])
        # Ensure timestamp is timezone-naive if it became localized somehow
        if timestamp.tzinfo is not None:
            timestamp = timestamp.tz_localize(None)

        price_entry = PriceData(
            symbol=symbol,
            exchange=exchange_name,
            timestamp=timestamp,
            open=row['Open'],
            high=row['High'],
            low=row['Low'],
            close=row['Close'],
            volume=row['Volume']
        )
        try:
            session.add(price_entry)
            session.commit()
            added_count += 1
        except IntegrityError:
            session.rollback()  # Rollback the failed commit
            # logger.debug(f"Record for {symbol} at {timestamp} already exists. Skipping.")
            skipped_count += 1
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving data for {symbol} at {timestamp} from {exchange_name}: {e}")
            skipped_count +=1 # Count as skipped due to error

    logger.info(f"Data saving for {symbol} from {exchange_name} complete. Added: {added_count}, Skipped (duplicates/errors): {skipped_count}")


def main():
    parser = argparse.ArgumentParser(description="Fetch OHLCV data from exchanges and store in DB.")
    parser.add_argument("symbols", nargs='+', help="List of symbols to fetch (e.g., AAPL BTC-USD ETHUSDT).")
    parser.add_argument("--exchange", type=str, required=True, choices=['yahoo', 'binance'], # Add more choices later
                        help="Exchange to fetch from.")
    parser.add_argument("--period", type=str, default="1y", help="Period to fetch (e.g., 1mo, 1y, 2y, max).")
    parser.add_argument("--interval", type=str, default="1d", help="Data interval (e.g., 1m, 5m, 15m, 1h, 1d).")

    args = parser.parse_args()

    db_session = get_db_session()

    try:
        for symbol_arg in args.symbols:
            if args.exchange == 'yahoo':
                # yfinance uses '-' for pairs like BTC-USD, stock tickers are direct like AAPL
                logger.info(f"Processing symbol: {symbol_arg} for Yahoo Finance.")
                ohlcv_data = fetch_yfinance_data(symbol_arg, args.period, args.interval)
                if not ohlcv_data.empty:
                    save_data_to_db(db_session, ohlcv_data, symbol_arg, "Yahoo Finance")
            elif args.exchange == 'binance':
                # Binance typically uses concatenated format like BTCUSDT
                logger.info(f"Processing symbol: {symbol_arg} for Binance.")
                ohlcv_data = fetch_binance_data(symbol_arg, args.period, args.interval)
                if not ohlcv_data.empty:
                    # The 'Datetime' column from Binance fetcher is already the correct name
                    save_data_to_db(db_session, ohlcv_data, symbol_arg, "Binance")
            else:
                logger.error(f"Exchange {args.exchange} not supported.")

    except Exception as e:
        logger.error(f"An error occurred in the main execution: {e}")
    finally:
        if db_session:
            db_session.close()
        logger.info("Script finished.")

if __name__ == "__main__":
    # Example usage:
    # python scripts/fetch_ohlcv.py AAPL BTC-USD --exchange yahoo --period 1y --interval 1d
    # python scripts/fetch_ohlcv.py BTCUSDT ETHBTC --exchange binance --period 1mo --interval 1h (when implemented)
    main()
