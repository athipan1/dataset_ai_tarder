from pydantic import BaseModel, EmailStr
from typing import Optional
import datetime

# --- Base Schemas ---


class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None  # For password updates


# --- Properties to receive via API on creation, but not stored in DB as is (e.g. password) ---
# (UserCreate already handles this for password)


# --- Properties shared by models stored in DB ---
class UserInDBBase(UserBase):
    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
    is_deleted: bool = False  # Assuming soft delete is used

    class Config:
        orm_mode = True  # Pydantic V1 way, or from_attributes = True for Pydantic V2


# --- Properties to return to client (filters out sensitive data like hashed_password) ---
class User(UserInDBBase):
    pass


# --- Properties stored in DB (includes hashed_password if needed for internal use) ---
class UserInDB(UserInDBBase):
    hashed_password: str
