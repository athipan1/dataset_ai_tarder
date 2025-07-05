# As the project grows, consider splitting these models into multiple files
# under a dedicated `models/` directory for better organization and modularity.
# For example:
# - models/base.py (for Base and common elements)
# - models/user_models.py (for User)
# - models/market_data_models.py (for Asset, PriceData)
# - models/trading_models.py (for Strategy, Signal, Order, BacktestResult)

import enum
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Enum, ForeignKey, Text, Index, JSON
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    strategies = relationship("Strategy", back_populates="user")
    orders = relationship("Order", back_populates="user")


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True, nullable=False)  # e.g., BTC, ETH, EURUSD
    name = Column(String, nullable=True)  # e.g., Bitcoin, Ethereum, Euro/US Dollar
    asset_type = Column(String, nullable=True)  # e.g., CRYPTO, FOREX, STOCK
    created_at = Column(DateTime, default=func.now())

    price_data = relationship("PriceData", back_populates="asset")
    signals = relationship("Signal", back_populates="asset")
    orders = relationship("Order", back_populates="asset")


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    model_version = Column(String, nullable=True)
    parameters = Column(JSON, nullable=True)  # Store parameters as JSON
    # TODO: Storing API keys in plaintext is insecure.
    # Consider using environment variables, a secret management service, or encryption.
    api_key = Column(String, nullable=True)  # API key for the strategy
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Optional: if strategies are user-specific
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="strategies")
    signals = relationship("Signal", back_populates="strategy")
    orders = relationship("Order", back_populates="strategy")
    backtest_results = relationship("BacktestResult", back_populates="strategy")


class PriceData(Base):
    __tablename__ = "price_data"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    source = Column(String, nullable=False)

    asset = relationship("Asset", back_populates="price_data")

    __table_args__ = (
        Index("idx_asset_timestamp_source", "asset_id", "timestamp", "source", unique=True),
    )


class SignalType(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    signal_type = Column(Enum(SignalType), nullable=False, index=True)
    confidence_score = Column(Float, nullable=True)  # Value between 0 and 1
    risk_score = Column(Float, nullable=True)  # Risk score associated with the signal
    price_at_signal = Column(Float, nullable=True)  # Price when the signal was generated

    asset = relationship("Asset", back_populates="signals")
    strategy = relationship("Strategy", back_populates="signals")

    __table_args__ = (
        Index("idx_signal_asset_strategy_timestamp", "asset_id", "strategy_id", "timestamp"),
    )


class OrderStatus(enum.Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class OrderType(enum.Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"


class OrderSide(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Optional: if orders are user-specific
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=True)  # Strategy that triggered this order
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=True)  # Signal that triggered this order

    order_type = Column(Enum(OrderType), nullable=False, default=OrderType.MARKET)
    order_side = Column(Enum(OrderSide), nullable=False)
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING, index=True)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=True)  # Entry price for limit/stop orders, fill price for market orders
    filled_quantity = Column(Float, default=0.0)
    average_fill_price = Column(Float, nullable=True)
    commission = Column(Float, nullable=True)
    exchange_order_id = Column(String, nullable=True, index=True)  # ID from the exchange, if applicable
    is_simulated = Column(Integer, default=1, nullable=False)  # 0 for real, 1 for simulated/paper trading

    created_at = Column(DateTime, default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="orders")
    asset = relationship("Asset", back_populates="orders")
    strategy = relationship("Strategy", back_populates="orders")
    # A direct relationship to signal might be useful if an order is directly created from a signal
    # signal = relationship("Signal", back_populates="orders")  # If one signal can lead to one order

    __table_args__ = (
        Index("idx_order_asset_strategy_created", "asset_id", "strategy_id", "created_at"),
    )


class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    initial_capital = Column(Float, nullable=False)
    final_capital = Column(Float, nullable=False)
    total_profit = Column(Float, nullable=False)
    total_trades = Column(Integer, nullable=False)
    winning_trades = Column(Integer, nullable=False)
    losing_trades = Column(Integer, nullable=False)
    win_rate = Column(Float, nullable=False)  # winning_trades / total_trades
    accuracy = Column(Float, nullable=True)  # Accuracy of the strategy
    max_drawdown = Column(Float, nullable=False)
    sharpe_ratio = Column(Float, nullable=True)
    sortino_ratio = Column(Float, nullable=True)
    # Other relevant metrics
    # e.g., profit_factor, average_win, average_loss, etc.
    parameters_used = Column(Text, nullable=True)  # JSON string of parameters for this specific backtest run
    created_at = Column(DateTime, default=func.now())

    strategy = relationship("Strategy", back_populates="backtest_results")

    __table_args__ = (
        Index("idx_backtest_strategy_created", "strategy_id", "created_at"),
    )


# Example of how to create the tables in a database (e.g., SQLite for local dev)
if __name__ == "__main__":
    # For SQLite, the file will be created in the same directory
    engine = create_engine("sqlite:///./ai_trader.db")
    # For PostgreSQL, an example connection string would be:
    # DB_USER = "your_postgres_user"
    # DB_PASSWORD = "your_postgres_password"
    # DB_HOST = "localhost"  # or your DB host
    # DB_PORT = "5432"       # default PostgreSQL port
    # DB_NAME = "ai_trader_db"
    # POSTGRES_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    # engine = create_engine(POSTGRES_URL)

    # For production or larger projects, consider using a database migration tool like Alembic
    # to manage schema changes systematically.
    # e.g., alembic revision -m "create_initial_tables"
    #       alembic upgrade head
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")
