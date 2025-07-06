from sqlalchemy.orm import Session
from typing import List, Optional

from ai_trader import models
from schemas import strategy as strategy_schema


class CRUDStrategy:
    def get_strategy(self, db: Session, strategy_id: int) -> Optional[models.Strategy]:
        return (
            db.query(models.Strategy)
            .filter(
                models.Strategy.id == strategy_id, models.Strategy.is_deleted == False
            )
            .first()
        )

    def get_strategies_by_user(
        self, db: Session, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[models.Strategy]:
        return (
            db.query(models.Strategy)
            .filter(
                models.Strategy.user_id == user_id, models.Strategy.is_deleted == False
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_all_strategies(
        self, db: Session, skip: int = 0, limit: int = 100
    ) -> List[models.Strategy]:
        return (
            db.query(models.Strategy)
            .filter(models.Strategy.is_deleted == False)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_strategy(
        self, db: Session, *, strategy_in: strategy_schema.StrategyCreate, user_id: int
    ) -> models.Strategy:
        db_strategy = models.Strategy(
            **strategy_in.model_dump(), user_id=user_id  # Pydantic V2  # Set the owner
        )
        db.add(db_strategy)
        db.commit()
        db.refresh(db_strategy)
        return db_strategy

    def update_strategy(
        self,
        db: Session,
        *,
        db_strategy: models.Strategy,
        strategy_in: strategy_schema.StrategyUpdate
    ) -> models.Strategy:
        update_data = strategy_in.model_dump(exclude_unset=True)  # Pydantic V2

        for field, value in update_data.items():
            setattr(db_strategy, field, value)

        db.add(db_strategy)
        db.commit()
        db.refresh(db_strategy)
        return db_strategy

    def delete_strategy(
        self, db: Session, *, strategy_id: int
    ) -> Optional[models.Strategy]:
        db_strategy = (
            db.query(models.Strategy)
            .filter(
                models.Strategy.id == strategy_id, models.Strategy.is_deleted == False
            )
            .first()
        )
        if db_strategy:
            # Soft delete:
            # db_strategy.is_deleted = True
            # db_strategy.deleted_at = datetime.datetime.utcnow()
            db_strategy.soft_delete(session=db)  # Pass the session
            db.commit()
            db.refresh(db_strategy)
            return db_strategy
        return None


strategy = CRUDStrategy()
