import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from .base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    table_name = Column(String, nullable=False)
    record_id = Column(Integer, nullable=False)
    action = Column(String, nullable=False)
    changed_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    changes = Column(JSON, nullable=True)

    def __repr__(self):
        return (
            f"<AuditLog(id={self.id}, table='{self.table_name}', record_id='{self.record_id}', "
            f"action='{self.action}', user_id={self.changed_by})>"
        )
