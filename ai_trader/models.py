import datetime
import enum
from typing import List, Optional

from sqlalchemy import JSON, Boolean, Column, Date, DateTime
from sqlalchemy import Enum as DBEnum
from sqlalchemy import (Float, ForeignKey, Index, Integer, Numeric, String,
                        Text, UniqueConstraint, create_engine)
from sqlalchemy.orm import (Mapped, declarative_base, mapped_column,
                            relationship)
from sqlalchemy.sql import func

Base = declarative_base()

class SoftDeleteMixin:
    """A mixin to add soft delete functionality to models."""
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    deleted_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True, index=True)

    def soft_delete(self, session):
        """Marks the instance as deleted and cascades the soft delete to related models."""
        if self.is_deleted:
            return
        self.is_deleted = True
        self.deleted_at = datetime.datetime.now(datetime.timezone.utc)
        if self not in session:
            session.add(self)

        # Cascade soft delete
        for relationship_name in self.__mapper__.relationships.keys():
            related_items = getattr(self, relationship_name)
            if related_items:
                if isinstance(related_items, list):
                    for item in related_items:
                        if isinstance(item, SoftDeleteMixin) and not item.is_deleted:
                            item.soft_delete(session)
                elif isinstance(related_items, SoftDeleteMixin) and not related_items.is_deleted:
                    related_items.soft_delete(session)

# --- Enums ---
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

class TradeType(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


# --- Models ---
class User(SoftDeleteMixin, Base):
    """Represents a user of the system."""
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    strategies: Mapped[List["Strategy"]] = relationship("Strategy", back_populates="user", passive_deletes=True)
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="user")
    behavior_logs: Mapped[List["UserBehaviorLog"]] = relationship("UserBehaviorLog", back_populates="user", passive_deletes=True)
    trade_analytics: Mapped[List["TradeAnalytics"]] = relationship("TradeAnalytics", back_populates="user", passive_deletes=True)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"

class Asset(Base):
    """Represents a financial asset."""
    __tablename__ = "assets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String)
    asset_type: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())

    price_data: Mapped[List["PriceData"]] = relationship("PriceData", back_populates="asset", cascade="all, delete", lazy="dynamic")
    signals: Mapped[List["Signal"]] = relationship("Signal", back_populates="asset", passive_deletes=True)
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="asset", passive_deletes=True)

    def __repr__(self) -> str:
        return f"<Asset(id={self.id}, symbol='{self.symbol}')>"

# ... (similar docstrings and type hints for all other models) ...

class Strategy(SoftDeleteMixin, Base):
    """Represents a trading strategy."""
    __tablename__ = "strategies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    model_version: Mapped[Optional[str]] = mapped_column(String)
    parameters: Mapped[Optional[dict]] = mapped_column(JSON)
    api_key: Mapped[Optional[str]] = mapped_column(String)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship("User", back_populates="strategies")
    signals: Mapped[List["Signal"]] = relationship("Signal", back_populates="strategy", passive_deletes=True)
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="strategy")
    backtest_results: Mapped[List["BacktestResult"]] = relationship("BacktestResult", back_populates="strategy", passive_deletes=True)
    trade_analytics: Mapped[List["TradeAnalytics"]] = relationship("TradeAnalytics", back_populates="strategy", passive_deletes=True)

    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_user_strategy_name"),)

    def __repr__(self) -> str:
        return f"<Strategy(id={self.id}, name='{self.name}')>"

class PriceData(Base):
    """Represents OHLCV price data for an asset."""
    __tablename__ = "price_data"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, index=True)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)

    asset: Mapped["Asset"] = relationship("Asset", back_populates="price_data")

    __table_args__ = (Index("idx_asset_timestamp_source", "asset_id", "timestamp", "source", unique=True),)

    def __repr__(self) -> str:
        return f"<PriceData(asset_id={self.asset_id}, timestamp='{self.timestamp}', close={self.close})>"

class Signal(SoftDeleteMixin, Base):
    """Represents a trading signal generated by a strategy."""
    __tablename__ = "signals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    strategy_id: Mapped[int] = mapped_column(Integer, ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, index=True)
    signal_type: Mapped[SignalType] = mapped_column(DBEnum(SignalType), nullable=False, index=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float)
    risk_score: Mapped[Optional[float]] = mapped_column(Float)
    price_at_signal: Mapped[Optional[float]] = mapped_column(Float)

    asset: Mapped["Asset"] = relationship("Asset", back_populates="signals")
    strategy: Mapped["Strategy"] = relationship("Strategy", back_populates="signals")

    def __repr__(self) -> str:
        return f"<Signal(id={self.id}, type='{self.signal_type.value}')>"

class Order(SoftDeleteMixin, Base):
    """Represents a trading order."""
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    strategy_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("strategies.id", ondelete="SET NULL"))
    signal_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("signals.id"))
    order_type: Mapped[OrderType] = mapped_column(DBEnum(OrderType), nullable=False, default=OrderType.MARKET)
    order_side: Mapped[OrderSide] = mapped_column(DBEnum(OrderSide), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(DBEnum(OrderStatus), nullable=False, default=OrderStatus.PENDING, index=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    price: Mapped[Optional[float]] = mapped_column(Float)
    filled_quantity: Mapped[float] = mapped_column(Float, default=0.0)
    average_fill_price: Mapped[Optional[float]] = mapped_column(Float)
    commission: Mapped[Optional[float]] = mapped_column(Float)
    exchange_order_id: Mapped[Optional[str]] = mapped_column(String, index=True)
    is_simulated: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), index=True)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship("User", back_populates="orders")
    asset: Mapped["Asset"] = relationship("Asset", back_populates="orders")
    strategy: Mapped["Strategy"] = relationship("Strategy", back_populates="orders")
    trades: Mapped[List["Trade"]] = relationship("Trade", back_populates="executed_order", passive_deletes=True)

    def __repr__(self) -> str:
        return f"<Order(id={self.id}, side='{self.order_side.value}', status='{self.status.value}')>"

class BacktestResult(SoftDeleteMixin, Base):
    """Represents the results of a backtest."""
    __tablename__ = "backtest_results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    strategy_id: Mapped[int] = mapped_column(Integer, ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)
    start_time: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    initial_capital: Mapped[float] = mapped_column(Float, nullable=False)
    final_capital: Mapped[float] = mapped_column(Float, nullable=False)
    total_profit: Mapped[float] = mapped_column(Float, nullable=False)
    total_trades: Mapped[int] = mapped_column(Integer, nullable=False)
    winning_trades: Mapped[int] = mapped_column(Integer, nullable=False)
    losing_trades: Mapped[int] = mapped_column(Integer, nullable=False)
    win_rate: Mapped[float] = mapped_column(Float, nullable=False)
    accuracy: Mapped[Optional[float]] = mapped_column(Float)
    max_drawdown: Mapped[float] = mapped_column(Float, nullable=False)
    sharpe_ratio: Mapped[Optional[float]] = mapped_column(Float)
    sortino_ratio: Mapped[Optional[float]] = mapped_column(Float)
    parameters_used: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())

    strategy: Mapped["Strategy"] = relationship("Strategy", back_populates="backtest_results")

    def __repr__(self) -> str:
        return f"<BacktestResult(id={self.id}, strategy_id={self.strategy_id}, profit={self.total_profit})>"

class Trade(SoftDeleteMixin, Base):
    """Represents an executed trade."""
    __tablename__ = "trades"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    symbol: Mapped[str] = mapped_column(String, nullable=False, index=True)
    quantity: Mapped[float] = mapped_column(Numeric(19, 8), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(19, 8), nullable=False)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    trade_type: Mapped[TradeType] = mapped_column(DBEnum(TradeType), nullable=False)
    commission: Mapped[Optional[float]] = mapped_column(Numeric(19, 8))
    commission_asset: Mapped[Optional[str]] = mapped_column(String)

    executed_order: Mapped["Order"] = relationship("Order", back_populates="trades")

    def __repr__(self) -> str:
        return f"<Trade(id={self.id}, symbol='{self.symbol}', type='{self.trade_type.value}')>"

class ArchivedTrade(Base):
    """Represents a trade that has been archived."""
    __tablename__ = "archived_trades"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True)
    order_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), index=True)
    symbol: Mapped[str] = mapped_column(String, nullable=False, index=True)
    quantity: Mapped[float] = mapped_column(Numeric(19, 8), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(19, 8), nullable=False)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    trade_type: Mapped[TradeType] = mapped_column(DBEnum(TradeType), nullable=False)
    commission: Mapped[Optional[float]] = mapped_column(Numeric(19, 8))
    commission_asset: Mapped[Optional[str]] = mapped_column(String)
    archived_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    def __repr__(self) -> str:
        return f"<ArchivedTrade(id={self.id}, symbol='{self.symbol}')>"

class UserBehaviorLog(SoftDeleteMixin, Base):
    """Logs user behavior."""
    __tablename__ = "user_behavior_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    session_id: Mapped[Optional[str]] = mapped_column(String, index=True)
    meta_data: Mapped[Optional[dict]] = mapped_column(JSON)

    user: Mapped["User"] = relationship("User", back_populates="behavior_logs")

    def __repr__(self) -> str:
        return f"<UserBehaviorLog(id={self.id}, user_id={self.user_id}, action_type='{self.action_type}')>"

class TradeAnalytics(SoftDeleteMixin, Base):
    """Stores trade analytics."""
    __tablename__ = "trade_analytics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    strategy_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("strategies.id", ondelete="CASCADE"), index=True)
    total_trades: Mapped[int] = mapped_column(Integer, nullable=False)
    win_rate: Mapped[float] = mapped_column(Float, nullable=False)
    total_pnl: Mapped[float] = mapped_column(Float, nullable=False)
    avg_risk_reward: Mapped[Optional[float]] = mapped_column(Float)
    max_drawdown: Mapped[Optional[float]] = mapped_column(Float)
    analysis_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, default=func.current_date())
    notes: Mapped[Optional[str]] = mapped_column(Text)

    user: Mapped["User"] = relationship("User", back_populates="trade_analytics")
    strategy: Mapped["Strategy"] = relationship("Strategy", back_populates="trade_analytics")

    def __repr__(self) -> str:
        return f"<TradeAnalytics(id={self.id}, user_id={self.user_id}, analysis_date='{self.analysis_date}')>"

class MarketEvent(Base):
    """Represents a market event."""
    __tablename__ = "market_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    event_datetime: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    symbol: Mapped[Optional[str]] = mapped_column(String, index=True)
    impact_score: Mapped[Optional[float]] = mapped_column(Float)
    source: Mapped[Optional[str]] = mapped_column(String)
    meta_data: Mapped[Optional[dict]] = mapped_column(JSON)

    def __repr__(self) -> str:
        return f"<MarketEvent(id={self.id}, event_type='{self.event_type}')>"

class AuditLog(Base):
    """Logs changes to other models."""
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    table_name: Mapped[str] = mapped_column(String, nullable=False)
    record_id: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    changed_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    changes: Mapped[Optional[dict]] = mapped_column(JSON)

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, table='{self.table_name}', record_id='{self.record_id}')>"

class Features(Base):
    """Stores calculated features for an asset."""
    __tablename__ = "features"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    rsi_14: Mapped[Optional[float]] = mapped_column(Float)
    sma_20: Mapped[Optional[float]] = mapped_column(Float)
    sma_50: Mapped[Optional[float]] = mapped_column(Float)
    ema_20: Mapped[Optional[float]] = mapped_column(Float)
    ema_50: Mapped[Optional[float]] = mapped_column(Float)
    macd_line: Mapped[Optional[float]] = mapped_column(Float)
    macd_signal: Mapped[Optional[float]] = mapped_column(Float)
    macd_hist: Mapped[Optional[float]] = mapped_column(Float)
    atr_14: Mapped[Optional[float]] = mapped_column(Float)
    bb_upperband: Mapped[Optional[float]] = mapped_column(Float)
    bb_middleband: Mapped[Optional[float]] = mapped_column(Float)
    bb_lowerband: Mapped[Optional[float]] = mapped_column(Float)

    asset: Mapped["Asset"] = relationship("Asset")

    __table_args__ = (UniqueConstraint("asset_id", "timestamp", name="uq_feature_asset_timestamp"),)

    def __repr__(self) -> str:
        return f"<Features(asset_id={self.asset_id}, timestamp='{self.timestamp}')>"
