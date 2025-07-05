from sqlalchemy import Column, Integer, String, Text, ForeignKey, Index, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ai_trader.db.base import Base

# Ensure User is imported if type hinting is needed, or use string reference "User"
# from .user import User


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    model_version = Column(String, nullable=True)  # From original root models.py
    parameters = Column(
        JSON, nullable=True
    )  # From original root models.py. For PG, use sqlalchemy.dialects.postgresql.JSONB

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    user = relationship("User", back_populates="strategies")
    signals = relationship("Signal", back_populates="strategy")
    orders = relationship("Order", back_populates="strategy")
    backtest_results = relationship("BacktestResult", back_populates="strategy")

    __table_args__ = (
        Index(
            "ix_strategy_user_id_name", "user_id", "name", unique=True
        ),  # A user shouldn't have two strategies with the same name
        Index(
            "ix_strategy_name", "name"
        ),  # Retain if searching by name across users is common
        # user_id is already indexed by ForeignKey constraint implicitly for many DBs, but explicit index is fine.
    )

    def __repr__(self):
        return f"<Strategy(id={self.id}, name='{self.name}', user_id={self.user_id})>"
