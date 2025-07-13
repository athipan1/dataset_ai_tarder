from sqlalchemy import (JSON, Column, Date, DateTime, Float, ForeignKey, Index,
                        Integer, String, Text, UniqueConstraint)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, SoftDeleteMixin


class Features(Base):
    __tablename__ = "features"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    timestamp = Column(DateTime, nullable=False)

    rsi_14 = Column(Float, nullable=True)
    sma_20 = Column(Float, nullable=True)
    sma_50 = Column(Float, nullable=True)
    ema_20 = Column(Float, nullable=True)
    ema_50 = Column(Float, nullable=True)
    macd_line = Column(Float, nullable=True)
    macd_signal = Column(Float, nullable=True)
    macd_hist = Column(Float, nullable=True)
    atr_14 = Column(Float, nullable=True)
    bb_upperband = Column(Float, nullable=True)
    bb_middleband = Column(Float, nullable=True)
    bb_lowerband = Column(Float, nullable=True)

    asset = relationship("Asset")

    __table_args__ = (
        UniqueConstraint("asset_id", "timestamp", name="uq_feature_asset_timestamp"),
        Index("idx_feature_asset_timestamp", "asset_id", "timestamp"),
    )

    def __repr__(self):
        return f"<Features(asset_id={self.asset_id}, timestamp='{self.timestamp}')>"


class BacktestResult(SoftDeleteMixin, Base):
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


class UserBehaviorLog(SoftDeleteMixin, Base):
    __tablename__ = "user_behavior_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action_type = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    session_id = Column(String, index=True, nullable=True)
    meta_data = Column(JSON, nullable=True)

    user = relationship("User", back_populates="behavior_logs")

    def __repr__(self):
        return f"<UserBehaviorLog(id={self.id}, user_id={self.user_id}, action_type='{self.action_type}')>"


class TradeAnalytics(SoftDeleteMixin, Base):
    __tablename__ = "trade_analytics"

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
    win_rate = Column(Float, nullable=False)
    total_pnl = Column(Float, nullable=False)
    avg_risk_reward = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    analysis_date = Column(Date, nullable=False, default=func.current_date())
    notes = Column(Text, nullable=True)

    user = relationship("User", back_populates="trade_analytics")
    strategy = relationship("Strategy", back_populates="trade_analytics")

    def __repr__(self):
        return f"<TradeAnalytics(id={self.id}, user_id={self.user_id}, analysis_date='{self.analysis_date}')>"
