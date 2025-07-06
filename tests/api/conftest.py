import pytest
from typing import Generator, Any

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool  # Recommended for SQLite in tests

from ai_trader.models import Base  # Corrected import for Base
from api.main import app  # Your FastAPI application
from api.deps.db import get_db  # The dependency we want to override
from ai_trader.config import settings  # To potentially use a test DB URL if defined
from ai_trader import (
    models as GLOBAL_MODELS,
)  # Make alias available globally in this file

# --- Test Database Setup ---
# Using an in-memory SQLite database for tests
# SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
# More robust: Use a test-specific database URL from settings or a default
TEST_DATABASE_URL = (
    settings.DATABASE_URL + "_test" if settings.DATABASE_URL else "sqlite:///:memory:"
)
if "sqlite" in TEST_DATABASE_URL:
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},  # Needed for SQLite
        poolclass=StaticPool,  # Use StaticPool for SQLite in-memory for tests
    )
else:
    engine = create_engine(TEST_DATABASE_URL)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables in the test database
# This should happen once before any tests run that interact with the DB.
# A fixture can manage this, or it can be done globally here if careful.
# For simplicity here, but pytest-django or similar might offer more robust setup/teardown.


@pytest.fixture(scope="session", autouse=True)
def create_test_tables():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# --- Override `get_db` Dependency for Tests ---
def override_get_db() -> Generator[Session, Any, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


# --- Fixtures ---
@pytest.fixture(
    scope="module"
)  # Or "session" if client can be reused across all test files
def client() -> Generator[TestClient, Any, None]:
    """
    Yield a TestClient instance that uses the overridden get_db.
    """
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")  # Session scope for initial DB setup for all tests
def module_db_session(create_test_tables: None) -> Generator[Session, Any, None]:
    # create_test_tables ensures tables are ready for the whole test session
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db_session(
    create_test_tables: None,
) -> Generator[Session, Any, None]:  # Depends on table creation
    """
    Yield a database session for direct interaction during tests (function scope).
    Ensures the session is closed after the test.
    """
    # This fixture provides a session directly from TestingSessionLocal
    # which is what override_get_db also uses.
    # Useful for setting up data or verifying DB state outside of API calls.
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Fixture to get a regular user's token and the user model instance
@pytest.fixture(scope="module")
def normal_user_token_headers(
    client: TestClient, module_db_session: Session
) -> dict[str, str]:
    from crud import crud_user  # Imports crud_user.user object
    from crud.crud_user import (
        get_password_hash,
    )  # Import directly from crud_user module
    from schemas.user import UserCreate
    from ai_trader.config import settings
    from api.deps.auth import create_access_token

    # GLOBAL_MODELS is now defined at the top of the file

    # Ensure a consistent test user for token generation
    # This user is created once per module if not existing.
    username = settings.PROJECT_NAME.lower().replace(" ", "") + "_testuser@example.com"
    email = username
    password = "testpassword"

    user = crud_user.user.get_user_by_username(module_db_session, username=username)
    if not user:
        hashed_password = get_password_hash(password)  # Use the same hashing as in app
        user = GLOBAL_MODELS.User(
            username=username, email=email, hashed_password=hashed_password
        )
        module_db_session.add(user)
        module_db_session.commit()
        module_db_session.refresh(user)

    access_token = create_access_token(data={"sub": user.username})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture(scope="module")
def test_user(module_db_session: Session) -> GLOBAL_MODELS.User:
    from crud import crud_user  # crud_user.user object
    from ai_trader.config import settings

    # This fixture provides the user object corresponding to normal_user_token_headers
    username = settings.PROJECT_NAME.lower().replace(" ", "") + "_testuser@example.com"
    user = crud_user.user.get_user_by_username(module_db_session, username=username)
    assert (
        user is not None
    ), "Test user should have been created by normal_user_token_headers fixture"
    return user


# --- Fixture for a second user (useful for testing permissions) ---
@pytest.fixture(scope="module")
def other_user(module_db_session: Session) -> GLOBAL_MODELS.User:
    from crud import crud_user  # Imports crud_user.user object
    from crud.crud_user import (
        get_password_hash,
    )  # Import directly from crud_user module
    from schemas.user import UserCreate

    # GLOBAL_MODELS is now defined at the top of the file

    username = "otheruser@example.com"
    email = "otheruser@example.com"
    password = "otherpassword"

    user = crud_user.user.get_user_by_username(module_db_session, username=username)
    if not user:
        hashed_password = get_password_hash(password)
        user = GLOBAL_MODELS.User(
            username=username, email=email, hashed_password=hashed_password
        )
        module_db_session.add(user)
        module_db_session.commit()
        module_db_session.refresh(user)
    return user


# --- Data Seeding Fixtures (using Faker and concepts from seed scripts) ---
from faker import Faker
import random
from decimal import Decimal
from datetime import datetime, timedelta, timezone

fake = Faker()


@pytest.fixture(scope="module")
def test_assets(module_db_session: Session) -> list[GLOBAL_MODELS.Asset]:
    # GLOBAL_MODELS is now defined at the top of the file
    assets_data = [
        {"symbol": "BTCUSD", "name": "Bitcoin USD", "asset_type": "CRYPTO"},
        {"symbol": "ETHUSD", "name": "Ethereum USD", "asset_type": "CRYPTO"},
        {"symbol": "AAPL", "name": "Apple Inc.", "asset_type": "STOCK"},
    ]
    created_assets = []
    for asset_data in assets_data:
        asset = (
            module_db_session.query(GLOBAL_MODELS.Asset)
            .filter_by(symbol=asset_data["symbol"])
            .first()
        )
        if not asset:
            asset = GLOBAL_MODELS.Asset(**asset_data)
            module_db_session.add(asset)
            module_db_session.commit()  # Commit each to ensure they are available if needed by other fixtures
            module_db_session.refresh(asset)
        created_assets.append(asset)
    return created_assets


@pytest.fixture(scope="function")  # Function scope if strategies are modified by tests
def test_strategy_for_user(
    db_session: Session, test_user: GLOBAL_MODELS.User
) -> GLOBAL_MODELS.Strategy:
    # GLOBAL_MODELS is now defined at the top of the file
    strategy_data = {
        "name": f"Test Strategy {fake.word()}",
        "description": fake.sentence(),
        "user_id": test_user.id,
        "parameters": {"param1": random.randint(1, 100), "param2": fake.word()},
    }
    strategy = GLOBAL_MODELS.Strategy(**strategy_data)
    db_session.add(strategy)
    db_session.commit()
    db_session.refresh(strategy)
    return strategy


@pytest.fixture(scope="function")
def test_trade_for_user(
    db_session: Session,
    test_user: GLOBAL_MODELS.User,
    test_assets: list[GLOBAL_MODELS.Asset],
) -> GLOBAL_MODELS.Trade:
    # GLOBAL_MODELS is now defined at the top of the file
    from ai_trader.models import TradeType  # Enum can be imported directly

    selected_asset = random.choice(test_assets)

    # Create a simple order first (as trades are often linked to orders)
    # For API tests, we might not need full order details if trade creation is direct
    # However, if CRUD layer for trade requires order_id, we need one.
    # Assuming Trade model has user_id directly and order_id is optional or handled by CRUD

    trade_data = {
        "user_id": test_user.id,
        "symbol": selected_asset.symbol,
        "quantity": Decimal(str(random.uniform(0.1, 10.0))),
        "price": Decimal(str(random.uniform(100.0, 50000.0))),
        "timestamp": datetime.now(timezone.utc) - timedelta(days=random.randint(0, 30)),
        "trade_type": random.choice(list(TradeType)),
        "commission": Decimal(str(random.uniform(0.1, 5.0))),
        "commission_asset": "USD",
    }
    trade = GLOBAL_MODELS.Trade(**trade_data)
    db_session.add(trade)
    db_session.commit()
    db_session.refresh(trade)
    return trade
