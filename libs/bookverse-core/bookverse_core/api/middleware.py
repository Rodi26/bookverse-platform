"""
Common middleware for BookVerse Demo Services.

DEMO PURPOSE: This module demonstrates how to standardize middleware across services.
Instead of each service implementing its own middleware patterns, they can use these
shared, consistent implementations.

Key Demo Benefits:
- Consistent request logging across all services
- Standardized error handling and responses  
- Automatic request ID tracking for debugging
- Single place to update middleware behavior

Focus: Core middleware patterns that every service needs, kept simple for demo clarity.
"""

import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .responses import create_error_response

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add unique request IDs to all requests.
    
    Adds a unique request ID to each request for tracing and logging.
    """
    
    def __init__(self, app, header_name: str = "X-Request-ID"):
        """
        Initialize request ID middleware.
        
        Args:
            app: FastAPI application
            header_name: Header name for request ID
        """
        super().__init__(app)
        self.header_name = header_name
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add request ID.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/endpoint
            
        Returns:
            Response with request ID header
        """
        # Get existing request ID or generate new one
        request_id = request.headers.get(self.header_name) or str(uuid.uuid4())
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add request ID to response headers
        response.headers[self.header_name] = request_id
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request/response logging.
    
    Logs all HTTP requests with timing and status information.
    """
    
    def __init__(
        self,
        app,
        log_requests: bool = True,
        log_responses: bool = True,
        log_request_body: bool = False,
        log_response_body: bool = False,
        exclude_paths: list = None
    ):
        """
        Initialize logging middleware.
        
        Args:
            app: FastAPI application
            log_requests: Whether to log requests
            log_responses: Whether to log responses
            log_request_body: Whether to log request body
            log_response_body: Whether to log response body
            exclude_paths: Paths to exclude from logging
        """
        super().__init__(app)
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/redoc", "/openapi.json"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with logging.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/endpoint
            
        Returns:
            Response
        """
        # Skip logging for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        start_time = time.time()
        request_id = getattr(request.state, "request_id", "unknown")
        
        # Log request
        if self.log_requests:
            log_data = {
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown"),
            }
            
            if self.log_request_body and request.method in ["POST", "PUT", "PATCH"]:
                try:
                    body = await request.body()
                    if body:
                        log_data["request_body"] = body.decode("utf-8")[:1000]  # Limit size
                except Exception:
                    pass
            
            logger.info(f"📥 Request: {log_data}")
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log error
            duration = time.time() - start_time
            logger.error(
                f"❌ Request failed: {request_id} {request.method} {request.url.path} "
                f"- {type(e).__name__}: {str(e)} ({duration:.3f}s)"
            )
            raise
        
        # Log response
        if self.log_responses:
            duration = time.time() - start_time
            log_data = {
                "request_id": request_id,
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 2),
            }
            
            # Determine log level based on status code
            if response.status_code >= 500:
                log_level = logging.ERROR
                emoji = "❌"
            elif response.status_code >= 400:
                log_level = logging.WARNING
                emoji = "⚠️"
            else:
                log_level = logging.INFO
                emoji = "📤"
            
            logger.log(log_level, f"{emoji} Response: {log_data}")
        
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for centralized error handling.
    
    Catches unhandled exceptions and returns consistent error responses.
    """
    
    def __init__(self, app, include_traceback: bool = False):
        """
        Initialize error handling middleware.
        
        Args:
            app: FastAPI application
            include_traceback: Whether to include traceback in error responses
        """
        super().__init__(app)
        self.include_traceback = include_traceback
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with error handling.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/endpoint
            
        Returns:
            Response or error response
        """
        try:
            return await call_next(request)
        except HTTPException:
            # Let FastAPI handle HTTP exceptions
            raise
        except Exception as e:
            # Handle unexpected exceptions
            request_id = getattr(request.state, "request_id", "unknown")
            
            logger.exception(
                f"❌ Unhandled exception in request {request_id}: {type(e).__name__}: {str(e)}"
            )
            
            # Create error response
            error_details = {
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
            }
            
            if self.include_traceback:
                import traceback
                error_details["traceback"] = traceback.format_exc()
            
            error_response = create_error_response(
                error="Internal server error",
                error_code="internal_error",
                details=error_details,
                request_id=request_id
            )
            
            return JSONResponse(
                status_code=500,
                content=error_response.model_dump()
            )


# Note: Removed RateLimitMiddleware for demo simplicity
# Focus on core middleware that all services need: RequestID, Logging, ErrorHandling
