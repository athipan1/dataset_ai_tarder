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
    # Add updated_at for consistency if other tables have it, good practice
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    strategies = relationship("Strategy", back_populates="user")
    orders = relationship("Order", back_populates="user")
    trades = relationship("Trade", back_populates="user")  # Assuming Trade model has a user relationship

    __table_args__ = (
        Index("ix_user_username", "username"),
        Index("ix_user_email", "email"),
    )

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
