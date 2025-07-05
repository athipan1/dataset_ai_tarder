from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    Numeric,
    ForeignKey,
    Index,
    Text,
    JSON,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ai_trader.db.base import Base

# from .strategy import Strategy


class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(
        Integer,
        ForeignKey("strategies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # user_id might be useful if backtests are user-specific and strategy could be shared/template
    # user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    name = Column(String, nullable=True)  # Optional name for the backtest run
    description = Column(Text, nullable=True)  # Optional description

    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)

    initial_capital = Column(Numeric(19, 8), nullable=False)
    final_capital = Column(Numeric(19, 8), nullable=False)

    total_pnl = Column(Numeric(19, 8), nullable=False)  # Profit and Loss
    pnl_percentage = Column(Numeric(10, 4), nullable=False)  # (total_pnl / initial_capital) * 100

    total_trades = Column(Integer, nullable=False)
    winning_trades = Column(Integer, nullable=False)
    losing_trades = Column(Integer, nullable=False)
    neutral_trades = Column(Integer, default=0)  # Trades with zero profit/loss

    win_rate = Column(Numeric(7, 4), nullable=True)  # winning_trades / (winning_trades + losing_trades)

    max_drawdown_abs = Column(Numeric(19, 8), nullable=True)  # Absolute max drawdown value
    max_drawdown_pct = Column(Numeric(7, 4), nullable=True)  # Max drawdown percentage

    sharpe_ratio = Column(Numeric(10, 4), nullable=True)
    sortino_ratio = Column(Numeric(10, 4), nullable=True)
    calmar_ratio = Column(Numeric(10, 4), nullable=True)

    avg_trade_pnl = Column(Numeric(19, 8), nullable=True)
    avg_winning_trade = Column(Numeric(19, 8), nullable=True)
    avg_losing_trade = Column(Numeric(19, 8), nullable=True)
    profit_factor = Column(Numeric(10, 4), nullable=True)  # Gross Profit / Gross Loss

    # Parameters used for this specific backtest run.
    # Using JSON type is better for structured data if DB supports it (e.g. PostgreSQL JSONB)
    parameters_used = Column(JSON, nullable=True)
    # Full trade log or summary could be stored as JSON or Text, or in a separate table if very large
    trade_log_summary = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    # updated_at if results can be re-calculated or annotated
    # updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    strategy = relationship("Strategy", back_populates="backtest_results")
    # user = relationship("User") # if user_id is added

    __table_args__ = (
        Index(
            "ix_backtest_result_strategy_id_created_at",
            "strategy_id",
            "created_at",
            unique=False,
        ),  # A strategy can have multiple backtests
        # Index("ix_backtest_result_user_id_created_at", "user_id", "created_at"), # if user_id is added
    )

    def __repr__(self):
        return (
            f"<BacktestResult(id={self.id}, strategy_id={self.strategy_id}, "
            f"name='{self.name}', pnl_pct={self.pnl_percentage})>"
        )
