import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from typing import Dict

from ai_trader import models  # For type hinting models.User
from schemas.user import UserCreate
from crud import crud_user
from ai_trader.config import settings  # For any default settings or test user details

# A utility to get random string for unique usernames/emails in tests
import random
import string


def random_lower_string(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase, k=length))


def random_email() -> str:
    return f"{random_lower_string()}@{random_lower_string()}.com"


# --- User Registration and Login Tests ---


def test_create_user_new_email_username(
    client: TestClient, db_session: Session
) -> None:
    username = random_lower_string()
    email = random_email()
    password = random_lower_string(12)
    data = {"username": username, "email": email, "password": password}

    response = client.post("/api/v1/users/register", json=data)

    assert response.status_code == 201, response.text
    created_user = response.json()
    assert created_user["email"] == email
    assert created_user["username"] == username
    assert "id" in created_user
    assert "hashed_password" not in created_user  # Ensure password is not returned

    user_in_db = crud_user.user.get_user_by_username(db_session, username=username)
    assert user_in_db
    assert user_in_db.email == email
    # You might want to verify the password, but that requires hashing the test password
    # and comparing, or using the authenticate method. For now, presence is enough.


def test_create_user_duplicate_username(
    client: TestClient, test_user: models.User
) -> None:
    # test_user fixture already creates a user
    data = {
        "username": test_user.username,  # Using existing username
        "email": random_email(),  # New email
        "password": "newpassword123",
    }
    response = client.post("/api/v1/users/register", json=data)
    assert response.status_code == 400
    assert "username already exists" in response.json()["detail"].lower()


def test_create_user_duplicate_email(
    client: TestClient, test_user: models.User
) -> None:
    data = {
        "username": random_lower_string(),  # New username
        "email": test_user.email,  # Using existing email
        "password": "newpassword123",
    }
    response = client.post("/api/v1/users/register", json=data)
    assert response.status_code == 400
    assert "email already exists" in response.json()["detail"].lower()


def test_login_successful(client: TestClient, test_user: models.User) -> None:
    # test_user fixture ensures user "testuser@example.com" with password "testpassword" exists
    login_data = {
        "username": test_user.username,  # from conftest test_user
        "password": "testpassword",  # from conftest test_user
    }
    response = client.post("/api/v1/users/login", data=login_data)
    assert response.status_code == 200, response.text
    tokens = response.json()
    assert "access_token" in tokens
    assert tokens["token_type"] == "bearer"


def test_login_incorrect_password(client: TestClient, test_user: models.User) -> None:
    login_data = {"username": test_user.username, "password": "wrongpassword"}
    response = client.post("/api/v1/users/login", data=login_data)
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]


def test_login_nonexistent_user(client: TestClient) -> None:
    login_data = {"username": "nonexistentuser@example.com", "password": "anypassword"}
    response = client.post("/api/v1/users/login", data=login_data)
    assert response.status_code == 401  # Or 404, depending on how auth is implemented
    # 401 is common to avoid user enumeration
    assert "Incorrect username or password" in response.json()["detail"]


# --- Authenticated User Endpoint Tests (/me) ---


def test_read_users_me_successful(
    client: TestClient,
    normal_user_token_headers: Dict[str, str],
    test_user: models.User,
) -> None:
    response = client.get("/api/v1/users/me", headers=normal_user_token_headers)
    assert response.status_code == 200, response.text
    current_user_data = response.json()
    assert current_user_data["email"] == test_user.email
    assert current_user_data["username"] == test_user.username
    assert current_user_data["id"] == test_user.id


def test_read_users_me_no_token(client: TestClient) -> None:
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401  # Expecting unauthorized
    assert (
        "Not authenticated" in response.json()["detail"]
    )  # Or "Could not validate credentials"


def test_update_user_me_successful(
    client: TestClient,
    normal_user_token_headers: Dict[str, str],
    test_user: models.User,
    db_session: Session,
) -> None:
    new_username = random_lower_string(10)
    new_email = random_email()
    update_data = {"username": new_username, "email": new_email}

    response = client.put(
        "/api/v1/users/me", headers=normal_user_token_headers, json=update_data
    )
    assert response.status_code == 200, response.text
    updated_user_data = response.json()
    assert updated_user_data["username"] == new_username
    assert updated_user_data["email"] == new_email

    # Verify in DB
    db_session.refresh(test_user)  # Refresh the original test_user instance
    assert test_user.username == new_username
    assert test_user.email == new_email


def test_update_user_me_duplicate_email_other_user(
    client: TestClient,
    normal_user_token_headers: Dict[str, str],
    db_session: Session,
    test_user: models.User,
):
    # Create another user first
    other_username = random_lower_string()
    other_email = random_email()
    other_password = "password123"
    other_user_in = UserCreate(
        username=other_username, email=other_email, password=other_password
    )
    crud_user.user.create_user(db_session, user_in=other_user_in)

    # Attempt to update current user (test_user) to other_user's email
    update_data = {"email": other_email}
    response = client.put(
        "/api/v1/users/me", headers=normal_user_token_headers, json=update_data
    )
    assert response.status_code == 400
    assert "email already exists" in response.json()["detail"].lower()


# --- Get User by ID Test --- (Example, assuming /users/{user_id} exists)


def test_read_user_by_id_successful(
    client: TestClient,
    normal_user_token_headers: Dict[str, str],
    test_user: models.User,
) -> None:
    response = client.get(
        f"/api/v1/users/{test_user.id}", headers=normal_user_token_headers
    )
    assert response.status_code == 200, response.text
    user_data = response.json()
    assert user_data["id"] == test_user.id
    assert user_data["username"] == test_user.username


def test_read_user_by_id_not_found(
    client: TestClient, normal_user_token_headers: Dict[str, str]
) -> None:
    non_existent_id = 9999999
    response = client.get(
        f"/api/v1/users/{non_existent_id}", headers=normal_user_token_headers
    )
    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


# Add more tests:
# - Updating password for /me
# - Attempting to update /me with username that conflicts with another user
# - Testing authentication with invalid/expired tokens (more involved, may need to mock datetime)
# - If admin routes for listing/managing users are added, test those with appropriate admin user fixture.
# - Test soft deletion of user and ensure they cannot log in / access authenticated routes.


@pytest.mark.skip(
    reason="Soft delete test needs user recreation or careful state management"
)
def test_login_soft_deleted_user(
    client: TestClient, db_session: Session, test_user: models.User
):
    # Soft delete the user
    crud_user.user.delete_user(db=db_session, user_id=test_user.id)
    db_session.commit()  # Ensure delete is committed

    login_data = {
        "username": test_user.username,
        "password": "testpassword",  # Original password
    }
    response = client.post("/api/v1/users/login", data=login_data)

    # Expected behavior:
    # 1. crud_user.authenticate might return None if it filters by is_deleted=False.
    # 2. Or, login route explicitly checks user.is_deleted.
    # The user router's login endpoint checks user.is_deleted.
    assert (
        response.status_code == 400
    )  # Based on current implementation in users.py router
    assert "Inactive user" in response.json()["detail"]

    # Cleanup: Reactivate or recreate user if other tests depend on this user being active
    # For simplicity, this test is skipped or should be run last/isolated.
    # Or, create a new user specifically for this test.
    # test_user_reloaded = crud_user.user.get_user(db_session, user_id=test_user.id) # This will fail if get_user filters deleted
    # if test_user_reloaded:
    #     test_user_reloaded.is_deleted = False
    #     test_user_reloaded.deleted_at = None
    #     db_session.add(test_user_reloaded)
    #     db_session.commit()
