import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np # For NaN comparison if needed, and for creating test data
from datetime import datetime
import os
import sys

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_trader.data_pipeline import calculate_features, get_price_data, save_features_to_db
from ai_trader.models import Asset, PriceData, Features # Assuming these are needed for context or deeper tests

class TestDataPipeline(unittest.TestCase):

    def setUp(self):
        # Sample PriceData DataFrame for testing feature calculation - increased size for longer period indicators
        num_records = 100 # Ensure enough data for SMA50, MACD etc.
        start_date = datetime(2023, 1, 1)
        timestamps = [start_date + pd.Timedelta(days=i) for i in range(num_records)]

        # Simple cyclical data for close prices to generate some indicator movement
        close_prices = [10 + (i % 10) + np.sin(i/5)*2 for i in range(num_records)]

        self.sample_price_df = pd.DataFrame({
            'timestamp': pd.to_datetime(timestamps),
            'open':  [p - 0.5 for p in close_prices],
            'high':  [p + 1 for p in close_prices],
            'low':   [p - 1 for p in close_prices],
            'close': close_prices,
            'volume': [100 + i * 10 for i in range(num_records)]
        })
        # Set timestamp as index for pandas_ta (which it prefers),
        # but also keep 'timestamp' as a column because that's what get_price_data provides to calculate_features
        self.sample_price_df.set_index('timestamp', inplace=True, drop=False)


    def test_calculate_features_rsi(self):
        """Test RSI calculation."""
        # For RSI, we need enough data points (typically period + lookback for smoothing)
        # pandas-ta default RSI length is 14.
        # The first 14 RSI values will be NaN.

        df_copy = self.sample_price_df.copy()
        features_df = calculate_features(df_copy)

        self.assertIn('rsi_14', features_df.columns)

        # Check that the first 14 RSI values are NaN (or None after potential fillna)
        # Note: calculate_features itself doesn't do fillna(None) but save_features_to_db does for row processing
        # So, here we check for pd.NA or np.nan if we expect them from pandas_ta
        self.assertTrue(features_df['rsi_14'].iloc[:14].isna().all())

        # Check a known RSI value if possible, or just that non-NaN values are calculated
        # Calculating exact RSI by hand is tedious and prone to small diffs due to EMA smoothing methods (Wilder's vs regular EMA)
        # For this test, we'll ensure that after the initial NaN period, we get numbers.
        self.assertFalse(features_df['rsi_14'].iloc[14:].isna().any(),
                         f"Expected non-NaN RSI values after initial period. Got: \n{features_df['rsi_14']}")

        # Check if other expected columns are present
        expected_cols = ['sma_20', 'ema_20', 'macd_line', 'atr_14', 'bb_middleband']
        for col in expected_cols:
            self.assertIn(col, features_df.columns, f"Expected column {col} not found.")

        self.assertIn('timestamp', features_df.columns, "Timestamp column should be preserved.")

    def test_calculate_features_all_present(self):
        """Test that all requested features are calculated and columns are named correctly."""
        df_copy = self.sample_price_df.copy()
        features_df = calculate_features(df_copy)

        expected_feature_model_columns = [
            'rsi_14', 'sma_20', 'sma_50', 'ema_20', 'ema_50',
            'macd_line', 'macd_signal', 'macd_hist', 'atr_14',
            'bb_upperband', 'bb_middleband', 'bb_lowerband'
        ]
        for col in expected_feature_model_columns:
            self.assertIn(col, features_df.columns, f"Model column {col} is missing from calculated features.")

        self.assertIn('timestamp', features_df.columns)


    @patch('ai_trader.data_pipeline.SessionLocal')
    def test_get_price_data(self, mock_session_local):
        """Test fetching price data from the database."""
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session

        mock_records = [
            PriceData(asset_id=1, timestamp=datetime(2023,1,1), open=10, high=11, low=9, close=10.5, volume=100, source="test"),
            PriceData(asset_id=1, timestamp=datetime(2023,1,2), open=10.5, high=11.5, low=10, close=11, volume=110, source="test")
        ]

        # Setup the mock query object that will be returned by session.query(PriceData)
        mock_price_data_query = MagicMock()

        # Ensure chained calls return the mock_price_data_query object itself
        mock_price_data_query.filter.return_value = mock_price_data_query
        mock_price_data_query.order_by.return_value = mock_price_data_query
        mock_price_data_query.all.return_value = mock_records # This is what all() should return

        # Ensure that session.query(PriceData) returns our configured mock_price_data_query
        def query_side_effect(model_class):
            if model_class == PriceData:
                return mock_price_data_query
            # Fallback for other queries if any, though this test focuses on PriceData
            return MagicMock(filter=MagicMock(return_value=MagicMock(order_by=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))))

        mock_session.query.side_effect = query_side_effect

        df = get_price_data(mock_session, asset_id=1, start_date="2023-01-01", end_date="2023-01-02")

        mock_session.query.assert_called_with(PriceData)
        # Example: Check that filter was called (at least once for asset_id)
        mock_price_data_query.filter.assert_called()
        mock_price_data_query.order_by.assert_called_once()
        mock_price_data_query.all.assert_called_once()

        self.assertEqual(len(df), 2)
        self.assertListEqual(list(df.columns), ['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        self.assertEqual(df['close'].iloc[0], 10.5)
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(df['timestamp']))
        # Crucially, check set_index worked by verifying the index
        self.assertEqual(df.index.name, 'timestamp')
        self.assertEqual(df.index[0], pd.to_datetime(datetime(2023,1,1)))


    def test_save_features_to_db_dry_run(self):
        """Test saving features with dry_run=True."""
        mock_session = MagicMock()
        asset_id = 1
        # Sample features_df (output from calculate_features)
        features_data = {
            'timestamp': pd.to_datetime(['2023-01-15', '2023-01-16']), # After initial NaN period for most indicators
            'rsi_14': [50.0, 52.0],
            'sma_20': [13.0, 13.5],
            'ema_20': [13.2, 13.3],
            # ... other features ...
        }
        # Ensure all model columns are present, even if with None/NaN
        all_model_cols = ['rsi_14', 'sma_20', 'sma_50', 'ema_20', 'ema_50', 'macd_line', 'macd_signal', 'macd_hist', 'atr_14', 'bb_upperband', 'bb_middleband', 'bb_lowerband']
        for col in all_model_cols:
            if col not in features_data:
                features_data[col] = [np.nan, np.nan] # Use np.nan as pandas_ta would

        sample_features_df = pd.DataFrame(features_data)

        save_features_to_db(mock_session, asset_id, sample_features_df, dry_run=True)

        mock_session.add.assert_not_called()
        mock_session.commit.assert_not_called()

    def test_save_features_to_db_actual_save(self):
        """Test actual saving of features (mocking DB interaction)."""
        mock_session = MagicMock()
        # Simulate no existing features
        mock_session.query(Features).filter_by().first.return_value = None

        asset_id = 1
        ts1 = pd.to_datetime('2023-01-15 00:00:00')
        ts2 = pd.to_datetime('2023-01-16 00:00:00')

        features_data = {
            'timestamp': [ts1, ts2],
            'rsi_14': [50.0, 52.0], 'sma_20': [13.0, 13.5], 'sma_50': [12.0, 12.5],
            'ema_20': [13.2, 13.3], 'ema_50': [12.2, 12.3],
            'macd_line': [0.5, 0.6], 'macd_signal': [0.4, 0.45], 'macd_hist': [0.1, 0.15],
            'atr_14': [1.0, 1.1],
            'bb_upperband': [15.0, 15.5], 'bb_middleband': [13.0, 13.5], 'bb_lowerband': [11.0, 11.5]
        }
        sample_features_df = pd.DataFrame(features_data)

        save_features_to_db(mock_session, asset_id, sample_features_df, dry_run=False)

        self.assertEqual(mock_session.add.call_count, 2)
        self.assertEqual(mock_session.commit.call_count, 2)

        # Check the first added object's data
        first_added_feature_obj = mock_session.add.call_args_list[0][0][0]
        self.assertIsInstance(first_added_feature_obj, Features)
        self.assertEqual(first_added_feature_obj.asset_id, asset_id)
        self.assertEqual(first_added_feature_obj.timestamp, ts1)
        self.assertEqual(first_added_feature_obj.rsi_14, 50.0)
        self.assertEqual(first_added_feature_obj.sma_20, 13.0)


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
