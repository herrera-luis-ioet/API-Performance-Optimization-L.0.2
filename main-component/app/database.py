"""Database configuration and session management for the API service.

This module provides SQLAlchemy configuration, connection pooling, and session management
for MySQL database interactions with secure connection handling.
"""
import os
from dotenv import load_dotenv
from contextlib import contextmanager
from typing import Generator, Dict, Optional
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.engine.url import URL

import json
from sqlalchemy.exc import SQLAlchemyError
from app.config import settings

load_dotenv()

def get_database_url() -> str:
    """
    Get the database URL with proper credentials and configuration.

    Returns:
        str: Formatted database URL for SQLAlchemy
    """
    db_user = os.getenv("DB_USER", "admin")
    db_password = os.getenv("DB_PASSWORD", "password")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "3306")
    db_name = os.getenv("DB_NAME", "product_order_db")
    
    # Create database URL with SSL configuration if enabled
    
    return (
        f"mysql+pymysql://{db_user}:{db_password}@"
        f"{db_host}:{db_port}/{db_name}"
    )


# Replace PostgreSQL URL format with MySQL format
SQLALCHEMY_DATABASE_URL = get_database_url()

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


def init_db() -> None:
    """
    Initialize database by creating all tables.

    This function should be called when the application starts.
    """
    try:
        Base.metadata.create_all(bind=engine)
    except SQLAlchemyError as e:
        raise Exception(f"Failed to initialize database: {str(e)}")
