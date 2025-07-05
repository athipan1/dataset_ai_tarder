from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Numeric,
    ForeignKey,
    Enum as DBEnum,
    Index,
    Text,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from ai_trader.db.base import Base
from .trade import TradeType  # Re-using TradeType enum from trade model

# from sqlalchemy.dialects.postgresql import JSONB # For PostgreSQL, otherwise use JSON or Text


class TradeVersion(Base):
    __tablename__ = "trade_versions"

    id = Column(Integer, primary_key=True, index=True)
    trade_id = Column(Integer, ForeignKey("trades.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False, default=1)

    # Fields from Trade model that might be versioned
    # Not all fields need to be here, only those that can change and need versioning
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )  # Original user_id might change
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    symbol = Column(String, nullable=False)
    trade_type = Column(DBEnum(TradeType), nullable=False)
    quantity = Column(Numeric(19, 8), nullable=False)
    price = Column(Numeric(19, 8), nullable=False)
    executed_at = Column(DateTime(timezone=True), nullable=False)  # The original execution time
    commission = Column(Numeric(19, 8), nullable=True)

    # Metadata for the version
    changed_at = Column(DateTime(timezone=True), server_default=func.now())  # When this version was created
    # changed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Who made this version
    change_reason = Column(Text, nullable=True)  # Reason for this version/change

    # To store what actually changed, could use a JSON field
    changes = Column(JSON, nullable=True)  # For SQLite / MySQL

    __table_args__ = (
        UniqueConstraint("trade_id", "version_number", name="uq_trade_id_version_number"),
        Index("ix_trade_version_trade_id", "trade_id"),
    )

    def __repr__(self):
        return f"<TradeVersion(id={self.id}, trade_id={self.trade_id}, version={self.version_number})>"
