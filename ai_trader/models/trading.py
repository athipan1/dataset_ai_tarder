import enum

from sqlalchemy import JSON, Column, DateTime
from sqlalchemy import Enum as DBEnum
from sqlalchemy import (Float, ForeignKey, Index, Integer, Numeric, String,
                        Text, UniqueConstraint)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, SoftDeleteMixin


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


class Strategy(SoftDeleteMixin, Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    model_version = Column(String, nullable=True)
    parameters = Column(JSON, nullable=True)
    api_key = Column(String, nullable=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="strategies")
    signals = relationship("Signal", back_populates="strategy", passive_deletes=True)
    orders = relationship("Order", back_populates="strategy")
    backtest_results = relationship(
        "BacktestResult", back_populates="strategy", passive_deletes=True
    )
    trade_analytics = relationship(
        "TradeAnalytics", back_populates="strategy", passive_deletes=True
    )

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_strategy_name"),
        Index("ix_strategy_name", "name"),
    )

    def __repr__(self):
        return f"<Strategy(id={self.id}, name='{self.name}')>"


class Signal(SoftDeleteMixin, Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    strategy_id = Column(
        Integer, ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False
    )
    timestamp = Column(DateTime, nullable=False, index=True)
    signal_type = Column(DBEnum(SignalType), nullable=False, index=True)
    confidence_score = Column(Float, nullable=True)
    risk_score = Column(Float, nullable=True)
    price_at_signal = Column(Float, nullable=True)

    asset = relationship("Asset", back_populates="signals")
    strategy = relationship("Strategy", back_populates="signals")

    __table_args__ = (
        Index(
            "idx_signal_asset_strategy_timestamp",
            "asset_id",
            "strategy_id",
            "timestamp",
        ),
    )

    def __repr__(self):
        return f"<Signal(id={self.id}, asset_id={self.asset_id}, strategy_id={self.strategy_id}, type='{self.signal_type.value}')>"


class Order(SoftDeleteMixin, Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    asset_id = Column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    strategy_id = Column(
        Integer, ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True
    )
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=True)

    order_type = Column(DBEnum(OrderType), nullable=False, default=OrderType.MARKET)
    order_side = Column(DBEnum(OrderSide), nullable=False)
    status = Column(
        DBEnum(OrderStatus), nullable=False, default=OrderStatus.PENDING, index=True
    )
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=True)
    filled_quantity = Column(Float, default=0.0)
    average_fill_price = Column(Float, nullable=True)
    commission = Column(Float, nullable=True)
    exchange_order_id = Column(String, nullable=True, index=True)
    is_simulated = Column(Integer, default=1, nullable=False)

    created_at = Column(DateTime, default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="orders")
    asset = relationship("Asset", back_populates="orders")
    strategy = relationship("Strategy", back_populates="orders")
    trades = relationship(
        "Trade", back_populates="executed_order", passive_deletes=True
    )

    __table_args__ = (
        Index("ix_order_status_user_created", "status", "user_id", "created_at"),
        Index(
            "idx_order_asset_strategy_created", "asset_id", "strategy_id", "created_at"
        ),
    )

    def __repr__(self):
        return f"<Order(id={self.id}, asset_id={self.asset_id}, type='{self.order_type.value}', side='{self.order_side.value}', status='{self.status.value}')>"


class Trade(SoftDeleteMixin, Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_id = Column(
        Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=True, index=True
    )

    symbol = Column(String, nullable=False, index=True)
    quantity = Column(Numeric(19, 8), nullable=False)
    price = Column(Numeric(19, 8), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    trade_type = Column(DBEnum(TradeType), nullable=False)
    commission = Column(Numeric(19, 8), nullable=True)
    commission_asset = Column(String, nullable=True)

    executed_order = relationship("Order")

    __table_args__ = (
        Index(
            "ix_trade_user_symbol_timestamp_type",
            "user_id",
            "symbol",
            "timestamp",
            "trade_type",
        ),
    )

    def __repr__(self):
        return (
            f"<Trade(id={self.id}, symbol='{self.symbol}', "
            f"type='{self.trade_type.value}', quantity={self.quantity}, "
            f"price={self.price})>"
        )


class ArchivedTrade(Base):
    __tablename__ = "archived_trades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    order_id = Column(
        Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True
    )

    symbol = Column(String, nullable=False, index=True)
    quantity = Column(Numeric(19, 8), nullable=False)
    price = Column(Numeric(19, 8), nullable=False)
    timestamp = Column(DateTime(timezone=True))
    trade_type = Column(DBEnum(TradeType), nullable=False)
    commission = Column(Numeric(19, 8), nullable=True)
    commission_asset = Column(String, nullable=True)
    archived_at = Column(DateTime(timezone=True), default=func.now())

    __table_args__ = (
        Index(
            "ix_archived_trade_user_symbol_timestamp", "user_id", "symbol", "timestamp"
        ),
        Index("ix_archived_trade_archived_at", "archived_at"),
    )

    def __repr__(self):
        return (
            f"<ArchivedTrade(id={self.id}, symbol='{self.symbol}', "
            f"type='{self.trade_type.value}', quantity={self.quantity}, "
            f"price={self.price}, archived_at='{self.archived_at}')>"
        )
