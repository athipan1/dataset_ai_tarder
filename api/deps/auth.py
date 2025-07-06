from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

# from passlib.context import CryptContext  # F401: Unused
from sqlalchemy.orm import Session

from ai_trader.config import settings
from ai_trader import models
from schemas import token as token_schema

# from schemas import user as user_schema  # F401: Unused
from crud import crud_user
from .db import get_db  # Import get_db from within deps


# --- Configuration ---
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"  # Standard algorithm for JWT
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Token validity period

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="api/v1/users/login"
)  # Corrected: Relative to server root


# Password utilities (verify_password, get_password_hash) are now expected to be imported
# from crud.crud_user or a dedicated security utility module if needed by auth functions directly.
# For token creation and validation, they are not directly used here.
# The login endpoint itself uses crud_user.authenticate which handles password verification.


# --- Token Creation ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# --- Current User Dependency ---
async def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = token_schema.TokenData(username=username)
    except JWTError:
        raise credentials_exception

    user = crud_user.user.get_user_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    if user.is_deleted:  # Check if user is soft-deleted
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return user


async def get_current_active_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    # This function can be expanded to check for other "active" flags if needed
    # For now, get_current_user already checks is_deleted.
    # If there were a separate `is_active` field, you'd check it here.
    # if not current_user.is_active:  # Example if an is_active field existed
    #     raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# Optional: Dependency for superuser/admin
# async def get_current_active_superuser(
#     current_user: models.User = Depends(get_current_active_user),
# ) -> models.User:
#     if not current_user.is_superuser:  # Assuming User model has is_superuser
#         raise HTTPException(
#             status_code=403, detail="The user doesn't have enough privileges"
#         )
#     return current_user
