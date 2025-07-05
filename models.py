import enum
import datetime

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime,
    Enum as SQLAlchemyEnum, ForeignKey, Text, Index, JSON, Boolean
)
from sqlalchemy.orm import relationship, declarative_base


Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow
    )

    strategies = relationship("Strategy", back_populates="user")
    orders = relationship("Order", back_populates="user")


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)  # e.g., Bitcoin, Euro/USD
    asset_type = Column(String, nullable=True)  # e.g., CRYPTO, FOREX
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    price_data = relationship("PriceData", back_populates="asset")
    signals = relationship("Signal", back_populates="asset")
    orders = relationship("Order", back_populates="asset")
    # New relationships
    technical_indicators = relationship(
        "TechnicalIndicator", back_populates="asset"
    )
    target_labels = relationship("TargetLabel", back_populates="asset")


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    model_version = Column(String, nullable=True)
    parameters = Column(JSON, nullable=True)  # Store parameters as JSON
    api_key = Column(String, nullable=True)  # API key for the strategy
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow
    )

    user = relationship("User", back_populates="strategies")
    signals = relationship("Signal", back_populates="strategy")
    orders = relationship("Order", back_populates="strategy")
    backtest_results = relationship(
        "BacktestResult", back_populates="strategy"
    )


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
    # Relationship to indicators calculated from this price point
    indicators = relationship(
        "TechnicalIndicator", back_populates="price_data_point"
    )

    __table_args__ = (
        Index(
            "idx_asset_timestamp_source",
            "asset_id", "timestamp", "source", unique=True
        ),
        # Added for queries across assets by timestamp
        Index("idx_pricedata_timestamp", "timestamp")
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
    signal_type = Column(SQLAlchemyEnum(SignalType), nullable=False, index=True)
    confidence_score = Column(Float, nullable=True)  # Value between 0 and 1
    # Risk score associated with the signal
    risk_score = Column(Float, nullable=True)
    # Price when the signal was generated
    price_at_signal = Column(Float, nullable=True)

    asset = relationship("Asset", back_populates="signals")
    strategy = relationship("Strategy", back_populates="signals")

    __table_args__ = (
        Index(
            "idx_signal_asset_strategy_timestamp",
            "asset_id", "strategy_id", "timestamp"
        ),
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
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=True)

    order_type = Column(
        SQLAlchemyEnum(OrderType), nullable=False, default=OrderType.MARKET
    )
    order_side = Column(SQLAlchemyEnum(OrderSide), nullable=False)
    status = Column(
        SQLAlchemyEnum(OrderStatus),
        nullable=False,
        default=OrderStatus.PENDING,
        index=True
    )
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=True)
    filled_quantity = Column(Float, default=0.0)
    average_fill_price = Column(Float, nullable=True)
    commission = Column(Float, nullable=True)
    exchange_order_id = Column(String, nullable=True, index=True)
    is_simulated = Column(Boolean, default=True, nullable=False)

    pnl = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow
    )

    user = relationship("User", back_populates="orders")
    asset = relationship("Asset", back_populates="orders")
    strategy = relationship("Strategy", back_populates="orders")
    # signal = relationship("Signal", backref="order", uselist=False)
    # # If one signal leads to max one order

    __table_args__ = (
        Index(
            "idx_order_asset_strategy_created",
            "asset_id", "strategy_id", "created_at"
        ),
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
    win_rate = Column(Float, nullable=False)
    accuracy = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=False)
    sharpe_ratio = Column(Float, nullable=True)
    sortino_ratio = Column(Float, nullable=True)
    parameters_used = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    strategy = relationship("Strategy", back_populates="backtest_results")

    __table_args__ = (
        Index(
            "idx_backtest_strategy_created", "strategy_id", "created_at"
        ),
    )


# --- New Table: TechnicalIndicator ---
class TechnicalIndicator(Base):
    __tablename__ = "technical_indicators"

    id = Column(Integer, primary_key=True, index=True)
    price_data_id = Column(Integer, ForeignKey("price_data.id"), nullable=False)
    # For easier querying
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    # Should align with PriceData timestamp
    timestamp = Column(DateTime, nullable=False, index=True)

    # e.g., "RSI", "MACD_signal", "SMA_20"
    indicator_name = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    parameters = Column(JSON, nullable=True)

    # Relationships
    price_data_point = relationship("PriceData", back_populates="indicators")
    asset = relationship("Asset", back_populates="technical_indicators")

    __table_args__ = (
        Index(
            "idx_indicator_asset_timestamp_name",
            "asset_id", "timestamp", "indicator_name"
        ),
        # Ensures one unique indicator value per price point,
        # per indicator name and its parameters.
        # If parameters are stored as JSON, ensuring uniqueness with them
        # directly in a SQL index is tricky.
        # The unique constraint below assumes indicator_name itself is
        # unique for a given price_data_id.
        # If multiple indicators of the same name but different params can
        # exist for the same price_data_id, this unique constraint needs
        # adjustment or parameters should be part of the index in a
        # normalized way (e.g. parameter_hash).
        Index(
            "idx_indicator_price_data_id_name",
            "price_data_id",
            "indicator_name",
            unique=True
        ),
    )


# --- New Enum and Table: TargetLabel ---
class TargetLabelType(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    # STRONG_BUY = "STRONG_BUY"  # Example of extension


class TargetLabel(Base):
    __tablename__ = "target_labels"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    # Timestamp of the market data point this label is for
    timestamp = Column(DateTime, nullable=False)

    label = Column(SQLAlchemyEnum(TargetLabelType), nullable=False)
    # Optional: details about how the label was generated
    # label_horizon = Column(String, nullable=True)  # e.g., "1h", "4h"
    # label_generation_method = Column(String, nullable=True)
    # # e.g., "price_increase_5percent"

    asset = relationship("Asset", back_populates="target_labels")

    __table_args__ = (
        # One label per asset per timestamp
        Index(
            "idx_label_asset_timestamp",
            "asset_id",
            "timestamp",
            unique=True
        ),
    )


# Example of how to create the tables in a database
if __name__ == "__main__":
    import os
    # Default to SQLite if DATABASE_URL is not set,
    # facilitating easy local setup.
    # For production or other environments, set DATABASE_URL env variable.
    # Example: postgresql://user:password@host:port/database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ai_trader_v2.db")
    engine = create_engine(DATABASE_URL)

    print(f"Attempting to create database tables using URL: {DATABASE_URL}")
    try:
        Base.metadata.create_all(bind=engine)
        print("Database tables created/verified successfully.")
    except Exception as e:
        print(f"Error creating database tables: {e}")
        # Consider more specific error handling or logging here
