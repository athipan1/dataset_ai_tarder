from sqlalchemy import Column, Integer, DateTime, Numeric, String, ForeignKey, Index
from sqlalchemy.orm import relationship
from ai_trader.db.base import Base
# from .asset import Asset # Use string "Asset" for relationship to avoid circular import if Asset imports PriceData

class PriceData(Base):
    __tablename__ = "price_data"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False) # Cascade delete if asset is deleted
    timestamp = Column(DateTime(timezone=True), nullable=False)
    open = Column(Numeric(19, 8), nullable=False)
    high = Column(Numeric(19, 8), nullable=False)
    low = Column(Numeric(19, 8), nullable=False)
    close = Column(Numeric(19, 8), nullable=False)
    volume = Column(Numeric(19, 8), nullable=True) # Volume can sometimes be zero or not applicable
    source = Column(String, nullable=True, index=True) # e.g., 'binance', 'yahoo', can be nullable if source is not always known

    asset = relationship("Asset", back_populates="price_data")

    __table_args__ = (
        Index("ix_price_data_asset_id_timestamp_source", "asset_id", "timestamp", "source", unique=True), # Most specific unique constraint
        Index("ix_price_data_timestamp", "timestamp"),
        # asset_id is already indexed by ForeignKey for many DBs, but explicit index is fine if needed for other types of queries.
        # Index("ix_price_data_asset_id", "asset_id"),
    )

    def __repr__(self):
        return f"<PriceData(id={self.id}, asset_id={self.asset_id}, timestamp='{self.timestamp}', close={self.close}, source='{self.source}')>"
