import enum
from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    Numeric,
    ForeignKey,
    Index,
    Enum as DBEnum,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ai_trader.db.base import Base

# from .asset import Asset # Use string "Asset"
# from .strategy import Strategy # Use string "Strategy"


class SignalType(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    STRONG_BUY = "STRONG_BUY"
    STRONG_SELL = "STRONG_SELL"


class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    strategy_id = Column(Integer, ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)

    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    signal_type = Column(DBEnum(SignalType), nullable=False, index=True)

    confidence_score = Column(Numeric(5, 4), nullable=True)  # e.g., 0.0000 to 1.0000
    price_at_signal = Column(Numeric(19, 8), nullable=True)
    # Additional fields from original root models.py that might be useful
    # risk_score = Column(Numeric(5, 4), nullable=True) # This was in the original plan for this file
    details = Column(Text, nullable=True)  # For any extra information, like indicators values
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    asset = relationship("Asset", back_populates="signals")
    strategy = relationship("Strategy", back_populates="signals")
    # A signal might lead to an order, but one signal could also be just informational
    # If an order is always created from a signal, a one-to-one (Signal-Order) might be an option.
    # Or an Order can have a nullable signal_id as already designed in Order model.
    # order = relationship("Order", back_populates="signal", uselist=False) # If one signal -> one order

    __table_args__ = (
        Index(
            "ix_signal_asset_strategy_timestamp",
            "asset_id",
            "strategy_id",
            "timestamp",
            unique=False,
        ),  # Signals might not be unique for this combo always
        Index("ix_signal_strategy_timestamp", "strategy_id", "timestamp"),  # Query signals by strategy over time
        # signal_type is indexed
        # timestamp is indexed
    )

    def __repr__(self):
        return (
            f"<Signal(id={self.id}, asset_id={self.asset_id}, "
            f"strategy_id={self.strategy_id}, type='{self.signal_type.value}', "
            f"time='{self.timestamp}')>"
        )
