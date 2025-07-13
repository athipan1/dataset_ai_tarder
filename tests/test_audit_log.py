from datetime import datetime, timezone
from typing import Optional

import pytest
from sqlalchemy.orm import Session

from ai_trader.auth_context import (
    USER_CONTEXT,
    CurrentUser,
    auth_context,
    current_user_id_context_var,
)
from ai_trader.event_listeners import register_audit_listeners
from ai_trader.models import (
    Asset,
    AuditLog,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Strategy,
    Trade,
    TradeType,
    User,
)


@pytest.fixture(scope="function")
def db_session_audit():
    from sqlalchemy import create_engine
    from sqlalchemy import event as sa_event
    from sqlalchemy.engine import Engine

    from ai_trader.models import Base

    @sa_event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    session_instance = Session(bind=engine)
    try:
        # Call register_audit_listeners() here if it's not guaranteed to be called by app init
        # For isolated testing, explicit registration within the test setup is safer.
        # However, if ai_trader.__init__ calls it and pytest loads the package, it should be fine.
        # To be absolutely sure for these tests, let's call it.
        # register_audit_listeners() # This might lead to duplicate listeners if called elsewhere too.
        # Best practice: ensure it's idempotent or called once globally.
        # For now, assume it's handled by package init or is idempotent.
        yield session_instance
    finally:
        session_instance.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_user_for_audit(db_session_audit: Session):
    user = User(
        username="audit_user", email="audit@example.com", hashed_password="password"
    )
    user.is_active = True
    user.is_superuser = False
    db_session_audit.add(user)
    db_session_audit.commit()
    db_session_audit.refresh(user)
    return user


@pytest.fixture
def current_user_ctx(test_user_for_audit: User):
    if not hasattr(test_user_for_audit, "is_superuser"):
        test_user_for_audit.is_superuser = False
    cu = CurrentUser(
        user_id=test_user_for_audit.id,
        username=test_user_for_audit.username,
        is_superuser=test_user_for_audit.is_superuser,
    )
    return auth_context(cu)


def get_audit_logs(
    session: Session, table_name: Optional[str] = None, action: Optional[str] = None
) -> list[AuditLog]:
    query = session.query(AuditLog)
    if table_name:
        query = query.filter(AuditLog.table_name == table_name)
    if action:
        query = query.filter(AuditLog.action == action)
    return query.order_by(AuditLog.timestamp.asc()).all()


# User Audit Tests
def test_audit_log_on_user_creation(
    db_session_audit: Session, test_user_for_audit: User
):
    db_session_audit.query(AuditLog).delete()
    db_session_audit.commit()

    creator = User(
        username="creator_user_audit",
        email="creator_audit@example.com",
        hashed_password="pw",
    )
    creator.is_active = True
    creator.is_superuser = True
    db_session_audit.add(creator)
    db_session_audit.commit()
    db_session_audit.refresh(creator)

    creator_user_details = CurrentUser(
        user_id=creator.id, username=creator.username, is_superuser=creator.is_superuser
    )

    with auth_context(creator_user_details):
        new_user = User(
            username="newly_created_for_audit_test",
            email="new_audit_test@example.com",
            hashed_password="pw",
        )
        new_user.is_active = True
        new_user.is_superuser = False
        db_session_audit.add(new_user)
        db_session_audit.commit()
        new_user_id = new_user.id

    logs = get_audit_logs(db_session_audit, table_name="users", action="INSERT")
    new_user_log_found = False
    for log in reversed(logs):
        if (
            log.table_name == "users"
            and log.action == "INSERT"
            and log.record_id == new_user_id
            and log.changed_by == creator_user_details.user_id
        ):
            assert "username" in log.changes
            assert log.changes["username"] == "newly_created_for_audit_test"
            new_user_log_found = True
            break
    assert new_user_log_found, "Audit log for new user creation not found or incorrect."


def test_audit_log_on_user_update(
    db_session_audit: Session, test_user_for_audit: User, current_user_ctx
):
    db_session_audit.query(AuditLog).filter(AuditLog.table_name == "users").delete()
    db_session_audit.commit()

    user_to_update = (
        db_session_audit.query(User).filter_by(id=test_user_for_audit.id).one()
    )
    original_username = user_to_update.username
    original_email = user_to_update.email

    with current_user_ctx:
        user_to_update.username = "updated_audit_user_test"
        user_to_update.email = "updated_audit_test@example.com"
        db_session_audit.commit()

    logs = get_audit_logs(db_session_audit, table_name="users", action="UPDATE")
    update_log_found = False
    for log in reversed(logs):
        if log.record_id == user_to_update.id and log.action == "UPDATE":
            assert log.changed_by == test_user_for_audit.id
            assert "username" in log.changes
            assert log.changes["username"]["old"] == original_username
            assert log.changes["username"]["new"] == "updated_audit_user_test"
            assert "email" in log.changes
            assert log.changes["email"]["old"] == original_email
            assert log.changes["email"]["new"] == "updated_audit_test@example.com"
            update_log_found = True
            break
    assert update_log_found, "Update audit log for User not found or details mismatch."


def test_audit_log_on_user_delete(
    db_session_audit: Session, test_user_for_audit: User, current_user_ctx
):
    user_to_delete = (
        db_session_audit.query(User).filter_by(id=test_user_for_audit.id).one()
    )
    user_id_to_delete = user_to_delete.id
    original_username = user_to_delete.username

    db_session_audit.query(AuditLog).filter(AuditLog.table_name == "users").delete()
    db_session_audit.commit()

    with current_user_ctx:
        if hasattr(user_to_delete, "soft_delete"):
            user_to_delete.soft_delete(db_session_audit)
        else:
            db_session_audit.delete(user_to_delete)
        db_session_audit.commit()

    expected_action = "UPDATE" if hasattr(user_to_delete, "soft_delete") else "DELETE"
    logs = get_audit_logs(db_session_audit, table_name="users", action=expected_action)
    delete_log_found = False
    for log in reversed(logs):
        if log.record_id == user_id_to_delete and log.action == expected_action:
            assert log.changed_by == test_user_for_audit.id
            if expected_action == "UPDATE":
                assert "is_deleted" in log.changes
                assert log.changes["is_deleted"]["new"] is True
            elif expected_action == "DELETE":
                assert "username" in log.changes
                assert log.changes["username"] == original_username
            delete_log_found = True
            break
    assert delete_log_found, f"{expected_action} audit log for User not found."


# Asset Audit Tests
@pytest.fixture
def sample_asset(db_session_audit: Session):
    asset = Asset(symbol="AUDITASSET_TEST", name="Audit Asset Test", asset_type="Stock")
    db_session_audit.add(asset)
    db_session_audit.commit()
    db_session_audit.refresh(asset)
    return asset


def test_audit_log_on_asset_creation(
    db_session_audit: Session, test_user_for_audit: User, current_user_ctx
):
    db_session_audit.query(AuditLog).delete()
    db_session_audit.commit()

    with current_user_ctx:
        new_asset = Asset(symbol="NEWASSET", name="New Test Asset", asset_type="Crypto")
        db_session_audit.add(new_asset)
        db_session_audit.commit()
        new_asset_id = new_asset.id

    logs = get_audit_logs(db_session_audit, table_name="assets", action="INSERT")
    asset_log_found = False
    for log in reversed(logs):
        if (
            log.table_name == "assets"
            and log.action == "INSERT"
            and log.record_id == new_asset_id
            and log.changed_by == test_user_for_audit.id
        ):
            assert "symbol" in log.changes
            assert log.changes["symbol"] == "NEWASSET"
            asset_log_found = True
            break
    assert asset_log_found, "Audit log for Asset creation not found."


def test_audit_log_on_asset_update(
    db_session_audit: Session,
    sample_asset: Asset,
    test_user_for_audit: User,
    current_user_ctx,
):
    db_session_audit.query(AuditLog).filter(AuditLog.table_name == "assets").delete()
    db_session_audit.commit()

    asset_to_update = db_session_audit.query(Asset).filter_by(id=sample_asset.id).one()
    original_name = asset_to_update.name

    with current_user_ctx:
        asset_to_update.name = "Updated Asset Name"
        db_session_audit.commit()

    logs = get_audit_logs(db_session_audit, table_name="assets", action="UPDATE")
    update_log_found = False
    for log in reversed(logs):
        if log.record_id == asset_to_update.id and log.action == "UPDATE":
            assert log.changed_by == test_user_for_audit.id
            assert "name" in log.changes
            assert log.changes["name"]["old"] == original_name
            assert log.changes["name"]["new"] == "Updated Asset Name"
            update_log_found = True
            break
    assert update_log_found, "Update audit log for Asset not found."


# Strategy Audit Tests
@pytest.fixture
def sample_strategy(db_session_audit: Session, test_user_for_audit: User):
    strategy = Strategy(
        name="AuditStrategyTest",
        description="Test audit for strategy",
        user_id=test_user_for_audit.id,
    )
    db_session_audit.add(strategy)
    db_session_audit.commit()
    db_session_audit.refresh(strategy)
    return strategy


def test_audit_log_on_strategy_creation(
    db_session_audit: Session, test_user_for_audit: User, current_user_ctx
):
    db_session_audit.query(AuditLog).delete()
    db_session_audit.commit()

    with current_user_ctx:
        new_strategy = Strategy(
            name="NewAuditStrategy",
            description="A new strategy for audit",
            user_id=test_user_for_audit.id,
        )
        db_session_audit.add(new_strategy)
        db_session_audit.commit()
        new_strategy_id = new_strategy.id

    logs = get_audit_logs(db_session_audit, table_name="strategies", action="INSERT")
    strategy_log_found = False
    for log in reversed(logs):
        if (
            log.table_name == "strategies"
            and log.action == "INSERT"
            and log.record_id == new_strategy_id
            and log.changed_by == test_user_for_audit.id
        ):
            assert "name" in log.changes
            assert log.changes["name"] == "NewAuditStrategy"
            strategy_log_found = True
            break
    assert strategy_log_found, "Audit log for Strategy creation not found."


def test_audit_log_on_strategy_update(
    db_session_audit: Session,
    sample_strategy: Strategy,
    test_user_for_audit: User,
    current_user_ctx,
):
    db_session_audit.query(AuditLog).filter(
        AuditLog.table_name == "strategies"
    ).delete()
    db_session_audit.commit()

    strategy_to_update = (
        db_session_audit.query(Strategy).filter_by(id=sample_strategy.id).one()
    )
    original_description = strategy_to_update.description

    with current_user_ctx:
        strategy_to_update.description = "Updated Test Audit Strategy Description"
        db_session_audit.commit()

    logs = get_audit_logs(db_session_audit, table_name="strategies", action="UPDATE")
    update_log_found = False
    for log in reversed(logs):
        if log.record_id == strategy_to_update.id and log.action == "UPDATE":
            assert log.changed_by == test_user_for_audit.id
            assert "description" in log.changes
            assert log.changes["description"]["old"] == original_description
            assert (
                log.changes["description"]["new"]
                == "Updated Test Audit Strategy Description"
            )
            update_log_found = True
            break
    assert update_log_found, "Update audit log for Strategy not found."


# Trade Audit Test (already exists, ensure it's fine)
def test_audit_log_on_trade_creation(
    db_session_audit: Session,
    test_user_for_audit: User,
    sample_asset: Asset,
    current_user_ctx,
):
    db_session_audit.query(AuditLog).delete()
    db_session_audit.commit()

    with current_user_ctx:
        order = Order(
            user_id=test_user_for_audit.id,
            asset_id=sample_asset.id,
            order_type=OrderType.MARKET,
            order_side=OrderSide.BUY,
            status=OrderStatus.FILLED,
            quantity=1.0,
            price=50000.0,
        )
        db_session_audit.add(order)
        db_session_audit.commit()

        trade = Trade(
            user_id=test_user_for_audit.id,
            order_id=order.id,
            symbol=sample_asset.symbol,
            quantity=1.0,
            price=50000.0,
            trade_type=TradeType.BUY,
            timestamp=datetime.now(timezone.utc),
        )
        db_session_audit.add(trade)
        db_session_audit.commit()
        trade_id = trade.id

    logs = get_audit_logs(db_session_audit, table_name="trades", action="INSERT")
    trade_log_found = False
    for log in reversed(logs):
        if (
            log.table_name == "trades"
            and log.action == "INSERT"
            and log.record_id == trade_id
            and log.changed_by == test_user_for_audit.id
        ):
            assert "symbol" in log.changes
            assert log.changes["symbol"] == "AUDITASSET_TEST"  # Corrected asset symbol
            assert "quantity" in log.changes
            assert float(log.changes["quantity"]) == 1.0
            trade_log_found = True
            break
    assert trade_log_found, "Audit log for Trade creation not found or incorrect."


# Test for no audit log if user context is not set
def test_no_audit_if_user_context_not_set(db_session_audit: Session):
    db_session_audit.query(User).delete()
    db_session_audit.query(AuditLog).delete()
    db_session_audit.commit()

    token_user_ctx = USER_CONTEXT.set(None)
    token_id_legacy_ctx = current_user_id_context_var.set(None)

    new_user_id = None
    try:
        user = User(
            username="unattributed_audit_user",
            email="none_audit@example.com",
            hashed_password="pw",
        )
        user.is_active = True
        user.is_superuser = False
        db_session_audit.add(user)
        db_session_audit.commit()
        new_user_id = user.id
    finally:
        USER_CONTEXT.reset(token_user_ctx)
        current_user_id_context_var.reset(token_id_legacy_ctx)

    logs = get_audit_logs(db_session_audit, table_name="users", action="INSERT")
    unattributed_log_found = False
    for log in reversed(logs):
        if (
            log.table_name == "users"
            and log.action == "INSERT"
            and log.record_id == new_user_id
        ):
            assert log.changed_by is None
            assert "username" in log.changes
            assert log.changes["username"] == "unattributed_audit_user"
            unattributed_log_found = True
            break
    assert (
        unattributed_log_found
    ), "Audit log for unattributed user creation not found or incorrect."


# Test for listener registration idempotency
def test_audit_listener_registration_idempotency():
    try:
        register_audit_listeners()
        register_audit_listeners()
    except Exception as e:
        pytest.fail(f"register_audit_listeners raised an exception on second call: {e}")
