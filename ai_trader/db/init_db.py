import logging

from sqlalchemy.orm import Session

from ai_trader.db.session import SessionLocal, engine
from ai_trader.models import Base

logger = logging.getLogger(__name__)

def init_db(db_engine=engine):
    """
    Initializes the database by creating all tables defined in the models.
    WARNING: This should not be used on a database managed by Alembic.
    """
    logger.info("Initializing database...")
    logger.info(f"Using engine: {db_engine.url}")
    try:
        # The following line will create tables. It is commented out by default
        # to prevent accidental execution on a database managed by Alembic.
        # Base.metadata.create_all(bind=db_engine)
        logger.info("Database tables created (if they didn't exist). --- Call to create_all() is COMMENTED OUT.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}", exc_info=True)
        raise

def get_db_session() -> Session:
    """Helper to get a new database session."""
    return SessionLocal()
