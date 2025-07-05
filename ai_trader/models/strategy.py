from sqlalchemy import Column, Integer, String, Text, ForeignKey, Index
from sqlalchemy.orm import relationship

from ai_trader.db.base import Base


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    owner = relationship("User")  # Establishes a relationship to the User model

    __table_args__ = (
        Index("ix_strategy_name", "name"),
        Index("ix_strategy_user_id", "user_id"),
    )

    def __repr__(self):
        return f"<Strategy(id={self.id}, name='{self.name}')>"
