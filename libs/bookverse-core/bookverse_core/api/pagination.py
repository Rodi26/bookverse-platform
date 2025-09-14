"""
Pagination utilities for BookVerse Demo Services.

DEMO PURPOSE: This module demonstrates how to standardize pagination across services.
Instead of each service implementing its own pagination logic (like the inventory service's
create_pagination_meta function), all services can use this shared implementation.

Key Demo Benefits:
- Consistent pagination format across all services
- Reusable pagination parameters and response models
- Single place to update pagination behavior
- Eliminates duplicate pagination code

Focus: Standard offset-based pagination that demonstrates the pattern clearly.
"""

import math
from typing import Any, List, Optional, TypeVar, Generic

from fastapi import Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Query as SQLQuery

from .responses import PaginatedResponse, PaginationMeta

T = TypeVar('T')


class PaginationParams(BaseModel):
    """
    Pagination parameters for API endpoints.
    
    Can be used as a FastAPI dependency to standardize pagination parameters.
    """
    
    page: int = Field(
        default=1,
        ge=1,
        description="Page number (1-based)"
    )
    
    per_page: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of items per page (max 100)"
    )
    
    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.per_page
    
    @property
    def limit(self) -> int:
        """Get limit for database queries."""
        return self.per_page


def create_pagination_params(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page")
) -> PaginationParams:
    """
    FastAPI dependency for pagination parameters.
    
    Args:
        page: Page number (1-based)
        per_page: Items per page
        
    Returns:
        PaginationParams instance
    """
    return PaginationParams(page=page, per_page=per_page)


def create_pagination_meta(
    total: int,
    page: int,
    per_page: int
) -> PaginationMeta:
    """
    Create pagination metadata.
    
    Args:
        total: Total number of items
        page: Current page number
        per_page: Items per page
        
    Returns:
        PaginationMeta instance
    """
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
    query: SQLQuery,
    pagination: PaginationParams
) -> tuple[List[Any], int]:
    """
    Apply pagination to a SQLAlchemy query.
    
    Args:
        query: SQLAlchemy query to paginate
        pagination: Pagination parameters
        
    Returns:
        Tuple of (items, total_count)
    """
    # Get total count before applying pagination
    total = query.count()
    
    # Apply pagination
    items = query.offset(pagination.offset).limit(pagination.limit).all()
    
    return items, total


def paginate(
    items: List[T],
    total: int,
    pagination: PaginationParams,
    request_id: Optional[str] = None
) -> PaginatedResponse[T]:
    """
    Create a paginated response from items and pagination info.
    
    Args:
        items: List of items for current page
        total: Total number of items
        pagination: Pagination parameters
        request_id: Optional request ID
        
    Returns:
        PaginatedResponse instance
    """
    pagination_meta = create_pagination_meta(
        total=total,
        page=pagination.page,
        per_page=pagination.per_page
    )
    
    return PaginatedResponse(
        items=items,
        pagination=pagination_meta,
        request_id=request_id
    )


class PaginatedList(Generic[T]):
    """
    A paginated list container.
    
    Provides a convenient way to work with paginated data.
    """
    
    def __init__(
        self,
        items: List[T],
        total: int,
        page: int,
        per_page: int
    ):
        """
        Initialize paginated list.
        
        Args:
            items: List of items for current page
            total: Total number of items
            page: Current page number
            per_page: Items per page
        """
        self.items = items
        self.total = total
        self.page = page
        self.per_page = per_page
        self.pages = max(1, math.ceil(total / per_page))
    
    @property
    def has_next(self) -> bool:
        """Check if there is a next page."""
        return self.page < self.pages
    
    @property
    def has_prev(self) -> bool:
        """Check if there is a previous page."""
        return self.page > 1
    
    @property
    def next_page(self) -> Optional[int]:
        """Get next page number."""
        return self.page + 1 if self.has_next else None
    
    @property
    def prev_page(self) -> Optional[int]:
        """Get previous page number."""
        return self.page - 1 if self.has_prev else None
    
    @property
    def start_index(self) -> int:
        """Get start index of current page (1-based)."""
        return (self.page - 1) * self.per_page + 1
    
    @property
    def end_index(self) -> int:
        """Get end index of current page (1-based)."""
        return min(self.page * self.per_page, self.total)
    
    def to_response(self, request_id: Optional[str] = None) -> PaginatedResponse[T]:
        """
        Convert to PaginatedResponse.
        
        Args:
            request_id: Optional request ID
            
        Returns:
            PaginatedResponse instance
        """
        return PaginatedResponse(
            items=self.items,
            pagination=PaginationMeta(
                total=self.total,
                page=self.page,
                per_page=self.per_page,
                pages=self.pages,
                has_next=self.has_next,
                has_prev=self.has_prev
            ),
            request_id=request_id
        )
    
    def __len__(self) -> int:
        """Get number of items in current page."""
        return len(self.items)
    
    def __iter__(self):
        """Iterate over items in current page."""
        return iter(self.items)
    
    def __getitem__(self, index: int) -> T:
        """Get item by index."""
        return self.items[index]


# Note: Removed cursor-based pagination for demo simplicity
# Focus on standard offset-based pagination that all services currently use
