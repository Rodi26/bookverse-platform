"""
Authentication middleware for FastAPI applications.

Provides middleware for handling JWT authentication at the application level.
"""

import logging
from typing import Callable, Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .jwt_auth import validate_jwt_token, is_auth_enabled, is_development_mode, create_mock_user

logger = logging.getLogger(__name__)


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling JWT authentication.
    
    Automatically validates JWT tokens and adds user information to request state.
    """
    
    def __init__(
        self,
        app,
        exclude_paths: Optional[list] = None,
        require_auth_paths: Optional[list] = None
    ):
        """
        Initialize JWT authentication middleware.
        
        Args:
            app: FastAPI application instance
            exclude_paths: List of paths to exclude from authentication
            require_auth_paths: List of paths that require authentication
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/docs", "/redoc", "/openapi.json", "/health", "/info"
        ]
        self.require_auth_paths = require_auth_paths or []
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and handle authentication.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response object
        """
        # Skip authentication for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Initialize user state
        request.state.user = None
        request.state.authenticated = False
        
        # Handle authentication disabled mode
        if not is_auth_enabled():
            request.state.user = create_mock_user()
            request.state.authenticated = True
            logger.debug("🔓 Authentication disabled - using mock user")
            return await call_next(request)
        
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        token = None
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
        
        # Validate token if present
        if token:
            try:
                user = await validate_jwt_token(token)
                request.state.user = user
                request.state.authenticated = True
                logger.debug(f"✅ User authenticated: {user.email}")
            except Exception as e:
                logger.warning(f"⚠️ Token validation failed: {e}")
                # Don't fail here - let endpoints handle auth requirements
                pass
        
        # Check if authentication is required for this path
        path_requires_auth = any(
            request.url.path.startswith(path) for path in self.require_auth_paths
        )
        
        if path_requires_auth and not request.state.authenticated:
            if is_development_mode():
                logger.debug("🔧 Development mode - allowing unauthenticated access to protected path")
            else:
                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": "Authentication required",
                        "type": "authentication_required"
                    },
                    headers={"WWW-Authenticate": "Bearer"}
                )
        
        return await call_next(request)


def get_user_from_request(request: Request) -> Optional[object]:
    """
    Get authenticated user from request state.
    
    Args:
        request: FastAPI request object
        
    Returns:
        AuthUser instance if authenticated, None otherwise
    """
    return getattr(request.state, "user", None)


def is_authenticated(request: Request) -> bool:
    """
    Check if request is authenticated.
    
    Args:
        request: FastAPI request object
        
    Returns:
        True if request is authenticated, False otherwise
    """
    return getattr(request.state, "authenticated", False)
