# This file will be used to import all models from this directory
from .user import User
from .trade import Trade, TradeType
from .strategy import Strategy
from .user_behavior import UserBehaviorLog
from .trade_analytics import TradeAnalytics
from .market_event import MarketEvent

# You can also define __all__ if you want to control what `from .models import *` imports
__all__ = [
    "User",
    "Trade",
    "TradeType",
    "Strategy",
    "UserBehaviorLog",
    "TradeAnalytics",
    "MarketEvent",
]
