import os
import sys
import argparse
import logging
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_trader.db.session import SessionLocal
from ai_trader.models import Asset, Features, Signal, Strategy, SignalType, User, PriceData

# Configure logging
logger = logging.getLogger(__name__)

DEFAULT_STRATEGY_NAME = "EMA_Crossover_Labeling_v1"
DEFAULT_USER_ID = 1 # Assuming a default user for automated strategies

def get_db_session():
    """Returns a new SQLAlchemy DB session."""
    return SessionLocal()

def get_or_create_strategy(db: Session, strategy_name: str, user_id: int, dry_run: bool = False) -> Optional[Strategy]:
    """
    Retrieves a strategy by name for a given user_id, or creates it if it doesn't exist.
    """
    strategy = db.query(Strategy).filter(Strategy.name == strategy_name, Strategy.user_id == user_id).first()
    if not strategy:
        logger.info(f"Strategy '{strategy_name}' for user_id {user_id} not found. Attempting to create.")
        if dry_run:
            logger.info(f"[DRY RUN] Would create strategy '{strategy_name}' for user_id {user_id}.")
            # Return a temporary strategy object for dry_run flow
            temp_strategy = Strategy(name=strategy_name, user_id=user_id, description="Automated labeling strategy based on EMA crossover.")
            temp_strategy.id = -1 # Placeholder ID
            return temp_strategy

        # Ensure the user exists before creating a strategy linked to them
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"User with ID {user_id} not found. Cannot create strategy '{strategy_name}'.")
            # As a fallback for headless operation, could try creating a default user,
            # but that's beyond this script's scope. For now, error out.
            logger.warning(f"Please create User ID {user_id} or ensure it exists in the database.")
            # To make this runnable without pre-seeding users for this specific case:
            # We could try to create a default user if user_id=1 (DEFAULT_USER_ID) and it's not found.
            # This is a bit of a hack for convenience.
            if user_id == DEFAULT_USER_ID:
                logger.info(f"Attempting to create default user with ID {DEFAULT_USER_ID} for strategy creation.")
                default_user = User(id=DEFAULT_USER_ID, username=f"default_user_{DEFAULT_USER_ID}", email=f"user{DEFAULT_USER_ID}@example.com", hashed_password="!") # Dummy password
                try:
                    db.add(default_user)
                    db.commit()
                    logger.info(f"Created default user with ID {DEFAULT_USER_ID}.")
                    user = default_user
                except IntegrityError: # If user was created concurrently
                    db.rollback()
                    logger.warning(f"Default user {DEFAULT_USER_ID} might have been created concurrently. Re-fetching.")
                    user = db.query(User).filter(User.id == user_id).first()
                except Exception as e_user:
                    db.rollback()
                    logger.error(f"Failed to create default user {DEFAULT_USER_ID}: {e_user}")
                    return None
            if not user: # If still no user after attempt
                 logger.error(f"User with ID {user_id} still not found after attempting creation. Cannot create strategy.")
                 return None


        strategy = Strategy(name=strategy_name, user_id=user_id, description="Automated labeling strategy based on EMA crossover.")
        try:
            db.add(strategy)
            db.commit()
            logger.info(f"Strategy '{strategy_name}' created successfully with ID {strategy.id} for user_id {user_id}.")
            db.refresh(strategy)
        except IntegrityError: # Should not happen if query().first() was accurate, but as safeguard
            db.rollback()
            logger.warning(f"Integrity error creating strategy {strategy_name}, it might have been created concurrently. Re-fetching.")
            strategy = db.query(Strategy).filter(Strategy.name == strategy_name, Strategy.user_id == user_id).first()
            if not strategy:
                 logger.critical(f"Failed to create or find strategy {strategy_name} after integrity error.")
                 return None
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating strategy {strategy_name}: {e}", exc_info=True)
            return None
    else:
        logger.debug(f"Found existing strategy '{strategy_name}' with ID {strategy.id} for user_id {user_id}.")
    return strategy

def get_features_data(db: Session, asset_id: int, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
    """
    Retrieves Features data (specifically EMA20, EMA50, and timestamp) for a given asset_id and optional date range.
    """
    logger.info(f"Fetching features data for asset_id: {asset_id} (start: {start_date}, end: {end_date})")
    query = db.query(
        Features.timestamp,
        Features.ema_20,
        Features.ema_50,
        PriceData.close.label("price_at_signal") # Get close price from PriceData for the signal
    ).join(PriceData, (Features.asset_id == PriceData.asset_id) & (Features.timestamp == PriceData.timestamp))\
    .filter(Features.asset_id == asset_id)


    if start_date:
        query = query.filter(Features.timestamp >= start_date)
    if end_date:
        end_datetime = pd.to_datetime(end_date).replace(hour=23, minute=59, second=59, microsecond=999999)
        query = query.filter(Features.timestamp <= end_datetime)

    query = query.order_by(Features.timestamp.asc())

    feature_records = query.all()

    if not feature_records:
        logger.warning(f"No features data found for asset_id: {asset_id} in the given range.")
        return pd.DataFrame()

    df = pd.DataFrame(feature_records, columns=['timestamp', 'ema_20', 'ema_50', 'price_at_signal'])
    logger.info(f"Retrieved {len(df)} feature records for asset_id: {asset_id}.")
    return df

def generate_labels(features_df: pd.DataFrame) -> pd.DataFrame:
    """
    Generates BUY/SELL/HOLD labels based on EMA20 and EMA50.
    Input DataFrame must have 'ema_20' and 'ema_50' columns.
    """
    if features_df.empty or 'ema_20' not in features_df.columns or 'ema_50' not in features_df.columns:
        logger.warning("Features DataFrame is empty or missing EMA columns. Cannot generate labels.")
        return pd.DataFrame()

    labels = []
    for _, row in features_df.iterrows():
        if pd.isna(row['ema_20']) or pd.isna(row['ema_50']):
            labels.append(SignalType.HOLD) # Or skip/None if preferred for NA EMAs
        elif row['ema_20'] > row['ema_50']:
            labels.append(SignalType.BUY)
        elif row['ema_20'] < row['ema_50']:
            labels.append(SignalType.SELL)
        else:
            labels.append(SignalType.HOLD)

    features_df['signal_type'] = labels
    logger.info(f"Generated {len(labels)} labels. Counts: {features_df['signal_type'].value_counts().to_dict()}")
    return features_df

def save_labels_to_db(db: Session, asset_id: int, strategy_id: int, labels_df: pd.DataFrame, dry_run: bool = False):
    """
    Saves generated labels to the Signal table.
    """
    if labels_df.empty or 'signal_type' not in labels_df.columns or 'timestamp' not in labels_df.columns:
        logger.info("No labels to save or required columns missing.")
        return

    added_count = 0
    skipped_count = 0
    error_count = 0

    logger.info(f"Saving {len(labels_df)} labels for asset_id: {asset_id}, strategy_id: {strategy_id}.")

    for _, row in labels_df.iterrows():
        signal_type_enum = row['signal_type']
        if not isinstance(signal_type_enum, SignalType): # Ensure it's the enum type
            try:
                signal_type_enum = SignalType[str(row['signal_type']).upper()]
            except KeyError:
                logger.error(f"Invalid signal type value: {row['signal_type']}. Skipping.")
                error_count +=1
                continue

        price_at_signal = row.get('price_at_signal') # Get from DataFrame, might be None
        if pd.isna(price_at_signal):
            price_at_signal = None


        signal_data = {
            "asset_id": asset_id,
            "strategy_id": strategy_id,
            "timestamp": row['timestamp'],
            "signal_type": signal_type_enum,
            "price_at_signal": price_at_signal
            # 'confidence_score' and 'risk_score' could be added later
        }

        if dry_run:
            logger.info(f"[DRY RUN] Would save Signal: {signal_data}")
            added_count += 1
            continue

        # Check for existing signal to avoid duplicates
        try:
            existing_signal = db.query(Signal).filter_by(
                asset_id=asset_id,
                strategy_id=strategy_id,
                timestamp=row['timestamp']
            ).first()

            if existing_signal:
                # Optional: Update existing signal if logic changes, or just skip
                # For now, skip if exists
                skipped_count += 1
                continue
        except Exception as e_query:
            logger.error(f"Error querying existing Signal for asset {asset_id}, strategy {strategy_id} at {row['timestamp']}: {e_query}", exc_info=True)
            error_count += 1
            continue

        signal_entry = Signal(**signal_data)
        try:
            db.add(signal_entry)
            db.commit()
            added_count += 1
        except IntegrityError: # Should be caught by the check above
            db.rollback()
            logger.debug(f"Integrity error (likely duplicate) for signal. Asset: {asset_id}, Strat: {strategy_id}, TS: {row['timestamp']}. Skipping.")
            skipped_count += 1
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving signal for asset_id {asset_id}, strategy_id {strategy_id} at {row['timestamp']}: {e}", exc_info=True)
            error_count += 1

    log_prefix = "[DRY RUN] " if dry_run else ""
    logger.info(f"{log_prefix}Signal saving for asset_id {asset_id}, strategy_id {strategy_id} complete. "
                f"Added: {added_count}, Skipped (duplicates): {skipped_count}, Errors: {error_count}")

def main():
    parser = argparse.ArgumentParser(description="Generate BUY/SELL/HOLD labels based on EMA crossovers and save as Signals.")
    parser.add_argument("--symbol", type=str, required=True, help="Asset symbol (e.g., BTC-USD, AAPL).")
    parser.add_argument("--strategy_name", type=str, default=DEFAULT_STRATEGY_NAME,
                        help=f"Name of the labeling strategy to use/create (default: {DEFAULT_STRATEGY_NAME}).")
    parser.add_argument("--user_id", type=int, default=DEFAULT_USER_ID,
                        help=f"User ID to associate with the strategy (default: {DEFAULT_USER_ID}).")
    parser.add_argument("--start_date", type=str, default=None, help="Start date for processing (YYYY-MM-DD). Optional.")
    parser.add_argument("--end_date", type=str, default=None, help="End date for processing (YYYY-MM-DD). Optional.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate processing without writing to DB.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging (DEBUG level).")

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', stream=sys.stdout)
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
            logger.error(f"Asset with symbol '{args.symbol}' not found. Please ensure data is fetched and features are generated first.")
            return

        logger.info(f"Processing labels for asset: {asset.symbol} (ID: {asset.id})")

        # Get or Create Strategy
        strategy = get_or_create_strategy(db, args.strategy_name, args.user_id, args.dry_run)
        if not strategy or strategy.id is None: # strategy.id can be -1 in dry_run
            logger.error(f"Could not get or create strategy '{args.strategy_name}'. Cannot proceed.")
            return

        logger.info(f"Using strategy: {strategy.name} (ID: {strategy.id})")

        # Get Features data (EMA20, EMA50, timestamp)
        features_df = get_features_data(db, asset.id, args.start_date, args.end_date)
        if features_df.empty:
            logger.warning(f"No features data retrieved for {asset.symbol}. Cannot generate labels.")
            return

        # Generate Labels
        labels_df = generate_labels(features_df.copy())
        if labels_df.empty:
            logger.warning(f"No labels generated for {asset.symbol}.")
            return

        # Save Labels as Signals
        save_labels_to_db(db, asset.id, strategy.id, labels_df, args.dry_run)

    except Exception as e:
        logger.critical(f"A critical error occurred in the label generation pipeline: {e}", exc_info=True)
    finally:
        if db:
            db.close()
            logger.debug("Database session closed.")
        logger.info("Label generation script finished.")

if __name__ == "__main__":
    # Example Usage:
    # python ai_trader/label_generator.py --symbol BTC-USD --start_date 2023-01-01 --end_date 2023-12-31 --verbose
    # python ai_trader/label_generator.py --symbol AAPL --strategy_name MyEMALabels --dry-run
    main()
