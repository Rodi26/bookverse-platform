"""
Database session management for BookVerse Demo Services.

DEMO PURPOSE: This module demonstrates how to standardize database session management.
Instead of each service implementing its own database setup (like inventory's database.py
and checkout's database.py), all services can use this shared implementation.

Key Demo Benefits:
- Consistent database session handling across all services
- Standardized database configuration and connection management
- Reusable FastAPI dependency for database sessions
- Single place to update database connection logic

Focus: Essential session management patterns that all services need.
"""

import logging
from typing import Generator, Optional
from contextlib import contextmanager

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class DatabaseConfig(BaseModel):
    """
    Database configuration for demo services.
    
    DEMO PURPOSE: Provides a simple, consistent way to configure database connections
    across all services, replacing the various approaches currently used.
    """
    
    database_url: str
    echo: bool = False  # Set to True for SQL query logging in development
    pool_size: int = 5
    max_overflow: int = 10
    
    model_config = ConfigDict(env_prefix="DB_")  # Allow DB_DATABASE_URL, DB_ECHO, etc.


# Global variables for database engine and session factory
_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker] = None


def create_database_engine(config: DatabaseConfig) -> Engine:
    """
    Create a SQLAlchemy database engine.
    
    DEMO PURPOSE: Standardizes database engine creation across all services.
    Previously: Each service had its own engine setup
    Now: Single, consistent implementation
    
    Args:
        config: Database configuration
        
    Returns:
        SQLAlchemy engine instance
    """
    global _engine
    
    if _engine is None:
        _engine = create_engine(
            config.database_url,
            echo=config.echo,
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
            # Connection pool settings for demo stability
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=3600,   # Recycle connections after 1 hour
        )
        logger.info(f"✅ Database engine created: {config.database_url}")
    
    return _engine


def create_session_factory(engine: Engine) -> sessionmaker:
    """
    Create a SQLAlchemy session factory.
    
    Args:
        engine: SQLAlchemy engine
        
    Returns:
        Session factory
    """
    global _session_factory
    
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=engine,
            autocommit=False,
            autoflush=False,
        )
        logger.info("✅ Database session factory created")
    
    return _session_factory


def get_database_session(config: DatabaseConfig) -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.
    
    DEMO PURPOSE: Provides a standard FastAPI dependency that all services can use
    for database access. Replaces the various get_db() implementations across services.
    
    Usage in FastAPI endpoints:
        @app.get("/items")
        def get_items(db: Session = Depends(get_database_session)):
            return db.query(Item).all()
    
    Args:
        config: Database configuration
        
    Yields:
        Database session
    """
    # Create engine and session factory if needed
    engine = create_database_engine(config)
    session_factory = create_session_factory(engine)
    
    # Create session
    session = session_factory()
    
    try:
        yield session
        # Commit any pending transactions
        session.commit()
    except Exception as e:
        # Rollback on error
        session.rollback()
        logger.error(f"❌ Database session error: {e}")
        raise
    finally:
        # Always close the session
        session.close()


@contextmanager
def database_session_context(config: DatabaseConfig) -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    
    DEMO PURPOSE: Provides a context manager for database operations outside of FastAPI.
    Useful for background tasks, CLI scripts, or other non-web contexts.
    
    Usage:
        with database_session_context(config) as db:
            items = db.query(Item).all()
    
    Args:
        config: Database configuration
        
    Yields:
        Database session
    """
    engine = create_database_engine(config)
    session_factory = create_session_factory(engine)
    session = session_factory()
    
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Database context error: {e}")
        raise
    finally:
        session.close()


def create_tables(config: DatabaseConfig, base_class):
    """
    Create database tables from SQLAlchemy models.
    
    DEMO PURPOSE: Provides a simple way to create tables for demo purposes.
    In production, you'd use Alembic migrations.
    
    Args:
        config: Database configuration
        base_class: SQLAlchemy declarative base class
    """
    try:
        engine = create_database_engine(config)
        base_class.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully")
    except Exception as e:
        logger.error(f"❌ Failed to create database tables: {e}")
        raise


def test_database_connection(config: DatabaseConfig) -> bool:
    """
    Test database connectivity.
    
    DEMO PURPOSE: Simple connectivity test for health checks and debugging.
    
    Args:
        config: Database configuration
        
    Returns:
        True if connection successful, False otherwise
    """
    try:
        engine = create_database_engine(config)
        with engine.connect() as connection:
            # Simple query to test connection
            connection.execute("SELECT 1")
        logger.info("✅ Database connection test successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection test failed: {e}")
        return False


# Utility function to reset global state (useful for testing)
def reset_database_globals():
    """
    Reset global database state.
    
    DEMO PURPOSE: Allows resetting database connections for testing or reconfiguration.
    """
    global _engine, _session_factory
    
    if _engine:
        _engine.dispose()
        _engine = None
    
    _session_factory = None
    logger.info("🔄 Database globals reset")
