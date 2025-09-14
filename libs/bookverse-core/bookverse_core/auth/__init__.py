"""
Authentication module for BookVerse services.

Provides JWT-based authentication using OIDC/OAuth2 standards with support for
both development and production configurations.
"""

from .jwt_auth import AuthUser, validate_jwt_token
from .dependencies import (
    get_current_user,
    require_authentication,
    require_scope,
    require_role,
    RequireAuth,
    RequireUser,
    RequireApiScope,
)
from .middleware import JWTAuthMiddleware
from .oidc import get_oidc_configuration, get_jwks
from .health import get_auth_status, check_auth_connection

__all__ = [
    # Core classes
    "AuthUser",
    "JWTAuthMiddleware",
    
    # Authentication functions
    "validate_jwt_token",
    "get_current_user",
    "require_authentication",
    "require_scope", 
    "require_role",
    
    # FastAPI dependencies
    "RequireAuth",
    "RequireUser",
    "RequireApiScope",
    
    # OIDC utilities
    "get_oidc_configuration",
    "get_jwks",
    
    # Health checks
    "get_auth_status",
    "check_auth_connection",
]
