"""
Database session management for es-inventory-hub
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import Generator

from common.config import Config
from common.logging import get_logger

logger = get_logger(__name__)

# Global engine and session factory
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create database engine"""
    global _engine
    if _engine is None:
        config = Config()
        _engine = create_engine(
            config.database.url,
            poolclass=StaticPool,
            pool_pre_ping=True,
            echo=config.app.debug
        )
        logger.info(f"Database engine created for {config.database.host}:{config.database.port}/{config.database.database}")
    return _engine


def get_session_factory():
    """Get or create session factory"""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        logger.info("Database session factory created")
    return _SessionLocal


def get_db_session() -> Generator[Session, None, None]:
    """Get database session generator"""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Get database session context manager"""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_database():
    """Initialize database tables"""
    from .models import Base
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")


def test_connection() -> bool:
    """Test database connection"""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        logger.info("Database connection test successful")
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False
