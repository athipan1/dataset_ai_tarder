import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from typing import Dict, List, Optional  # For type hints
import datetime

from ai_trader import models
from schemas import analytics as analytics_schema
from crud import crud_analytics, crud_strategy  # For creating related strategies


# --- Helper to generate analytics data ---
def get_analytics_create_data(
    total_trades: int = 100, win_rate: float = 0.75, total_pnl: float = 5000.0
) -> dict:
    return {
        "total_trades": total_trades,
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "avg_risk_reward": 1.5,
        "max_drawdown": 0.10,  # 10%
        "notes": "Initial performance data.",
    }


# --- Analytics Endpoint Tests ---


def test_create_analytics_entry_for_user(
    client: TestClient,
    normal_user_token_headers: Dict[str, str],
    test_user: models.User,
) -> None:
    data = get_analytics_create_data()

    response = client.post(
        "/api/v1/analytics/", headers=normal_user_token_headers, json=data
    )

    assert response.status_code == 201, response.text
    created_entry_data = response.json()
    assert created_entry_data["total_trades"] == data["total_trades"]
    assert created_entry_data["user_id"] == test_user.id
    assert (
        created_entry_data["strategy_id"] is None
    )  # No strategy_id passed as query param
    assert "id" in created_entry_data
    assert (
        datetime.date.fromisoformat(created_entry_data["analysis_date"])
        == datetime.date.today()
    )


def test_create_analytics_entry_for_user_with_strategy(
    client: TestClient,
    normal_user_token_headers: Dict[str, str],
    test_user: models.User,
    test_strategy_for_user: models.Strategy,  # Fixture that creates a strategy for test_user
) -> None:
    data = get_analytics_create_data(total_trades=50)
    strategy_id = test_strategy_for_user.id

    response = client.post(
        f"/api/v1/analytics/?strategy_id={strategy_id}",
        headers=normal_user_token_headers,
        json=data,
    )

    assert response.status_code == 201, response.text
    created_entry_data = response.json()
    assert created_entry_data["total_trades"] == data["total_trades"]
    assert created_entry_data["user_id"] == test_user.id
    assert created_entry_data["strategy_id"] == strategy_id


def test_create_analytics_entry_with_nonexistent_strategy(
    client: TestClient,
    normal_user_token_headers: Dict[str, str],
    test_user: models.User,
) -> None:
    data = get_analytics_create_data()
    non_existent_strategy_id = 99999
    response = client.post(
        f"/api/v1/analytics/?strategy_id={non_existent_strategy_id}",
        headers=normal_user_token_headers,
        json=data,
    )
    assert response.status_code == 404  # Not Found for strategy
    assert "Strategy with id" in response.json()["detail"]


def test_create_analytics_entry_with_strategy_of_other_user(
    client: TestClient,
    normal_user_token_headers: Dict[str, str],  # Belongs to test_user
    test_user: models.User,
    other_user: models.User,  # Another user
    db_session: Session,
) -> None:
    from schemas import strategy as strategy_schema  # Added import

    # Create a strategy for other_user
    other_user_strategy = crud_strategy.strategy.create_strategy(
        db=db_session,
        strategy_in=strategy_schema.StrategyCreate(name="OtherUserStrat", description="desc"),  # type: ignore
        user_id=other_user.id,
    )
    data = get_analytics_create_data()

    response = client.post(
        f"/api/v1/analytics/?strategy_id={other_user_strategy.id}",
        headers=normal_user_token_headers,
        json=data,
    )
    assert response.status_code == 403  # Forbidden
    assert "Strategy does not belong to the current user" in response.json()["detail"]


def test_read_analytics_entry_owned_by_user(
    client: TestClient,
    normal_user_token_headers: Dict[str, str],
    db_session: Session,
    test_user: models.User,
) -> None:
    entry = crud_analytics.trade_analytics.create_analytic_entry(
        db=db_session,
        analytics_in=analytics_schema.AnalyticsDataCreate(
            **get_analytics_create_data()
        ),
        user_id=test_user.id,
    )

    response = client.get(
        f"/api/v1/analytics/{entry.id}", headers=normal_user_token_headers
    )
    assert response.status_code == 200, response.text
    entry_data = response.json()
    assert entry_data["id"] == entry.id
    assert entry_data["user_id"] == test_user.id


def test_read_analytics_by_user(
    client: TestClient,
    normal_user_token_headers: Dict[str, str],
    db_session: Session,
    test_user: models.User,
) -> None:
    crud_analytics.trade_analytics.create_analytic_entry(
        db=db_session,
        analytics_in=analytics_schema.AnalyticsDataCreate(
            **get_analytics_create_data(total_trades=10)
        ),
        user_id=test_user.id,
    )
    crud_analytics.trade_analytics.create_analytic_entry(
        db=db_session,
        analytics_in=analytics_schema.AnalyticsDataCreate(
            **get_analytics_create_data(total_trades=20)
        ),
        user_id=test_user.id,
    )

    response = client.get("/api/v1/analytics/user/", headers=normal_user_token_headers)
    assert response.status_code == 200, response.text
    entries_list = response.json()
    assert isinstance(entries_list, list)
    assert len(entries_list) >= 2
    for entry_data in entries_list:
        assert entry_data["user_id"] == test_user.id


def test_read_analytics_by_strategy_owned_by_user(
    client: TestClient,
    normal_user_token_headers: Dict[str, str],
    db_session: Session,
    test_user: models.User,
    test_strategy_for_user: models.Strategy,  # Strategy owned by test_user
) -> None:
    strategy_id = test_strategy_for_user.id
    crud_analytics.trade_analytics.create_analytic_entry(
        db=db_session,
        analytics_in=analytics_schema.AnalyticsDataCreate(
            **get_analytics_create_data(total_trades=30)
        ),
        user_id=test_user.id,
        strategy_id=strategy_id,
    )
    crud_analytics.trade_analytics.create_analytic_entry(
        db=db_session,
        analytics_in=analytics_schema.AnalyticsDataCreate(
            **get_analytics_create_data(total_trades=40)
        ),
        user_id=test_user.id,
        strategy_id=strategy_id,
    )

    response = client.get(
        f"/api/v1/analytics/strategy/{strategy_id}", headers=normal_user_token_headers
    )
    assert response.status_code == 200, response.text
    entries_list = response.json()
    assert isinstance(entries_list, list)
    assert len(entries_list) >= 2
    for entry_data in entries_list:
        assert entry_data["user_id"] == test_user.id
        assert entry_data["strategy_id"] == strategy_id


def test_read_analytics_by_strategy_of_other_user_forbidden(
    client: TestClient,
    normal_user_token_headers: Dict[str, str],  # Belongs to test_user
    db_session: Session,
    other_user: models.User,  # Another user
):
    from schemas import strategy as strategy_schema  # Added import

    # Strategy belonging to other_user
    other_user_strategy = crud_strategy.strategy.create_strategy(
        db=db_session,
        strategy_in=strategy_schema.StrategyCreate(name="OtherUserStratAnalytics", description="desc"),  # type: ignore
        user_id=other_user.id,
    )
    response = client.get(
        f"/api/v1/analytics/strategy/{other_user_strategy.id}",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 403  # Forbidden
    assert "Strategy does not belong to the current user" in response.json()["detail"]


def test_update_analytics_entry_owned_by_user(
    client: TestClient,
    normal_user_token_headers: Dict[str, str],
    db_session: Session,
    test_user: models.User,
) -> None:
    entry = crud_analytics.trade_analytics.create_analytic_entry(
        db=db_session,
        analytics_in=analytics_schema.AnalyticsDataCreate(
            **get_analytics_create_data()
        ),
        user_id=test_user.id,
    )
    update_data = {"total_pnl": 12345.67, "notes": "Updated notes."}

    response = client.put(
        f"/api/v1/analytics/{entry.id}",
        headers=normal_user_token_headers,
        json=update_data,
    )
    assert response.status_code == 200, response.text
    updated_entry_data = response.json()
    assert updated_entry_data["total_pnl"] == 12345.67
    assert updated_entry_data["notes"] == "Updated notes."


def test_delete_analytics_entry_owned_by_user(
    client: TestClient,
    normal_user_token_headers: Dict[str, str],
    db_session: Session,
    test_user: models.User,
) -> None:
    entry = crud_analytics.trade_analytics.create_analytic_entry(
        db=db_session,
        analytics_in=analytics_schema.AnalyticsDataCreate(
            **get_analytics_create_data()
        ),
        user_id=test_user.id,
    )
    entry_id_to_delete = entry.id

    response = client.delete(
        f"/api/v1/analytics/{entry_id_to_delete}", headers=normal_user_token_headers
    )
    assert response.status_code == 200, response.text
    deleted_entry_data = response.json()
    assert deleted_entry_data["id"] == entry_id_to_delete
    assert deleted_entry_data["is_deleted"] is True

    # Verify in DB
    db_entry = crud_analytics.trade_analytics.get_analytic(
        db=db_session, analytic_id=entry_id_to_delete
    )
    assert db_entry is None


# Add tests for:
# - Permissions when trying to update/delete analytics of another user.
# - Invalid input for create/update (e.g., win_rate > 1.0).
# - Pagination for list endpoints.
# - Behavior when associated strategy is deleted (if analytics entries should also be soft-deleted - depends on cascade logic).
#   The current soft_delete in Strategy model cascades to TradeAnalytics. So, if a strategy is soft-deleted,
#   its related analytics entries should also be soft-deleted. This interaction needs testing.
#   Example:
#   1. Create User U1, Strategy S1 (for U1), Analytics A1 (for S1, U1).
#   2. Soft delete S1 (e.g., via API or direct CRUD call for test setup).
#   3. Try to GET A1 via API. Expect 404 (as it should also be soft-deleted).
#   4. Query DB directly to confirm A1.is_deleted is True.
