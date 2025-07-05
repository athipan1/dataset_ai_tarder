import enum
from sqlalchemy import Column, Integer, String, DateTime, Index, Enum as DBEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ai_trader.db.base import Base


class AssetType(enum.Enum):
    CRYPTO = "CRYPTO"
    FOREX = "FOREX"
    STOCK = "STOCK"
    ETF = "ETF"
    COMMODITY = "COMMODITY"
    INDEX = "INDEX"
    UNKNOWN = "UNKNOWN"


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True, nullable=False)  # e.g., BTCUSD, ETHUSD, EURUSD, AAPL
    name = Column(String, nullable=True)  # e.g., Bitcoin, Ethereum, Euro/US Dollar, Apple Inc.
    asset_type = Column(DBEnum(AssetType), default=AssetType.UNKNOWN, index=True)
    exchange = Column(String, nullable=True, index=True)  # e.g., NASDAQ, NYSE, BINANCE, FTX

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    price_data = relationship("PriceData", back_populates="asset", cascade="all, delete-orphan")
    signals = relationship("Signal", back_populates="asset", cascade="all, delete-orphan")
    orders = relationship(
        "Order", back_populates="asset"
    )  # Don't cascade delete orders if asset is deleted, handle manually or set NULL.

    __table_args__ = (
        Index("ix_asset_symbol", "symbol", unique=True),  # unique=True was already on column
        Index("ix_asset_type", "asset_type"),
        Index("ix_asset_exchange", "exchange"),
    )

    def __repr__(self):
        asset_type_val = self.asset_type.value if self.asset_type else None
        return f"<Asset(id={self.id}, symbol='{self.symbol}', " f"type='{asset_type_val}')>"
