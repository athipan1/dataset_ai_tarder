from sqlalchemy import Column, Integer, Date, Numeric, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import relationship
from ai_trader.db.base import Base

class MonthlySummary(Base):
    __tablename__ = "monthly_summaries"

    id = Column(Integer, primary_key=True, index=True)

    # Representing the month, e.g., "YYYY-MM" or first day of the month
    # Using Date (first day of month) for easier querying and consistency
    month_year = Column(Date, nullable=False)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True, index=True)

    total_profit = Column(Numeric(19, 8), nullable=False, default=0.0)
    total_trades = Column(Integer, nullable=False, default=0)
    total_volume = Column(Numeric(19, 8), nullable=True)
    # Could add other metrics like win_rate, avg_profit_per_trade etc. for the month

    # Relationships
    user = relationship("User")
    strategy = relationship("Strategy")

    __table_args__ = (
        UniqueConstraint("month_year", "user_id", "strategy_id", name="uq_monthly_summary_month_user_strategy"),
        Index("ix_monthly_summary_month_year", "month_year"),
    )

    def __repr__(self):
        return f"<MonthlySummary(month='{self.month_year.strftime('%Y-%m') if self.month_year else None}', user_id={self.user_id}, strategy_id={self.strategy_id}, profit={self.total_profit})>"
