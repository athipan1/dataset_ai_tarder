from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, Text
from sqlalchemy.sql import func

from ai_trader.db.base import Base


class MarketEvent(Base):
    __tablename__ = "market_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False)
    event_datetime = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    symbol = Column(String, nullable=True, index=True)
    impact_score = Column(Float, nullable=True)  # Assuming a scale, e.g., 0.0 to 1.0
    source = Column(String, nullable=True)
    meta_data = Column(JSON)  # Or Text

    def __repr__(self):
        return f"<MarketEvent(id={self.id}, event_type='{self.event_type}', symbol='{self.symbol}')>"
