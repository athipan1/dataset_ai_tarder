import enum
from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    Numeric,
    ForeignKey,
    Index,
    String,
    Enum as DBEnum,
    Boolean,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ai_trader.db.base import Base

# from .user import User
# from .asset import Asset
# from .strategy import Strategy
# from .signal import Signal


class OrderStatus(enum.Enum):
    PENDING = "PENDING"  # Order placed but not yet acknowledged by exchange or system
    NEW = "NEW"  # Order acknowledged by exchange, not yet active (e.g. for conditional orders)
    OPEN = "OPEN"  # Order is active on the exchange (e.g. limit order waiting for fill)
    FILLED = "FILLED"  # Order has been completely filled
    PARTIALLY_FILLED = "PARTIALLY_FILLED"  # Order has been partially filled
    CANCELLED = "CANCELLED"  # Order was cancelled by user or system
    REJECTED = "REJECTED"  # Order was rejected by exchange or system
    EXPIRED = "EXPIRED"  # Order expired (e.g. GTC orders with expiry)
    FAILED = "FAILED"  # Order submission failed for some reason


class OrderType(enum.Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_MARKET = "STOP_MARKET"  # Stop order that becomes a market order
    STOP_LIMIT = "STOP_LIMIT"  # Stop order that becomes a limit order
    TAKE_PROFIT_MARKET = "TAKE_PROFIT_MARKET"
    TAKE_PROFIT_LIMIT = "TAKE_PROFIT_LIMIT"
    TRAILING_STOP = "TRAILING_STOP"


class OrderSide(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )  # If user deleted, keep order
    asset_id = Column(
        Integer,
        ForeignKey("assets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )  # Don't delete asset if orders exist
    strategy_id = Column(
        Integer,
        ForeignKey("strategies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    signal_id = Column(
        Integer,
        ForeignKey("signals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    order_type = Column(DBEnum(OrderType), nullable=False, default=OrderType.MARKET, index=True)
    order_side = Column(DBEnum(OrderSide), nullable=False, index=True)
    status = Column(DBEnum(OrderStatus), nullable=False, default=OrderStatus.PENDING, index=True)

    quantity_requested = Column(Numeric(19, 8), nullable=False)  # Requested quantity
    quantity_filled = Column(Numeric(19, 8), default=0.0)  # Total filled quantity for this order

    limit_price = Column(Numeric(19, 8), nullable=True)  # For LIMIT or STOP_LIMIT orders
    stop_price = Column(Numeric(19, 8), nullable=True)  # For STOP or STOP_LIMIT orders

    # average_fill_price can be calculated from related Trade entries or stored here if exchange provides it directly for the order
    average_fill_price = Column(Numeric(19, 8), nullable=True)
    commission_paid = Column(Numeric(19, 8), nullable=True, default=0.0)  # Total commission for this order

    exchange_order_id = Column(
        String, nullable=True, index=True, unique=False
    )  # Exchange ID might not be unique if same ID used on different exchanges or test environments
    client_order_id = Column(String, nullable=True, index=True, unique=False)  # Custom ID from client system

    is_simulated = Column(Boolean, default=True, nullable=False, index=True)

    time_in_force = Column(String, nullable=True)  # e.g. GTC, IOC, FOK

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        index=True,
    )
    # filled_at = Column(DateTime(timezone=True), nullable=True) # Timestamp when order was fully filled
    # cancelled_at = Column(DateTime(timezone=True), nullable=True) # Timestamp when order was cancelled
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    user = relationship("User", back_populates="orders")
    asset = relationship("Asset", back_populates="orders")
    strategy = relationship("Strategy", back_populates="orders")
    signal = relationship("Signal")  # An order is related to one signal. Signal doesn't list orders.

    # One order can have multiple trades (fills)
    trades = relationship("Trade", back_populates="order", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_order_user_status", "user_id", "status"),  # Common query: user's open/filled orders
        Index("ix_order_asset_status", "asset_id", "status"),  # Common query: asset's open orders
        Index("ix_order_exchange_id", "exchange_order_id"),  # Already indexed on column
    )

    def __repr__(self):
        cls_name = self.__class__.__name__
        parts = [
            f"<{cls_name}(",  # This f-string prefix can be just a string if no vars here
            f"id={self.id}, ",
            f"user_id={self.user_id}, ",
            f"asset_id={self.asset_id}, ",
            f"status='{self.status.value}'",
            ")>",  # Corrected F541: No longer an f-string
        ]
        return "".join(parts)
