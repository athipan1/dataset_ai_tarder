import os
import sys
import unittest
from datetime import datetime, timezone  # Added timezone
from unittest.mock import MagicMock, patch

import pandas as pd

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_trader.models import Asset, PriceData

# Important: The script to be tested should be imported AFTER sys.path is modified,
# if it relies on project-level imports and is not installed as a package.
# However, for scripts, it's common to test their functions directly.
from scripts.fetch_price_data import (
    fetch_yfinance_data,
    get_or_create_asset,
    save_data_to_db,
)


class TestFetchPriceData(unittest.TestCase):

    def setUp(self):
        # This specific setUp is not strictly necessary if tests define their own mock data,
        # but can be kept if multiple tests use the exact same sample_yf_data structure.
        # For the failing test, the mock return is defined inside the test method.
        pass

    @patch("scripts.fetch_price_data.yf.Ticker")
    def test_fetch_yfinance_data_success(self, mock_ticker_constructor):
        """Test successful data fetching from yfinance."""
        # Sample DataFrame that yfinance.Ticker().history() would return (Datetime as index)
        raw_yf_output = pd.DataFrame(
            {
                "Open": [100, 101, 102],
                "High": [105, 106, 107],
                "Low": [99, 100, 101],
                "Close": [102, 103, 104],
                "Volume": [1000, 1100, 1200],
            },
            index=pd.to_datetime(
                [
                    datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                    datetime(2023, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
                    datetime(2023, 1, 3, 0, 0, 0, tzinfo=timezone.utc),
                ]
            ),
        )
        raw_yf_output.index.name = "Datetime"  # yfinance typically names this index

        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = (
            raw_yf_output  # Return with Datetime as index
        )
        mock_ticker_constructor.return_value = mock_ticker_instance

        symbol = "TEST.SA"
        start_date = "2023-01-01"
        end_date = (
            "2023-01-03"  # yfinance end is exclusive for daily, so script adds 1 day
        )

        # Expected end_date for yf.Ticker().history call
        expected_yf_end_date = (
            datetime.strptime(end_date, "%Y-%m-%d") + pd.Timedelta(days=1)
        ).strftime("%Y-%m-%d")

        df = fetch_yfinance_data(
            symbol, start_date=start_date, end_date=end_date, interval="1d"
        )

        mock_ticker_constructor.assert_called_once_with(symbol)
        mock_ticker_instance.history.assert_called_once_with(
            start=start_date, end=expected_yf_end_date, interval="1d"
        )

        self.assertFalse(df.empty)
        self.assertEqual(len(df), 3)
        self.assertListEqual(
            list(df.columns), ["Datetime", "Open", "High", "Low", "Close", "Volume"]
        )
        # Check if Datetime column is naive (as it should be after processing)
        self.assertTrue(df["Datetime"].dt.tz is None)

    @patch("scripts.fetch_price_data.yf.Ticker")
    def test_fetch_yfinance_data_empty(self, mock_ticker_constructor):
        """Test yfinance returning empty data."""
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = pd.DataFrame()  # Empty data
        mock_ticker_constructor.return_value = mock_ticker_instance

        df = fetch_yfinance_data(
            "FAIL.SA", start_date="2023-01-01", end_date="2023-01-03", interval="1d"
        )
        self.assertTrue(df.empty)

    @patch("scripts.fetch_price_data.yf.Ticker")
    def test_fetch_yfinance_data_api_error(self, mock_ticker_constructor):
        """Test yfinance raising an exception."""
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.side_effect = Exception("API Error")
        mock_ticker_constructor.return_value = mock_ticker_instance

        df = fetch_yfinance_data(
            "ERROR.SA", start_date="2023-01-01", end_date="2023-01-03", interval="1d"
        )
        self.assertTrue(df.empty)

    def test_get_or_create_asset_new(self):
        """Test creating a new asset."""
        mock_session = MagicMock()
        mock_session.query(Asset).filter(
            Asset.symbol == "NEWCO"
        ).first.return_value = None  # Simulate asset not found

        asset = get_or_create_asset(mock_session, "NEWCO", "Stock", dry_run=False)

        self.assertIsNotNone(asset)
        self.assertEqual(asset.symbol, "NEWCO")
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(asset)

    def test_get_or_create_asset_existing(self):
        """Test retrieving an existing asset."""
        mock_existing_asset = Asset(
            id=1, symbol="OLDCO", name="OLDCO", asset_type="Stock"
        )
        mock_session = MagicMock()
        mock_session.query(Asset).filter(
            Asset.symbol == "OLDCO"
        ).first.return_value = mock_existing_asset

        asset = get_or_create_asset(mock_session, "OLDCO", "Stock", dry_run=False)

        self.assertEqual(asset, mock_existing_asset)
        mock_session.add.assert_not_called()
        mock_session.commit.assert_not_called()

    def test_get_or_create_asset_dry_run_new(self):
        """Test creating a new asset with dry_run."""
        mock_session = MagicMock()
        mock_session.query(Asset).filter(
            Asset.symbol == "DRYNEW"
        ).first.return_value = None

        asset = get_or_create_asset(mock_session, "DRYNEW", "Crypto", dry_run=True)

        self.assertIsNotNone(asset)
        self.assertEqual(asset.symbol, "DRYNEW")
        self.assertEqual(asset.id, -1)  # Placeholder ID for dry run
        mock_session.add.assert_not_called()
        mock_session.commit.assert_not_called()

    def test_save_data_to_db(self):
        """Test saving data to DB."""
        mock_session = MagicMock()
        # Simulate no existing data for these timestamps
        mock_session.query(PriceData).filter_by(
            asset_id=1, timestamp=pd.to_datetime("2023-01-01"), source="TestLSource"
        ).first.return_value = None
        mock_session.query(PriceData).filter_by(
            asset_id=1, timestamp=pd.to_datetime("2023-01-02"), source="TestSource"
        ).first.return_value = None

        test_asset = Asset(id=1, symbol="TESTDB", name="TestDB Asset")
        data_to_save = pd.DataFrame(
            {
                "Open": [100, 101],
                "High": [102, 103],
                "Low": [99, 100],
                "Close": [101, 102],
                "Volume": [1000, 1100],
                "Datetime": pd.to_datetime(
                    ["2023-01-01", "2023-01-02"]
                ),  # Naive, as expected after fetch processing
            }
        )

        save_data_to_db(
            mock_session, data_to_save, test_asset, "TestSource", dry_run=False
        )

        self.assertEqual(mock_session.add.call_count, 2)
        self.assertEqual(mock_session.commit.call_count, 2)

        # Check that PriceData objects were constructed correctly for add()
        first_call_args = mock_session.add.call_args_list[0][0][0]
        self.assertEqual(first_call_args.asset_id, 1)
        self.assertEqual(first_call_args.timestamp, pd.to_datetime("2023-01-01"))
        self.assertEqual(first_call_args.close, 101)

    def test_save_data_to_db_dry_run(self):
        """Test saving data to DB with dry_run."""
        mock_session = (
            MagicMock()
        )  # Session won't be used for DB ops in dry_run for PriceData
        test_asset = Asset(id=1, symbol="TESTDRYDB", name="TestDryDB Asset")
        # For dry_run, asset_id can be -1 if asset was 'created' in dry_run
        test_asset_dry_created = Asset(id=-1, symbol="NEWDRY", name="NewDry Asset")

        data_to_save = pd.DataFrame(
            {
                "Open": [100],
                "High": [102],
                "Low": [99],
                "Close": [101],
                "Volume": [1000],
                "Datetime": pd.to_datetime(["2023-01-01"]),
            }
        )

        save_data_to_db(
            mock_session,
            data_to_save,
            test_asset_dry_created,
            "TestSourceDry",
            dry_run=True,
        )

        mock_session.add.assert_not_called()
        mock_session.commit.assert_not_called()
        # Add more assertions here if there are specific log messages for dry run to check

    def test_save_data_to_db_skip_existing(self):
        """Test that existing data points are skipped."""
        mock_session = MagicMock()
        existing_pd_entry = PriceData(
            asset_id=1,
            timestamp=pd.to_datetime("2023-01-01"),
            source="TestSource",
            open=1,
            high=1,
            low=1,
            close=1,
            volume=1,
        )

        # Simulate first entry exists, second does not
        def query_side_effect(*args, **kwargs):
            filter_args = kwargs["asset_id"], kwargs["timestamp"], kwargs["source"]
            if filter_args == (1, pd.to_datetime("2023-01-01"), "TestSource"):
                return MagicMock(first=MagicMock(return_value=existing_pd_entry))
            elif filter_args == (1, pd.to_datetime("2023-01-02"), "TestSource"):
                return MagicMock(first=MagicMock(return_value=None))
            return MagicMock(first=MagicMock(return_value=None))

        mock_session.query(PriceData).filter_by.side_effect = query_side_effect

        test_asset = Asset(id=1, symbol="TESTSKIP", name="TestSkip Asset")
        data_to_save = pd.DataFrame(
            {
                "Datetime": pd.to_datetime(["2023-01-01", "2023-01-02"]),
                "Open": [100, 101],
                "High": [102, 103],
                "Low": [99, 100],
                "Close": [101, 102],
                "Volume": [1000, 1100],
            }
        )

        save_data_to_db(
            mock_session, data_to_save, test_asset, "TestSource", dry_run=False
        )

        # Should only add the second entry
        self.assertEqual(mock_session.add.call_count, 1)
        self.assertEqual(mock_session.commit.call_count, 1)
        added_entry_args = mock_session.add.call_args[0][0]
        self.assertEqual(added_entry_args.timestamp, pd.to_datetime("2023-01-02"))


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
