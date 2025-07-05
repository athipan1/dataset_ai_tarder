from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ai_trader.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    behavior_logs = relationship("UserBehaviorLog", back_populates="user")
    trade_analytics = relationship("TradeAnalytics", back_populates="user")
    strategies = relationship("Strategy", back_populates="owner") # Assuming you want to access strategies from user

    __table_args__ = (
        Index("ix_user_username", "username"),
        Index("ix_user_email", "email"),
    )

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
