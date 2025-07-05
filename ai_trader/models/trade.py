from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, Index, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ai_trader.db.base import Base
import enum


class TradeType(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)
    quantity = Column(Numeric(10, 2), nullable=False)  # Assuming quantity can have 2 decimal places
    price = Column(Numeric(10, 4), nullable=False)  # Assuming price can have 4 decimal places for precision
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    trade_type = Column(Enum(TradeType), nullable=False)

    owner = relationship("User")  # Establishes a relationship to the User model

    __table_args__ = (
        Index("ix_trade_user_id", "user_id"),
        Index("ix_trade_symbol", "symbol"),
        Index("ix_trade_timestamp", "timestamp"),
    )

    def __repr__(self):
        return (
            f"<Trade(id={self.id}, symbol='{self.symbol}', "
            f"type='{self.trade_type.value}', quantity={self.quantity}, "
            f"price={self.price})>"
        )
