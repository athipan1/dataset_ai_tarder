import argparse
import logging
import os
import sys
from datetime import datetime, timedelta, timezone

import pandas as pd
import yfinance as yf
from binance.client import Client  # For Binance

# from sqlalchemy import create_engine # Not directly used, SessionLocal handles engine
# from sqlalchemy.orm import sessionmaker # Not directly used, SessionLocal is instance
from sqlalchemy.exc import IntegrityError

# Add project root to Python path to allow importing project modules
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_trader.config import settings  # For BINANCE_API_KEY/SECRET
from ai_trader.db.session import (
    SessionLocal,
)  # SessionLocal is a configured sessionmaker
from ai_trader.models import Asset, PriceData  # Import specific models

# Configure logging - will be set in main based on args
logger = logging.getLogger(__name__)


def get_db_session():
    """Returns a new SQLAlchemy DB session from the configured SessionLocal."""
    return SessionLocal()


def fetch_yfinance_data(
    symbol: str,
    start_date: str | None = None,
    end_date: str | None = None,
    period: str | None = None,
    interval: str = "1d",
) -> pd.DataFrame:
    """
    Fetches historical OHLCV data from Yahoo Finance.
    Uses start_date and end_date if provided, otherwise falls back to period.

    Args:
        symbol (str): The stock/crypto symbol (e.g., "AAPL", "BTC-USD").
        start_date (str, optional): Start date in YYYY-MM-DD format.
        end_date (str, optional): End date in YYYY-MM-DD format.
                                  Data is fetched up to, but not including, this date by yfinance.
                                  To include data for 'end_date', it might be necessary to pass 'end_date + 1 day'.
                                  For daily data, yfinance `end` parameter means "until this date". If you give 2023-01-05,
                                  it means data until 2023-01-05 00:00:00, so the last daily bar included is 2023-01-04.
                                  To get data for 2023-01-05, end should be 2023-01-06.
        period (str, optional): The period for which to fetch data if start/end dates are not provided (e.g., "1y", "2y", "max").
        interval (str): The data interval (e.g., "1d", "1h", "15m").

    Returns:
        pd.DataFrame: A DataFrame with OHLCV data, or an empty DataFrame if an error occurs.
                      Columns: Datetime (index), Open, High, Low, Close, Volume.
    """
    fetch_params = {"interval": interval}
    log_msg_parts = [f"Fetching data for {symbol} from Yahoo Finance"]

    if start_date and end_date:
        try:
            # For yfinance, to include data for the end_date, we need to specify the day after.
            dt_end_date = datetime.strptime(end_date, "%Y-%m-%d")
            actual_yf_end_date = (dt_end_date + timedelta(days=1)).strftime("%Y-%m-%d")
            fetch_params["start"] = start_date
            fetch_params["end"] = actual_yf_end_date
            log_msg_parts.append(
                f"start: {start_date}, end: {end_date} (querying up to {actual_yf_end_date})"
            )
        except ValueError:
            logger.error(
                f"Invalid date format for start_date ('{start_date}') or end_date ('{end_date}'). Use YYYY-MM-DD."
            )
            return pd.DataFrame()
    elif period:
        fetch_params["period"] = period
        log_msg_parts.append(f"period: {period}")
    else:
        # This case should be handled by argument parsing logic in main()
        logger.error(
            "Either start_date/end_date or period must be provided for yfinance."
        )
        return pd.DataFrame()

    log_msg_parts.append(f"interval: {interval}")
    logger.info(", ".join(log_msg_parts))

    try:
        ticker = yf.Ticker(symbol)
        history = ticker.history(**fetch_params)

        if history.empty:
            logger.warning(
                f"No data found for {symbol} with specified parameters from Yahoo Finance."
            )
            return pd.DataFrame()

        history.reset_index(inplace=True)
        ts_column = None
        if "Datetime" in history.columns:
            ts_column = "Datetime"
        elif "Date" in history.columns:
            ts_column = "Date"
        else:
            logger.error(
                f"Timestamp column ('Datetime' or 'Date') not found in yfinance data for {symbol}."
            )
            return pd.DataFrame()

        history[ts_column] = pd.to_datetime(
            history[ts_column], utc=True
        )  # Ensure datetime objects, assume UTC if mixed/naive
        history[ts_column] = history[ts_column].dt.tz_localize(
            None
        )  # Make naive for DB storage (as UTC)

        # Filter out data outside the originally requested end_date if yfinance returned extra
        # This is because we asked for end_date + 1 day.
        if start_date and end_date:  # only if end_date was originally specified
            # Ensure comparison is between datetime objects (or series)
            # Convert end_date string to a datetime object for comparison, set time to end of day
            requested_end_datetime = pd.to_datetime(end_date).replace(
                hour=23, minute=59, second=59, microsecond=999999
            )
            history = history[history[ts_column] <= requested_end_datetime]

        logger.info(
            f"Successfully fetched {len(history)} records for {symbol} from Yahoo Finance."
        )
        return history

    except Exception as e:
        logger.error(
            f"Error fetching data for {symbol} from Yahoo Finance: {e}", exc_info=True
        )
        return pd.DataFrame()


def fetch_binance_data(
    symbol: str,
    start_date: str | None = None,
    end_date: str | None = None,
    period: str | None = None,
    interval: str = "1d",
) -> pd.DataFrame:
    """
    Fetches historical OHLCV data from Binance.

    Args:
        symbol (str): The trading pair symbol (e.g., "BTCUSDT", "ETHBTC").
        start_date (str, optional): Start date in YYYY-MM-DD format.
        end_date (str, optional): End date in YYYY-MM-DD format. Data is fetched up to this date.
                                  Binance `end_str` for `get_historical_klines` is exclusive for the timestamp.
                                  So, to get data for 2023-12-31, end_str should be "2024-01-01".
        period (str, optional): The period for which to fetch data if start/end dates are not directly used by underlying API.
        interval (str): The data interval (e.g., "1d", "1h", "15m").

    Returns:
        pd.DataFrame: A DataFrame with OHLCV data, or an empty DataFrame if an error occurs.
                      Columns: Datetime, Open, High, Low, Close, Volume.
    """

    # Initialize Binance client
    try:
        api_key = getattr(settings, "BINANCE_API_KEY", None)
        api_secret = getattr(settings, "BINANCE_API_SECRET", None)
        if api_key and api_secret:
            client = Client(api_key, api_secret)
            logger.debug("Using Binance API key from settings.")
        else:
            client = Client()  # Public access
            logger.debug(
                "Attempting public Binance API access (no key found in settings)."
            )
    except Exception as e:
        logger.error(
            f"Error initializing Binance client: {e}. Ensure python-binance is installed and settings are correct if using API keys."
        )
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
        "1M": Client.KLINE_INTERVAL_1MONTH,
    }
    binance_interval = interval_map.get(interval)
    if not binance_interval:
        logger.error(
            f"Unsupported interval for Binance: {interval}. Supported: {list(interval_map.keys())}"
        )
        return pd.DataFrame()

    klines_args = {"symbol": symbol, "interval": binance_interval}
    log_msg_parts = [f"Fetching data for {symbol} from Binance"]
    actual_binance_end_str: str | None = None

    if start_date:
        klines_args["start_str"] = start_date  # e.g., "2021-01-01"
        log_msg_parts.append(f"start: {start_date}")
        if end_date:
            try:
                dt_end_date = datetime.strptime(end_date, "%Y-%m-%d")
                actual_binance_end_dt = dt_end_date + timedelta(days=1)
                actual_binance_end_str = actual_binance_end_dt.strftime("%Y-%m-%d")
                klines_args["end_str"] = actual_binance_end_str
                log_msg_parts.append(
                    f"end: {end_date} (querying up to {actual_binance_end_str})"
                )
            except ValueError:
                logger.error(
                    f"Invalid date format for end_date ('{end_date}'). Use YYYY-MM-DD."
                )
                return pd.DataFrame()
        else:
            log_msg_parts.append("end: latest")
    elif period:
        current_time_utc = datetime.now(timezone.utc)
        start_dt_calc: datetime
        if period.endswith("y"):
            start_dt_calc = current_time_utc - timedelta(days=365 * int(period[:-1]))
        elif period.endswith("M"):
            start_dt_calc = current_time_utc - timedelta(
                days=30 * int(period[:-1])
            )  # Approx
        elif period.endswith("w"):
            start_dt_calc = current_time_utc - timedelta(days=7 * int(period[:-1]))
        elif period.endswith("d"):
            start_dt_calc = current_time_utc - timedelta(days=int(period[:-1]))
        elif period.endswith("h"):
            start_dt_calc = current_time_utc - timedelta(hours=int(period[:-1]))
        elif period == "max":
            start_dt_calc = datetime(
                2017, 1, 1, tzinfo=timezone.utc
            )  # Common practical limit
            logger.info("Using '1 Jan, 2017' as start for 'max' period with Binance.")
        else:
            logger.error(f"Unsupported period format: {period}.")
            return pd.DataFrame()
        klines_args["start_str"] = start_dt_calc.strftime("%Y-%m-%d %H:%M:%S")
        log_msg_parts.append(f"period: {period} (from {klines_args['start_str']})")
    else:
        logger.error(
            "Either start_date/end_date or period must be provided for Binance."
        )
        return pd.DataFrame()

    log_msg_parts.append(f"interval: {interval}")
    logger.info(", ".join(log_msg_parts))

    try:
        klines = client.get_historical_klines(**klines_args)
        if not klines:
            logger.warning(
                f"No data found for {symbol} with specified parameters from Binance."
            )
            return pd.DataFrame()

        df = pd.DataFrame(
            klines,
            columns=[
                "Datetime",
                "Open",
                "High",
                "Low",
                "Close",
                "Volume",
                "CloseTime",
                "QuoteAssetVolume",
                "NumberofTrades",
                "TakerBuyBaseAssetVolume",
                "TakerBuyQuoteAssetVolume",
                "Ignore",
            ],
        )
        df["Datetime"] = pd.to_datetime(df["Datetime"], unit="ms", utc=True)
        df["Datetime"] = df["Datetime"].dt.tz_localize(None)  # Store as naive UTC

        for col in ["Open", "High", "Low", "Close", "Volume"]:
            df[col] = pd.to_numeric(df[col])

        # Filter out data beyond the originally requested end_date if Binance returned extra
        if start_date and end_date:
            requested_end_datetime = pd.to_datetime(end_date).replace(
                hour=23, minute=59, second=59, microsecond=999999
            )
            df = df[df["Datetime"] <= requested_end_datetime]

        logger.info(
            f"Successfully fetched {len(df)} records for {symbol} from Binance."
        )
        return df
    except Exception as e:
        logger.error(
            f"Error fetching data for {symbol} from Binance: {e}", exc_info=True
        )
        return pd.DataFrame()


def get_or_create_asset(
    session, symbol_str: str, asset_type_str: str = "Unknown", dry_run: bool = False
) -> Asset | None:
    """
    Retrieves an asset by its symbol or creates it if it doesn't exist.
    If dry_run is True, it will log the creation but not commit to DB.

    Args:
        session: SQLAlchemy session object (can be None if dry_run is True).
        symbol_str (str): The asset symbol (e.g., "AAPL", "BTC-USD").
        asset_type_str (str): The type of asset (e.g., "Stock", "Crypto").
        dry_run (bool): If True, simulates asset creation without DB changes.

    Returns:
        Asset: The existing or newly created Asset object, or None on failure.
    """
    if not dry_run and session is None:
        logger.error(
            "Database session is None in get_or_create_asset for non-dry_run. Cannot proceed."
        )
        return None

    asset: Asset | None = None
    if (
        session
    ):  # Only query if session exists (i.e., not dry_run or dry_run with an actual session)
        try:
            asset = session.query(Asset).filter(Asset.symbol == symbol_str).first()
        except Exception as e:
            logger.error(f"Error querying asset {symbol_str}: {e}", exc_info=True)
            return None  # Cannot proceed if query fails

    if not asset:
        logger.info(
            f"Asset with symbol '{symbol_str}' not found. Attempting to create new asset."
        )
        # Create a temporary Asset object for all cases first
        temp_asset = Asset(
            symbol=symbol_str, name=symbol_str, asset_type=asset_type_str
        )

        if dry_run:
            logger.info(
                f"[DRY RUN] Would create asset '{symbol_str}' (type: {asset_type_str})."
            )
            temp_asset.id = -1  # Placeholder ID for dry run
            return temp_asset
        else:  # Actual creation
            if session is None:  # Should have been caught earlier, but defensive check
                logger.error("DB session is None. Cannot create asset in non-dry_run.")
                return None
            session.add(temp_asset)
            try:
                session.commit()
                logger.info(
                    f"Asset '{symbol_str}' created successfully with ID {temp_asset.id}."
                )
                session.refresh(
                    temp_asset
                )  # Ensure we get the ID and other DB defaults
                return temp_asset
            except IntegrityError:
                session.rollback()
                logger.warning(
                    f"Integrity error creating asset {symbol_str}, likely created concurrently. Re-fetching."
                )
                try:
                    asset = (
                        session.query(Asset).filter(Asset.symbol == symbol_str).first()
                    )
                    if asset:
                        logger.info(
                            f"Successfully re-fetched asset '{symbol_str}' after integrity error."
                        )
                        return asset
                    else:
                        logger.error(
                            f"Failed to re-fetch asset '{symbol_str}' after integrity error."
                        )
                        return None
                except Exception as e_fetch:
                    logger.error(
                        f"Error re-fetching asset {symbol_str} after integrity error: {e_fetch}",
                        exc_info=True,
                    )
                    return None
            except Exception as e:
                session.rollback()
                logger.error(f"Error creating asset {symbol_str}: {e}", exc_info=True)
                return None
    else:  # Asset was found
        logger.debug(f"Found existing asset '{symbol_str}' with ID {asset.id}.")
        return asset


def save_data_to_db(
    session,
    data: pd.DataFrame,
    asset_obj: Asset,
    source_name: str,
    dry_run: bool = False,
):
    """
    Saves OHLCV data to the PriceData table in the database.
    Skips entries if a record with the same asset_id, timestamp, and source already exists.
    If dry_run is True, logs actions but does not commit to DB.
    """
    if asset_obj is None:
        logger.error(
            f"Invalid asset object (None) provided. Cannot save price data for source {source_name}."
        )
        return

    # In dry_run, asset_obj.id might be -1. In actual run, it must be a valid ID.
    if not dry_run and (asset_obj.id is None or asset_obj.id == -1):
        logger.error(
            f"Invalid asset ID for asset '{asset_obj.symbol}'. Cannot save price data."
        )
        return

    if data.empty:
        logger.info(
            f"No data to save for asset '{asset_obj.symbol}' from {source_name}."
        )
        return

    added_count = 0
    skipped_count = 0
    error_count = 0

    # Timestamps in 'data' DataFrame are expected to be naive (representing UTC)
    ts_column = "Datetime"  # Standardized in fetch functions

    for _, row in data.iterrows():
        timestamp_val = pd.to_datetime(
            row[ts_column]
        )  # Should already be datetime from fetch

        if dry_run:
            logger.info(
                f"[DRY RUN] Would add PriceData: Asset Symbol {asset_obj.symbol}, Timestamp {timestamp_val}, "
                f"O={row['Open']:.2f}, H={row['High']:.2f}, L={row['Low']:.2f}, C={row['Close']:.2f}, V={row['Volume']:.0f}, Source {source_name}"
            )
            added_count += 1
            continue

        if session is None:  # Should be caught by main logic if not dry_run
            logger.error("Database session is None in save_data_to_db. Cannot save.")
            error_count += len(data) - added_count - skipped_count
            break

        # Check for existing entry to prevent IntegrityError and allow skipping
        try:
            existing_entry = (
                session.query(PriceData)
                .filter_by(
                    asset_id=asset_obj.id, timestamp=timestamp_val, source=source_name
                )
                .first()
            )
        except Exception as e_query:
            logger.error(
                f"Error querying existing PriceData for {asset_obj.symbol} at {timestamp_val}: {e_query}",
                exc_info=True,
            )
            error_count += 1
            continue  # Skip this record

        if existing_entry:
            skipped_count += 1
            continue

        price_entry = PriceData(
            asset_id=asset_obj.id,
            source=source_name,
            timestamp=timestamp_val,
            open=row["Open"],
            high=row["High"],
            low=row["Low"],
            close=row["Close"],
            volume=row["Volume"],
        )
        try:
            session.add(price_entry)
            session.commit()
            added_count += 1
        except IntegrityError:  # Should be caught by the check above, but as a fallback
            session.rollback()
            logger.debug(
                f"Integrity error (likely duplicate despite check) for asset ID {asset_obj.id} at {timestamp_val} from {source_name}. Skipping."
            )
            skipped_count += 1
        except Exception as e:
            session.rollback()
            logger.error(
                f"Error saving data for asset ID {asset_obj.id} at {timestamp_val} from {source_name}: {e}",
                exc_info=True,
            )
            error_count += 1

    log_prefix = "[DRY RUN] " if dry_run else ""
    logger.info(
        f"{log_prefix}Data saving for asset '{asset_obj.symbol}' from {source_name} complete. "
        f"Added: {added_count}, Skipped (duplicates): {skipped_count}, Errors: {error_count}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Fetch OHLCV data from exchanges and store in DB."
    )
    parser.add_argument(
        "symbols",
        nargs="+",
        help="List of symbols to fetch (e.g., AAPL BTC-USD ETHUSDT).",
    )
    parser.add_argument(
        "--exchange",
        type=str,
        required=True,
        choices=["yahoo", "binance"],
        help="Exchange to fetch from.",
    )
    parser.add_argument(
        "--start_date",
        type=str,
        default=None,
        help="Start date for data fetching (YYYY-MM-DD). Inclusive.",
    )
    parser.add_argument(
        "--end_date",
        type=str,
        default=None,
        help="End date for data fetching (YYYY-MM-DD). Inclusive.",
    )
    parser.add_argument(
        "--period",
        type=str,
        default=None,
        help="Period to fetch if start/end date not given (e.g., 1mo, 1y, max).",
    )
    parser.add_argument(
        "--interval",
        type=str,
        default="1d",
        help="Data interval (e.g., 1m, 5m, 15m, 1h, 1d).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate fetching and saving without writing to DB.",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose logging (DEBUG level)."
    )

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    if (
        not logging.getLogger().hasHandlers()
    ):  # Setup basicConfig only if no handlers are present
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            stream=sys.stdout,
        )
    else:  # If handlers exist, just set the level for the root logger and this script's logger
        logging.getLogger().setLevel(log_level)
        logger.setLevel(log_level)

    if args.dry_run:
        logger.info("Performing a DRY RUN. No changes will be made to the database.")

    # Validate date inputs and period
    if args.start_date and not args.end_date:
        parser.error("--start_date requires --end_date.")
    if args.end_date and not args.start_date:
        parser.error("--end_date requires --start_date.")

    if args.start_date and args.end_date:
        try:
            datetime.strptime(args.start_date, "%Y-%m-%d")
            datetime.strptime(args.end_date, "%Y-%m-%d")
        except ValueError:
            parser.error(
                "Invalid date format for --start_date or --end_date. Use YYYY-MM-DD."
            )
        if args.period:
            logger.warning(
                "Both date range (--start_date, --end_date) and --period are specified. Date range will take precedence."
            )
            args.period = None
    elif args.period is None:  # No dates and no period
        args.period = "1y"  # Default period
        logger.info(
            f"No start/end date or period specified, defaulting to period='{args.period}'."
        )

    db_session = None
    if not args.dry_run:
        try:
            db_session = get_db_session()
            if (
                db_session is None
            ):  # Should not happen if SessionLocal is correctly configured
                logger.critical("Failed to get DB session from SessionLocal. Exiting.")
                return
        except Exception as e_sess:
            logger.critical(f"Failed to initialize DB session: {e_sess}", exc_info=True)
            return  # Cannot proceed without a DB session in non-dry_run mode

    try:
        for symbol_arg in args.symbols:
            asset_type = "Unknown"  # Default
            if args.exchange == "yahoo":
                if (
                    all(c.isalpha() or c == "." for c in symbol_arg)
                    and symbol_arg.isupper()
                ):  # Basic check for stock tickers like "AAPL", "BRK.A"
                    asset_type = "Stock"
                elif "-" in symbol_arg:  # e.g., BTC-USD
                    asset_type = "Crypto"
            elif args.exchange == "binance":  # e.g., BTCUSDT
                asset_type = "Crypto"

            asset_object = get_or_create_asset(
                db_session, symbol_arg, asset_type_str=asset_type, dry_run=args.dry_run
            )

            if not asset_object:
                logger.error(
                    f"Could not get or create asset for symbol {symbol_arg}. Skipping."
                )
                continue

            asset_identifier_log = asset_object.symbol
            if asset_object.id != -1:
                asset_identifier_log += f" (ID: {asset_object.id})"

            source_name_str = ""
            ohlcv_data = pd.DataFrame()

            if args.exchange == "yahoo":
                source_name_str = "Yahoo Finance"
                ohlcv_data = fetch_yfinance_data(
                    symbol_arg,
                    args.start_date,
                    args.end_date,
                    args.period,
                    args.interval,
                )
            elif args.exchange == "binance":
                source_name_str = "Binance"
                ohlcv_data = fetch_binance_data(
                    symbol_arg,
                    args.start_date,
                    args.end_date,
                    args.period,
                    args.interval,
                )

            if not ohlcv_data.empty:
                save_data_to_db(
                    db_session,
                    ohlcv_data,
                    asset_object,
                    source_name_str,
                    dry_run=args.dry_run,
                )
            else:
                logger.info(
                    f"No data fetched for {asset_identifier_log} from {source_name_str}. Nothing to save."
                )

    except Exception as e:
        logger.critical(
            f"A critical error occurred in the main execution loop: {e}", exc_info=True
        )
    finally:
        if db_session:
            db_session.close()
            logger.debug("Database session closed.")
        logger.info("Script finished.")


if __name__ == "__main__":
    # Example usage:
    # python scripts/fetch_price_data.py BTC-USD --exchange yahoo --start_date 2023-01-01 --end_date 2023-01-31 --interval 1d --verbose
    # python scripts/fetch_price_data.py AAPL --exchange yahoo --period 1mo --interval 1h --dry-run
    # python scripts/fetch_price_data.py BTCUSDT ETHUSDT --exchange binance --start_date 2023-12-01 --end_date 2023-12-31 --interval 1h --verbose
    # python scripts/fetch_price_data.py SOL-USD --exchange yahoo --start_date 2024-01-01 --end_date 2024-03-31
    main()
