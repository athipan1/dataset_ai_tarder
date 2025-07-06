import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from typing import Dict, List  # For type hints

from ai_trader import models  # For type hinting models.User, models.Strategy
from schemas import strategy as strategy_schema  # For creating StrategyCreate schemas
from crud import crud_strategy  # To potentially verify DB state directly


# --- Helper to generate strategy data ---
def get_strategy_create_data(
    name: str = "My Algo Strategy", description: str = "A test strategy"
) -> dict:
    return {
        "name": name,
        "description": description,
        "model_version": "1.0.0",
        "parameters": {"lookback": 20, "threshold": 0.5},
    }


# --- Strategy Endpoint Tests ---


def test_create_strategy_for_current_user(
    client: TestClient,
    normal_user_token_headers: Dict[str, str],
    test_user: models.User,
) -> None:
    data = get_strategy_create_data(name="User1 New Strategy")

    response = client.post(
        "/api/v1/strategies/", headers=normal_user_token_headers, json=data
    )

    assert response.status_code == 201, response.text
    created_strategy_data = response.json()
    assert created_strategy_data["name"] == data["name"]
    assert created_strategy_data["user_id"] == test_user.id
    assert "id" in created_strategy_data
    assert created_strategy_data["parameters"]["lookback"] == 20


def test_create_strategy_no_auth(client: TestClient) -> None:
    data = get_strategy_create_data()
    response = client.post("/api/v1/strategies/", json=data)
    assert response.status_code == 401  # Unauthorized


def test_read_strategy_owned_by_user(
    client: TestClient,
    normal_user_token_headers: Dict[str, str],
    test_strategy_for_user: models.Strategy,
) -> None:
    # test_strategy_for_user fixture creates a strategy for the 'test_user'
    response = client.get(
        f"/api/v1/strategies/{test_strategy_for_user.id}",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 200, response.text
    strategy_data = response.json()
    assert strategy_data["id"] == test_strategy_for_user.id
    assert strategy_data["user_id"] == test_strategy_for_user.user_id
    assert strategy_data["name"] == test_strategy_for_user.name


def test_read_strategy_not_found(
    client: TestClient, normal_user_token_headers: Dict[str, str]
) -> None:
    non_existent_id = 888888
    response = client.get(
        f"/api/v1/strategies/{non_existent_id}", headers=normal_user_token_headers
    )
    assert response.status_code == 404
    assert "Strategy not found" in response.json()["detail"]


def test_read_strategy_forbidden_other_user(
    client: TestClient,
    normal_user_token_headers: Dict[str, str],  # Token for test_user
    db_session: Session,
    other_user: models.User,  # A different user
):
    # Create a strategy for other_user
    other_user_strategy_data = get_strategy_create_data(name="Other User Strategy")
    strategy_in_schema = strategy_schema.StrategyCreate(**other_user_strategy_data)
    other_strategy = crud_strategy.strategy.create_strategy(
        db=db_session, strategy_in=strategy_in_schema, user_id=other_user.id
    )

    # test_user tries to access other_user's strategy
    response = client.get(
        f"/api/v1/strategies/{other_strategy.id}", headers=normal_user_token_headers
    )
    assert response.status_code == 403  # Forbidden
    assert "Not enough permissions" in response.json()["detail"]


def test_read_strategies_for_current_user(
    client: TestClient,
    normal_user_token_headers: Dict[str, str],
    db_session: Session,
    test_user: models.User,
) -> None:
    # Ensure user has at least a couple of strategies
    crud_strategy.strategy.create_strategy(
        db=db_session,
        strategy_in=strategy_schema.StrategyCreate(
            **get_strategy_create_data("Strat A")
        ),
        user_id=test_user.id,
    )
    crud_strategy.strategy.create_strategy(
        db=db_session,
        strategy_in=strategy_schema.StrategyCreate(
            **get_strategy_create_data("Strat B")
        ),
        user_id=test_user.id,
    )

    response = client.get("/api/v1/strategies/", headers=normal_user_token_headers)
    assert response.status_code == 200, response.text
    strategies_list = response.json()
    assert isinstance(strategies_list, list)
    assert len(strategies_list) >= 2  # Based on strategies created
    for strat_data in strategies_list:
        assert strat_data["user_id"] == test_user.id


def test_update_strategy_owned_by_user(
    client: TestClient,
    normal_user_token_headers: Dict[str, str],
    test_strategy_for_user: models.Strategy,
) -> None:
    update_data = {
        "name": "Updated Strategy Name",
        "parameters": {"lookback": 30, "new_param": "test"},
    }

    response = client.put(
        f"/api/v1/strategies/{test_strategy_for_user.id}",
        headers=normal_user_token_headers,
        json=update_data,
    )
    assert response.status_code == 200, response.text
    updated_strategy_data = response.json()
    assert updated_strategy_data["name"] == "Updated Strategy Name"
    assert updated_strategy_data["parameters"]["lookback"] == 30
    assert updated_strategy_data["parameters"]["new_param"] == "test"
    assert (
        updated_strategy_data["description"] == test_strategy_for_user.description
    )  # Check non-updated field


def test_update_strategy_forbidden_other_user(
    client: TestClient,
    normal_user_token_headers: Dict[str, str],
    db_session: Session,
    other_user: models.User,
):
    other_strategy = crud_strategy.strategy.create_strategy(
        db=db_session,
        strategy_in=strategy_schema.StrategyCreate(
            **get_strategy_create_data("Other Strat")
        ),
        user_id=other_user.id,
    )
    update_data = {"name": "Attempted Update"}

    response = client.put(
        f"/api/v1/strategies/{other_strategy.id}",
        headers=normal_user_token_headers,
        json=update_data,
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]


def test_delete_strategy_owned_by_user(
    client: TestClient,
    normal_user_token_headers: Dict[str, str],
    test_strategy_for_user: models.Strategy,
    db_session: Session,
) -> None:
    strategy_id_to_delete = test_strategy_for_user.id
    response = client.delete(
        f"/api/v1/strategies/{strategy_id_to_delete}", headers=normal_user_token_headers
    )
    assert response.status_code == 200, response.text
    deleted_strategy_data = response.json()
    assert deleted_strategy_data["id"] == strategy_id_to_delete
    assert deleted_strategy_data["is_deleted"] == True

    # Verify in DB
    db_strategy = crud_strategy.strategy.get_strategy(
        db=db_session, strategy_id=strategy_id_to_delete
    )
    assert db_strategy is None


def test_delete_strategy_forbidden_other_user(
    client: TestClient,
    normal_user_token_headers: Dict[str, str],
    db_session: Session,
    other_user: models.User,
):
    other_strategy = crud_strategy.strategy.create_strategy(
        db=db_session,
        strategy_in=strategy_schema.StrategyCreate(
            **get_strategy_create_data("Other Strat to Delete")
        ),
        user_id=other_user.id,
    )

    response = client.delete(
        f"/api/v1/strategies/{other_strategy.id}", headers=normal_user_token_headers
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]


# Add tests for:
# - Invalid input data for create/update (e.g., missing name, invalid parameter structure if validated)
# - Uniqueness constraint on (user_id, name) if enforced by DB/model.
# - Pagination for list endpoint.
# - Cascading deletes (e.g., if deleting a strategy also deletes related signals or analytics - depends on model relationships and soft_delete logic).
#   The current soft_delete on Strategy model cascades to Orders, Signals, BacktestResults, TradeAnalytics. This needs careful testing.
#   For API tests, we'd check that related items are also soft-deleted or handled as per business logic.
#   This might involve creating these related items first, then deleting the strategy and verifying.
#   Example:
#   1. Create User U1.
#   2. Create Strategy S1 for U1.
#   3. Create Analytics A1 for S1 and U1.
#   4. Delete S1 via API.
#   5. Verify S1 is soft-deleted.
#   6. Verify A1 is also soft-deleted (by trying to GET it and expecting 404, or querying DB directly).
