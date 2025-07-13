# Expose key components of the ai_trader package

# Auth context for audit logging and user identification
# Configuration
# Models
# Event listeners for audit logging (registration is usually handled internally)
from . import event_listeners, models

# Database session and initialization
from .db import (
    session as db_session,
)  # Alias to avoid conflict if 'session' is used locally
from .models import *  # Expose all models for convenience

__all__ = [
    "auth_context",
    "get_current_user_id",
    "set_current_user_id",
    "event_listeners",
    "db_session",
    "get_db",
    "SessionLocal",
    "models",
    # All model names will be included by "from .models import *"
    # but we can also list them explicitly if preferred, by importing them here.
    "settings",
    "config",
]

# Add all model names to __all__ to make them available via "from ai_trader import User"
# This requires models.__all__ to be defined, which it is.
if hasattr(models, "__all__"):
    __all__.extend(models.__all__)
    # Remove duplicates that might have been added manually above if any
    __all__ = sorted(list(set(__all__)))
else:
    # Fallback if models.__all__ is not defined (though it is in our case)
    # This would require listing them manually or introspecting models.Base.metadata.tables
    pass

# Ensure event listeners are registered when this package is imported at a high level.
# This is now the primary place for registration to avoid circular imports.
# The event_listeners module is imported above as `from . import event_listeners`.

# Ensure all necessary modules (like db.session for engine setup, models) are initialized
# before registering listeners, if there are such implicit dependencies for the listeners
# to function correctly (e.g. models being fully defined).
# Given the typical import order, this should be fine here.
event_listeners.register_audit_listeners()

print("AI Trader package initialized. Audit listeners registered.")
