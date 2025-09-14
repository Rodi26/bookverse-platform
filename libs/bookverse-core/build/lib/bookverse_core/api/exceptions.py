"""
HTTP Exception helpers for BookVerse services.

DEMO PURPOSE: This module demonstrates how to standardize error handling patterns
across services. The checkout service has sophisticated error handling with specific
status codes and error categorization that can be reused by all services.

Key Demo Benefits:
- Consistent error responses across all services
- Proper HTTP status codes for different error types
- Detailed error logging with context preservation
- Idempotency conflict handling
- Upstream service error mapping
- Validation error standardization

Focus: Practical error handling patterns that eliminate duplication and improve consistency.
"""

import logging
from typing import Any, Dict, Optional, Union
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class BookVerseHTTPException(HTTPException):
    """
    Enhanced HTTP exception with additional context.
    
    DEMO PURPOSE: Provides structured error handling with logging and context
    that can be used consistently across all services.
    """
    
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        log_level: str = "warning"
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code
        self.context = context or {}
        
        # Log the error with appropriate level
        log_message = f"HTTP {status_code}: {detail}"
        if error_code:
            log_message += f" (code: {error_code})"
        if context:
            log_message += f" - Context: {context}"
        
        if log_level == "error":
            logger.error(log_message)
        elif log_level == "warning":
            logger.warning(log_message)
        else:
            logger.info(log_message)


# Business Logic Errors (400 series)

def raise_validation_error(
    message: str,
    field: Optional[str] = None,
    value: Optional[Any] = None
) -> None:
    """
    Raise a validation error (400).
    
    DEMO PURPOSE: Standardizes validation error responses across services.
    Replaces inconsistent validation error handling.
    
    Args:
        message: Validation error message
        field: Field that failed validation
        value: Invalid value
        
    Raises:
        BookVerseHTTPException: 400 validation error
    """
    context = {}
    if field:
        context["field"] = field
    if value is not None:
        context["value"] = str(value)
    
    raise BookVerseHTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=message,
        error_code="validation_error",
        context=context,
        log_level="info"
    )


def raise_not_found_error(
    resource_type: str,
    resource_id: Union[str, int],
    message: Optional[str] = None
) -> None:
    """
    Raise a not found error (404).
    
    DEMO PURPOSE: Standardizes 404 responses like the checkout service's
    order not found handling.
    
    Args:
        resource_type: Type of resource (e.g., "order", "book", "user")
        resource_id: ID of the resource
        message: Optional custom message
        
    Raises:
        BookVerseHTTPException: 404 not found error
    """
    detail = message or f"{resource_type.title()} not found"
    
    raise BookVerseHTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=detail,
        error_code="not_found",
        context={
            "resource_type": resource_type,
            "resource_id": str(resource_id)
        },
        log_level="info"
    )


def raise_conflict_error(
    message: str,
    conflict_type: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """
    Raise a conflict error (409).
    
    DEMO PURPOSE: Handles conflicts like the checkout service's idempotency
    conflicts and insufficient stock errors.
    
    Args:
        message: Conflict error message
        conflict_type: Type of conflict (e.g., "idempotency", "stock", "duplicate")
        context: Additional context
        
    Raises:
        BookVerseHTTPException: 409 conflict error
    """
    error_code = f"{conflict_type}_conflict" if conflict_type else "conflict"
    
    raise BookVerseHTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=message,
        error_code=error_code,
        context=context or {},
        log_level="warning"
    )


def raise_idempotency_conflict(
    idempotency_key: str,
    message: Optional[str] = None
) -> None:
    """
    Raise an idempotency conflict error (409).
    
    DEMO PURPOSE: Specific handling for idempotency conflicts like in
    the checkout service.
    
    Args:
        idempotency_key: The conflicting idempotency key
        message: Optional custom message
        
    Raises:
        BookVerseHTTPException: 409 idempotency conflict
    """
    detail = message or "Idempotency key conflict - request hash mismatch"
    
    raise BookVerseHTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=detail,
        error_code="idempotency_conflict",
        context={"idempotency_key": idempotency_key},
        log_level="warning"
    )


def raise_insufficient_stock_error(
    book_id: str,
    requested: int,
    available: int
) -> None:
    """
    Raise an insufficient stock error (409).
    
    DEMO PURPOSE: Specific business logic error from checkout service
    that can be reused by inventory and other services.
    
    Args:
        book_id: Book identifier
        requested: Requested quantity
        available: Available quantity
        
    Raises:
        BookVerseHTTPException: 409 insufficient stock
    """
    raise BookVerseHTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"Insufficient stock for book {book_id}",
        error_code="insufficient_stock",
        context={
            "book_id": book_id,
            "requested": requested,
            "available": available
        },
        log_level="info"
    )


# Server Errors (500 series)

def raise_upstream_error(
    service_name: str,
    error: Exception,
    message: Optional[str] = None
) -> None:
    """
    Raise an upstream service error (502).
    
    DEMO PURPOSE: Handles upstream service failures like the checkout service's
    inventory service error handling.
    
    Args:
        service_name: Name of the upstream service
        error: Original exception
        message: Optional custom message
        
    Raises:
        BookVerseHTTPException: 502 upstream error
    """
    detail = message or f"Upstream service error: {service_name}"
    
    # Log the full exception for debugging
    logger.error(
        f"Upstream service '{service_name}' error: {error}",
        exc_info=True
    )
    
    raise BookVerseHTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=detail,
        error_code="upstream_error",
        context={
            "service": service_name,
            "error_type": type(error).__name__
        },
        log_level="error"
    )


def raise_internal_error(
    message: str,
    error: Optional[Exception] = None,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """
    Raise an internal server error (500).
    
    DEMO PURPOSE: Standardizes internal error handling with proper logging.
    
    Args:
        message: Error message
        error: Optional original exception
        context: Additional context
        
    Raises:
        BookVerseHTTPException: 500 internal server error
    """
    if error:
        logger.error(f"Internal server error: {message} - {error}", exc_info=True)
    else:
        logger.error(f"Internal server error: {message}")
    
    raise BookVerseHTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Internal server error",  # Don't expose internal details
        error_code="internal_error",
        context=context or {},
        log_level="error"
    )


# Exception Handlers and Utilities

def handle_service_exception(
    error: Exception,
    service_name: str = "unknown",
    operation: str = "operation"
) -> None:
    """
    Handle service exceptions with appropriate error mapping.
    
    DEMO PURPOSE: Provides the same exception mapping pattern as the
    checkout service for consistent error handling across services.
    
    Usage:
        try:
            result = some_service_call()
        except Exception as e:
            handle_service_exception(e, "inventory", "get_book_stock")
    
    Args:
        error: Exception to handle
        service_name: Name of the service/component
        operation: Operation being performed
        
    Raises:
        BookVerseHTTPException: Appropriate HTTP exception
    """
    if isinstance(error, ValueError):
        detail = str(error)
        
        # Handle specific business logic errors
        if detail.startswith("idempotency_conflict"):
            raise_conflict_error(detail, "idempotency")
        elif detail.startswith("insufficient_stock"):
            raise_conflict_error(detail, "stock")
        elif "not found" in detail.lower():
            # Extract resource info if possible
            parts = detail.split()
            resource_id = parts[-1] if parts else "unknown"
            raise_not_found_error("resource", resource_id, detail)
        else:
            raise_validation_error(detail)
    
    elif isinstance(error, FileNotFoundError):
        raise_not_found_error("file", str(error.filename or "unknown"))
    
    elif isinstance(error, PermissionError):
        raise BookVerseHTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied",
            error_code="permission_denied",
            context={"operation": operation}
        )
    
    elif isinstance(error, ConnectionError):
        raise_upstream_error(service_name, error)
    
    else:
        # Generic internal error
        raise_internal_error(
            f"Unexpected error in {operation}",
            error,
            {"service": service_name, "operation": operation}
        )


def create_error_context(
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create error context dictionary.
    
    DEMO PURPOSE: Standardizes error context creation for consistent
    error reporting and debugging.
    
    Args:
        request_id: Request identifier
        user_id: User identifier
        **kwargs: Additional context fields
        
    Returns:
        Error context dictionary
    """
    context = {}
    
    if request_id:
        context["request_id"] = request_id
    if user_id:
        context["user_id"] = user_id
    
    context.update(kwargs)
    return context

