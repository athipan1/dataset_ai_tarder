import datetime
import enum
from sqlalchemy import event
from sqlalchemy.orm import Session, attributes
from sqlalchemy.orm.exc import UnmappedColumnError

from ai_trader.models import AuditLog, User, Asset, Strategy, Trade # Add other models as needed
from ai_trader.auth_context import get_current_user_id
from ai_trader.db.session import SessionLocal # To create a session if one isn't available

def _get_session(target_instance, connection=None):
    """Gets or creates a session for logging."""
    session = Session.object_session(target_instance)
    if session:
        return session
    # If the instance is not associated with a session (e.g., during deletion flush),
    # try to use the connection to get a session or create a new one.
    # This is a fallback and might need careful handling depending on transaction semantics.
    if connection:
        # Try to get a session associated with the connection if possible
        # This part is tricky as SA doesn't directly expose session from connection easily
        # in all contexts. Creating a new session might be safer if audit is critical.
        # For now, let's create a new one, assuming changes will be committed with the main transaction.
        # This needs to be tested carefully.
        # A more robust solution might involve passing the session explicitly if available.
        temp_session = Session(bind=connection)
        return temp_session

    # Fallback: create a new session from SessionLocal if no connection either
    # This is less ideal as it's a separate transaction for the audit log.
    # print("Warning: Creating a new session for audit logging. Ensure this is intended.")
    # return SessionLocal()
    # For safety, let's rely on object_session or session from connection
    # and if neither, it implies a more complex state we might not want to auto-handle with new session.
    # The listeners are usually called within a session context.
    # Let's assume Session.object_session(target) will mostly work.
    # If target is detached, it's an issue.

    # Simpler approach for now: rely on object_session. If it's None, the target might be transient
    # or detached in a way that makes auditing difficult without explicit session passing.
    # The listeners are typically invoked when the instance is part of a session's flush process.
    if not session:
        # This case should be rare for "before_update", "before_delete", "after_insert"
        # when an object is actually being persisted.
        # If it happens, it means the object isn't managed by a session that's flushing.
        # For "before_delete", target might be in a "deleted" state but still session-aware.
        # For "after_insert", target is definitely session-aware.
        # For "before_update", target is session-aware.
        # print(f"Warning: Could not obtain session for {target_instance}. Audit log may not be saved.")
        # A possible scenario for None session is if an object is created but not added to a session,
        # then modified. But SQLAlchemy events typically fire on session flush.
        # A more robust way if Session.object_session(target) is None,
        # is to check if the target has an active instrumented state manager with a session.
        state = attributes.instance_state(target_instance)
        if state.session_id:
            session = state.session
        elif connection: # Fallback to using the connection if available
             # This is more for "before_delete" where the object might be expunged
             # but the connection is still valid for the transaction.
            session = Session(bind=connection)


    if not session:
        # As a last resort if no session is found, we might need to create one.
        # This is often discouraged within event listeners if it starts a new transaction
        # that's not part of the main one. However, for audit logging, it might be acceptable
        # if the alternative is no log.
        # print(f"Warning: Creating a new temporary session for AuditLog for {target_instance}")
        # temp_session_for_audit = SessionLocal()
        # # We need to ensure this session is closed.
        # # This approach is problematic due to session management.
        # # A better way is to ensure listeners are called with active sessions.
        # # For now, let's assume the standard listeners will have a session via object_session or connection.
        pass

    return session


def _serialize_value(value):
    """Converts value to a JSON-serializable format."""
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, enum.Enum):
        return value.value
    # Add other type conversions if necessary (e.g., Decimal to string)
    # For most basic types (str, int, float, bool, list, dict), it's fine.
    return value

def log_insert(mapper, connection, target):
    """Logs INSERT operations."""
    session = _get_session(target, connection)
    if not session:
        print(f"AUDIT_LOG_ERROR: No session for INSERT on {target.__tablename__} {target.id if hasattr(target, 'id') else ''}")
        return

    # Ensure target.id is available after insert (it should be post-flush)
    # The "after_insert" event guarantees the PK is populated.
    record_id = getattr(target, 'id', None)
    if record_id is None:
        # This should not happen for "after_insert" if 'id' is the PK.
        # If composite PK or different PK name, this needs adjustment.
        print(f"AUDIT_LOG_ERROR: No record_id for INSERT on {target.__tablename__}. PK might not be 'id' or not populated.")
        return

    changes = {}
    for attr in mapper.column_attrs:
        try:
            changes[attr.key] = _serialize_value(getattr(target, attr.key))
        except AttributeError:
            # This might happen for some internal attributes or unmapped ones.
            pass
        except UnmappedColumnError: # Should not happen with column_attrs
            pass


    log_entry = AuditLog(
        table_name=target.__tablename__,
        record_id=record_id,
        action="INSERT",
        changed_by=get_current_user_id(),
        changes=changes,
        timestamp=datetime.datetime.utcnow()
    )
    session.add(log_entry)
    # The session that `target` is part of will handle flushing this log_entry.

def log_update(mapper, connection, target):
    """Logs UPDATE operations."""
    session = _get_session(target, connection)
    if not session:
        print(f"AUDIT_LOG_ERROR: No session for UPDATE on {target.__tablename__} {target.id}")
        return

    record_id = getattr(target, 'id', None)
    if record_id is None:
        print(f"AUDIT_LOG_ERROR: No record_id for UPDATE on {target.__tablename__}. PK might not be 'id'.")
        return

    changes = {}
    for attr in mapper.column_attrs:
        history = attributes.get_history(target, attr.key)
        if history.has_changes():
            old_value = history.deleted[0] if history.deleted else None
            new_value = history.added[0] if history.added else None
            changes[attr.key] = {
                "old": _serialize_value(old_value),
                "new": _serialize_value(new_value)
            }

    if not changes: # No auditable changes detected
        return

    log_entry = AuditLog(
        table_name=target.__tablename__,
        record_id=record_id,
        action="UPDATE",
        changed_by=get_current_user_id(),
        changes=changes,
        timestamp=datetime.datetime.utcnow()
    )
    session.add(log_entry)

def log_delete(mapper, connection, target):
    """Logs DELETE operations."""
    session = _get_session(target, connection)
    if not session:
        # For delete, the object might be detached from its original session
        # but the connection should still be valid for the transaction.
        # Let's try creating a temporary session with the connection.
        if connection:
            session = Session(bind=connection)
        else:
            print(f"AUDIT_LOG_ERROR: No session or connection for DELETE on {target.__tablename__} {target.id}")
            return


    record_id = getattr(target, 'id', None)
    if record_id is None:
        print(f"AUDIT_LOG_ERROR: No record_id for DELETE on {target.__tablename__}. PK might not be 'id'.")
        return

    changes = {} # Store the state of the record before deletion
    for attr in mapper.column_attrs:
        try:
            changes[attr.key] = _serialize_value(getattr(target, attr.key))
        except AttributeError:
            pass
        except UnmappedColumnError:
            pass


    log_entry = AuditLog(
        table_name=target.__tablename__,
        record_id=record_id,
        action="DELETE",
        changed_by=get_current_user_id(),
        changes=changes, # Log current values as "old" values effectively
        timestamp=datetime.datetime.utcnow()
    )
    session.add(log_entry)
    if session.bind == connection : # If we created a temp session for delete
        try:
            session.flush() # Ensure the log is written within the same transaction
        except Exception as e:
            print(f"AUDIT_LOG_ERROR: Failed to flush audit log for DELETE: {e}")
            session.rollback() # Rollback this temp session part
        finally:
            # Do not close if it's using an externally managed connection.
            # session.close() # Only if we fully manage this session.
            # For safety, if we created a session(bind=connection), we should let the outer transaction handle commit/rollback.
            # Flushing is enough to get it into the transaction's scope.
            pass


def register_audit_listeners():
    """Registers audit logging event listeners for specified models."""
    models_to_audit = [User, Asset, Strategy, Trade] # Extend this list as needed

    for model_class in models_to_audit:
        event.listen(model_class, "after_insert", log_insert)
        event.listen(model_class, "before_update", log_update)
        event.listen(model_class, "before_delete", log_delete)

    print("Audit event listeners registered.")
