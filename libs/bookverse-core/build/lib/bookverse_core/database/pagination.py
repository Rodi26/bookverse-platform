"""
Database pagination utilities for BookVerse Demo Services.

DEMO PURPOSE: This module demonstrates how to eliminate pagination code duplication.
The inventory service currently has a create_pagination_meta() function that could be
shared across all services that need pagination.

Key Demo Benefits:
- Eliminates duplicate pagination logic across services
- Consistent pagination behavior and response format
- Reusable with any SQLAlchemy query
- Single place to update pagination logic

Focus: Simple, practical pagination that works with SQLAlchemy queries.
"""

import math
from typing import Any, List, Tuple, TypeVar

from sqlalchemy.orm import Query
from pydantic import BaseModel

T = TypeVar('T')


class PaginationMeta(BaseModel):
    """
    Pagination metadata model.
    
    DEMO PURPOSE: Standardizes pagination metadata across all services.
    This replaces similar pagination structures in different services.
    """
    
    total: int
    page: int
    per_page: int
    pages: int
    has_next: bool
    has_prev: bool


def create_pagination_meta(total: int, page: int, per_page: int) -> PaginationMeta:
    """
    Create pagination metadata.
    
    DEMO PURPOSE: This function replaces the create_pagination_meta function
    in the inventory service and provides the same functionality for all services.
    
    Previously: Only inventory service had this utility
    Now: All services can use the same pagination logic
    
    Args:
        total: Total number of items
        page: Current page number (1-based)
        per_page: Items per page
        
    Returns:
        PaginationMeta with calculated pagination information
    """
    # Calculate total pages (minimum 1)
    pages = max(1, math.ceil(total / per_page))
    
    return PaginationMeta(
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
        has_next=page < pages,
        has_prev=page > 1
    )


def paginate_query(
    query: Query,
    page: int = 1,
    per_page: int = 20
) -> Tuple[List[Any], PaginationMeta]:
    """
    Apply pagination to a SQLAlchemy query and return results with metadata.
    
    DEMO PURPOSE: Provides a simple, reusable way to paginate any SQLAlchemy query.
    This eliminates the need for each service to implement its own pagination logic.
    
    Usage Example:
        # In any service
        query = db.query(Book).filter(Book.is_active == True)
        items, pagination = paginate_query(query, page=1, per_page=10)
        
        return PaginatedResponse(
            items=items,
            pagination=pagination
        )
    
    Args:
        query: SQLAlchemy query to paginate
        page: Page number (1-based)
        per_page: Number of items per page
        
    Returns:
        Tuple of (items_list, pagination_metadata)
    """
    # Validate parameters
    page = max(1, page)  # Ensure page is at least 1
    per_page = max(1, min(per_page, 100))  # Limit per_page to reasonable range
    
    # Get total count before applying pagination
    total = query.count()
    
    # Calculate offset
    offset = (page - 1) * per_page
    
    # Apply pagination to query
    items = query.offset(offset).limit(per_page).all()
    
    # Create pagination metadata
    pagination = create_pagination_meta(
        total=total,
        page=page,
        per_page=per_page
    )
    
    return items, pagination


def validate_pagination_params(page: int, per_page: int) -> Tuple[int, int]:
    """
    Validate and normalize pagination parameters.
    
    DEMO PURPOSE: Provides consistent validation of pagination parameters
    across all services, with clear error messages for demo purposes.
    
    Args:
        page: Page number
        per_page: Items per page
        
    Returns:
        Tuple of (validated_page, validated_per_page)
        
    Raises:
        ValueError: If parameters are invalid (with clear demo-friendly message)
    """
    # Validate page number
    if page < 1:
        raise ValueError(
            f"Page number must be 1 or greater. Got: {page}. "
            "Demo tip: Page numbers are 1-based, not 0-based."
        )
    
    # Validate per_page
    if per_page < 1:
        raise ValueError(
            f"Items per page must be 1 or greater. Got: {per_page}"
        )
    
    if per_page > 100:
        raise ValueError(
            f"Items per page cannot exceed 100 for demo purposes. Got: {per_page}. "
            "Demo tip: Large page sizes can impact performance."
        )
    
    return page, per_page


class PaginationHelper:
    """
    Helper class for pagination operations.
    
    DEMO PURPOSE: Provides a convenient way to work with pagination
    that can be reused across services.
    """
    
    def __init__(self, default_per_page: int = 20, max_per_page: int = 100):
        """
        Initialize pagination helper.
        
        Args:
            default_per_page: Default items per page
            max_per_page: Maximum items per page
        """
        self.default_per_page = default_per_page
        self.max_per_page = max_per_page
    
    def paginate(
        self,
        query: Query,
        page: int = 1,
        per_page: int = None
    ) -> Tuple[List[Any], PaginationMeta]:
        """
        Paginate a query using helper defaults.
        
        Args:
            query: SQLAlchemy query
            page: Page number
            per_page: Items per page (uses default if None)
            
        Returns:
            Tuple of (items, pagination_metadata)
        """
        if per_page is None:
            per_page = self.default_per_page
        
        # Enforce maximum
        per_page = min(per_page, self.max_per_page)
        
        return paginate_query(query, page, per_page)
    
    def get_page_info(self, total: int, page: int, per_page: int = None) -> PaginationMeta:
        """
        Get pagination metadata without executing a query.
        
        Args:
            total: Total number of items
            page: Page number
            per_page: Items per page (uses default if None)
            
        Returns:
            Pagination metadata
        """
        if per_page is None:
            per_page = self.default_per_page
        
        per_page = min(per_page, self.max_per_page)
        
        return create_pagination_meta(total, page, per_page)
