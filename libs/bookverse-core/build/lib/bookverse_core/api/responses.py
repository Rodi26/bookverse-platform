"""
Standard response models for BookVerse services.

Provides consistent response formats across all services.
"""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict

T = TypeVar('T')


class BaseResponse(BaseModel):
    """Base response model with common fields."""
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = Field(default=None)
    
    model_config = ConfigDict(from_attributes=True)


class SuccessResponse(BaseResponse, Generic[T]):
    """Standard success response."""
    
    success: bool = Field(default=True)
    data: T
    message: Optional[str] = Field(default=None)


class ErrorResponse(BaseResponse):
    """Standard error response."""
    
    success: bool = Field(default=False)
    error: str
    error_code: Optional[str] = Field(default=None)
    details: Optional[Dict[str, Any]] = Field(default=None)


class ValidationErrorResponse(ErrorResponse):
    """Validation error response with field details."""
    
    error_code: str = Field(default="validation_error")
    field_errors: Optional[List[Dict[str, Any]]] = Field(default=None)


class PaginationMeta(BaseModel):
    """Pagination metadata."""
    
    total: int = Field(description="Total number of items")
    page: int = Field(description="Current page number")
    per_page: int = Field(description="Items per page")
    pages: int = Field(description="Total number of pages")
    has_next: bool = Field(description="Whether there is a next page")
    has_prev: bool = Field(description="Whether there is a previous page")


class PaginatedResponse(BaseResponse, Generic[T]):
    """Paginated response with metadata."""
    
    items: List[T]
    pagination: PaginationMeta
    success: bool = Field(default=True)


class HealthResponse(BaseResponse):
    """Health check response."""
    
    status: str = Field(description="Health status (healthy, unhealthy, degraded)")
    service: str = Field(description="Service name")
    version: str = Field(description="Service version")
    checks: Optional[Dict[str, Any]] = Field(default=None, description="Individual health checks")
    uptime: Optional[float] = Field(default=None, description="Service uptime in seconds")


class InfoResponse(BaseResponse):
    """Service information response."""
    
    service: str = Field(description="Service name")
    version: str = Field(description="Service version")
    description: Optional[str] = Field(default=None)
    environment: Optional[str] = Field(default=None)
    api_version: Optional[str] = Field(default=None)
    build_info: Optional[Dict[str, Any]] = Field(default=None)
    features: Optional[Dict[str, bool]] = Field(default=None)


class StatusResponse(BaseResponse):
    """Generic status response."""
    
    status: str
    message: Optional[str] = Field(default=None)
    data: Optional[Dict[str, Any]] = Field(default=None)


class BatchResponse(BaseResponse, Generic[T]):
    """Batch operation response."""
    
    total_processed: int
    successful: int
    failed: int
    results: List[T]
    errors: Optional[List[Dict[str, Any]]] = Field(default=None)


class AsyncOperationResponse(BaseResponse):
    """Asynchronous operation response."""
    
    operation_id: str = Field(default_factory=lambda: str(uuid4()))
    status: str = Field(description="Operation status (pending, running, completed, failed)")
    message: Optional[str] = Field(default=None)
    progress: Optional[float] = Field(default=None, description="Progress percentage (0-100)")
    estimated_completion: Optional[datetime] = Field(default=None)


def create_success_response(
    data: Any,
    message: Optional[str] = None,
    request_id: Optional[str] = None
) -> SuccessResponse:
    """
    Create a success response.
    
    Args:
        data: Response data
        message: Optional success message
        request_id: Optional request ID
        
    Returns:
        Success response instance
    """
    return SuccessResponse(
        data=data,
        message=message,
        request_id=request_id
    )


def create_error_response(
    error: str,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> ErrorResponse:
    """
    Create an error response.
    
    Args:
        error: Error message
        error_code: Optional error code
        details: Optional error details
        request_id: Optional request ID
        
    Returns:
        Error response instance
    """
    return ErrorResponse(
        error=error,
        error_code=error_code,
        details=details,
        request_id=request_id
    )


def create_paginated_response(
    items: List[Any],
    total: int,
    page: int,
    per_page: int,
    request_id: Optional[str] = None
) -> PaginatedResponse:
    """
    Create a paginated response.
    
    Args:
        items: List of items for current page
        total: Total number of items
        page: Current page number
        per_page: Items per page
        request_id: Optional request ID
        
    Returns:
        Paginated response instance
    """
    import math
    
    pages = max(1, math.ceil(total / per_page))
    
    pagination = PaginationMeta(
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
        has_next=page < pages,
        has_prev=page > 1
    )
    
    return PaginatedResponse(
        items=items,
        pagination=pagination,
        request_id=request_id
    )


def create_health_response(
    status: str,
    service: str,
    version: str,
    checks: Optional[Dict[str, Any]] = None,
    uptime: Optional[float] = None
) -> HealthResponse:
    """
    Create a health check response.
    
    Args:
        status: Health status
        service: Service name
        version: Service version
        checks: Individual health checks
        uptime: Service uptime in seconds
        
    Returns:
        Health response instance
    """
    return HealthResponse(
        status=status,
        service=service,
        version=version,
        checks=checks,
        uptime=uptime
    )
