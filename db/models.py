import enum
import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Enum as SAEnum, ForeignKey, Text, Index, JSON, TIMESTAMP
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

# --- Enum Definitions (from existing models) ---
class SignalType(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

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

# --- Models based on user request and existing models ---

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    role = Column(String(20)) # As per user request
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    strategies = relationship("StrategyConfig", back_populates="user")
    trade_logs = relationship("TradeLog", back_populates="user")
    audit_logs_performed = relationship("AuditLog", back_populates="performed_by_user")


class MarketData(Base):
    __tablename__ = "market_data"
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    exchange = Column(String(20), nullable=False)
    datetime = Column(TIMESTAMP, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)

    __table_args__ = (
        Index("idx_marketdata_symbol_exchange_datetime", "symbol", "exchange", "datetime", unique=True),
        Index("idx_marketdata_symbol_datetime", "symbol", "datetime"), # Suggested by user
    )

class Features(Base):
    __tablename__ = "features"
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    feature_name = Column(String(50), nullable=False)
    value = Column(Float)
    datetime = Column(TIMESTAMP, nullable=False)

    __table_args__ = (
        Index("idx_features_symbol_feature_datetime", "symbol", "feature_name", "datetime", unique=True),
    )

class TradeLog(Base):
    __tablename__ = "trade_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    open_time = Column(TIMESTAMP, nullable=False)
    close_time = Column(TIMESTAMP)
    side = Column(String(10), nullable=False)
    qty = Column(Float, nullable=False)
    open_price = Column(Float, nullable=False)
    close_price = Column(Float)
    profit = Column(Float)
    status = Column(String(20))
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="trade_logs")

class ModelLog(Base):
    __tablename__ = "model_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String(50), nullable=False)
    params = Column(Text)
    metric = Column(Float)
    path = Column(Text)
    created_at = Column(TIMESTAMP, default=datetime.datetime.utcnow)

class StrategyConfig(Base):
    __tablename__ = "strategy_configs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), index=True, nullable=False)
    config = Column(Text)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User", back_populates="strategies")
    signals = relationship("Signal", back_populates="strategy_config")
    backtest_results = relationship("BacktestResult", back_populates="strategy_config")

class BacktestResult(Base):
    __tablename__ = "backtest_results"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    strategy_id = Column(Integer, ForeignKey("strategy_configs.id"), nullable=False)
    result = Column(Text)
    created_at = Column(TIMESTAMP, default=datetime.datetime.utcnow)

    strategy_config = relationship("StrategyConfig", back_populates="backtest_results")
    __table_args__ = (
        Index("idx_backtest_strategy_created", "strategy_id", "created_at"),
    )

class ErrorLog(Base):
    __tablename__ = "error_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    error_msg = Column(Text)
    traceback = Column(Text)
    created_at = Column(TIMESTAMP, default=datetime.datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String(50))
    detail = Column(Text)
    performed_by = Column(Integer, ForeignKey("users.id"))
    performed_at = Column(TIMESTAMP, default=datetime.datetime.utcnow)

    performed_by_user = relationship("User", back_populates="audit_logs_performed")

class Asset(Base):
    __tablename__ = "assets"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    asset_type = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    signals = relationship("Signal", back_populates="asset")

class Signal(Base):
    __tablename__ = "signals"
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    strategy_id = Column(Integer, ForeignKey("strategy_configs.id"), nullable=False) # Corrected FK
    timestamp = Column(DateTime, nullable=False, index=True)
    signal_type = Column(SAEnum(SignalType), nullable=False, index=True) # Corrected Enum to SAEnum
    confidence_score = Column(Float, nullable=True)
    risk_score = Column(Float, nullable=True)
    price_at_signal = Column(Float, nullable=True)

    asset = relationship("Asset", back_populates="signals")
    strategy_config = relationship("StrategyConfig", back_populates="signals") # Corrected relationship name

    __table_args__ = (
        Index("idx_signal_asset_strategy_timestamp", "asset_id", "strategy_id", "timestamp"),
    )
