from ai_trader.db.session import SessionLocal


def get_db():  # E302 fixed
    """
    Dependency injector for FastAPI to get a database session.
    Ensures the session is closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
