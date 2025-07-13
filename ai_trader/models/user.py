from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, SoftDeleteMixin


class User(SoftDeleteMixin, Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    strategies = relationship("Strategy", back_populates="user", passive_deletes=True)
    orders = relationship("Order", back_populates="user")
    behavior_logs = relationship(
        "UserBehaviorLog", back_populates="user", passive_deletes=True
    )
    trade_analytics = relationship(
        "TradeAnalytics", back_populates="user", passive_deletes=True
    )

    __table_args__ = (
        Index("ix_user_username", "username", unique=True),
        Index("ix_user_email", "email", unique=True),
    )

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
