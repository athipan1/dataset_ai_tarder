from sqlalchemy.orm import Session
from typing import List, Optional

from ai_trader import models
from schemas import trade as trade_schema


class CRUDTrade:
    def get_trade(self, db: Session, trade_id: int) -> Optional[models.Trade]:
        return (
            db.query(models.Trade)
            .filter(models.Trade.id == trade_id, models.Trade.is_deleted == False)
            .first()
        )

    def get_trades_by_user(
        self, db: Session, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[models.Trade]:
        return (
            db.query(models.Trade)
            .filter(models.Trade.user_id == user_id, models.Trade.is_deleted == False)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_all_trades(
        self, db: Session, skip: int = 0, limit: int = 100
    ) -> List[models.Trade]:
        return (
            db.query(models.Trade)
            .filter(models.Trade.is_deleted == False)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_trade(
        self, db: Session, *, trade_in: trade_schema.TradeCreate, user_id: int
    ) -> models.Trade:
        db_trade = models.Trade(
            **trade_in.model_dump(),  # Pydantic V2
            user_id=user_id  # Ensure user_id is set
        )
        db.add(db_trade)
        db.commit()
        db.refresh(db_trade)
        return db_trade

    def update_trade(
        self, db: Session, *, db_trade: models.Trade, trade_in: trade_schema.TradeUpdate
    ) -> models.Trade:
        update_data = trade_in.model_dump(exclude_unset=True)  # Pydantic V2

        for field, value in update_data.items():
            setattr(db_trade, field, value)

        db.add(db_trade)  # or db.merge(db_trade) if db_trade could be detached
        db.commit()
        db.refresh(db_trade)
        return db_trade

    def delete_trade(self, db: Session, *, trade_id: int) -> Optional[models.Trade]:
        db_trade = (
            db.query(models.Trade)
            .filter(models.Trade.id == trade_id, models.Trade.is_deleted == False)
            .first()
        )
        if db_trade:
            # Soft delete:
            # db_trade.is_deleted = True
            # db_trade.deleted_at = datetime.datetime.utcnow()
            # Use the model's soft_delete method if it handles cascades or related logic
            db_trade.soft_delete(session=db)  # Pass the session
            db.commit()
            db.refresh(db_trade)
            return db_trade
        return None


trade = CRUDTrade()
