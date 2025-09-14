"""
Database utilities for BookVerse Demo Services.

DEMO PURPOSE: This module demonstrates how to standardize database patterns across services.
Instead of each service implementing its own database session management and utilities,
they can use these shared, consistent implementations.

Key Demo Benefits:
- Consistent database session management across all services
- Reusable pagination utilities (replaces inventory service's pagination logic)
- Standard database dependency injection patterns
- Single place to update database behavior

Focus: Essential database utilities that demonstrate standardization, kept simple for demo clarity.
Note: We intentionally avoid base model classes as they showed low similarity across services.
"""

from .session import get_database_session, create_database_engine, DatabaseConfig
from .pagination import paginate_query, create_pagination_meta

__all__ = [
    # Session management
    "get_database_session",
    "create_database_engine", 
    "DatabaseConfig",
    
    # Pagination utilities
    "paginate_query",
    "create_pagination_meta",
]
