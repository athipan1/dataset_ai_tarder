from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, Index, Enum as DBEnum # Renamed Enum to DBEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ai_trader.db.base import Base
# from .user import User # For type hinting if used
import enum


class TradeType(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


class Trade(Base): # This model represents executed trades, similar to a fill.
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # If trades are directly linked to an asset_id from an Asset table:
    # asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, index=True)
    # symbol = Column(String, nullable=False, index=True) # Keep if assets table not used for this, or denormalized

    # If linking to an Order that was filled:
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True, index=True) # Trade resulted from which order

    symbol = Column(String, nullable=False, index=True) # Denormalized for easy query, or if no direct asset link

    trade_type = Column(DBEnum(TradeType), nullable=False) # BUY or SELL
    quantity = Column(Numeric(19, 8), nullable=False)
    price = Column(Numeric(19, 8), nullable=False) # Execution price

    # timestamp from original model might be 'created_at' or 'execution_time'
    # Using 'executed_at' for clarity if this represents fill time.
    executed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    commission = Column(Numeric(19, 8), nullable=True, default=0.0)
    # Add other relevant fields like fees, related_fill_id (if it's part of a larger fill)

    # Relationships
    user = relationship("User", back_populates="trades")
    # asset = relationship("Asset") # If asset_id is added
    order = relationship("Order") # If order_id is added and Order model is defined

    __table_args__ = (
        Index("ix_trade_user_id_symbol_executed_at", "user_id", "symbol", "executed_at"),
        # Index("ix_trade_user_id", "user_id"), # Covered by above
        # Index("ix_trade_symbol", "symbol"), # Covered by above
        # Index("ix_trade_timestamp", "executed_at"), # Covered by above / Renamed
        Index("ix_trade_order_id", "order_id"), # If order_id is used
    )

    def __repr__(self):
        return (
            f"<Trade(id={self.id}, symbol='{self.symbol}', "
            f"type='{self.trade_type.value}', quantity={self.quantity}, "
            f"price={self.price}, user_id={self.user_id})>"
        )
