import argparse
import logging
import os
import sys
from typing import Optional

# Monkey-patch for pandas-ta numpy.NaN issue with numpy 2.x
import numpy
import pandas as pd

if not hasattr(numpy, "NaN"):
    numpy.NaN = numpy.nan
if not hasattr(numpy, "float"):  # For older pandas_ta versions if they use np.float
    numpy.float = float

import pandas_ta as ta  # For technical indicators
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_trader.db.session import SessionLocal
from ai_trader.models import Asset, Features, PriceData

# Configure logging
logger = logging.getLogger(__name__)


def get_db_session():
    """Returns a new SQLAlchemy DB session."""
    return SessionLocal()


def calculate_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates technical indicators for the given price data DataFrame.
    The input DataFrame must have 'high', 'low', 'close', 'volume' columns.
    Timestamps should be in the index or a 'timestamp' column for merging.
    """
    if df.empty:
        logger.warning("Input DataFrame for feature calculation is empty.")
        return pd.DataFrame()

    logger.info(f"Calculating features for {len(df)} data points.")

    # Ensure columns are named as expected by pandas_ta (lowercase)
    df.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        },
        inplace=True,
        errors="ignore",
    )  # ignore errors if already lowercase

    # Calculate indicators using pandas_ta
    # RSI
    df.ta.rsi(length=14, append=True, col_names="rsi_14")
    # SMAs
    df.ta.sma(length=20, append=True, col_names="sma_20")
    df.ta.sma(length=50, append=True, col_names="sma_50")
    # EMAs
    df.ta.ema(length=20, append=True, col_names="ema_20")
    df.ta.ema(length=50, append=True, col_names="ema_50")
    # MACD
    # For MACD, pandas-ta typically outputs three columns: MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
    # We want them as macd_line, macd_hist, macd_signal.
    # We can calculate it and then rename, or use specific col_names if supported for multi-column output.
    # Using col_names for direct naming:
    df.ta.macd(
        fast=12,
        slow=26,
        signal=9,
        append=True,
        col_names=("macd_line", "macd_hist", "macd_signal"),
    )
    # ATR
    df.ta.atr(length=14, append=True, col_names="atr_14")
    # Bollinger Bands
    # pandas-ta bbands outputs: BBL_20_2.0, BBM_20_2.0, BBU_20_2.0, BBB_20_2.0, BBP_20_2.0
    # We need 'bb_lowerband', 'bb_middleband', 'bb_upperband'
    df.ta.bbands(
        length=20,
        std=2,
        append=True,
        col_names=(
            "bb_lowerband",
            "bb_middleband",
            "bb_upperband",
            "bb_bandwidth",
            "bb_percent",
        ),
    )

    # The col_names argument should directly create columns with the specified names.
    # The previous complex renaming logic can be removed if col_names works as expected for all indicators.
    # Let's verify the column names after calculation and select only the ones needed for the model.

    # Select only the columns relevant for the Features model plus timestamp for merging/identification
    feature_columns = [
        "rsi_14",
        "sma_20",
        "sma_50",
        "ema_20",
        "ema_50",
        "macd_line",
        "macd_signal",
        "macd_hist",
        "atr_14",
        "bb_upperband",
        "bb_middleband",
        "bb_lowerband",
    ]
    # Add timestamp if it's a column (it should be from PriceData query)
    if "timestamp" in df.columns:
        final_columns = ["timestamp"] + feature_columns
    else:  # Should not happen if data is prepared correctly
        logger.error(
            "Timestamp column is missing from DataFrame for feature calculation."
        )
        return pd.DataFrame()

    # Keep only existing feature columns to prevent errors if some weren't calculated
    existing_feature_cols = [col for col in final_columns if col in df.columns]

    # Fill NaN with None for database compatibility (NaNs can cause issues with some DB types)
    # Or, some indicators might produce NaNs at the beginning of the series.
    # These rows might be dropped or kept as None.
    features_df = df[existing_feature_cols].copy()
    # features_df.fillna(value=pd.NA, inplace=True) # Convert NaN to NA, then to None for SQLAlchemy

    logger.info(f"Calculated features: {', '.join(features_df.columns.tolist())}")
    return features_df


def get_price_data(
    db: Session,
    asset_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Retrieves PriceData for a given asset_id and optional date range.
    """
    logger.info(
        f"Fetching price data for asset_id: {asset_id} (start: {start_date}, end: {end_date})"
    )
    query = db.query(PriceData).filter(PriceData.asset_id == asset_id)

    if start_date:
        query = query.filter(PriceData.timestamp >= start_date)
    if end_date:
        # To include the end_date, query up to the end of that day
        end_datetime = pd.to_datetime(end_date).replace(
            hour=23, minute=59, second=59, microsecond=999999
        )
        query = query.filter(PriceData.timestamp <= end_datetime)

    query = query.order_by(PriceData.timestamp.asc())

    price_data_records = query.all()

    if not price_data_records:
        logger.warning(
            f"No price data found for asset_id: {asset_id} in the given range."
        )
        return pd.DataFrame()

    df = pd.DataFrame(
        [
            {
                "timestamp": record.timestamp,
                "open": record.open,
                "high": record.high,
                "low": record.low,
                "close": record.close,
                "volume": record.volume,
            }
            for record in price_data_records
        ]
    )

    df.set_index(
        "timestamp", inplace=True, drop=False
    )  # Keep timestamp as a column too
    logger.info(f"Retrieved {len(df)} price data records for asset_id: {asset_id}.")
    return df


def save_features_to_db(
    db: Session, asset_id: int, features_df: pd.DataFrame, dry_run: bool = False
):
    """
    Saves calculated features to the Features table.
    """
    if features_df.empty:
        logger.info("No features to save.")
        return

    added_count = 0
    skipped_count = 0
    error_count = 0

    logger.info(f"Saving {len(features_df)} feature sets for asset_id: {asset_id}.")

    for _, row in features_df.iterrows():
        # Convert Pandas NA to None for SQLAlchemy
        feature_data = {
            col: None if pd.isna(row[col]) else row[col]
            for col in row.index
            if col != "timestamp"
        }
        feature_data["asset_id"] = asset_id
        feature_data["timestamp"] = row[
            "timestamp"
        ]  # Timestamp is from the index/column

        if dry_run:
            logger.info(
                f"[DRY RUN] Would save Features for asset_id {asset_id} at {row['timestamp']}: {feature_data}"
            )
            added_count += 1
            continue

        # Check for existing entry
        try:
            existing_feature = (
                db.query(Features)
                .filter_by(asset_id=asset_id, timestamp=row["timestamp"])
                .first()
            )
            if existing_feature:
                skipped_count += 1
                continue
        except Exception as e_query:
            logger.error(
                f"Error querying existing Feature for asset {asset_id} at {row['timestamp']}: {e_query}",
                exc_info=True,
            )
            error_count += 1
            continue

        feature_entry = Features(**feature_data)
        try:
            db.add(feature_entry)
            db.commit()
            added_count += 1
        except IntegrityError:  # Should be caught by the check above
            db.rollback()
            logger.debug(
                f"Integrity error (likely duplicate) for asset_id {asset_id} at {row['timestamp']}. Skipping."
            )
            skipped_count += 1
        except Exception as e:
            db.rollback()
            logger.error(
                f"Error saving feature for asset_id {asset_id} at {row['timestamp']}: {e}",
                exc_info=True,
            )
            error_count += 1

    log_prefix = "[DRY RUN] " if dry_run else ""
    logger.info(
        f"{log_prefix}Features saving for asset_id {asset_id} complete. "
        f"Added: {added_count}, Skipped (duplicates): {skipped_count}, Errors: {error_count}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Calculate technical features from PriceData and store them."
    )
    parser.add_argument(
        "--symbol", type=str, required=True, help="Asset symbol (e.g., BTC-USD, AAPL)."
    )
    parser.add_argument(
        "--start_date",
        type=str,
        default=None,
        help="Start date for processing (YYYY-MM-DD). Optional.",
    )
    parser.add_argument(
        "--end_date",
        type=str,
        default=None,
        help="End date for processing (YYYY-MM-DD). Optional.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate processing without writing to DB.",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose logging (DEBUG level)."
    )

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            stream=sys.stdout,
        )
    else:
        logging.getLogger().setLevel(log_level)
        logger.setLevel(log_level)

    if args.dry_run:
        logger.info("Performing a DRY RUN. No changes will be made to the database.")

    db: Optional[Session] = None
    try:
        db = get_db_session()

        # Get Asset ID
        asset = db.query(Asset).filter(Asset.symbol == args.symbol).first()
        if not asset:
            logger.error(
                f"Asset with symbol '{args.symbol}' not found. Please ensure data is fetched first using fetch_price_data.py."
            )
            return

        logger.info(f"Processing features for asset: {asset.symbol} (ID: {asset.id})")

        # Get PriceData
        price_df = get_price_data(db, asset.id, args.start_date, args.end_date)
        if price_df.empty:
            logger.warning(
                f"No price data retrieved for {asset.symbol}. Cannot calculate features."
            )
            return

        # Calculate Features
        features_df = calculate_features(
            price_df.copy()
        )  # Pass a copy to avoid SettingWithCopyWarning
        if features_df.empty:
            logger.warning(
                f"No features calculated for {asset.symbol}. Nothing to save."
            )
            return

        # Save Features
        save_features_to_db(db, asset.id, features_df, args.dry_run)

    except Exception as e:
        logger.critical(
            f"A critical error occurred in the feature engineering pipeline: {e}",
            exc_info=True,
        )
    finally:
        if db:
            db.close()
            logger.debug("Database session closed.")
        logger.info("Feature engineering script finished.")


if __name__ == "__main__":
    # Example Usage:
    # python ai_trader/data_pipeline.py --symbol BTC-USD --start_date 2023-01-01 --end_date 2023-12-31 --verbose
    # python ai_trader/data_pipeline.py --symbol AAPL --dry-run
    main()
