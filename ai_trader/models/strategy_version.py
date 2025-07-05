from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, JSON, UniqueConstraint, Index
from sqlalchemy.sql import func
from ai_trader.db.base import Base

class StrategyVersion(Base):
    __tablename__ = "strategy_versions"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False, default=1) # Incremental version number for each strategy

    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    model_version = Column(String, nullable=True)
    parameters = Column(JSON, nullable=True)
    # Potentially other fields from Strategy that should be versioned

    changed_at = Column(DateTime(timezone=True), server_default=func.now()) # Timestamp of when this version was created
    # changed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Optional: who made the change

    # No direct back_populates from Strategy to StrategyVersion to keep Strategy model cleaner.
    # Query versions directly using strategy_id.

    __table_args__ = (
        # Unique constraint on strategy_id and version_number
        # Consider Index("ix_strategy_version_strategy_id_version", "strategy_id", "version_number", unique=True),
        # However, if version_number is manually managed or could have gaps, a simple index might be better.
        # For now, assume version_number is programmatically incremented upon change.
        UniqueConstraint("strategy_id", "version_number", name="uq_strategy_id_version_number"),
        Index("ix_strategy_version_strategy_id", "strategy_id"), # Index for quick lookup of versions for a strategy
    )

    def __repr__(self):
        return f"<StrategyVersion(id={self.id}, strategy_id={self.strategy_id}, version={self.version_number})>"
