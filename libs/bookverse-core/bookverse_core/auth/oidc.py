"""
OIDC (OpenID Connect) configuration and JWKS management.

Handles fetching and caching of OIDC configuration and JSON Web Key Sets (JWKS)
for JWT token validation.
"""

import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional

import requests
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# Configuration from environment variables
OIDC_AUTHORITY = os.getenv("OIDC_AUTHORITY", "https://dev-auth.bookverse.com")
JWKS_CACHE_DURATION = int(os.getenv("JWKS_CACHE_DURATION", "3600"))  # 1 hour in seconds

# Global cache variables
_oidc_config: Optional[Dict[str, Any]] = None
_jwks: Optional[Dict[str, Any]] = None
_jwks_last_updated: Optional[float] = None


async def get_oidc_configuration() -> Dict[str, Any]:
    """
    Fetch OIDC configuration from the authority.
    
    Caches the configuration to avoid repeated requests.
    
    Returns:
        Dict containing OIDC configuration
        
    Raises:
        HTTPException: If OIDC configuration cannot be fetched
    """
    global _oidc_config
    
    if _oidc_config is None:
        try:
            response = requests.get(
                f"{OIDC_AUTHORITY}/.well-known/openid_configuration", 
                timeout=10
            )
            response.raise_for_status()
            _oidc_config = response.json()
            logger.info("✅ OIDC configuration loaded successfully")
        except Exception as e:
            from .jwt_auth import is_development_mode
            if is_development_mode():
                logger.warning(f"⚠️ OIDC configuration unavailable in demo mode: {e}")
            else:
                logger.error(f"❌ Failed to fetch OIDC configuration: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable (expected in demo mode)" if is_development_mode() else "Authentication service unavailable"
            )
    
    return _oidc_config


async def get_jwks() -> Dict[str, Any]:
    """
    Fetch and cache JWKS (JSON Web Key Set) for token validation.
    
    Implements time-based cache refresh to balance performance and security.
    
    Returns:
        Dict containing JWKS data
        
    Raises:
        HTTPException: If JWKS cannot be fetched and no cached version exists
    """
    global _jwks, _jwks_last_updated
    
    current_time = datetime.now().timestamp()
    
    # Check if we need to refresh the cache
    if (
        _jwks is None
        or _jwks_last_updated is None
        or current_time - _jwks_last_updated > JWKS_CACHE_DURATION
    ):
        try:
            oidc_config = await get_oidc_configuration()
            jwks_uri = oidc_config.get("jwks_uri")
            
            if not jwks_uri:
                raise ValueError("No jwks_uri found in OIDC configuration")
            
            response = requests.get(jwks_uri, timeout=10)
            response.raise_for_status()
            _jwks = response.json()
            _jwks_last_updated = current_time
            logger.info("✅ JWKS refreshed successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch JWKS: {e}")
            if _jwks is None:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Authentication service unavailable"
                )
            # Use cached version if available
            logger.warning("⚠️ Using cached JWKS due to fetch failure")
    
    return _jwks


def get_public_key(token_header: Dict[str, Any], jwks: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract the public key for token verification from JWKS.
    
    Args:
        token_header: JWT token header containing key ID
        jwks: JSON Web Key Set containing public keys
        
    Returns:
        Dict containing the matching public key
        
    Raises:
        ValueError: If key ID is missing or no matching key is found
    """
    kid = token_header.get("kid")
    if not kid:
        raise ValueError("Token header missing 'kid' field")
    
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    
    raise ValueError(f"No matching key found for kid: {kid}")


def clear_cache() -> None:
    """
    Clear the OIDC configuration and JWKS cache.
    
    Useful for testing or forcing a refresh of cached data.
    """
    global _oidc_config, _jwks, _jwks_last_updated
    _oidc_config = None
    _jwks = None
    _jwks_last_updated = None
    logger.info("🔄 OIDC and JWKS cache cleared")
