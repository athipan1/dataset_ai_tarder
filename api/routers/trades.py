from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any

from api.deps import db as deps_db
from api.deps import auth as deps_auth
from crud import crud_trade
from schemas import trade as trade_schema
from ai_trader import models

router = APIRouter()


@router.post(
    "/",
    response_model=trade_schema.Trade,
    status_code=status.HTTP_201_CREATED,
    tags=["trades"],
)
def create_trade(
    *,
    db: Session = Depends(deps_db.get_db),
    trade_in: trade_schema.TradeCreate,
    current_user: models.User = Depends(deps_auth.get_current_active_user),
) -> Any:
    """
    Create a new trade for the current user.
    """
    # user_id is taken from current_user, not from payload for security.
    created_trade = crud_trade.trade.create_trade(
        db=db, trade_in=trade_in, user_id=current_user.id
    )
    return created_trade


@router.get("/{trade_id}", response_model=trade_schema.Trade, tags=["trades"])
def read_trade(
    *,
    db: Session = Depends(deps_db.get_db),
    trade_id: int,
    current_user: models.User = Depends(deps_auth.get_current_active_user),
) -> Any:
    """
    Get a specific trade by ID.
    Only accessible by the user who owns the trade (or admin - not implemented yet).
    """
    trade = crud_trade.trade.get_trade(db=db, trade_id=trade_id)
    if not trade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found"
        )
    if trade.user_id != current_user.id:
        # Add admin check here if admins should be able to access any trade
        # if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )
    return trade


@router.get("/", response_model=List[trade_schema.Trade], tags=["trades"])
def read_trades_by_user(
    db: Session = Depends(deps_db.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps_auth.get_current_active_user),
) -> Any:
    """
    Retrieve all trades for the current user.
    """
    trades = crud_trade.trade.get_trades_by_user(
        db=db, user_id=current_user.id, skip=skip, limit=limit
    )
    return trades


@router.put("/{trade_id}", response_model=trade_schema.Trade, tags=["trades"])
def update_trade(
    *,
    db: Session = Depends(deps_db.get_db),
    trade_id: int,
    trade_in: trade_schema.TradeUpdate,
    current_user: models.User = Depends(deps_auth.get_current_active_user),
) -> Any:
    """
    Update a trade.
    Only accessible by the user who owns the trade.
    """
    db_trade = crud_trade.trade.get_trade(db=db, trade_id=trade_id)
    if not db_trade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found"
        )
    if db_trade.user_id != current_user.id:
        # if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    updated_trade = crud_trade.trade.update_trade(
        db=db, db_trade=db_trade, trade_in=trade_in
    )
    return updated_trade


@router.delete("/{trade_id}", response_model=trade_schema.Trade, tags=["trades"])
def delete_trade(
    *,
    db: Session = Depends(deps_db.get_db),
    trade_id: int,
    current_user: models.User = Depends(deps_auth.get_current_active_user),
) -> Any:
    """
    Delete a trade (soft delete).
    Only accessible by the user who owns the trade.
    """
    db_trade = crud_trade.trade.get_trade(db=db, trade_id=trade_id)
    if not db_trade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trade not found"
        )
    if db_trade.user_id != current_user.id:
        # if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    deleted_trade = crud_trade.trade.delete_trade(db=db, trade_id=trade_id)
    if (
        not deleted_trade
    ):  # Should not happen if previous checks passed, but good for safety
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trade not found during delete operation",
        )
    return deleted_trade


# Admin endpoint to get all trades (example, if needed)
# @router.get("/all/", response_model=List[trade_schema.Trade], tags=["trades", "admin"])
# def read_all_trades_admin(
#     db: Session = Depends(deps_db.get_db),
#     skip: int = 0,
#     limit: int = 100,
#     current_user: models.User = Depends(deps_auth.get_current_active_superuser), # Requires superuser
# ) -> Any:
#     """
#     Retrieve all trades in the system (Admin only).
#     """
#     trades = crud_trade.trade.get_all_trades(db=db, skip=skip, limit=limit)
#     return trades
