import os
import sys
import unittest
from datetime import datetime
from unittest.mock import ANY, MagicMock, patch

import pandas as pd

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_trader.services.label_generator import (generate_labels, get_features_data,
                                       get_or_create_strategy,
                                       save_labels_to_db)
from ai_trader.models import (Asset, Features, PriceData, Signal, SignalType,
                              Strategy, User)


class TestLabelGenerator(unittest.TestCase):

    def setUp(self):
        self.sample_features_df = pd.DataFrame({
            'timestamp': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05']),
            'ema_20': [10.0, 10.5, 10.2, 10.8, 11.0],
            'ema_50': [10.2, 10.4, 10.3, 10.7, 11.0], # SELL, BUY, SELL, BUY, HOLD
            'price_at_signal': [100.0, 101.0, 102.0, 103.0, 104.0] # Example prices
        })
        self.sample_features_df_with_na = pd.DataFrame({
            'timestamp': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03']),
            'ema_20': [10.0, None, 10.2], # EMA can be None/NaN at start
            'ema_50': [10.2, 10.4, 10.3],
            'price_at_signal': [100.0, 101.0, 102.0]
        })


    def test_generate_labels(self):
        """Test the core label generation logic."""
        labels_df = generate_labels(self.sample_features_df.copy())

        self.assertIn('signal_type', labels_df.columns)
        expected_signals = [SignalType.SELL, SignalType.BUY, SignalType.SELL, SignalType.BUY, SignalType.HOLD]
        self.assertListEqual(labels_df['signal_type'].tolist(), expected_signals)

    def test_generate_labels_with_na_emas(self):
        """Test label generation when EMAs can be NaN/None."""
        labels_df = generate_labels(self.sample_features_df_with_na.copy())

        self.assertIn('signal_type', labels_df.columns)
        # Expect HOLD if any EMA is NA, then normal logic
        expected_signals = [SignalType.SELL, SignalType.HOLD, SignalType.SELL]
        self.assertListEqual(labels_df['signal_type'].tolist(), expected_signals)

    @patch('ai_trader.label_generator.SessionLocal')
    def test_get_or_create_strategy_new(self, mock_session_local):
        """Test creating a new strategy."""
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session

        mock_strategy_query = MagicMock()
        mock_user_query = MagicMock()

        # Configure what session.query(Model) returns
        def query_side_effect(model_class):
            if model_class == Strategy:
                return mock_strategy_query
            if model_class == User:
                return mock_user_query
            return MagicMock() # Default for other models if any

        mock_session.query.side_effect = query_side_effect

        # Strategy not found
        mock_strategy_query.filter.return_value.first.return_value = None

        # User found
        mock_user_obj = User(id=1, username="testuser", email="t@e.com", hashed_password="pw")
        mock_user_query.filter.return_value.first.return_value = mock_user_obj

        # Mock the refresh to do nothing to the object itself for testing purposes
        mock_session.refresh = MagicMock()

        # Mock commit to assign an ID to the object passed to add
        # This simulates the database assigning an ID upon commit.
        def commit_side_effect_for_strategy():
            if mock_session.add.call_args:
                added_object = mock_session.add.call_args[0][0]
                if isinstance(added_object, Strategy):
                    added_object.id = 123 # Simulate DB assigning an ID
        mock_session.commit.side_effect = commit_side_effect_for_strategy

        created_strategy = get_or_create_strategy(mock_session, "TestStrat", user_id=1, dry_run=False)

        self.assertIsNotNone(created_strategy)
        self.assertIsInstance(created_strategy, Strategy, "Should be a Strategy instance")
        self.assertEqual(created_strategy.name, "TestStrat")
        self.assertEqual(created_strategy.id, 123)

        mock_session.add.assert_called_once()
        self.assertIsInstance(mock_session.add.call_args[0][0], Strategy)
        self.assertEqual(mock_session.add.call_args[0][0].name, "TestStrat")

        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(created_strategy)

    @patch('ai_trader.label_generator.SessionLocal')
    def test_get_or_create_strategy_existing(self, mock_session_local):
        """Test retrieving an existing strategy."""
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session

        mock_existing_strategy = Strategy(id=5, name="OldStrat", user_id=1)
        mock_session.query(Strategy).filter(Strategy.name == "OldStrat", Strategy.user_id == 1).first.return_value = mock_existing_strategy

        strategy = get_or_create_strategy(mock_session, "OldStrat", user_id=1, dry_run=False)

        self.assertEqual(strategy, mock_existing_strategy)
        mock_session.add.assert_not_called()

    @patch('ai_trader.label_generator.SessionLocal')
    def test_get_or_create_strategy_new_user_creation(self, mock_session_local):
        """Test creating a new strategy when the default user also needs to be created."""
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session

        # Simulate strategy not found
        mock_session.query(Strategy).filter(Strategy.name == "AutoUserStrat", Strategy.user_id == 1).first.return_value = None
        # Simulate user not found initially
        mock_session.query(User).filter(User.id == 1).first.return_value = None

        # This is a bit complex to mock perfectly without deeper session.get behavior or identity map
        # We'll check that add is called for user then for strategy

        # Side effect for commit: first commit is for user, second for strategy (simplified)
        def commit_side_effect():
            # After user commit, mock the user as existing for strategy creation part
            created_user = User(id=1, username="default_user_1", email="user1@example.com", hashed_password="!")
            mock_session.query(User).filter(User.id == 1).first.return_value = created_user
            return None

        mock_session.commit.side_effect = [commit_side_effect, None]


        strategy = get_or_create_strategy(mock_session, "AutoUserStrat", user_id=1, dry_run=False)

        self.assertIsNotNone(strategy)
        self.assertEqual(strategy.name, "AutoUserStrat")
        self.assertEqual(strategy.user_id, 1)

        # Check add calls: first for User, then for Strategy
        self.assertEqual(mock_session.add.call_count, 2)
        self.assertIsInstance(mock_session.add.call_args_list[0][0][0], User) # First add is User
        self.assertIsInstance(mock_session.add.call_args_list[1][0][0], Strategy) # Second add is Strategy
        self.assertEqual(mock_session.commit.call_count, 2)


    def test_save_labels_to_db_dry_run(self):
        """Test saving labels with dry_run=True."""
        mock_session = MagicMock()
        asset_id = 1
        strategy_id = 10

        labels_df = self.sample_features_df.copy() # Re-use df with EMAs
        labels_df = generate_labels(labels_df)     # Add signal_type column

        save_labels_to_db(mock_session, asset_id, strategy_id, labels_df, dry_run=True)

        mock_session.add.assert_not_called()
        mock_session.commit.assert_not_called()

    def test_save_labels_to_db_actual_save(self):
        """Test actual saving of labels (mocking DB)."""
        mock_session = MagicMock()
        # Simulate no existing signals
        mock_session.query(Signal).filter_by().first.return_value = None

        asset_id = 1
        strategy_id = 10

        labels_df = self.sample_features_df.copy()
        labels_df = generate_labels(labels_df)

        save_labels_to_db(mock_session, asset_id, strategy_id, labels_df, dry_run=False)

        self.assertEqual(mock_session.add.call_count, len(labels_df))
        self.assertEqual(mock_session.commit.call_count, len(labels_df))

        # Check the first added object's data
        first_added_signal_obj = mock_session.add.call_args_list[0][0][0]
        self.assertIsInstance(first_added_signal_obj, Signal)
        self.assertEqual(first_added_signal_obj.asset_id, asset_id)
        self.assertEqual(first_added_signal_obj.strategy_id, strategy_id)
        self.assertEqual(first_added_signal_obj.timestamp, self.sample_features_df['timestamp'].iloc[0])
        self.assertEqual(first_added_signal_obj.signal_type, SignalType.SELL)
        self.assertEqual(first_added_signal_obj.price_at_signal, self.sample_features_df['price_at_signal'].iloc[0])

    @patch('ai_trader.label_generator.SessionLocal')
    def test_get_features_data_structure(self, mock_session_local):
        """Test the structure of data returned by get_features_data."""
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session

        # Mock data returned by the query
        mock_query_results = [
            (datetime(2023, 1, 1, 0, 0, 0), 10.5, 10.2, 100.0), # timestamp, ema_20, ema_50, price_at_signal
            (datetime(2023, 1, 2, 0, 0, 0), 10.6, 10.3, 101.0),
        ]

        # More robust mocking for chained calls
        mock_query_chain = MagicMock()
        mock_session.query.return_value = mock_query_chain # query() returns an object
        mock_query_chain.join.return_value = mock_query_chain # join() returns the same object
        mock_query_chain.filter.return_value = mock_query_chain # filter() returns the same object
        mock_query_chain.order_by.return_value = mock_query_chain # order_by() returns the same object
        mock_query_chain.all.return_value = mock_query_results # all() returns the results

        asset_id = 1
        df = get_features_data(mock_session, asset_id, "2023-01-01", "2023-01-02")

        # Verify that session.query was called with the correct initial arguments
        # (Features.timestamp, Features.ema_20, Features.ema_50, PriceData.close.label("price_at_signal"))
        # This is a bit tricky because the arguments are SQLAlchemy constructs.
        # We can check the call count or a specific part of the arguments if needed,
        # but often, ensuring the chain leads to the correct .all() result is sufficient.
        mock_session.query.assert_called_once() # Check it was called
        # Example of checking part of the arguments (might be fragile):
        # self.assertEqual(mock_session.query.call_args[0][0], Features.timestamp) # Checks only the first arg

        mock_query_chain.join.assert_called_once() # Check join was called
        # Example: mock_query_chain.join.assert_called_with(PriceData, ANY) if you want to check specific join args

        # Check filter calls (usually there are multiple for asset_id, start_date, end_date)
        # For this test, 3 filter calls are expected (asset_id, start_date, end_date)
        # If start_date or end_date are None in some paths, the number of filter calls can change.
        # Here, both start_date and end_date are provided.
        num_expected_filters = 1 # For Features.asset_id == asset_id
        if "2023-01-01": num_expected_filters += 1
        if "2023-01-02": num_expected_filters += 1
        self.assertEqual(mock_query_chain.filter.call_count, num_expected_filters)

        mock_query_chain.order_by.assert_called_once()
        mock_query_chain.all.assert_called_once()

        self.assertFalse(df.empty)
        self.assertEqual(len(df), 2)
        expected_cols = ['timestamp', 'ema_20', 'ema_50', 'price_at_signal']
        self.assertListEqual(list(df.columns), expected_cols)
        self.assertEqual(df['ema_20'].iloc[0], 10.5)
        self.assertEqual(df['price_at_signal'].iloc[1], 101.0)


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
