from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Optional

from pydantic import BaseModel


class CurrentUser(BaseModel):
    """Pydantic model to represent the current user in context."""

    user_id: int
    username: str
    is_superuser: bool = False
    # Add other relevant fields like email, roles, permissions if needed


# ContextVar to hold the current user object (or None)
USER_CONTEXT: ContextVar[Optional[CurrentUser]] = ContextVar(
    "user_context", default=None
)

# Keep the old current_user_id for AuditLog compatibility for now,
# but new code should prefer using USER_CONTEXT and CurrentUser object.
current_user_id_context_var: ContextVar[Optional[int]] = ContextVar(
    "current_user_id_context_var", default=None
)


@contextmanager
def auth_context(user: Optional[CurrentUser]):
    """
    A context manager to set the current user in the context.
    Also sets the user_id in the old context var for compatibility.
    """
    token_user: Optional[Token] = None
    token_id: Optional[Token] = None
    if user:
        token_user = USER_CONTEXT.set(user)
        token_id = current_user_id_context_var.set(user.user_id)
    else:
        # Explicitly set to None if user is None
        token_user = USER_CONTEXT.set(None)
        token_id = current_user_id_context_var.set(None)
    try:
        yield
    finally:
        if token_user:
            USER_CONTEXT.reset(token_user)
        if token_id:
            current_user_id_context_var.reset(token_id)


def get_current_user() -> CurrentUser:
    """
    Retrieves the current user from the context.
    Raises LookupError if no user is set.
    """
    user = USER_CONTEXT.get()
    if user is None:
        raise LookupError("User not found in context. Ensure auth_context is used.")
    return user


def get_current_user_or_none() -> Optional[CurrentUser]:
    """
    Retrieves the current user from the context.
    Returns None if no user is set.
    """
    return USER_CONTEXT.get()


# --- Compatibility functions for existing AuditLog ---


def set_current_user_id(user_id: Optional[int]) -> Token:
    """
    Sets the current user's ID in the dedicated legacy context.
    Prefer using `auth_context` with a `CurrentUser` object for new code.
    """
    # This function is primarily for being called by legacy auth systems
    # that only have user_id. If a full CurrentUser object is available,
    # auth_context should be used, which also sets this.
    return current_user_id_context_var.set(user_id)


def get_current_user_id() -> Optional[int]:
    """
    Gets the current user's ID from the dedicated legacy context.
    Prefer using `get_current_user` or `get_current_user_or_none` for new code.
    """
    # Try to get from new context first if available
    current_user_obj = USER_CONTEXT.get()
    if current_user_obj:
        return current_user_obj.user_id
    # Fallback to old context var
    return current_user_id_context_var.get()


def reset_current_user_id(token: Token) -> None:
    """Resets the current_user_id_context_var using the provided token."""
    current_user_id_context_var.reset(token)


# Example usage of new system:
#
# from ai_trader.models import User as DBUser # Assuming your DB User model
#
# # In your authentication logic/middleware:
# async def get_authenticated_user_details(...) -> Optional[CurrentUser]:
#     db_user: Optional[DBUser] = await actual_authentication_logic(...)
#     if db_user and db_user.is_active:
#         return CurrentUser(user_id=db_user.id, username=db_user.username, is_superuser=db_user.is_superuser)
#     return None
#
# # In a FastAPI dependency or middleware:
# async def user_context_dependency(request: Request):
#     current_user_details = await get_authenticated_user_details(request)
#     with auth_context(current_user_details):
#         yield # Allows the request to be processed with user in context
#
# # In an endpoint:
# @app.get("/me")
# async def read_users_me(user: CurrentUser = Depends(get_current_user)): # Or use a dependency that calls get_current_user
#     return user
#
# # For audit logging that still relies on get_current_user_id():
# # The auth_context manager will ensure current_user_id_context_var is also set.
#
# # If you only have user_id and need to set it for audit logging (legacy path):
# # token_id = set_current_user_id(user_id_from_somewhere)
# # try:
# #     # do stuff
# # finally:
# #     reset_current_user_id(token_id)
