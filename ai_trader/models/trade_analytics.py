from sqlalchemy import Column, Integer, String, Float, Date, Text, ForeignKey
from sqlalchemy.orm import relationship

from ai_trader.db.base import Base


class TradeAnalytics(Base):
    __tablename__ = "trade_analytics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=True, index=True)  # Optional strategy link
    total_trades = Column(Integer, nullable=False)
    win_rate = Column(Float, nullable=False)
    total_pnl = Column(Float, nullable=False)
    avg_risk_reward = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    analysis_date = Column(Date, nullable=False)
    notes = Column(Text, nullable=True)

    user = relationship("User", back_populates="trade_analytics")
    strategy = relationship("Strategy", back_populates="trade_analytics")

    def __repr__(self):
        return f"<TradeAnalytics(id={self.id}, user_id={self.user_id}, strategy_id={self.strategy_id}, analysis_date='{self.analysis_date}')>"
