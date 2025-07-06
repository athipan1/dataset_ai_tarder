from pydantic import BaseModel, Field
from typing import Optional, Text
import datetime


class AnalyticsDataBase(BaseModel):
    total_trades: int = Field(..., ge=0)
    win_rate: float = Field(..., ge=0.0, le=1.0)  # Percentage, e.g., 0.75 for 75%
    total_pnl: float  # Profit and Loss
    avg_risk_reward: Optional[float] = None
    max_drawdown: Optional[float] = None  # Percentage or absolute value
    notes: Optional[Text] = None
    # user_id and strategy_id will often be path parameters or derived from context
    # analysis_date will be set by the system on creation


class AnalyticsDataCreate(AnalyticsDataBase):
    # If user_id or strategy_id need to be part of the payload:
    # user_id: int
    # strategy_id: Optional[int] = None
    pass


class AnalyticsDataUpdate(BaseModel):
    total_trades: Optional[int] = Field(None, ge=0)
    win_rate: Optional[float] = Field(None, ge=0.0, le=1.0)
    total_pnl: Optional[float] = None
    avg_risk_reward: Optional[float] = None
    max_drawdown: Optional[float] = None
    notes: Optional[Text] = None


class AnalyticsDataInDBBase(AnalyticsDataBase):
    id: int
    user_id: int
    strategy_id: Optional[int] = None
    analysis_date: datetime.date
    is_deleted: bool = False  # Assuming soft delete

    class Config:
        orm_mode = True  # Pydantic V1 or from_attributes = True for V2


class AnalyticsData(AnalyticsDataInDBBase):
    """Properties to return to client."""

    pass


class AnalyticsDataInDB(AnalyticsDataInDBBase):
    """Properties stored in DB."""

    pass
