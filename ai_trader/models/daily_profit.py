from sqlalchemy import (
    Column,
    Integer,
    Date,
    Numeric,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from ai_trader.db.base import Base


class DailyProfit(Base):
    __tablename__ = "daily_profits"

    id = Column(Integer, primary_key=True, index=True)

    # Date for which the profit is recorded
    profit_date = Column(Date, nullable=False)

    # Link to user, strategy (optional, could be system-wide or per user/strategy)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    strategy_id = Column(
        Integer,
        ForeignKey("strategies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # asset_id = Column(Integer, ForeignKey("assets.id"), nullable=True, index=True) # Optional: if profit is tracked per asset

    total_profit = Column(Numeric(19, 8), nullable=False, default=0.0)
    total_trades = Column(Integer, nullable=False, default=0)
    total_volume = Column(Numeric(19, 8), nullable=True)  # e.g., total value of assets traded

    # Relationships
    user = relationship("User")
    strategy = relationship("Strategy")
    # asset = relationship("Asset")

    __table_args__ = (
        # Unique constraint to prevent duplicate entries for the same day, user, strategy
        UniqueConstraint(
            "profit_date",
            "user_id",
            "strategy_id",
            name="uq_daily_profit_date_user_strategy",
        ),
        Index("ix_daily_profit_date", "profit_date"),
    )

    def __repr__(self):
        return (  # noqa: E501
            f"<DailyProfit("
            f"date='{self.profit_date}', "
            f"user_id={self.user_id}, "
            f"strategy_id={self.strategy_id}, "
            f"profit={self.total_profit:.2f}"
            f")>"
        )
