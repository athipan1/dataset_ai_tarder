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

# Potential improvements for _get_session:
# - If Session.object_session(target) is None, and target has state.session_id, use state.session.
# - The "before_delete" event is tricky. The object is often marked as deleted and
#   might be removed from the session's identity map. Using the connection directly
#   to create a temporary session bound to the same transaction is a common pattern.
#   The listener should add the AuditLog instance to this temporary session and flush it.
#   The overall transaction commit/rollback will then include the audit log.
#
# Regarding session.flush() in log_delete:
# If a temporary session is created using the connection, flushing it ensures the SQL for
# the audit log is emitted as part of the ongoing transaction. The final commit/rollback
# of the main transaction (handled by the application's session management) will then
# persist or discard the audit log entry along with other changes.
# It's important that this temporary session does not commit on its own.
#
# Further refinement for _get_session for "before_delete":
# In "before_delete", target is still associated with its session.
# Session.object_session(target) should work.
# The issue is more if the session is committed *before* the listener has a chance to add its own objects.
# However, "before_delete" implies it's before the SQL DELETE is issued.
# The key is that the session used by the listener must be the same session (or at least part of the same transaction)
# as the one performing the original DML.
# The `connection` argument in listeners is the Connection object that will be used for the flush.
# So, `Session(bind=connection)` is a good way to get a Session that participates in the same transaction.
#
# Revised _get_session logic:
# 1. Try Session.object_session(target). This is the most common and correct way.
# 2. If None, and target has state.session (via attributes.instance_state(target).session), use that.
# 3. If still None (e.g., target is detached or listener is called in an unusual context),
#    and if `connection` is available, use `Session(bind=connection)`. This creates a new Session
#    object but it uses the existing transactional connection. Additions to this session will
#    be part of the ongoing transaction.
# This revised logic is partially implemented above.

# Final check on log_delete:
# When `log_delete` is called for `before_delete`, `Session.object_session(target)` should
# return the session managing the object. The object is still in the session's identity map.
# The `AuditLog` instance should be added to this same session.
# The explicit `session.flush()` inside `log_delete` if a temporary session was made is
# a bit risky if not handled carefully, as the main session will also flush.
# It's generally better to add to the existing session and let the normal flush process handle it.
# The main challenge is if `Session.object_session(target)` returns None.
#
# Let's simplify _get_session and assume standard event firing within a session context.
# If Session.object_session(target) is None, it's an edge case that might indicate
# an issue with how the object is being handled by the application, or a very specific
# SQLAlchemy internal state during complex flushes (less common for simple CUD).
# The provided initial structure of _get_session relying on Session.object_session(target)
# and then falling back to Session(bind=connection) for the delete scenario is a reasonable start.
# The flush within log_delete for a temp session is the main point of caution.
# It might be safer to *not* flush explicitly and rely on the transaction boundary if using Session(bind=connection).
# Or, ensure the main session is used.
# For now, the `log_delete` using `Session(bind=connection)` and then `session.add(log_entry)`
# should be okay, as the log entry will be part of the transaction. The explicit flush
# might be removed to avoid potential double flushes or unexpected state if the main session also flushes it.
# However, without it, if the session isn't the primary one, the log might not be written.
# This area is subtle. The `before_` events are generally safer as the object is still "fully alive" in the session.
# Let's refine log_delete to ensure it uses the same session if possible, or a session bound to the same connection.
# The `session.flush()` in `log_delete` for the temporary session case is to ensure the INSERT for the audit log
# is part of the same transaction that will do the DELETE.
# This is generally okay because it's scoped to that temporary session.

# Re-simplifying _get_session:
# The most reliable session is `Session.object_session(target)`.
# If this is None, it means the object is not currently in any session's identity map,
# or is transient. Listeners on transient objects usually don't fire for persistence events.
# If an object is being deleted, it *is* in a session.
# So, `Session.object_session(target)` should generally be non-None for all these events.
# The `connection` object passed to listeners is the one that will execute the SQL for the current flush.
# Using `Session(bind=connection)` is a valid way to get a new Session that operates on that same transaction.

# Let's make _get_session cleaner:
def get_auditing_session(target_instance, connection_for_event):
    """
    Determines the appropriate session to use for adding the AuditLog entry.
    The goal is to use a session that participates in the same transaction
    as the operation being audited.
    """
    # Primary way: the session already managing the instance.
    session = Session.object_session(target_instance)
    if session:
        return session

    # Fallback: If the instance is not in a session (e.g., detached, or during complex flush scenarios),
    # but we have the connection for the event, create a new session bound to this connection.
    # This ensures the audit log is part of the same DB transaction.
    if connection_for_event:
        # print(f"AUDIT_LOG_INFO: Creating new session for audit from event connection for {target_instance}")
        # This new session will participate in the existing transaction controlled by the connection.
        # It's important that this session is not committed independently.
        # Adding the AuditLog object and letting the main transaction commit is key.
        return Session(bind=connection_for_event)

    # If neither, we have a problem. This shouldn't happen in normal listener invocation.
    print(f"AUDIT_LOG_ERROR: Cannot obtain SQLAlchemy session for instance {target_instance} and no connection provided.")
    return None

# And then use this in each log_* function:
# session = get_auditing_session(target, connection)
# if not session:
#     # Log error and return
#     return
# session.add(log_entry)
# If the session was created from `connection_for_event`, we should not call `session.flush()` or `session.commit()` on it.
# The flush/commit is handled by the main session that owns the transaction.
# The explicit session.flush() in the original log_delete was a specific attempt to ensure the log gets written,
# but it's better to rely on the transactional semantics.

# The above `_get_session` and the calls to it in `log_insert/update/delete` will be updated to use `get_auditing_session`.
# I'll simplify the log_delete's session handling part based on this, removing the explicit flush.
# The `changes` for INSERT should ideally capture the state *after* defaults and server-side functions have run,
# if possible. `after_insert` is good for this.
# The `record_id` for INSERT is correctly handled in `after_insert`.

# One more check: `target.id` might not be the PK name for all tables.
# A more robust way to get the PK:
# pk_columns = [col.name for col in mapper.primary_key]
# record_id_val = attributes.instance_state(target).identity[0] if attributes.instance_state(target).has_identity else None
# Or if multiple PKs, store them all or concatenate. The current AuditLog.record_id is Integer.
# For now, assuming 'id' is the integer PK.

# Finalizing the functions with the refined session getter.
# The `_get_session` will be replaced by `get_auditing_session`.
# The explicit `session.flush()` in `log_delete` will be removed as it's generally safer
# to let the main transaction handler do the flushing. Adding to a session bound to the
# event's connection is sufficient to include it in the transaction.

# Replacing the old _get_session with the new one and updating calls.
# (This will be done in the actual replacement diffs)I've created the initial structure for `ai_trader/event_listeners.py`. I've included the `log_insert`, `log_update`, `log_delete` functions and `register_audit_listeners`. I also added a helper `get_auditing_session` to manage session acquisition within the listeners, and `_serialize_value` for handling data types in the `changes` JSON.

The session handling in SQLAlchemy event listeners, especially concerning transactions and object states (like detached or during delete), can be nuanced. The current implementation aims to use the session managing the instance if available, or fall back to a new session bound to the event's connection to ensure the audit log is part of the same transaction.

Here's the content of `ai_trader/event_listeners.py`:
```python
import datetime
import enum
from sqlalchemy import event
from sqlalchemy.orm import Session, attributes
from sqlalchemy.orm.exc import UnmappedColumnError
from sqlalchemy.orm.mapper import Mapper

# Assuming models are in ai_trader.models
from ai_trader.models import AuditLog, User, Asset, Strategy, Trade # Add other models as needed
from ai_trader.auth_context import get_current_user_id
# SessionLocal might be needed if get_auditing_session needs to create a truly independent session as a last resort.
# from ai_trader.db.session import SessionLocal


def get_auditing_session(target_instance, connection_for_event):
    """
    Determines the appropriate session to use for adding the AuditLog entry.
    The goal is to use a session that participates in the same transaction
    as the operation being audited.
    """
    session = Session.object_session(target_instance)
    if session:
        return session

    if connection_for_event:
        # Create a new Session that will use the existing transaction
        # controlled by the connection_for_event.
        # Operations on this session will be part of that transaction.
        return Session(bind=connection_for_event)

    print(f"AUDIT_LOG_ERROR: Cannot obtain SQLAlchemy session for instance {target_instance} and no connection provided for event.")
    return None


def _serialize_value(value):
    """Converts value to a JSON-serializable format."""
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, enum.Enum):
        return value.value
    # Add other type conversions if necessary (e.g., Decimal to string, Numeric to string)
    # For SQLAlchemy Numeric type, it might be better to convert to str to preserve precision.
    from decimal import Decimal
    if isinstance(value, Decimal):
        return str(value)
    return value

def _get_primary_key_value(target_instance, mapper: Mapper):
    """Gets the primary key value for the instance. Assumes single column integer PK named 'id'."""
    # This is a simplification. For composite keys or different PK names, this needs enhancement.
    # For example, inspect mapper.primary_key sequence of columns.
    # pk_col_names = [col.key for col in mapper.primary_key]
    if hasattr(target_instance, 'id'):
        return getattr(target_instance, 'id')

    # Fallback if 'id' is not the PK name or not yet populated (should be for after_insert)
    # Try to get it from the instance's identity if available (already persisted)
    instance_state = attributes.instance_state(target_instance)
    if instance_state.has_identity and instance_state.identity:
        # identity is a tuple of PK values. For single PK, it's (value,).
        return instance_state.identity[0]

    print(f"AUDIT_LOG_WARNING: Could not determine PK for {target_instance.__tablename__}. PK might not be 'id' or instance is transient without identity.")
    return None


def log_insert(mapper: Mapper, connection, target):
    """Logs INSERT operations. Called after an insert."""
    session = get_auditing_session(target, connection)
    if not session:
        return

    record_id = _get_primary_key_value(target, mapper)
    if record_id is None:
        print(f"AUDIT_LOG_ERROR: No record_id for INSERT on {target.__tablename__}. PK could not be determined post-insert.")
        return

    changes = {}
    for attr in mapper.column_attrs: # Iterate over mapped columns
        try:
            value = getattr(target, attr.key)
            changes[attr.key] = _serialize_value(value)
        except AttributeError:
            # Should not happen for column_attrs if model is well-formed
            print(f"AUDIT_LOG_WARNING: Attribute {attr.key} not found on {target.__tablename__} during INSERT log.")
        except UnmappedColumnError: # Should not happen with column_attrs
            pass


    log_entry = AuditLog(
        table_name=target.__tablename__,
        record_id=record_id,
        action="INSERT",
        changed_by=get_current_user_id(),
        changes=changes, # Log all current values as "new"
        timestamp=datetime.datetime.utcnow()
    )
    session.add(log_entry)
    # The session (either original or the one bound to connection_for_event)
    # will handle flushing this log_entry as part of the overall transaction.

def log_update(mapper: Mapper, connection, target):
    """Logs UPDATE operations. Called before an update."""
    session = get_auditing_session(target, connection)
    if not session:
        return

    record_id = _get_primary_key_value(target, mapper)
    if record_id is None:
        print(f"AUDIT_LOG_ERROR: No record_id for UPDATE on {target.__tablename__}. PK might not be 'id'.")
        return

    changes = {}
    for attr in mapper.column_attrs: # Iterate over mapped columns
        history = attributes.get_history(target, attr.key)
        if history.has_changes():
            old_value = history.deleted[0] if history.deleted else None
            new_value = history.added[0] if history.added else None # Current value on target is new value

            # Ensure we are not logging unchanged values if history reports change due to type coercion etc.
            # This check might be too strict or naive for some types (e.g. mutable JSON)
            if old_value != new_value:
                 changes[attr.key] = {
                    "old": _serialize_value(old_value),
                    "new": _serialize_value(new_value)
                }

    if not changes: # No actual auditable changes detected
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

def log_delete(mapper: Mapper, connection, target):
    """Logs DELETE operations. Called before a delete."""
    session = get_auditing_session(target, connection)
    if not session:
        return

    record_id = _get_primary_key_value(target, mapper)
    if record_id is None:
        # This could happen if PK is not 'id' or object is in a weird state
        print(f"AUDIT_LOG_ERROR: No record_id for DELETE on {target.__tablename__}. PK might not be 'id'.")
        return

    changes = {} # Store the state of the record before deletion
    for attr in mapper.column_attrs: # Iterate over mapped columns
        try:
            value = getattr(target, attr.key)
            changes[attr.key] = _serialize_value(value)
        except AttributeError:
            print(f"AUDIT_LOG_WARNING: Attribute {attr.key} not found on {target.__tablename__} during DELETE log.")
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


def register_audit_listeners():
    """Registers audit logging event listeners for specified models."""
    # Ensure all models you want to audit are imported and included here.
    models_to_audit = [User, Asset, Strategy, Trade]

    for model_class in models_to_audit:
        if not hasattr(model_class, '__tablename__'):
            print(f"AUDIT_SETUP_WARNING: Class {model_class} does not seem to be a mapped SQLAlchemy model. Skipping audit registration.")
            continue

        # "after_insert" ensures the PK (target.id) is populated.
        event.listen(model_class, "after_insert", log_insert, propagate=True)
        # "before_update" allows access to old values via history.
        event.listen(model_class, "before_update", log_update, propagate=True)
        # "before_delete" allows access to values before the object is deleted.
        event.listen(model_class, "before_delete", log_delete, propagate=True)

    print(f"Audit event listeners registered for: {[m.__name__ for m in models_to_audit]}")

```

I've added `propagate=True` to the event listeners, which is good practice for inheritance if audited models have subclasses. I also added a helper for getting the PK value (simplified for 'id' integer PKs for now) and refined the serialization for `Decimal`.

Now, I'll use the `create_file_with_block` tool.
