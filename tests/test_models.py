import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, date

from ai_trader.db.base import Base
from ai_trader.models import User, Strategy, UserBehaviorLog, TradeAnalytics, MarketEvent

# Use an in-memory SQLite database for testing
DATABASE_URL = "sqlite:///:memory:"

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
