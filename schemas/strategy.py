from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import datetime


class StrategyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    model_version: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    # api_key: Optional[str] = None # Sensitive, handle carefully. Not usually part of create/update directly.
    # user_id will be set by the system (e.g. from current authenticated user)


class StrategyCreate(StrategyBase):
    pass


class StrategyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    model_version: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    # api_key: Optional[str] = None # Consider a separate endpoint for managing API keys


class StrategyInDBBase(StrategyBase):
    id: int
    user_id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
    is_deleted: bool = False  # Assuming soft delete

    class Config:
        orm_mode = True  # Pydantic V1 or from_attributes = True for V2


class Strategy(StrategyInDBBase):
    """Properties to return to client."""

    pass


class StrategyInDB(StrategyInDBBase):
    """Properties stored in DB."""

    # api_key: Optional[str] = None # If stored directly; consider encryption or separate secure storage
    pass
