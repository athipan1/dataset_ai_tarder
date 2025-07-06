from pydantic import BaseModel
from typing import Optional


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
    # You might want to add other fields like user_id, scopes, etc.
    # For example:
    # user_id: Optional[int] = None
    # scopes: list[str] = []
