"""
FastAPI utilities and patterns for BookVerse services.

Provides app factory, middleware, response models, and common endpoints.
"""

from .app_factory import create_app
from .responses import (
    BaseResponse,
    SuccessResponse,
    ErrorResponse, 
    PaginatedResponse,
    HealthResponse,
    InfoResponse,
    create_success_response,
    create_error_response,
    create_paginated_response,
    create_health_response
)
from .middleware import (
    LoggingMiddleware,
    RequestIDMiddleware,
    ErrorHandlingMiddleware
)
from .health import create_health_router
from .pagination import PaginationParams, paginate
from .exceptions import (
    BookVerseHTTPException,
    raise_validation_error,
    raise_not_found_error,
    raise_conflict_error,
    raise_idempotency_conflict,
    raise_insufficient_stock_error,
    raise_upstream_error,
    raise_internal_error,
    handle_service_exception,
    create_error_context
)

__all__ = [
    # App factory
    "create_app",
    
    # Response models
    "BaseResponse",
    "SuccessResponse",
    "ErrorResponse",
    "PaginatedResponse", 
    "HealthResponse",
    "InfoResponse",
    
    # Response helpers
    "create_success_response",
    "create_error_response",
    "create_paginated_response",
    "create_health_response",
    
    # Middleware
    "LoggingMiddleware",
    "RequestIDMiddleware", 
    "ErrorHandlingMiddleware",
    
    # Health checks
    "create_health_router",
    
    # Pagination
    "PaginationParams",
    "paginate",
    
    # Exception handling
    "BookVerseHTTPException",
    "raise_validation_error",
    "raise_not_found_error", 
    "raise_conflict_error",
    "raise_idempotency_conflict",
    "raise_insufficient_stock_error",
    "raise_upstream_error",
    "raise_internal_error",
    "handle_service_exception",
    "create_error_context",
]
