import datetime
import enum
import logging

from sqlalchemy import event
from sqlalchemy.orm import Session, attributes
from sqlalchemy.orm.exc import UnmappedColumnError

from ai_trader.auth_context import get_current_user_id
from ai_trader.models import Asset, AuditLog, Strategy, Trade, User

logger = logging.getLogger(__name__)

def _get_session(target_instance, connection=None) -> Session:
    """Gets a session for logging, prioritizing the object's session."""
    session = Session.object_session(target_instance)
    if session:
        return session
    if connection:
        return Session(bind=connection)
    logger.error(f"Could not obtain session for {target_instance}. Audit log may not be saved.")
    return None

def _serialize_value(value):
    """Converts value to a JSON-serializable format."""
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    if isinstance(value, enum.Enum):
        return value.value
    return value

def log_insert(mapper, connection, target):
    """Logs INSERT operations."""
    session = _get_session(target, connection)
    if not session:
        return

    record_id = getattr(target, 'id', None)
    if record_id is None:
        logger.error(f"No record_id for INSERT on {target.__tablename__}. PK might not be 'id' or not populated.")
        return

    changes = {attr.key: _serialize_value(getattr(target, attr.key, None)) for attr in mapper.column_attrs}

    log_entry = AuditLog(
        table_name=target.__tablename__,
        record_id=record_id,
        action="INSERT",
        changed_by=get_current_user_id(),
        changes=changes,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    session.add(log_entry)

def log_update(mapper, connection, target):
    """Logs UPDATE operations."""
    session = _get_session(target, connection)
    if not session:
        return

    record_id = getattr(target, 'id', None)
    if record_id is None:
        logger.error(f"No record_id for UPDATE on {target.__tablename__}. PK might not be 'id'.")
        return

    changes = {}
    for attr in mapper.column_attrs:
        history = attributes.get_history(target, attr.key)
        if history.has_changes():
            old_value = history.deleted[0] if history.deleted else None
            new_value = history.added[0] if history.added else None
            changes[attr.key] = {"old": _serialize_value(old_value), "new": _serialize_value(new_value)}

    if not changes:
        return

    log_entry = AuditLog(
        table_name=target.__tablename__,
        record_id=record_id,
        action="UPDATE",
        changed_by=get_current_user_id(),
        changes=changes,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    session.add(log_entry)

def log_delete(mapper, connection, target):
    """Logs DELETE operations."""
    session = _get_session(target, connection)
    if not session:
        return

    record_id = getattr(target, 'id', None)
    if record_id is None:
        logger.error(f"No record_id for DELETE on {target.__tablename__}. PK might not be 'id'.")
        return

    changes = {attr.key: _serialize_value(getattr(target, attr.key, None)) for attr in mapper.column_attrs}

    log_entry = AuditLog(
        table_name=target.__tablename__,
        record_id=record_id,
        action="DELETE",
        changed_by=get_current_user_id(),
        changes=changes,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    session.add(log_entry)

    if session.bind == connection:
        try:
            session.flush()
        except Exception as e:
            logger.error(f"Failed to flush audit log for DELETE: {e}")
            session.rollback()

def register_audit_listeners():
    """Registers audit logging event listeners for specified models."""
    models_to_audit = [User, Asset, Strategy, Trade]
    for model_class in models_to_audit:
        event.listen(model_class, "after_insert", log_insert)
        event.listen(model_class, "before_update", log_update)
        event.listen(model_class, "before_delete", log_delete)
    logger.info("Audit event listeners registered.")
