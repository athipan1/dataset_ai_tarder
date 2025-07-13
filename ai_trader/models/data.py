from sqlalchemy import (Column, DateTime, Float, ForeignKey, Index, Integer,
                        String, JSON)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    asset_type = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())

    price_data = relationship(
        "PriceData", back_populates="asset", cascade="all, delete", lazy="dynamic"
    )
    signals = relationship("Signal", back_populates="asset", passive_deletes=True)
    orders = relationship("Order", back_populates="asset", passive_deletes=True)

    def __repr__(self):
        return f"<Asset(id={self.id}, symbol='{self.symbol}')>"


class PriceData(Base):
    __tablename__ = "price_data"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    timestamp = Column(DateTime, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    source = Column(String, nullable=False)

    asset = relationship("Asset", back_populates="price_data")

    __table_args__ = (
        Index(
            "idx_asset_timestamp_source", "asset_id", "timestamp", "source", unique=True
        ),
    )

    def __repr__(self):
        return f"<PriceData(asset_id={self.asset_id}, timestamp='{self.timestamp}', close={self.close})>"


class MarketEvent(Base):
    __tablename__ = "market_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False)
    event_datetime = Column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    symbol = Column(String, nullable=True, index=True)
    impact_score = Column(Float, nullable=True)
    source = Column(String, nullable=True)
    meta_data = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<MarketEvent(id={self.id}, event_type='{self.event_type}', symbol='{self.symbol}')>"
