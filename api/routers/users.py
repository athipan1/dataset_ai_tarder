from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Any  # List removed

from api.deps import db as deps_db  # Renamed to avoid conflict
from api.deps import auth as deps_auth
from crud import crud_user
from schemas import user as user_schema
from schemas import token as token_schema
from ai_trader import models

router = APIRouter()


@router.post(
    "/register",
    response_model=user_schema.User,
    status_code=status.HTTP_201_CREATED,
    tags=["users"],
)
def create_user_registration(
    *,
    db: Session = Depends(deps_db.get_db),
    user_in: user_schema.UserCreate,
) -> Any:
    """
    Create new user.
    """
    user = crud_user.user.get_user_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this email already exists in the system.",
        )
    user = crud_user.user.get_user_by_username(db, username=user_in.username)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this username already exists in the system.",
        )

    created_user = crud_user.user.create_user(db=db, user_in=user_in)
    return created_user


@router.post("/login", response_model=token_schema.Token, tags=["users"])
def login_for_access_token(
    db: Session = Depends(deps_db.get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user = crud_user.user.authenticate(
        db, username=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.is_deleted:  # Or check an is_active flag
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    access_token = deps_auth.create_access_token(
        data={
            "sub": user.username
        }  # Typically, 'sub' (subject) is the username or user ID
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=user_schema.User, tags=["users"])
def read_users_me(
    current_user: models.User = Depends(deps_auth.get_current_active_user),
) -> Any:
    """
    Get current user.
    """
    return current_user


@router.put("/me", response_model=user_schema.User, tags=["users"])
def update_user_me(
    *,
    db: Session = Depends(deps_db.get_db),
    user_in: user_schema.UserUpdate,
    current_user: models.User = Depends(deps_auth.get_current_active_user),
) -> Any:
    """
    Update own user.
    """
    # Check for email conflict if email is being updated
    if user_in.email and user_in.email != current_user.email:
        existing_user = crud_user.user.get_user_by_email(db, email=user_in.email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email already exists.",
            )
    # Check for username conflict if username is being updated
    if user_in.username and user_in.username != current_user.username:
        existing_user = crud_user.user.get_user_by_username(
            db, username=user_in.username
        )
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this username already exists.",
            )

    updated_user = crud_user.user.update_user(
        db=db, db_user=current_user, user_in=user_in
    )
    return updated_user


# Example of an admin-only route (if you implement is_superuser or roles)
# @router.get("/", response_model=List[user_schema.User], tags=["users"])
# def read_users(
#     db: Session = Depends(deps_db.get_db),
#     skip: int = 0,
#     limit: int = 100,
#     current_user: models.User = Depends(deps_auth.get_current_active_superuser), # Requires superuser
# ) -> Any:
#     """
#     Retrieve users. (Admin only)
#     """
#     users = crud_user.user.get_users(db, skip=skip, limit=limit)
#     return users


@router.get("/{user_id}", response_model=user_schema.User, tags=["users"])
def read_user_by_id(
    user_id: int,
    db: Session = Depends(deps_db.get_db),
    current_user: models.User = Depends(
        deps_auth.get_current_active_user
    ),  # Or superuser for access control
) -> Any:
    """
    Get a specific user by id.
    Accessible by admin or the user themselves (if user_id == current_user.id).
    """
    user = crud_user.user.get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Add access control: only admin or the user themselves can access.
    # if user.id != current_user.id and not current_user.is_superuser: # Assuming is_superuser flag
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    # For now, allowing any authenticated user to fetch if ID exists. Refine if needed.
    return user


# Add other user-related endpoints here if needed (e.g., delete user - typically admin)
