import datetime  # Added for AuditLog timestamp default
import enum
from typing import Optional

from sqlalchemy import JSON, Boolean, Column, Date, DateTime
from sqlalchemy import Enum as DBEnum  # Renamed Enum to DBEnum to avoid conflict
from sqlalchemy import (
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship
from sqlalchemy.sql import func

Base = declarative_base()

import datetime as dt  # Alias for easier use of datetime.UTC if needed, or just use datetime.UTC
from datetime import timezone  # For datetime.UTC

# --- Soft Delete Mixin ---


class SoftDeleteMixin:
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    deleted_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, nullable=True, index=True
    )

    @classmethod
    def query_with_deleted(cls, session):
        return session.query(cls)

    @classmethod
    def query_without_deleted(cls, session):
        return session.query(cls).filter(cls.is_deleted == False)

    # Default query to exclude deleted items
    # This assumes you are using session.query(Model) style.
    # If using query_property, that needs to be setup differently.
    # For now, providing class methods as a common pattern.
    # A more advanced setup would involve a custom Query class for query_property.

    def soft_delete(self, session):
        if self.is_deleted:  # Avoid recursion or reprocessing
            return

        self.is_deleted = True
        self.deleted_at = datetime.datetime.now(timezone.utc)

        # Add to session if not already persistent, or if changes need to be flushed
        # This ensures that the instance is part of the session so that relationships can be loaded.
        if self not in session:
            session.add(self)

        if isinstance(self, User):
            # Soft delete related Strategies
            if hasattr(self, "strategies"):
                for strategy in self.strategies:
                    if not strategy.is_deleted:
                        strategy.soft_delete(session)
            # Soft delete related Orders
            if hasattr(self, "orders"):
                for order in self.orders:
                    if not order.is_deleted:
                        order.soft_delete(session)
            # Soft delete related Trades (assuming direct relationship or via orders)
            # If Trades are only linked via Orders, they will be caught by Order's soft_delete
            # If User has a direct 'trades' relationship:
            if (
                hasattr(self, "trades") and self.trades
            ):  # Check if 'trades' attribute exists and is not None
                for (
                    trade
                ) in (
                    self.trades
                ):  # Note: User model does not have direct 'trades' relationship.
                    # This block might be for a generic case or other models.
                    # User's trades are cascaded via User -> Order -> Trade.
                    if not trade.is_deleted:
                        trade.soft_delete(session)

            # Cascade to UserBehaviorLog
            if hasattr(self, "behavior_logs"):
                for log in self.behavior_logs:
                    if not log.is_deleted:  # UserBehaviorLog must be SoftDeleteMixin
                        log.soft_delete(session)

            # Cascade to TradeAnalytics (those directly related to User)
            if hasattr(self, "trade_analytics"):  # User.trade_analytics relationship
                for analytic in self.trade_analytics:
                    if (
                        not analytic.is_deleted
                    ):  # TradeAnalytics must be SoftDeleteMixin
                        analytic.soft_delete(session)

        elif isinstance(self, Strategy):
            # Soft delete related Orders (which will then cascade to Trades)
            if hasattr(self, "orders"):
                for order in self.orders:
                    if not order.is_deleted:
                        order.soft_delete(session)

            # Cascade to Signals
            if hasattr(self, "signals"):
                for (
                    signal_item
                ) in self.signals:  # Renamed to avoid conflict with Signal class
                    if not signal_item.is_deleted:  # Signal must be SoftDeleteMixin
                        signal_item.soft_delete(session)

            # Cascade to BacktestResult
            if hasattr(self, "backtest_results"):
                for result in self.backtest_results:
                    if not result.is_deleted:  # BacktestResult must be SoftDeleteMixin
                        result.soft_delete(session)

            # Cascade to TradeAnalytics (those related to Strategy)
            if hasattr(
                self, "trade_analytics"
            ):  # Strategy.trade_analytics relationship
                for analytic in self.trade_analytics:
                    if (
                        not analytic.is_deleted
                    ):  # TradeAnalytics must be SoftDeleteMixin
                        analytic.soft_delete(session)

        elif isinstance(self, Order):
            # Soft delete related Trades
            if hasattr(self, "trades"):
                for trade in self.trades:
                    if not trade.is_deleted:
                        trade.soft_delete(session)


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
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships from root models.py
    strategies = relationship("Strategy", back_populates="user", passive_deletes=True)
    orders = relationship(
        "Order", back_populates="user"
    )  # user_id in Order is nullable, SET NULL is fine

    # Relationships from ai_trader/models/user.py
    behavior_logs = relationship(
        "UserBehaviorLog", back_populates="user", passive_deletes=True
    )
    trade_analytics = relationship(
        "TradeAnalytics", back_populates="user", passive_deletes=True
    )

    # __table_args__ from ai_trader/models/user.py (root model didn't have specific ones)
    # Root model had implicit indices from unique=True, index=True. Explicit can be fine.
    __table_args__ = (
        Index(
            "ix_user_username", "username", unique=True
        ),  # unique=True already on column
        Index("ix_user_email", "email", unique=True),  # unique=True already on column
    )

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"


class Asset(Base):  # Asset model does not get SoftDeleteMixin
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    asset_type = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())

    price_data = relationship(
        "PriceData", back_populates="asset", cascade="all, delete", lazy="dynamic"
    )
    signals = relationship("Signal", back_populates="asset", passive_deletes=True)
    orders = relationship("Order", back_populates="asset", passive_deletes=True)

    def __repr__(self):
        return f"<Asset(id={self.id}, symbol='{self.symbol}')>"


class Strategy(SoftDeleteMixin, Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    model_version = Column(String, nullable=True)
    parameters = Column(JSON, nullable=True)
    api_key = Column(String, nullable=True)  # TODO: Secure this
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="strategies")
    signals = relationship("Signal", back_populates="strategy", passive_deletes=True)
    orders = relationship(
        "Order", back_populates="strategy"
    )  # strategy_id in Order is nullable, SET NULL is fine
    backtest_results = relationship(
        "BacktestResult", back_populates="strategy", passive_deletes=True
    )
    trade_analytics = relationship(
        "TradeAnalytics", back_populates="strategy", passive_deletes=True
    )

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_strategy_name"),
        Index("ix_strategy_name", "name"),  # Already on column, but explicit is fine
        # user_id index already on column
    )

    def __repr__(self):
        return f"<Strategy(id={self.id}, name='{self.name}')>"


class PriceData(Base):  # PriceData model does not get SoftDeleteMixin
    __tablename__ = "price_data"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    timestamp = Column(DateTime, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    source = Column(String, nullable=False)

    asset = relationship("Asset", back_populates="price_data")

    __table_args__ = (
        Index(
            "idx_asset_timestamp_source", "asset_id", "timestamp", "source", unique=True
        ),
    )

    def __repr__(self):
        return f"<PriceData(asset_id={self.asset_id}, timestamp='{self.timestamp}', close={self.close})>"


class Signal(SoftDeleteMixin, Base):  # Added SoftDeleteMixin
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


# The entire duplicate Signal class definition below has been removed.


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
    signal_id = Column(
        Integer, ForeignKey("signals.id"), nullable=True
    )  # Assuming signals can be deleted without affecting orders

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
    )  # For ON DELETE CASCADE of Trade.order_id

    __table_args__ = (
        Index("ix_order_status_user_created", "status", "user_id", "created_at"),
        Index(
            "idx_order_asset_strategy_created", "asset_id", "strategy_id", "created_at"
        ),
    )

    def __repr__(self):
        return f"<Order(id={self.id}, asset_id={self.asset_id}, type='{self.order_type.value}', side='{self.order_side.value}', status='{self.status.value}')>"


class BacktestResult(SoftDeleteMixin, Base):  # Added SoftDeleteMixin
    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(
        Integer, ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False
    )
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
    parameters_used = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())

    strategy = relationship("Strategy", back_populates="backtest_results")

    __table_args__ = (
        Index("idx_backtest_strategy_created", "strategy_id", "created_at"),
    )

    def __repr__(self):
        return f"<BacktestResult(id={self.id}, strategy_id={self.strategy_id}, profit={self.total_profit})>"


# --- New Models from ai_trader/models/ ---


class Trade(SoftDeleteMixin, Base):
    __tablename__ = "trades"  # This table might conflict with 'orders' if they represent similar things.
    # Assuming 'trades' are actual executed transactions vs 'orders' which can be pending/cancelled.

    id = Column(Integer, primary_key=True, index=True)
    # user_id from ai_trader/models/trade.py, but orders already has user_id.
    # If a trade always comes from an order, this might be redundant or could link to order_id.
    # For now, keeping it as per user's request to include Trade model.
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_id = Column(
        Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=True, index=True
    )  # Added link to Order

    symbol = Column(
        String, nullable=False, index=True
    )  # Asset symbol, e.g. BTCUSD. Consider ForeignKey to Asset.asset_symbol
    quantity = Column(
        Numeric(19, 8), nullable=False
    )  # Adjusted precision based on typical crypto values
    price = Column(Numeric(19, 8), nullable=False)  # Adjusted precision
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    trade_type = Column(DBEnum(TradeType), nullable=False)
    commission = Column(Numeric(19, 8), nullable=True)
    commission_asset = Column(
        String, nullable=True
    )  # e.g., USDT or the traded asset itself

    # Relationship to User (already defined in User model via 'orders', but direct might be wanted if trades can exist without an order)
    # Not adding a direct user relationship here if orders are the primary link.
    # user = relationship("User") # This would conflict with User.orders if not named carefully.
    # Explicitly relating to order:
    executed_order = relationship(
        "Order"
    )  # Name it clearly if Order has a backref to trades.

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

    id = Column(Integer, primary_key=True, index=True)  # Keep original ID for reference
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    order_id = Column(
        Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True
    )  # Original order_id

    symbol = Column(String, nullable=False, index=True)
    quantity = Column(Numeric(19, 8), nullable=False)
    price = Column(Numeric(19, 8), nullable=False)
    timestamp = Column(DateTime(timezone=True))  # Original timestamp of the trade
    trade_type = Column(DBEnum(TradeType), nullable=False)
    commission = Column(Numeric(19, 8), nullable=True)
    commission_asset = Column(String, nullable=True)

    # Fields from the example not directly in the current Trade model, but might be useful for archived data
    # These would require the original Trade model to have them or be derived during archiving.
    # For now, I will stick to the columns present in the existing Trade model and add `archived_at`.
    # If PnL, entry/exit prices, opened/closed_at were part of the original Trade, they'd be here.
    # entry_price = Column(Float)
    # exit_price = Column(Float)
    # pnl = Column(Float)
    # opened_at = Column(DateTime)
    # closed_at = Column(DateTime)

    archived_at = Column(DateTime(timezone=True), default=func.now())

    # Relationships are generally not needed for archive tables as they are for historical record keeping
    # and not active operational data. Foreign keys are kept for data integrity / reference.
    # user = relationship("User")
    # executed_order = relationship("Order")

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


class UserBehaviorLog(SoftDeleteMixin, Base):  # Added SoftDeleteMixin
    __tablename__ = "user_behavior_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action_type = Column(
        String, nullable=False, index=True
    )  # E.g., 'login', 'view_dashboard', 'execute_trade'
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    session_id = Column(String, index=True, nullable=True)
    meta_data = Column(JSON, nullable=True)

    user = relationship("User", back_populates="behavior_logs")

    def __repr__(self):
        return f"<UserBehaviorLog(id={self.id}, user_id={self.user_id}, action_type='{self.action_type}')>"


class TradeAnalytics(SoftDeleteMixin, Base):  # Added SoftDeleteMixin
    __tablename__ = "trade_analytics"  # This seems to be summary data.

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    strategy_id = Column(
        Integer,
        ForeignKey("strategies.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    total_trades = Column(Integer, nullable=False)
    win_rate = Column(Float, nullable=False)  # Percentage, e.g., 0.75 for 75%
    total_pnl = Column(Float, nullable=False)  # Profit and Loss
    avg_risk_reward = Column(Float, nullable=True)  # Field name changed as per test
    max_drawdown = Column(Float, nullable=True)  # Percentage or absolute value
    analysis_date = Column(
        Date, nullable=False, default=func.current_date()
    )  # Changed to Date, added default
    notes = Column(Text, nullable=True)
    # Consider adding start_date and end_date for the period of this analysis

    user = relationship("User", back_populates="trade_analytics")
    strategy = relationship("Strategy", back_populates="trade_analytics")

    def __repr__(self):
        return f"<TradeAnalytics(id={self.id}, user_id={self.user_id}, analysis_date='{self.analysis_date}')>"


class MarketEvent(Base):
    __tablename__ = "market_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(
        String, nullable=False, index=True
    )  # E.g., 'news_release', 'earnings_report', 'fed_announcement'
    description = Column(Text, nullable=False)
    event_datetime = Column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    symbol = Column(
        String, nullable=True, index=True
    )  # Associated asset symbol, if any
    impact_score = Column(Float, nullable=True)  # E.g., -1.0 to 1.0 or 1-5 scale
    source = Column(
        String, nullable=True
    )  # E.g., 'Reuters', 'BloombergTerminal', 'Twitter'
    meta_data = Column(JSON, nullable=True)  # Additional structured data

    def __repr__(self):
        return f"<MarketEvent(id={self.id}, event_type='{self.event_type}', symbol='{self.symbol}')>"


# --- Audit Log Model ---


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    table_name = Column(String, nullable=False)
    record_id = Column(Integer, nullable=False)  # As per original task spec
    action = Column(String, nullable=False)  # INSERT / UPDATE / DELETE
    changed_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    changes = Column(JSON, nullable=True)  # optional: store changed fields & values

    # No direct relationships needed from AuditLog to other tables,
    # as it's a log. Foreign key to User is for identifying the user.

    def __repr__(self):
        return (
            f"<AuditLog(id={self.id}, table='{self.table_name}', record_id='{self.record_id}', "
            f"action='{self.action}', user_id={self.changed_by})>"
        )


# --- Features Model ---


class Features(Base):
    __tablename__ = "features"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    timestamp = Column(
        DateTime, nullable=False
    )  # This should match a PriceData timestamp for a given asset

    # Technical Indicators
    rsi_14 = Column(Float, nullable=True)
    sma_20 = Column(Float, nullable=True)
    sma_50 = Column(Float, nullable=True)
    ema_20 = Column(Float, nullable=True)
    ema_50 = Column(Float, nullable=True)
    macd_line = Column(Float, nullable=True)  # MACD line (e.g., 12,26,9)
    macd_signal = Column(Float, nullable=True)  # MACD signal line (e.g., 12,26,9)
    macd_hist = Column(Float, nullable=True)  # MACD histogram (e.g., 12,26,9)
    atr_14 = Column(Float, nullable=True)  # Average True Range (e.g., 14)
    bb_upperband = Column(Float, nullable=True)  # Bollinger Upper Band
    bb_middleband = Column(
        Float, nullable=True
    )  # Bollinger Middle Band (typically SMA20)
    bb_lowerband = Column(Float, nullable=True)  # Bollinger Lower Band
    # Add other indicators as needed, e.g.:
    # adx_14 = Column(Float, nullable=True)
    # cci_20 = Column(Float, nullable=True)
    # stoch_k = Column(Float, nullable=True)
    # stoch_d = Column(Float, nullable=True)

    asset = relationship("Asset")  # Relationship to Asset model

    # Unique constraint for asset_id and timestamp to ensure one feature set per candle
    __table_args__ = (
        UniqueConstraint("asset_id", "timestamp", name="uq_feature_asset_timestamp"),
        Index(
            "idx_feature_asset_timestamp", "asset_id", "timestamp"
        ),  # Index for faster lookups
    )

    def __repr__(self):
        return f"<Features(asset_id={self.asset_id}, timestamp='{self.timestamp}')>"


# Example of how to create the tables in a database (e.g., SQLite for local dev)
# This __main__ block should ideally not be run directly if using Alembic.
# It's here for illustrative purposes or very basic, non-Alembic setups.
if __name__ == "__main__":
    # For SQLite, the file will be created in the same directory as this script if relative path is used.
    # Better to use an absolute path or path derived from a config.
    # For this example, let's assume a project root structure.
    import os

    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DB_PATH = os.path.join(PROJECT_ROOT, "ai_trader_consolidated.db")
    engine = create_engine(f"sqlite:///{DB_PATH}")

    print(f"Attempting to create tables in database at: {DB_PATH}")
    # Base.metadata.create_all(bind=engine) # This line would create tables.
    # In an Alembic setup, you run 'alembic upgrade head'.
    print("If using Alembic, run 'alembic upgrade head' to create/update tables.")
    print("The Base.metadata.create_all() call is commented out in this example.")
    print("Models defined in this file are now ready to be used with Alembic.")

# To ensure all models are known to Base before Alembic import:
# (This is usually handled by importing Base from here into env.py and models into your app)
# No explicit list needed here as they are all defined in this file with the shared Base.

# An __all__ can be useful for `from .models import *`
__all__ = [
    "Base",
    "User",
    "Asset",
    "Strategy",
    "PriceData",
    "Features",  # Added Features model
    "Signal",
    "Order",
    "BacktestResult",
    "Trade",
    "ArchivedTrade",
    "UserBehaviorLog",
    "TradeAnalytics",
    "MarketEvent",
    "AuditLog",
    "SignalType",
    "OrderStatus",
    "OrderType",
    "OrderSide",
    "TradeType",
]
