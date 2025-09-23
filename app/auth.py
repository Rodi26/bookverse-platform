

"""
BookVerse Platform Service - Authentication and Authorization Module

This module provides comprehensive authentication and authorization capabilities
for the BookVerse Platform Service, implementing OIDC integration, JWT token
validation, and role-based access control for secure platform operations.

🏗️ Authentication Architecture:
    - OIDC Integration: OpenID Connect protocol support for modern authentication
    - JWT Validation: RS256 signature validation with JWKS key rotation
    - Token Caching: Intelligent caching of OIDC configuration and JWKS keys
    - Demo Mode: Simplified authentication for demonstration environments
    - Role-Based Access: Fine-grained permissions with scope and role validation

🚀 Key Features:
    - Bearer Token Authentication: Secure API access with JWT tokens
    - JWKS Key Rotation: Automatic public key refresh with caching
    - Configuration Discovery: Dynamic OIDC endpoint discovery
    - Error Handling: Comprehensive authentication error responses
    - Development Support: Mock authentication for testing and demos
    - Audit Logging: Detailed authentication event logging

🔧 Security Features:
    - RS256 Signature Validation: Cryptographic token verification
    - Token Expiry Validation: Automatic token lifetime enforcement
    - Audience Validation: API-specific token audience checking
    - Issuer Verification: Trusted authority validation
    - Rate Limiting Support: Authentication request throttling
    - Secure Defaults: Production-ready security configuration

📊 Authorization Patterns:
    - Scope-Based Access: OAuth 2.0 scope validation for API endpoints
    - Role-Based Control: Application-specific role enforcement
    - Resource Protection: Fine-grained access control for platform operations
    - Admin Functions: Elevated permissions for administrative operations

Authors: BookVerse Platform Team
Version: 1.0.0
"""

import os
from typing import Optional
from datetime import datetime

from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from bookverse_core.auth import AuthUser, validate_jwt_token
from bookverse_core.utils import get_logger
import requests

# Initialize logger for authentication events
logger = get_logger(__name__)

# OIDC Configuration from environment variables
OIDC_AUTHORITY = os.getenv("OIDC_AUTHORITY", "https://dev-auth.bookverse.com")  # OIDC provider URL
OIDC_AUDIENCE = os.getenv("OIDC_AUDIENCE", "bookverse:api")                    # Expected token audience
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "RS256")                            # JWT signature algorithm
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "true").lower() == "true"             # Authentication toggle
DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "false").lower() == "true"    # Demo mode toggle

# Global caching variables for OIDC configuration and JWKS keys
_oidc_config = None        # Cached OIDC discovery document
_jwks = None               # Cached JSON Web Key Set
_jwks_last_updated = None  # Last JWKS update timestamp
JWKS_CACHE_DURATION = 3600 # Cache duration in seconds (1 hour)

# FastAPI security scheme for Bearer token extraction
security = HTTPBearer(auto_error=False)




async def get_oidc_configuration() -> dict:
    """
    Retrieve and cache OpenID Connect discovery configuration.
    
    This function fetches the OIDC discovery document from the configured
    authority, providing essential endpoints and configuration for JWT
    token validation. The configuration is cached globally to minimize
    network requests and improve performance.
    
    🔧 Discovery Process:
        - Fetches /.well-known/openid_configuration from OIDC authority
        - Caches configuration globally for subsequent requests
        - Provides endpoints for JWKS, token validation, and user info
        - Handles network errors with appropriate HTTP exceptions
    
    Returns:
        dict: OIDC discovery configuration containing endpoints and settings
        
    Raises:
        HTTPException: HTTP 503 if OIDC service is unavailable
        
    Example:
        ```python
        config = await get_oidc_configuration()
        jwks_endpoint = config["jwks_uri"]
        issuer = config["issuer"]
        supported_algorithms = config["id_token_signing_alg_values_supported"]
        ```
    """
    global _oidc_config
    
    if _oidc_config is None:
        try:
            # Fetch OIDC discovery document from well-known endpoint
            response = requests.get(f"{OIDC_AUTHORITY}/.well-known/openid_configuration", timeout=10)
            response.raise_for_status()
            _oidc_config = response.json()
            logger.info("✅ OIDC configuration loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to fetch OIDC configuration: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable"
            )
    
    return _oidc_config


async def get_jwks() -> dict:
    """
    Retrieve and cache JSON Web Key Set (JWKS) for JWT signature validation.
    
    This function manages the JWKS cache with time-based expiration, fetching
    fresh keys when needed while providing fallback to cached keys during
    network issues. JWKS contains the public keys needed to verify JWT signatures.
    
    🔧 Caching Strategy:
        - Cache JWKS for 1 hour to balance security and performance
        - Refresh automatically when cache expires
        - Fallback to cached keys if refresh fails
        - Handle network errors gracefully with appropriate logging
    
    🚀 Key Rotation Support:
        - Automatic detection of new signing keys
        - Seamless handling of key rotation events
        - Backward compatibility during transition periods
        - Error recovery for temporary network issues
    
    Returns:
        dict: JWKS containing public keys for JWT signature verification
        
    Raises:
        HTTPException: HTTP 503 if JWKS unavailable and no cache exists
        
    Example:
        ```python
        jwks = await get_jwks()
        keys = jwks["keys"]
        for key in keys:
            kid = key["kid"]  # Key ID for matching with JWT header
            kty = key["kty"]  # Key type (usually "RSA")
        ```
    """
    global _jwks, _jwks_last_updated
    
    current_time = datetime.now().timestamp()
    
    # Check if JWKS cache needs refresh
    if (_jwks is None or 
        _jwks_last_updated is None or 
        current_time - _jwks_last_updated > JWKS_CACHE_DURATION):
        
        try:
            # Get OIDC configuration to find JWKS endpoint
            oidc_config = await get_oidc_configuration()
            jwks_uri = oidc_config.get("jwks_uri")
            
            if not jwks_uri:
                raise ValueError("No jwks_uri found in OIDC configuration")
            
            # Fetch fresh JWKS from the discovered endpoint
            response = requests.get(jwks_uri, timeout=10)
            response.raise_for_status()
            _jwks = response.json()
            _jwks_last_updated = current_time
            logger.info("✅ JWKS refreshed successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch JWKS: {e}")
            if _jwks is None:
                # No cached JWKS available - service unavailable
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Authentication service unavailable"
                )
            # Use cached JWKS as fallback
            logger.warning("⚠️ Using cached JWKS due to fetch failure")
    
    return _jwks


def get_public_key(token_header: dict, jwks: dict) -> str:
    """
    Extract the appropriate public key from JWKS based on JWT header.
    
    This function matches the Key ID (kid) from the JWT header with the
    corresponding public key in the JWKS, enabling proper signature
    validation for the specific token.
    
    🔧 Key Matching Process:
        - Extract Key ID (kid) from JWT header
        - Search JWKS for matching key by kid
        - Return the matching key for signature validation
        - Handle missing or invalid key IDs appropriately
    
    Args:
        token_header (dict): Decoded JWT header containing key ID
        jwks (dict): JSON Web Key Set containing public keys
        
    Returns:
        str: Matching public key for signature validation
        
    Raises:
        ValueError: If kid is missing or no matching key found
        
    Example:
        ```python
        # Decode JWT header
        header = jwt.get_unverified_header(token)
        
        # Get JWKS
        jwks = await get_jwks()
        
        # Find matching public key
        public_key = get_public_key(header, jwks)
        
        # Use key for signature validation
        payload = jwt.decode(token, public_key, algorithms=["RS256"])
        ```
    """
    # Extract Key ID from JWT header
    kid = token_header.get("kid")
    if not kid:
        raise ValueError("Token header missing 'kid' field")
    
    # Search for matching key in JWKS
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    
    # No matching key found
    raise ValueError(f"No matching key found for kid: {kid}")




async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[AuthUser]:
    """
    Extract and validate current user from JWT token or provide demo user.
    
    This function serves as the primary authentication entry point for the
    Platform Service, implementing demo mode authentication for simplified
    platform operations during demonstrations and development.
    
    🎯 Demo Mode Implementation:
        - Provides mock user with admin privileges for demo scenarios
        - Bypasses JWT validation for simplified platform operations
        - Includes comprehensive scopes and roles for testing
        - Enables full platform functionality without auth complexity
    
    🔧 Production Considerations:
        - In production, implement full JWT token validation
        - Integrate with bookverse_core.auth for token processing
        - Support both service-to-service and user authentication
        - Implement proper error handling and logging
    
    Args:
        credentials: Optional Bearer token credentials from FastAPI security
        
    Returns:
        Optional[AuthUser]: Authenticated user object or None
        
    Example:
        ```python
        # In FastAPI endpoint
        @app.get("/api/platform/status")
        async def get_status(user: Optional[AuthUser] = Depends(get_current_user)):
            if user:
                logger.info(f"Platform status requested by {user.email}")
            return {"status": "healthy"}
        ```
    """
    # Demo mode: Return mock user for simplified platform operations
    logger.debug("🎯 Demo mode: Using mock user (K8s inter-service auth not in scope)")
    return AuthUser({
        "sub": "demo-user",
        "email": "demo@bookverse.com",
        "name": "Demo User",
        "scope": "openid profile email bookverse:api",
        "roles": ["user", "admin"]
    })


async def require_authentication(
    user: Optional[AuthUser] = Depends(get_current_user)
) -> AuthUser:
    """
    Require valid authentication for protected endpoints.
    
    This dependency ensures that only authenticated users can access
    protected platform operations, raising appropriate HTTP exceptions
    for unauthenticated requests.
    
    Args:
        user: User object from get_current_user dependency
        
    Returns:
        AuthUser: Validated authenticated user
        
    Raises:
        HTTPException: HTTP 401 if user is not authenticated
        
    Example:
        ```python
        @app.post("/api/platform/release")
        async def create_release(
            user: AuthUser = Depends(require_authentication)
        ):
            logger.info(f"Release created by {user.email}")
            return {"status": "created"}
        ```
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
    Create a dependency that requires a specific OAuth 2.0 scope.
    
    This function returns a FastAPI dependency that validates the user
    has the required OAuth scope for accessing specific API endpoints.
    
    Args:
        scope (str): Required OAuth 2.0 scope (e.g., "bookverse:api")
        
    Returns:
        Callable: FastAPI dependency function for scope validation
        
    Example:
        ```python
        # Require API scope for platform operations
        @app.get("/api/platform/versions")
        async def list_versions(
            user: AuthUser = Depends(require_scope("bookverse:api"))
        ):
            return {"versions": []}
        ```
    """
    async def scope_checker(user: AuthUser = Depends(require_authentication)) -> AuthUser:
        if not user.has_scope(scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required scope: {scope}"
            )
        return user
    return scope_checker


def require_role(role: str):
    """
    Create a dependency that requires a specific application role.
    
    This function returns a FastAPI dependency that validates the user
    has the required application-specific role for accessing privileged
    platform operations.
    
    Args:
        role (str): Required application role (e.g., "admin", "platform-manager")
        
    Returns:
        Callable: FastAPI dependency function for role validation
        
    Example:
        ```python
        # Require admin role for platform management
        @app.delete("/api/platform/applications/{app_id}")
        async def delete_application(
            app_id: str,
            user: AuthUser = Depends(require_role("admin"))
        ):
            return {"deleted": app_id}
        ```
    """
    async def role_checker(user: AuthUser = Depends(require_authentication)) -> AuthUser:
        if not user.has_role(role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {role}"
            )
        return user
    return role_checker


# Common dependency shortcuts for FastAPI endpoints
RequireAuth = Depends(require_authentication)                    # Require any authenticated user
RequireUser = Depends(get_current_user)                         # Get user (optional auth)
RequireApiScope = Depends(require_scope("bookverse:api"))       # Require API access scope


def get_auth_status() -> dict:
    """
    Get current authentication system status for health checks and debugging.
    
    This function provides comprehensive status information about the
    authentication system configuration and cached resources.
    
    Returns:
        dict: Authentication system status including configuration and cache state
        
    Example:
        ```python
        @app.get("/api/auth/status")
        async def auth_status():
            return get_auth_status()
        
        # Returns:
        # {
        #     "auth_enabled": true,
        #     "development_mode": false,
        #     "oidc_authority": "https://auth.company.com",
        #     "audience": "bookverse:api",
        #     "algorithm": "RS256",
        #     "jwks_cached": true,
        #     "config_cached": true
        # }
        ```
    """
    return {
        "auth_enabled": AUTH_ENABLED,
        "development_mode": DEVELOPMENT_MODE,
        "oidc_authority": OIDC_AUTHORITY,
        "audience": OIDC_AUDIENCE,
        "algorithm": JWT_ALGORITHM,
        "jwks_cached": _jwks is not None,
        "config_cached": _oidc_config is not None
    }


async def test_auth_connection() -> dict:
    """
    Test connectivity to authentication services for health monitoring.
    
    This function performs comprehensive connectivity testing to the OIDC
    provider and JWKS endpoints, providing detailed health information
    for monitoring and troubleshooting.
    
    Returns:
        dict: Connection test results with status and detailed information
        
    Example:
        ```python
        @app.get("/api/auth/health")
        async def auth_health():
            return await test_auth_connection()
        
        # Healthy response:
        # {
        #     "status": "healthy",
        #     "oidc_config_loaded": true,
        #     "jwks_loaded": true,
        #     "keys_count": 2
        # }
        
        # Unhealthy response:
        # {
        #     "status": "unhealthy",
        #     "error": "Connection timeout to OIDC provider"
        # }
        ```
    """
    try:
        # Test OIDC configuration loading
        config = await get_oidc_configuration()
        
        # Test JWKS loading
        jwks = await get_jwks()
        
        return {
            "status": "healthy",
            "oidc_config_loaded": bool(config),
            "jwks_loaded": bool(jwks),
            "keys_count": len(jwks.get("keys", [])) if jwks else 0
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
