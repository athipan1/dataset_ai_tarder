from contextvars import ContextVar
from unittest.mock import patch

import pytest

from ai_trader.auth_context import (
    CurrentUser,
    auth_context,
    get_current_user,
    get_current_user_or_none,
)

# Assume User model is available for type hinting and creating mock user objects
from ai_trader.models import User

# Mock the ContextVar object used in auth_context.py
# This allows us to control its state during tests without affecting other tests
# or needing a real request context.
user_context_var: ContextVar[CurrentUser | None] = ContextVar(
    "user_context_var", default=None
)


@pytest.fixture(autouse=True)
def mock_user_context_var_in_module():
    """
    Patches the USER_CONTEXT in auth_context.py to use our test-controlled ContextVar.
    This ensures that calls to set/get on the context var within the auth_context module
    are using our mocked version.
    """
    with patch("ai_trader.auth_context.USER_CONTEXT", user_context_var):
        yield


@pytest.fixture
def mock_user_valid():
    """Provides a mock valid User object."""
    user = User(id=1, username="testuser", email="test@example.com")
    user.is_active = True
    user.is_superuser = False
    return CurrentUser(
        user_id=user.id, username=user.username, is_superuser=user.is_superuser
    )


@pytest.fixture
def mock_superuser_valid():
    """Provides a mock valid superuser User object."""
    user = User(id=2, username="superadmin", email="admin@example.com")
    user.is_active = True
    user.is_superuser = True
    return CurrentUser(
        user_id=user.id, username=user.username, is_superuser=user.is_superuser
    )


@pytest.fixture
def mock_user_inactive():
    """Provides a mock inactive User object - get_current_user should reject this if is_active was checked,
    but CurrentUser model itself doesn't have is_active. We'll assume the data passed to CurrentUser
    is already validated for activity if that's a requirement elsewhere."""
    user = User(id=3, username="inactiveuser", email="inactive@example.com")
    user.is_active = False
    user.is_superuser = False
    return CurrentUser(
        user_id=user.id, username=user.username, is_superuser=user.is_superuser
    )


def test_get_current_user_present(mock_user_valid):
    """Test get_current_user when a user is set in the context."""
    token = user_context_var.set(mock_user_valid)
    current_user = get_current_user()
    assert current_user is not None
    assert current_user.user_id == mock_user_valid.user_id
    assert current_user.username == mock_user_valid.username
    assert current_user.is_superuser == mock_user_valid.is_superuser
    user_context_var.reset(token)


def test_get_current_user_not_present_raises_exception():
    """Test get_current_user raises LookupError if no user is in context."""
    # Ensure context is empty
    # user_context_var.set(None) # Default is None, but explicitly set for clarity
    token = user_context_var.set(None)
    with pytest.raises(LookupError, match="User not found in context"):
        get_current_user()
    user_context_var.reset(token)


def test_get_current_user_or_none_present(mock_user_valid):
    """Test get_current_user_or_none when a user is set."""
    token = user_context_var.set(mock_user_valid)
    current_user = get_current_user_or_none()
    assert current_user is not None
    assert current_user.user_id == mock_user_valid.user_id
    user_context_var.reset(token)


def test_get_current_user_or_none_not_present_returns_none():
    """Test get_current_user_or_none returns None if no user is in context."""
    token = user_context_var.set(None)
    current_user = get_current_user_or_none()
    assert current_user is None
    user_context_var.reset(token)


def test_auth_context_manager_sets_and_resets_user(mock_user_valid):
    """Test the auth_context context manager correctly sets and resets the user."""
    assert (
        user_context_var.get() is None
    )  # Should be None initially or from fixture reset

    with auth_context(mock_user_valid):
        context_user = user_context_var.get()
        assert context_user is not None
        assert context_user.user_id == mock_user_valid.user_id
        assert context_user.username == mock_user_valid.username

    assert (
        user_context_var.get() is None
    )  # Should be reset to None after exiting context


def test_auth_context_manager_with_none_user():
    """Test the auth_context context manager with None user."""
    assert user_context_var.get() is None

    with auth_context(None):
        assert user_context_var.get() is None

    assert user_context_var.get() is None


def test_auth_context_manager_nested_contexts(mock_user_valid, mock_superuser_valid):
    """Test nested auth_context managers."""
    assert user_context_var.get() is None

    with auth_context(mock_user_valid):
        assert user_context_var.get().user_id == mock_user_valid.user_id
        with auth_context(mock_superuser_valid):
            assert user_context_var.get().user_id == mock_superuser_valid.user_id
        # Back to outer context
        assert user_context_var.get().user_id == mock_user_valid.user_id

    assert user_context_var.get() is None  # Back to initial state


def test_current_user_model_creation():
    """Test the CurrentUser Pydantic model can be created."""
    user_data = {"user_id": 10, "username": "pydantic_user", "is_superuser": False}
    current_user_obj = CurrentUser(**user_data)
    assert current_user_obj.user_id == 10
    assert current_user_obj.username == "pydantic_user"
    assert not current_user_obj.is_superuser

    user_data_super = {
        "user_id": 11,
        "username": "pydantic_super",
        "is_superuser": True,
    }
    current_user_super_obj = CurrentUser(**user_data_super)
    assert current_user_super_obj.user_id == 11
    assert current_user_super_obj.is_superuser


# Example of how one might test fallback if logic was more complex,
# For the current simple context var, direct set/get is primary.
# If get_current_user had fallback logic (e.g. to a system user if None),
# that would be tested here. The current version raises LookupError.

# No specific "reject wrong permissions" test here as get_current_user
# only retrieves. Permission checks would be done by the consumer of the user object.
# If get_current_user itself had logic to check user.is_active or similar and raise
# a specific error, that would be tested.
# For example, if get_current_user was:
# def get_current_user():
#     user = USER_CONTEXT.get()
#     if user is None:
#         raise LookupError("User not found")
#     if not user.is_active: # Assuming CurrentUser model had is_active
#         raise PermissionError("User is not active")
#     return user
# Then we would add a test for the PermissionError with an inactive user.
# However, the current CurrentUser pydantic model does not include 'is_active'.
# The active check is usually done before setting the user into the context.

# To test fallback behavior (e.g. to a default system user if no user is in context),
# the get_current_user function would need to implement such logic.
# The current implementation directly raises LookupError if no user is set.
# If a fallback was desired, get_current_user_or_none provides a way to handle "no user" gracefully.


# Test that CurrentUser is a Pydantic model as expected
def test_current_user_is_pydantic_model():
    from pydantic import BaseModel

    assert issubclass(CurrentUser, BaseModel)


def test_auth_context_handles_exceptions_within_block(mock_user_valid):
    """Ensure the context manager properly exits and resets context even if an exception occurs."""
    assert user_context_var.get() is None
    with pytest.raises(ValueError, match="Test exception inside context"):
        with auth_context(mock_user_valid):
            assert user_context_var.get().user_id == mock_user_valid.user_id
            raise ValueError("Test exception inside context")

    # Crucially, check that context was reset despite the error
    assert user_context_var.get() is None
