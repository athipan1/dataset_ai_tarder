from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Any, Optional

from api.deps import db as deps_db
from api.deps import auth as deps_auth
from crud import (
    crud_analytics,
)  # Ensure this is the correct import from your crud structure
from schemas import analytics as analytics_schema  # Ensure this is the correct import
from ai_trader import models

router = APIRouter()


@router.post(
    "/",
    response_model=analytics_schema.AnalyticsData,
    status_code=status.HTTP_201_CREATED,
    tags=["analytics"],
)
def create_analytics_entry(
    *,
    db: Session = Depends(deps_db.get_db),
    analytics_in: analytics_schema.AnalyticsDataCreate,
    current_user: models.User = Depends(deps_auth.get_current_active_user),
    strategy_id: Optional[int] = Query(
        None, description="Optional ID of the strategy this analytics entry relates to."
    ),
) -> Any:
    """
    Create a new trade analytics entry for the current user.
    Can optionally be linked to a strategy.
    """
    # Validate strategy_id if provided: check if it exists and belongs to the user
    if strategy_id:
        # This import should be from crud.crud_strategy, adjust if your structure is different
        from crud import crud_strategy  # Local import or move to top if used more

        strategy = crud_strategy.strategy.get_strategy(db=db, strategy_id=strategy_id)
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy with id {strategy_id} not found.",
            )
        if strategy.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Strategy does not belong to the current user.",
            )

    created_entry = crud_analytics.trade_analytics.create_analytic_entry(
        db=db,
        analytics_in=analytics_in,
        user_id=current_user.id,
        strategy_id=strategy_id,
    )
    return created_entry


@router.get(
    "/{analytic_id}", response_model=analytics_schema.AnalyticsData, tags=["analytics"]
)
def read_analytic_entry(
    *,
    db: Session = Depends(deps_db.get_db),
    analytic_id: int,
    current_user: models.User = Depends(deps_auth.get_current_active_user),
) -> Any:
    """
    Get a specific analytics entry by ID.
    Only accessible by the user who owns the entry.
    """
    entry = crud_analytics.trade_analytics.get_analytic(db=db, analytic_id=analytic_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Analytics entry not found"
        )
    if entry.user_id != current_user.id:
        # if not current_user.is_superuser: # Admin check
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )
    return entry


@router.get(
    "/user/", response_model=List[analytics_schema.AnalyticsData], tags=["analytics"]
)
def read_analytics_by_user(
    db: Session = Depends(deps_db.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps_auth.get_current_active_user),
) -> Any:
    """
    Retrieve all analytics entries for the current user.
    """
    entries = crud_analytics.trade_analytics.get_analytics_by_user(
        db=db, user_id=current_user.id, skip=skip, limit=limit
    )
    return entries


@router.get(
    "/strategy/{strategy_id}",
    response_model=List[analytics_schema.AnalyticsData],
    tags=["analytics"],
)
def read_analytics_by_strategy(
    *,
    strategy_id: int,
    db: Session = Depends(deps_db.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps_auth.get_current_active_user),
) -> Any:
    """
    Retrieve analytics entries for a specific strategy.
    Ensures the strategy belongs to the current user.
    """
    # Validate strategy: check if it exists and belongs to the user
    from crud import crud_strategy  # Local import

    strategy = crud_strategy.strategy.get_strategy(db=db, strategy_id=strategy_id)
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy with id {strategy_id} not found.",
        )
    if strategy.user_id != current_user.id:
        # if not current_user.is_superuser: # Admin check
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Strategy does not belong to the current user or you lack permissions.",
        )

    entries = crud_analytics.trade_analytics.get_analytics_by_strategy(
        db=db, strategy_id=strategy_id, skip=skip, limit=limit
    )
    return entries


@router.put(
    "/{analytic_id}", response_model=analytics_schema.AnalyticsData, tags=["analytics"]
)
def update_analytics_entry(
    *,
    db: Session = Depends(deps_db.get_db),
    analytic_id: int,
    analytics_in: analytics_schema.AnalyticsDataUpdate,
    current_user: models.User = Depends(deps_auth.get_current_active_user),
) -> Any:
    """
    Update an analytics entry.
    Only accessible by the user who owns the entry.
    """
    db_entry = crud_analytics.trade_analytics.get_analytic(
        db=db, analytic_id=analytic_id
    )
    if not db_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Analytics entry not found"
        )
    if db_entry.user_id != current_user.id:
        # if not current_user.is_superuser: # Admin check
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    updated_entry = crud_analytics.trade_analytics.update_analytic_entry(
        db=db, db_analytic_entry=db_entry, analytics_in=analytics_in
    )
    return updated_entry


@router.delete(
    "/{analytic_id}", response_model=analytics_schema.AnalyticsData, tags=["analytics"]
)
def delete_analytics_entry(
    *,
    db: Session = Depends(deps_db.get_db),
    analytic_id: int,
    current_user: models.User = Depends(deps_auth.get_current_active_user),
) -> Any:
    """
    Delete an analytics entry (soft delete).
    Only accessible by the user who owns the entry.
    """
    db_entry = crud_analytics.trade_analytics.get_analytic(
        db=db, analytic_id=analytic_id
    )
    if not db_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Analytics entry not found"
        )
    if db_entry.user_id != current_user.id:
        # if not current_user.is_superuser: # Admin check
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    deleted_entry = crud_analytics.trade_analytics.delete_analytic_entry(
        db=db, analytic_id=analytic_id
    )
    if not deleted_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analytics entry not found during delete operation",
        )
    return deleted_entry


# Admin endpoint to get all analytics (example, if needed)
# @router.get("/all/", response_model=List[analytics_schema.AnalyticsData], tags=["analytics", "admin"])
# def read_all_analytics_admin(
#     db: Session = Depends(deps_db.get_db),
#     skip: int = 0,
#     limit: int = 100,
#     current_user: models.User = Depends(deps_auth.get_current_active_superuser), # Requires superuser
# ) -> Any:
#     """
#     Retrieve all analytics entries in the system (Admin only).
#     """
#     entries = crud_analytics.trade_analytics.get_all_analytics(db=db, skip=skip, limit=limit)
#     return entries
