import enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as DBEnum, Index
from sqlalchemy.sql import func
from ai_trader.db.base import Base
# Potentially use JSONB for PostgreSQL for changed_fields if it's structured data
from sqlalchemy import JSON

class AuditAction(enum.Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE" # Could be soft delete or hard delete if that's ever used
    LOGIN = "LOGIN"   # Example of a custom action
    LOGOUT = "LOGOUT" # Example of a custom action
    ACCESS = "ACCESS" # Example for read actions if needed

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    # Who performed the action. Nullable if system action or user not available.
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    action = Column(DBEnum(AuditAction), nullable=False, index=True)

    table_name = Column(String, nullable=True, index=True) # Name of the table affected
    record_pk = Column(String, nullable=True, index=True) # Primary key of the record affected (as string to be generic)

    # Store old and new values, or just the changes. JSON is flexible.
    # For UPDATEs, this could store {field: [old_value, new_value]}
    # For CREATEs, this could store {field: new_value}
    # For DELETEs, this could store {field: old_value}
    changed_fields = Column(JSON, nullable=True)

    comment = Column(Text, nullable=True) # Optional comment, e.g., reason for manual change

    ip_address = Column(String, nullable=True) # IP address of the request originator
    user_agent = Column(String, nullable=True) # User agent of the request originator

    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # No relationships defined back from other tables to AuditLog to keep them clean.
    # AuditLogs are typically queried directly.

    __table_args__ = (
        Index("ix_audit_log_user_action_timestamp", "user_id", "action", "timestamp"),
        Index("ix_audit_log_table_record_timestamp", "table_name", "record_pk", "timestamp"),
    )

    def __repr__(self):
        return f"<AuditLog(id={self.id}, user_id={self.user_id}, action='{self.action.value}', table='{self.table_name}', record_pk='{self.record_pk}')>"
