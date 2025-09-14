"""
JWT token validation and user authentication for BookVerse Demo.

This module demonstrates how to eliminate authentication code duplication across services.
Instead of each service implementing its own JWT validation (281 lines x 4 services = 1,124 lines),
all services can import and use this shared implementation.

Key Demo Benefits:
- Single source of truth for authentication logic
- Consistent security implementation across all services  
- Easy to update authentication for all services at once
- Clear separation of concerns
"""

import logging
import os
from typing import Dict, Any, List

from fastapi import HTTPException, status
from jose import jwt, JWTError

from .oidc import get_jwks, get_public_key

logger = logging.getLogger(__name__)

# Configuration from environment variables with demo-friendly defaults
OIDC_AUTHORITY = os.getenv("OIDC_AUTHORITY", "https://dev-auth.bookverse.com")
OIDC_AUDIENCE = os.getenv("OIDC_AUDIENCE", "bookverse:api")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "RS256")
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "true").lower() == "true"
DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "true").lower() == "true"  # Default to true for demo


class AuthUser:
    """
    Represents an authenticated user with claims from JWT token.
    
    DEMO PURPOSE: This class replaces identical AuthUser implementations in all 4 services.
    Previously: Each service had its own copy (40+ lines each)
    Now: Single implementation shared by all services
    
    Provides convenient access to user information and permission checking.
    """
    
    def __init__(self, token_claims: Dict[str, Any]):
        """
        Initialize AuthUser from JWT token claims.
        
        Args:
            token_claims: Dictionary of JWT token claims
        """
        self.claims = token_claims
        self.user_id = token_claims.get("sub")
        self.email = token_claims.get("email")
        self.name = token_claims.get("name", self.email)
        self.roles = token_claims.get("roles", [])
        self.scopes = token_claims.get("scope", "").split() if token_claims.get("scope") else []
    
    def has_scope(self, scope: str) -> bool:
        """
        Check if user has a specific scope.
        
        Args:
            scope: The scope to check for
            
        Returns:
            True if user has the scope, False otherwise
        """
        return scope in self.scopes
    
    def has_role(self, role: str) -> bool:
        """
        Check if user has a specific role.
        
        Args:
            role: The role to check for
            
        Returns:
            True if user has the role, False otherwise
        """
        return role in self.roles
    
    # Note: Removed has_any_scope and has_any_role methods for demo simplicity
    # Focus on core functionality that demonstrates the pattern
    
    def __str__(self) -> str:
        return f"AuthUser(id={self.user_id}, email={self.email})"
    
    def __repr__(self) -> str:
        return self.__str__()


async def validate_jwt_token(token: str) -> AuthUser:
    """
    Validate JWT token and return authenticated user.
    
    DEMO PURPOSE: This function replaces identical validation logic in all services.
    Previously: Each service had its own validate_jwt_token function (50+ lines each)
    Now: Single implementation with clear error messages for demo purposes
    
    Args:
        token: JWT token string to validate
        
    Returns:
        AuthUser instance with user information
        
    Raises:
        HTTPException: If token validation fails (with clear demo-friendly messages)
    """
    try:
        # Decode header to get key ID
        header = jwt.get_unverified_header(token)
        
        # Get JWKS for key validation
        jwks = await get_jwks()
        
        # Find the correct public key
        public_key = get_public_key(header, jwks)
        
        # Verify and decode the token
        claims = jwt.decode(
            token,
            public_key,
            algorithms=[JWT_ALGORITHM],
            audience=OIDC_AUDIENCE,
            issuer=OIDC_AUTHORITY
        )
        
        # Validate required claims
        if not claims.get("sub"):
            raise ValueError("Token missing 'sub' claim")
        
        # Check if token has required scope
        scopes = claims.get("scope", "").split() if claims.get("scope") else []
        if "bookverse:api" not in scopes:
            raise ValueError("Token missing required 'bookverse:api' scope")
        
        logger.debug(f"✅ Token validated for user: {claims.get('email', claims.get('sub'))}")
        return AuthUser(claims)
        
    except JWTError as e:
        logger.warning(f"⚠️ JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        logger.error(f"❌ Token validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"}
        )


def create_mock_user() -> AuthUser:
    """
    Create a mock user for development/testing purposes.
    
    Returns:
        AuthUser instance with mock data
    """
    return AuthUser({
        "sub": "dev-user",
        "email": "dev@bookverse.com",
        "name": "Development User",
        "scope": "openid profile email bookverse:api",
        "roles": ["user", "admin"]
    })


def is_auth_enabled() -> bool:
    """
    Check if authentication is enabled.
    
    Returns:
        True if authentication is enabled, False otherwise
    """
    return AUTH_ENABLED


def is_development_mode() -> bool:
    """
    Check if development mode is enabled.
    
    Returns:
        True if development mode is enabled, False otherwise
    """
    return DEVELOPMENT_MODE
