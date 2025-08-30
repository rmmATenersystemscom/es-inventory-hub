"""Database utilities for es-inventory-hub."""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .config import get_dsn


# Create SQLAlchemy engine
engine = create_engine(get_dsn(), pool_pre_ping=True, future=True)

# Create session factory
SessionLocal = sessionmaker(
    bind=engine, 
    autoflush=False, 
    autocommit=False, 
    expire_on_commit=False
)


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """
    Provide a transactional scope around a series of operations.
    
    Yields:
        Session: SQLAlchemy session
        
    The session will be committed if no exceptions occur,
    otherwise it will be rolled back.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
