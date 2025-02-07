"""Database configuration and session management for the API service.

This module provides SQLAlchemy configuration, connection pooling, and session management
for MySQL database interactions.
"""
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from app.config import settings

# Replace PostgreSQL URL format with MySQL format
SQLALCHEMY_DATABASE_URL = str(settings.DATABASE_URL).replace("postgresql://", "mysql://")

# Configure the SQLAlchemy engine with connection pooling
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_POOL_OVERFLOW,
    pool_pre_ping=True  # Enable connection health checks
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for declarative models
Base = declarative_base()

# PUBLIC_INTERFACE
@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Get a database session from the connection pool.
    
    This context manager ensures proper handling of database sessions,
    including automatic cleanup and connection return to the pool.
    
    Yields:
        Session: SQLAlchemy database session
        
    Raises:
        SQLAlchemyError: If there's an issue with the database connection
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()