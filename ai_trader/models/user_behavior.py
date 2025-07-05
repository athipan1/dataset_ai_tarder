from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ai_trader.db.base import Base


class UserBehaviorLog(Base):
    __tablename__ = "user_behavior_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action_type = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    session_id = Column(String, index=True)
    meta_data = Column(JSON)  # Or Text if JSON is not supported/desired

    user = relationship("User", back_populates="behavior_logs")

    def __repr__(self):
        return f"<UserBehaviorLog(id={self.id}, user_id={self.user_id}, action_type='{self.action_type}')>"
