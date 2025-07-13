# Expose key components of the ai_trader package

# Auth context for audit logging and user identification
# Configuration
# Models
# Event listeners for audit logging (registration is usually handled internally)
from . import auth_context, config, event_listeners, models
from .auth_context import get_current_user_id, set_current_user_id
from .config import settings
# Database session and initialization
from .db import \
    session as \
    db_session  # Alias to avoid conflict if 'session' is used locally
from .db.session import SessionLocal, get_db

__all__ = [
    "auth_context",
    "get_current_user_id",
    "set_current_user_id",
    "event_listeners",
    "db_session",
    "get_db",
    "SessionLocal",
    "models",
    "settings",
    "config",
]

# Ensure event listeners are registered when this package is imported at a high level.
# This is now the primary place for registration to avoid circular imports.
# The event_listeners module is imported above as `from . import event_listeners`.

# Ensure all necessary modules (like db.session for engine setup, models) are initialized
# before registering listeners, if there are such implicit dependencies for the listeners
# to function correctly (e.g. models being fully defined).
# Given the typical import order, this should be fine here.
event_listeners.register_audit_listeners()

print("AI Trader package initialized. Audit listeners registered.")
