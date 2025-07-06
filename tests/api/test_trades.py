import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from typing import Dict, List  # For type hints
from decimal import Decimal

from ai_trader import models  # For type hinting models.User, models.Trade
from schemas import trade as trade_schema  # For creating TradeCreate schemas
from crud import crud_trade  # To potentially verify DB state directly


# --- Helper to generate trade data ---
def get_trade_create_data(
    symbol: str = "BTCUSD", quantity: float = 1.0, price: float = 50000.0
) -> dict:
    return {
        "symbol": symbol,
        "quantity": quantity,  # Pydantic will convert to Decimal if schema expects it
        "price": price,  # Pydantic will convert
        "trade_type": "BUY",  # Example
        "commission": 5.0,
        "commission_asset": "USD",
    }


# --- Trade Endpoint Tests ---


def test_create_trade_for_current_user(
    client: TestClient,
    normal_user_token_headers: Dict[str, str],
    test_user: models.User,
    test_assets: List[models.Asset],
) -> None:
    selected_asset = test_assets[0]
    data = get_trade_create_data(symbol=selected_asset.symbol)

    response = client.post(
        "/api/v1/trades/", headers=normal_user_token_headers, json=data
    )

    assert response.status_code == 201, response.text
    created_trade_data = response.json()
    assert created_trade_data["symbol"] == selected_asset.symbol
    assert created_trade_data["user_id"] == test_user.id
    assert Decimal(str(created_trade_data["quantity"])) == Decimal(
        str(data["quantity"])
    )  # Compare as Decimal
    assert "id" in created_trade_data


def test_create_trade_no_auth(
    client: TestClient, test_assets: List[models.Asset]
) -> None:
    data = get_trade_create_data(symbol=test_assets[0].symbol)
    response = client.post("/api/v1/trades/", json=data)
    assert response.status_code == 401  # Unauthorized


def test_read_trade_owned_by_user(
    client: TestClient,
    normal_user_token_headers: Dict[str, str],
    test_trade_for_user: models.Trade,
) -> None:
    # test_trade_for_user fixture creates a trade for the 'test_user'
    response = client.get(
        f"/api/v1/trades/{test_trade_for_user.id}", headers=normal_user_token_headers
    )
    assert response.status_code == 200, response.text
    trade_data = response.json()
    assert trade_data["id"] == test_trade_for_user.id
    assert trade_data["user_id"] == test_trade_for_user.user_id
    assert trade_data["symbol"] == test_trade_for_user.symbol


def test_read_trade_not_found(
    client: TestClient, normal_user_token_headers: Dict[str, str]
) -> None:
    non_existent_id = 999999
    response = client.get(
        f"/api/v1/trades/{non_existent_id}", headers=normal_user_token_headers
    )
    assert response.status_code == 404
    assert "Trade not found" in response.json()["detail"]


def test_read_trade_forbidden_other_user(
    client: TestClient,
    normal_user_token_headers: Dict[str, str],  # Token for test_user
    db_session: Session,
    other_user: models.User,  # A different user
    test_assets: List[models.Asset],
):
    # Create a trade for other_user
    other_user_trade_data = get_trade_create_data(symbol=test_assets[0].symbol)
    # Manually create trade for other_user using CRUD or a fixture if available
    trade_in_schema = trade_schema.TradeCreate(**other_user_trade_data)
    other_trade = crud_trade.trade.create_trade(
        db=db_session, trade_in=trade_in_schema, user_id=other_user.id
    )

    # test_user tries to access other_user's trade
    response = client.get(
        f"/api/v1/trades/{other_trade.id}", headers=normal_user_token_headers
    )
    assert response.status_code == 403  # Forbidden
    assert "Not enough permissions" in response.json()["detail"]


def test_read_trades_for_current_user(
    client: TestClient,
    normal_user_token_headers: Dict[str, str],
    db_session: Session,
    test_user: models.User,
    test_assets: List[models.Asset],
) -> None:
    # Ensure user has at least one trade (test_trade_for_user could be used if its scope allows multiples, or create one here)
    crud_trade.trade.create_trade(
        db=db_session,
        trade_in=trade_schema.TradeCreate(
            **get_trade_create_data(test_assets[0].symbol)
        ),
        user_id=test_user.id,
    )
    crud_trade.trade.create_trade(
        db=db_session,
        trade_in=trade_schema.TradeCreate(
            **get_trade_create_data(test_assets[1].symbol)
        ),
        user_id=test_user.id,
    )

    response = client.get("/api/v1/trades/", headers=normal_user_token_headers)
    assert response.status_code == 200, response.text
    trades_list = response.json()
    assert isinstance(trades_list, list)
    assert len(trades_list) >= 2  # Based on trades created above
    for trade_data in trades_list:
        assert trade_data["user_id"] == test_user.id


def test_update_trade_owned_by_user(
    client: TestClient,
    normal_user_token_headers: Dict[str, str],
    test_trade_for_user: models.Trade,
) -> None:
    update_data = {"quantity": 123.45, "commission": 7.89}  # Example update fields

    response = client.put(
        f"/api/v1/trades/{test_trade_for_user.id}",
        headers=normal_user_token_headers,
        json=update_data,
    )
    assert response.status_code == 200, response.text
    updated_trade_data = response.json()
    assert Decimal(str(updated_trade_data["quantity"])) == Decimal("123.45")
    assert Decimal(str(updated_trade_data["commission"])) == Decimal("7.89")
    assert (
        updated_trade_data["symbol"] == test_trade_for_user.symbol
    )  # Ensure other fields are intact or as expected


def test_update_trade_forbidden_other_user(
    client: TestClient,
    normal_user_token_headers: Dict[str, str],  # Token for test_user
    db_session: Session,
    other_user: models.User,
    test_assets: List[models.Asset],
):
    other_trade = crud_trade.trade.create_trade(
        db=db_session,
        trade_in=trade_schema.TradeCreate(
            **get_trade_create_data(test_assets[0].symbol)
        ),
        user_id=other_user.id,
    )
    update_data = {"quantity": 10.0}

    response = client.put(
        f"/api/v1/trades/{other_trade.id}",
        headers=normal_user_token_headers,
        json=update_data,
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]


def test_delete_trade_owned_by_user(
    client: TestClient,
    normal_user_token_headers: Dict[str, str],
    test_trade_for_user: models.Trade,
    db_session: Session,
) -> None:
    trade_id_to_delete = test_trade_for_user.id
    response = client.delete(
        f"/api/v1/trades/{trade_id_to_delete}", headers=normal_user_token_headers
    )
    assert response.status_code == 200, response.text
    deleted_trade_data = response.json()
    assert deleted_trade_data["id"] == trade_id_to_delete
    assert (
        deleted_trade_data["is_deleted"] == True
    )  # Assuming schema includes this for soft delete response

    # Verify in DB (it should be marked as deleted)
    db_trade = crud_trade.trade.get_trade(db=db_session, trade_id=trade_id_to_delete)
    assert db_trade is None  # Because get_trade filters out deleted ones

    # Optionally, query with deleted to confirm:
    # trade_with_deleted = db_session.query(models.Trade).filter(models.Trade.id == trade_id_to_delete).first()
    # assert trade_with_deleted is not None
    # assert trade_with_deleted.is_deleted == True


def test_delete_trade_forbidden_other_user(
    client: TestClient,
    normal_user_token_headers: Dict[str, str],
    db_session: Session,
    other_user: models.User,
    test_assets: List[models.Asset],
):
    other_trade = crud_trade.trade.create_trade(
        db=db_session,
        trade_in=trade_schema.TradeCreate(
            **get_trade_create_data(test_assets[0].symbol)
        ),
        user_id=other_user.id,
    )

    response = client.delete(
        f"/api/v1/trades/{other_trade.id}", headers=normal_user_token_headers
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]


# Add tests for:
# - Invalid input data for create/update (e.g., negative quantity, invalid symbol format if validated)
# - Pagination for list endpoint (if skip/limit are fully tested)
# - Filtering trades by other criteria if implemented (e.g., by symbol, date range)
