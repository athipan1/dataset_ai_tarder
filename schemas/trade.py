from pydantic import BaseModel
from typing import Optional
import datetime
from decimal import Decimal  # For precise numeric types

# Assuming TradeType and OrderSide enums are defined elsewhere,
# or you can redefine them here or import if they are in a shared location.
# For now, using string placeholders.
# from ai_trader.models import TradeType as ModelTradeType (if accessible)


class TradeBase(BaseModel):
    symbol: str
    quantity: Decimal
    price: Decimal
    trade_type: str  # Should ideally be an Enum: Literal["BUY", "SELL"]
    commission: Optional[Decimal] = None
    commission_asset: Optional[str] = None
    # user_id will be set by the system, not by client on creation usually
    # order_id might be optional if a trade can exist without a direct order link in some contexts


class TradeCreate(TradeBase):
    # user_id: int # If client needs to specify it (e.g. admin creating trade for user)
    order_id: Optional[int] = None


class TradeUpdate(BaseModel):
    quantity: Optional[Decimal] = None
    price: Optional[Decimal] = None
    commission: Optional[Decimal] = None
    commission_asset: Optional[str] = None
    # Other fields that are updatable


class TradeInDBBase(TradeBase):
    id: int
    user_id: int
    order_id: Optional[int] = None
    timestamp: datetime.datetime
    is_deleted: bool = False  # Assuming soft delete

    class Config:
        orm_mode = True  # Pydantic V1 or from_attributes = True for V2


class Trade(TradeInDBBase):
    """Properties to return to client."""

    pass


class TradeInDB(TradeInDBBase):
    """Properties stored in DB."""

    pass
