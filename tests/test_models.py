import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from datetime import datetime, date

from ai_trader.models import (
    Base, User, Strategy, Asset, PriceData, Signal, Order, OrderStatus,
    OrderType, OrderSide, BacktestResult, Trade, TradeType, UserBehaviorLog,
    TradeAnalytics, MarketEvent
)

# Use an in-memory SQLite database for testing
DATABASE_URL = "sqlite:///:memory:"

# Enable foreign key support for SQLite in-memory for tests
from sqlalchemy import event
from sqlalchemy.engine import Engine
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def test_user(db_session):
    user = User(username="testuser", email="test@example.com", hashed_password="password")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture(scope="function")
def test_strategy(db_session, test_user):
    strategy = Strategy(name="Test Strategy", description="A test strategy", user_id=test_user.id)
    db_session.add(strategy)
    db_session.commit()
    db_session.refresh(strategy)
    return strategy

@pytest.fixture(scope="function")
def test_asset(db_session):
    asset = Asset(symbol="TESTBTC", name="Test Bitcoin")
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    return asset

@pytest.fixture(scope="function")
def test_order(db_session, test_user, test_asset, test_strategy):
    order = Order(
        user_id=test_user.id,
        asset_id=test_asset.id,
        strategy_id=test_strategy.id,
        order_type=OrderType.MARKET,
        order_side=OrderSide.BUY,
        status=OrderStatus.OPEN,
        quantity=1.0,
        price=50000.0
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    return order

@pytest.fixture(scope="function")
def test_trade(db_session, test_user, test_order):
    trade = Trade(
        user_id=test_user.id,
        order_id=test_order.id,
        symbol=test_order.asset.symbol, # Assuming asset symbol from order
        quantity=test_order.quantity,
        price=test_order.price,
        trade_type=TradeType.BUY # Assuming from order side
    )
    db_session.add(trade)
    db_session.commit()
    db_session.refresh(trade)
    return trade

@pytest.fixture(scope="function")
def test_signal(db_session, test_asset, test_strategy):
    from ai_trader.models import SignalType # Local import if not already at top
    signal = Signal(
        asset_id=test_asset.id,
        strategy_id=test_strategy.id,
        timestamp=datetime.now(), # Added timestamp
        signal_type=SignalType.BUY,
        price_at_signal=test_asset.price_data[0].close if test_asset.price_data else 50000.0 # Simplified
    )
    db_session.add(signal)
    db_session.commit()
    db_session.refresh(signal)
    return signal

@pytest.fixture(scope="function")
def test_backtest_result(db_session, test_strategy):
    backtest = BacktestResult(
        strategy_id=test_strategy.id,
        start_time=datetime.now(),
        end_time=datetime.now(),
        initial_capital=10000,
        final_capital=12000,
        total_profit=2000,
        total_trades=10,
        winning_trades=7,
        losing_trades=3,
        win_rate=0.7,
        max_drawdown=0.05
    )
    db_session.add(backtest)
    db_session.commit()
    db_session.refresh(backtest)
    return backtest

@pytest.fixture(scope="function")
def test_price_data(db_session, test_asset):
    price = PriceData(
        asset_id=test_asset.id,
        timestamp=datetime.now(),
        open=49000, high=51000, low=48000, close=50000, volume=100,
        source="test_source"
    )
    db_session.add(price)
    db_session.commit()
    db_session.refresh(price)
    return price


def test_create_user_behavior_log(db_session, test_user):
    log_data = {
        "user_id": test_user.id,
        "action_type": "view_chart",
        "session_id": "session123",
        "meta_data": {"symbol": "BTCUSD", "timeframe": "1h"}
    }
    log = UserBehaviorLog(**log_data)
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)

    assert log.id is not None
    assert log.user_id == test_user.id
    assert log.action_type == "view_chart"
    assert log.meta_data["symbol"] == "BTCUSD"
    assert log.user == test_user
    assert log in test_user.behavior_logs

def test_create_trade_analytics(db_session, test_user, test_strategy):
    analytics_data = {
        "user_id": test_user.id,
        "strategy_id": test_strategy.id,
        "total_trades": 100,
        "win_rate": 0.65,
        "total_pnl": 1250.75,
        "avg_risk_reward": 1.5,
        "max_drawdown": 0.15,
        "analysis_date": date(2023, 10, 26),
        "notes": "Initial analysis"
    }
    analytics = TradeAnalytics(**analytics_data)
    db_session.add(analytics)
    db_session.commit()
    db_session.refresh(analytics)

    assert analytics.id is not None
    assert analytics.user_id == test_user.id
    assert analytics.strategy_id == test_strategy.id
    assert analytics.total_trades == 100
    assert analytics.win_rate == 0.65
    assert analytics.user == test_user
    assert analytics.strategy == test_strategy
    assert analytics in test_user.trade_analytics
    assert analytics in test_strategy.trade_analytics


def test_create_market_event(db_session):
    event_data = {
        "event_type": "economic_data",
        "description": "CPI data release",
        "event_datetime": datetime.now(),
        "symbol": "USD",
        "impact_score": 0.8,
        "source": "Official Statistics Bureau",
        "meta_data": {"country": "USA", "actual": "3.7%", "forecast": "3.6%"}
    }
    event = MarketEvent(**event_data)
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)

    assert event.id is not None
    assert event.event_type == "economic_data"
    assert event.description == "CPI data release"
    assert event.meta_data["country"] == "USA"

def test_user_behavior_log_relationships(db_session, test_user):
    log1 = UserBehaviorLog(user_id=test_user.id, action_type="login", session_id="s1")
    log2 = UserBehaviorLog(user_id=test_user.id, action_type="view_chart", session_id="s1", meta_data={"symbol": "ETHUSD"})
    db_session.add_all([log1, log2])
    db_session.commit()

    retrieved_user = db_session.query(User).filter_by(id=test_user.id).one()
    assert len(retrieved_user.behavior_logs) == 2
    assert log1 in retrieved_user.behavior_logs
    assert log2 in retrieved_user.behavior_logs

def test_trade_analytics_relationships(db_session, test_user, test_strategy):
    analytics1 = TradeAnalytics(
        user_id=test_user.id, strategy_id=test_strategy.id,
        total_trades=10, win_rate=0.5, total_pnl=100, analysis_date=date.today()
    )
    analytics2 = TradeAnalytics(
        user_id=test_user.id, # Can have analytics not tied to a specific strategy
        total_trades=5, win_rate=0.8, total_pnl=200, analysis_date=date.today()
    )
    db_session.add_all([analytics1, analytics2])
    db_session.commit()

    retrieved_user = db_session.query(User).filter_by(id=test_user.id).one()
    retrieved_strategy = db_session.query(Strategy).filter_by(id=test_strategy.id).one()

    assert len(retrieved_user.trade_analytics) == 2
    assert analytics1 in retrieved_user.trade_analytics
    assert analytics2 in retrieved_user.trade_analytics

    assert len(retrieved_strategy.trade_analytics) == 1
    assert analytics1 in retrieved_strategy.trade_analytics
    assert analytics2 not in retrieved_strategy.trade_analytics # as it has no strategy_id linked to this strategy

def test_market_event_defaults(db_session):
    event = MarketEvent(event_type="news", description="Some news")
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)

    assert event.id is not None
    assert event.event_datetime is not None # Should have a default
    assert event.symbol is None
    assert event.impact_score is None
    assert event.source is None
    assert event.meta_data is None

# --- New tests for constraints and cascades ---

def test_strategy_unique_constraint_user_name(db_session, test_user):
    """Test UniqueConstraint on Strategy for user_id and name."""
    # First strategy (created by fixture is fine)
    strat1 = Strategy(name="MyAlgo1", user_id=test_user.id, description="First strategy")
    db_session.add(strat1)
    db_session.commit()

    # Attempt to create another strategy with the same name for the same user
    strat2_same_user_same_name = Strategy(name="MyAlgo1", user_id=test_user.id, description="Duplicate attempt")
    db_session.add(strat2_same_user_same_name)
    with pytest.raises(IntegrityError): # Should fail due to unique constraint
        db_session.commit()
    db_session.rollback()

    # Create another user
    user2 = User(username="testuser2", email="test2@example.com", hashed_password="password")
    db_session.add(user2)
    db_session.commit()

    # Strategy with the same name for a different user should be fine
    strat3_different_user_same_name = Strategy(name="MyAlgo1", user_id=user2.id, description="Different user, same name")
    db_session.add(strat3_different_user_same_name)
    db_session.commit() # Should not raise error
    assert strat3_different_user_same_name.id is not None

    # Strategy with different name for the same user should be fine
    strat4_same_user_different_name = Strategy(name="MyAlgo2", user_id=test_user.id, description="Same user, different name")
    db_session.add(strat4_same_user_different_name)
    db_session.commit() # Should not raise error
    assert strat4_same_user_different_name.id is not None


def test_user_deletion_cascades_and_set_null(db_session, test_user, test_strategy, test_order, test_trade, test_signal, test_backtest_result, test_price_data):
    """Test that deleting a User cascades correctly or sets FKs to NULL."""
    # test_strategy, test_order, etc., are already linked to test_user by fixtures
    # Additional items to ensure they are also handled
    log = UserBehaviorLog(user_id=test_user.id, action_type="test_action")
    analytics = TradeAnalytics(user_id=test_user.id, strategy_id=test_strategy.id, total_trades=1, win_rate=1, total_pnl=1, analysis_date=date.today())
    db_session.add_all([log, analytics])
    db_session.commit()

    user_id = test_user.id
    strategy_id = test_strategy.id
    order_id = test_order.id
    trade_id = test_trade.id
    log_id = log.id
    analytics_id = analytics.id
    # Capture IDs of related objects that will be cascade deleted through Strategy
    backtest_result_id = test_backtest_result.id
    signal_id = test_signal.id


    # Delete the user
    db_session.delete(test_user)
    db_session.commit()

    # Strategies linked to user should be deleted (CASCADE)
    assert db_session.get(Strategy, strategy_id) is None
    # Orders linked to user should have user_id set to NULL (SET NULL)
    order_after_delete = db_session.get(Order, order_id)
    assert order_after_delete is not None # Order itself is not deleted
    assert order_after_delete.user_id is None
    # Trades linked to user should be deleted (CASCADE)
    assert db_session.get(Trade, trade_id) is None
    # TradeAnalytics linked to user should be deleted (CASCADE)
    assert db_session.get(TradeAnalytics, analytics_id) is None
    # UserBehaviorLogs linked to user should be deleted (CASCADE)
    assert db_session.get(UserBehaviorLog, log_id) is None
    # BacktestResults are linked to Strategy, which is deleted, so they should also be gone
    assert db_session.get(BacktestResult, backtest_result_id) is None
    # Signals are linked to Strategy, which is deleted, so they should also be gone
    assert db_session.get(Signal, signal_id) is None


def test_strategy_deletion_cascades_and_set_null(db_session, test_strategy, test_order, test_signal, test_backtest_result):
    """Test that deleting a Strategy cascades correctly or sets FKs to NULL."""
    # test_order, test_signal, test_backtest_result are linked to test_strategy
    analytics = TradeAnalytics(user_id=test_strategy.user_id, strategy_id=test_strategy.id, total_trades=1, win_rate=1, total_pnl=1, analysis_date=date.today())
    db_session.add(analytics)
    db_session.commit()

    strategy_id = test_strategy.id
    order_id = test_order.id
    signal_id = test_signal.id
    backtest_id = test_backtest_result.id
    analytics_id = analytics.id

    # Delete the strategy
    db_session.delete(test_strategy)
    db_session.commit()

    # Orders linked to strategy should have strategy_id set to NULL (SET NULL)
    order_after_delete = db_session.get(Order, order_id)
    assert order_after_delete is not None
    assert order_after_delete.strategy_id is None
    # Signals linked to strategy should be deleted (CASCADE)
    assert db_session.get(Signal, signal_id) is None
    # BacktestResults linked to strategy should be deleted (CASCADE)
    assert db_session.get(BacktestResult, backtest_id) is None
    # TradeAnalytics linked to strategy should be deleted (CASCADE)
    assert db_session.get(TradeAnalytics, analytics_id) is None


def test_asset_deletion_cascades(db_session, test_asset, test_price_data, test_signal, test_order):
    """Test that deleting an Asset cascades correctly."""
    # test_price_data, test_signal, test_order are linked to test_asset
    asset_id = test_asset.id
    price_data_id = test_price_data.id
    signal_id = test_signal.id
    order_id = test_order.id # This order is also linked to user and strategy

    # Ensure signal is linked to this asset
    test_signal.asset_id = asset_id
    db_session.commit()


    # Delete the asset
    db_session.delete(test_asset)
    db_session.commit()

    # PriceData linked to asset should be deleted (CASCADE)
    assert db_session.get(PriceData, price_data_id) is None
    # Signals linked to asset should be deleted (CASCADE)
    assert db_session.get(Signal, signal_id) is None
    # Orders linked to asset should be deleted (CASCADE)
    # This implies that if an asset is deleted, any open or historical orders for it are also removed.
    assert db_session.get(Order, order_id) is None


def test_order_deletion_cascades(db_session, test_order, test_trade):
    """Test that deleting an Order cascades correctly."""
    # test_trade is linked to test_order
    order_id = test_order.id
    trade_id = test_trade.id

    # Delete the order
    db_session.delete(test_order)
    db_session.commit()

    # Trades linked to order should be deleted (CASCADE)
    assert db_session.get(Trade, trade_id) is None
