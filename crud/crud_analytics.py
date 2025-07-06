from sqlalchemy.orm import Session
from typing import List, Optional
import datetime

from ai_trader import models
from schemas import analytics as analytics_schema


class CRUDTradeAnalytics:
    def get_analytic(
        self, db: Session, analytic_id: int
    ) -> Optional[models.TradeAnalytics]:
        return (
            db.query(models.TradeAnalytics)
            .filter(
                models.TradeAnalytics.id == analytic_id,
                models.TradeAnalytics.is_deleted == False,
            )
            .first()
        )

    def get_analytics_by_user(
        self, db: Session, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[models.TradeAnalytics]:
        return (
            db.query(models.TradeAnalytics)
            .filter(
                models.TradeAnalytics.user_id == user_id,
                models.TradeAnalytics.is_deleted == False,
            )
            .order_by(models.TradeAnalytics.analysis_date.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_analytics_by_strategy(
        self, db: Session, strategy_id: int, skip: int = 0, limit: int = 100
    ) -> List[models.TradeAnalytics]:
        return (
            db.query(models.TradeAnalytics)
            .filter(
                models.TradeAnalytics.strategy_id == strategy_id,
                models.TradeAnalytics.is_deleted == False,
            )
            .order_by(models.TradeAnalytics.analysis_date.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_all_analytics(
        self, db: Session, skip: int = 0, limit: int = 100
    ) -> List[models.TradeAnalytics]:
        return (
            db.query(models.TradeAnalytics)
            .filter(models.TradeAnalytics.is_deleted == False)
            .order_by(models.TradeAnalytics.analysis_date.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_analytic_entry(
        self,
        db: Session,
        *,
        analytics_in: analytics_schema.AnalyticsDataCreate,
        user_id: int,
        strategy_id: Optional[int] = None
    ) -> models.TradeAnalytics:
        db_analytic_entry = models.TradeAnalytics(
            **analytics_in.model_dump(),  # Pydantic V2
            user_id=user_id,
            strategy_id=strategy_id,
            analysis_date=datetime.date.today()  # Set current date for analysis
        )
        db.add(db_analytic_entry)
        db.commit()
        db.refresh(db_analytic_entry)
        return db_analytic_entry

    def update_analytic_entry(
        self,
        db: Session,
        *,
        db_analytic_entry: models.TradeAnalytics,
        analytics_in: analytics_schema.AnalyticsDataUpdate
    ) -> models.TradeAnalytics:
        update_data = analytics_in.model_dump(exclude_unset=True)  # Pydantic V2

        for field, value in update_data.items():
            setattr(db_analytic_entry, field, value)

        db.add(db_analytic_entry)
        db.commit()
        db.refresh(db_analytic_entry)
        return db_analytic_entry

    def delete_analytic_entry(
        self, db: Session, *, analytic_id: int
    ) -> Optional[models.TradeAnalytics]:
        db_analytic_entry = (
            db.query(models.TradeAnalytics)
            .filter(
                models.TradeAnalytics.id == analytic_id,
                models.TradeAnalytics.is_deleted == False,
            )
            .first()
        )
        if db_analytic_entry:
            # Soft delete:
            # db_analytic_entry.is_deleted = True
            # db_analytic_entry.deleted_at = datetime.datetime.utcnow()
            db_analytic_entry.soft_delete(session=db)  # Pass the session
            db.commit()
            db.refresh(db_analytic_entry)
            return db_analytic_entry
        return None


trade_analytics = CRUDTradeAnalytics()
