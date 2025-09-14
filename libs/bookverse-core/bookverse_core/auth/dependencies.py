"""
FastAPI dependencies for authentication and authorization.

Provides reusable FastAPI dependencies for different authentication scenarios.
"""

import logging
from typing import Optional

from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .jwt_auth import AuthUser, validate_jwt_token, create_mock_user, is_auth_enabled, is_development_mode

logger = logging.getLogger(__name__)

# HTTP Bearer security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[AuthUser]:
    """
    FastAPI dependency to get the current authenticated user.
    
    Supports multiple modes:
    - Production: Validates JWT tokens
    - Development with auth disabled: Returns mock user
    - Development mode: Allows unauthenticated access
    
    Args:
        credentials: HTTP Bearer credentials from request
        
    Returns:
        AuthUser instance if authenticated, None if unauthenticated in dev mode
        
    Raises:
        HTTPException: If authentication is required but fails
    """
    # If authentication is disabled, return a mock user for development
    if not is_auth_enabled():
        logger.debug("🔓 Authentication disabled - returning mock user")
        return create_mock_user()
    
    # If no credentials provided
    if not credentials:
        if is_development_mode():
            logger.debug("🔧 Development mode - allowing unauthenticated access")
            return None
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Validate the token
    return await validate_jwt_token(credentials.credentials)


async def require_authentication(
    user: Optional[AuthUser] = Depends(get_current_user)
) -> AuthUser:
    """
    FastAPI dependency that requires authentication.
    
    Args:
        user: Current user from get_current_user dependency
        
    Returns:
        AuthUser instance
        
    Raises:
        HTTPException: If user is not authenticated
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user


def require_scope(scope: str):
    """
    Factory function to create a dependency that requires a specific scope.
    
    Args:
        scope: The required scope
        
    Returns:
        FastAPI dependency function
    """
    async def scope_checker(user: AuthUser = Depends(require_authentication)) -> AuthUser:
        if not user.has_scope(scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required scope: {scope}"
            )
        return user
    
    scope_checker.__name__ = f"require_scope_{scope.replace(':', '_').replace('-', '_')}"
    return scope_checker


def require_role(role: str):
    """
    Factory function to create a dependency that requires a specific role.
    
    Args:
        role: The required role
        
    Returns:
        FastAPI dependency function
    """
    async def role_checker(user: AuthUser = Depends(require_authentication)) -> AuthUser:
        if not user.has_role(role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {role}"
            )
        return user
    
    role_checker.__name__ = f"require_role_{role}"
    return role_checker


def require_any_scope(*scopes: str):
    """
    Factory function to create a dependency that requires any of the specified scopes.
    
    Args:
        scopes: The required scopes (user must have at least one)
        
    Returns:
        FastAPI dependency function
    """
    async def scope_checker(user: AuthUser = Depends(require_authentication)) -> AuthUser:
        if not user.has_any_scope(list(scopes)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required one of scopes: {', '.join(scopes)}"
            )
        return user
    
    scope_checker.__name__ = f"require_any_scope_{'_'.join(s.replace(':', '_').replace('-', '_') for s in scopes)}"
    return scope_checker


def require_any_role(*roles: str):
    """
    Factory function to create a dependency that requires any of the specified roles.
    
    Args:
        roles: The required roles (user must have at least one)
        
    Returns:
        FastAPI dependency function
    """
    async def role_checker(user: AuthUser = Depends(require_authentication)) -> AuthUser:
        if not user.has_any_role(list(roles)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required one of roles: {', '.join(roles)}"
            )
        return user
    
    role_checker.__name__ = f"require_any_role_{'_'.join(roles)}"
    return role_checker


# Common dependencies for different access levels
RequireAuth = Depends(require_authentication)
RequireUser = Depends(get_current_user)
RequireApiScope = Depends(require_scope("bookverse:api"))
RequireAdminRole = Depends(require_role("admin"))
RequireUserRole = Depends(require_role("user"))
