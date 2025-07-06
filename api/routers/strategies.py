from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any

from api.deps import db as deps_db
from api.deps import auth as deps_auth
from crud import crud_strategy
from schemas import strategy as strategy_schema
from ai_trader import models

router = APIRouter()


@router.post(
    "/",
    response_model=strategy_schema.Strategy,
    status_code=status.HTTP_201_CREATED,
    tags=["strategies"],
)
def create_strategy(
    *,
    db: Session = Depends(deps_db.get_db),
    strategy_in: strategy_schema.StrategyCreate,
    current_user: models.User = Depends(deps_auth.get_current_active_user),
) -> Any:
    """
    Create a new strategy for the current user.
    """
    # user_id is taken from current_user.
    created_strategy = crud_strategy.strategy.create_strategy(
        db=db, strategy_in=strategy_in, user_id=current_user.id
    )
    return created_strategy


@router.get(
    "/{strategy_id}", response_model=strategy_schema.Strategy, tags=["strategies"]
)
def read_strategy(
    *,
    db: Session = Depends(deps_db.get_db),
    strategy_id: int,
    current_user: models.User = Depends(deps_auth.get_current_active_user),
) -> Any:
    """
    Get a specific strategy by ID.
    Only accessible by the user who owns the strategy.
    """
    strategy = crud_strategy.strategy.get_strategy(db=db, strategy_id=strategy_id)
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found"
        )
    if strategy.user_id != current_user.id:
        # if not current_user.is_superuser: # Admin check
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )
    return strategy


@router.get("/", response_model=List[strategy_schema.Strategy], tags=["strategies"])
def read_strategies_by_user(
    db: Session = Depends(deps_db.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps_auth.get_current_active_user),
) -> Any:
    """
    Retrieve all strategies for the current user.
    """
    strategies = crud_strategy.strategy.get_strategies_by_user(
        db=db, user_id=current_user.id, skip=skip, limit=limit
    )
    return strategies


@router.put(
    "/{strategy_id}", response_model=strategy_schema.Strategy, tags=["strategies"]
)
def update_strategy(
    *,
    db: Session = Depends(deps_db.get_db),
    strategy_id: int,
    strategy_in: strategy_schema.StrategyUpdate,
    current_user: models.User = Depends(deps_auth.get_current_active_user),
) -> Any:
    """
    Update a strategy.
    Only accessible by the user who owns the strategy.
    """
    db_strategy = crud_strategy.strategy.get_strategy(db=db, strategy_id=strategy_id)
    if not db_strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found"
        )
    if db_strategy.user_id != current_user.id:
        # if not current_user.is_superuser: # Admin check
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    updated_strategy = crud_strategy.strategy.update_strategy(
        db=db, db_strategy=db_strategy, strategy_in=strategy_in
    )
    return updated_strategy


@router.delete(
    "/{strategy_id}", response_model=strategy_schema.Strategy, tags=["strategies"]
)
def delete_strategy(
    *,
    db: Session = Depends(deps_db.get_db),
    strategy_id: int,
    current_user: models.User = Depends(deps_auth.get_current_active_user),
) -> Any:
    """
    Delete a strategy (soft delete).
    Only accessible by the user who owns the strategy.
    """
    db_strategy = crud_strategy.strategy.get_strategy(db=db, strategy_id=strategy_id)
    if not db_strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found"
        )
    if db_strategy.user_id != current_user.id:
        # if not current_user.is_superuser: # Admin check
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    deleted_strategy = crud_strategy.strategy.delete_strategy(
        db=db, strategy_id=strategy_id
    )
    if not deleted_strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found during delete operation",
        )
    return deleted_strategy


# Admin endpoint to get all strategies (example, if needed)
# @router.get("/all/", response_model=List[strategy_schema.Strategy], tags=["strategies", "admin"])
# def read_all_strategies_admin(
#     db: Session = Depends(deps_db.get_db),
#     skip: int = 0,
#     limit: int = 100,
#     current_user: models.User = Depends(deps_auth.get_current_active_superuser), # Requires superuser
# ) -> Any:
#     """
#     Retrieve all strategies in the system (Admin only).
#     """
#     strategies = crud_strategy.strategy.get_all_strategies(db=db, skip=skip, limit=limit)
#     return strategies
