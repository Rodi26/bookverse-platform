"""
Test suite for authentication module

Comprehensive test suite for validating OIDC/JWT authentication functionality
including token validation, OIDC configuration, and error handling.
"""

import pytest
import json
from unittest.mock import patch, Mock, AsyncMock
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

# Import the auth module
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from app import auth
from app.auth import (
    AuthUser, get_oidc_configuration, get_jwks, get_public_key, get_auth_status,
    validate_jwt_token, get_current_user, require_authentication,
    require_scope, require_role, test_auth_connection
)


class TestAuthUser:
    """Test AuthUser class functionality"""
    
    def test_auth_user_initialization(self):
        """Test AuthUser object creation with token claims"""
        claims = {
            "sub": "user123",
            "email": "test@bookverse.com",
            "name": "Test User",
            "scope": "openid profile email bookverse:api",
            "roles": ["user", "admin"]
        }
        user = AuthUser(claims)
        
        assert user.user_id == "user123"
        assert user.email == "test@bookverse.com"
        assert user.name == "Test User"
        assert user.roles == ["user", "admin"]
        assert user.scopes == ["openid", "profile", "email", "bookverse:api"]
    
    def test_auth_user_has_scope(self):
        """Test scope checking functionality"""
        claims = {"sub": "user123", "scope": "openid profile bookverse:api"}
        user = AuthUser(claims)
        
        assert user.has_scope("bookverse:api") is True
        assert user.has_scope("openid") is True
        assert user.has_scope("invalid_scope") is False
    
    def test_auth_user_has_role(self):
        """Test role checking functionality"""
        claims = {"sub": "user123", "roles": ["user", "admin"]}
        user = AuthUser(claims)
        
        assert user.has_role("user") is True
        assert user.has_role("admin") is True
        assert user.has_role("super_admin") is False
    
    def test_auth_user_fallback_name(self):
        """Test fallback to email when name is not provided"""
        claims = {"sub": "user123", "email": "test@bookverse.com"}
        user = AuthUser(claims)
        
        assert user.name == "test@bookverse.com"


class TestOIDCConfiguration:
    """Test OIDC configuration fetching"""
    
    @patch('app.auth.requests.get')
    def test_get_oidc_configuration_success(self, mock_get):
        """Test successful OIDC configuration retrieval"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "issuer": "https://dev-auth.bookverse.com",
            "jwks_uri": "https://dev-auth.bookverse.com/.well-known/jwks.json"
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Reset cached config
        auth._oidc_config = None
        
        config = auth.get_oidc_configuration()
        assert config["issuer"] == "https://dev-auth.bookverse.com"
        assert "jwks_uri" in config
        mock_get.assert_called_once()
    
    @patch('app.auth.requests.get')
    def test_get_oidc_configuration_failure(self, mock_get):
        """Test OIDC configuration retrieval failure"""
        mock_get.side_effect = Exception("Network error")
        
        # Reset cached config
        auth._oidc_config = None
        
        with pytest.raises(HTTPException) as exc_info:
            auth.get_oidc_configuration()
        
        assert exc_info.value.status_code == 503


class TestJWKS:
    """Test JWKS (JSON Web Key Set) functionality"""
    
    @patch('app.auth.get_oidc_configuration')
    @patch('app.auth.requests.get')
    def test_get_jwks_success(self, mock_get, mock_oidc_config):
        """Test successful JWKS retrieval"""
        mock_oidc_config.return_value = {
            "jwks_uri": "https://dev-auth.bookverse.com/.well-known/jwks.json"
        }
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "keys": [
                {
                    "kid": "key1",
                    "kty": "RSA",
                    "use": "sig",
                    "n": "test_n_value",
                    "e": "AQAB"
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Reset cached JWKS
        auth._jwks = None
        auth._jwks_last_updated = None
        
        jwks = auth.get_jwks()
        assert "keys" in jwks
        assert len(jwks["keys"]) == 1
        assert jwks["keys"][0]["kid"] == "key1"
    
    def test_get_public_key_success(self):
        """Test successful public key extraction"""
        token_header = {"kid": "key1", "alg": "RS256"}
        jwks = {
            "keys": [
                {"kid": "key1", "kty": "RSA", "use": "sig"},
                {"kid": "key2", "kty": "RSA", "use": "sig"}
            ]
        }
        
        key = get_public_key(token_header, jwks)
        assert key["kid"] == "key1"
        assert key["kty"] == "RSA"
    
    def test_get_public_key_missing_kid(self):
        """Test public key extraction with missing kid"""
        token_header = {"alg": "RS256"}
        jwks = {"keys": [{"kid": "key1", "kty": "RSA"}]}
        
        with pytest.raises(ValueError, match="Token header missing 'kid' field"):
            get_public_key(token_header, jwks)
    
    def test_get_public_key_no_matching_key(self):
        """Test public key extraction with no matching key"""
        token_header = {"kid": "nonexistent", "alg": "RS256"}
        jwks = {"keys": [{"kid": "key1", "kty": "RSA"}]}
        
        with pytest.raises(ValueError, match="No matching key found for kid"):
            get_public_key(token_header, jwks)


class TestTokenValidation:
    """Test JWT token validation"""
    
    @patch('app.auth.get_jwks')
    @patch('app.auth.jwt.get_unverified_header')
    @patch('app.auth.jwt.decode')
    @patch('app.auth.get_public_key')
    def test_validate_jwt_token_success(self, mock_get_key, mock_decode, mock_header, mock_jwks):
        """Test successful JWT token validation"""
        mock_header.return_value = {"kid": "key1", "alg": "RS256"}
        mock_jwks.return_value = {"keys": [{"kid": "key1"}]}
        mock_get_key.return_value = {"kid": "key1", "kty": "RSA"}
        mock_decode.return_value = {
            "sub": "user123",
            "email": "test@bookverse.com",
            "scope": "openid profile email bookverse:api",
            "iss": "https://dev-auth.bookverse.com",
            "aud": "bookverse:api"
        }
        
        token = "valid.jwt.token"
        user = auth.validate_jwt_token(token)
        
        assert isinstance(user, AuthUser)
        assert user.user_id == "user123"
        assert user.email == "test@bookverse.com"
        assert user.has_scope("bookverse:api")
    
    @patch('app.auth.get_jwks')
    @patch('app.auth.jwt.get_unverified_header')
    @patch('app.auth.jwt.decode')
    def test_validate_jwt_token_missing_sub(self, mock_decode, mock_header, mock_jwks):
        """Test JWT validation with missing sub claim"""
        mock_header.return_value = {"kid": "key1", "alg": "RS256"}
        mock_jwks.return_value = {"keys": []}
        mock_decode.return_value = {
            "email": "test@bookverse.com",
            "scope": "openid profile email bookverse:api"
        }
        
        token = "invalid.jwt.token"
        with pytest.raises(HTTPException) as exc_info:
            auth.validate_jwt_token(token)
        
        assert exc_info.value.status_code == 401
    
    @patch('app.auth.get_jwks')
    @patch('app.auth.jwt.get_unverified_header')
    @patch('app.auth.jwt.decode')
    @patch('app.auth.get_public_key')
    def test_validate_jwt_token_missing_scope(self, mock_get_key, mock_decode, mock_header, mock_jwks):
        """Test JWT validation with missing required scope"""
        mock_header.return_value = {"kid": "key1", "alg": "RS256"}
        mock_jwks.return_value = {"keys": [{"kid": "key1"}]}
        mock_get_key.return_value = {"kid": "key1", "kty": "RSA"}
        mock_decode.return_value = {
            "sub": "user123",
            "email": "test@bookverse.com",
            "scope": "openid profile email",  # Missing bookverse:api
            "iss": "https://dev-auth.bookverse.com",
            "aud": "bookverse:api"
        }
        
        token = "invalid.jwt.token"
        with pytest.raises(HTTPException) as exc_info:
            auth.validate_jwt_token(token)
        
        assert exc_info.value.status_code == 401


class TestCurrentUser:
    """Test current user retrieval and dependencies"""
    
    @patch.dict('os.environ', {'AUTH_ENABLED': 'false'})
    def test_get_current_user_auth_disabled(self):
        """Test get_current_user when authentication is disabled"""
        user = auth.get_current_user(None)
        
        assert isinstance(user, AuthUser)
        assert user.user_id == "dev-user"
        assert user.email == "dev@bookverse.com"
        assert user.has_scope("bookverse:api")
    
    @patch.dict('os.environ', {'AUTH_ENABLED': 'true', 'DEVELOPMENT_MODE': 'true'})
    def test_get_current_user_development_mode(self):
        """Test get_current_user in development mode without credentials"""
        user = auth.get_current_user(None)
        assert user is None
    
    @patch.dict('os.environ', {'AUTH_ENABLED': 'true', 'DEVELOPMENT_MODE': 'false'})
    def test_get_current_user_no_credentials(self):
        """Test get_current_user without credentials in production"""
        with pytest.raises(HTTPException) as exc_info:
            auth.get_current_user(None)
        
        assert exc_info.value.status_code == 401
    
    @patch('app.auth.validate_jwt_token')
    @patch.dict('os.environ', {'AUTH_ENABLED': 'true'})
    def test_get_current_user_valid_token(self, mock_validate):
        """Test get_current_user with valid token"""
        mock_user = AuthUser({
            "sub": "user123",
            "email": "test@bookverse.com",
            "scope": "bookverse:api"
        })
        mock_validate.return_value = mock_user
        
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid.jwt.token")
        user = auth.get_current_user(credentials)
        
        assert user == mock_user
        mock_validate.assert_called_once_with("valid.jwt.token")


class TestRequireAuthentication:
    """Test authentication requirement dependency"""
    
    def test_require_authentication_with_user(self):
        """Test require_authentication when user is provided"""
        mock_user = AuthUser({"sub": "user123", "scope": "bookverse:api"})
        
        user = auth.require_authentication(mock_user)
        assert user == mock_user
    
    def test_require_authentication_without_user(self):
        """Test require_authentication when no user is provided"""
        with pytest.raises(HTTPException) as exc_info:
            auth.require_authentication(None)
        
        assert exc_info.value.status_code == 401


class TestScopeAndRoleRequirements:
    """Test scope and role requirement factories"""
    
    def test_require_scope_success(self):
        """Test scope requirement when user has required scope"""
        mock_user = AuthUser({
            "sub": "user123",
            "scope": "openid profile bookverse:api"
        })
        
        scope_checker = require_scope("bookverse:api")
        user = scope_checker(mock_user)
        assert user == mock_user
    
    def test_require_scope_failure(self):
        """Test scope requirement when user lacks required scope"""
        mock_user = AuthUser({
            "sub": "user123",
            "scope": "openid profile"
        })
        
        scope_checker = require_scope("bookverse:api")
        with pytest.raises(HTTPException) as exc_info:
            scope_checker(mock_user)
        
        assert exc_info.value.status_code == 403
        assert "bookverse:api" in str(exc_info.value.detail)
    
    def test_require_role_success(self):
        """Test role requirement when user has required role"""
        mock_user = AuthUser({
            "sub": "user123",
            "roles": ["user", "admin"]
        })
        
        role_checker = require_role("admin")
        user = role_checker(mock_user)
        assert user == mock_user
    
    def test_require_role_failure(self):
        """Test role requirement when user lacks required role"""
        mock_user = AuthUser({
            "sub": "user123",
            "roles": ["user"]
        })
        
        role_checker = require_role("admin")
        with pytest.raises(HTTPException) as exc_info:
            role_checker(mock_user)
        
        assert exc_info.value.status_code == 403
        assert "admin" in str(exc_info.value.detail)


class TestHealthAndStatus:
    """Test health check and status endpoints"""
    
    @patch.dict('os.environ', {
        'AUTH_ENABLED': 'true',
        'DEVELOPMENT_MODE': 'false',
        'OIDC_AUTHORITY': 'https://test-auth.com',
        'OIDC_AUDIENCE': 'test:api'
    })
    def test_get_auth_status(self):
        """Test authentication status information"""
        status = get_auth_status()
        
        assert status["auth_enabled"] is True
        assert status["development_mode"] is False
        assert status["oidc_authority"] == "https://test-auth.com"
        assert status["audience"] == "test:api"
        assert "jwks_cached" in status
        assert "config_cached" in status
    
    @patch('app.auth.get_oidc_configuration')
    @patch('app.auth.get_jwks')
    async def test_test_auth_connection_success(self, mock_jwks, mock_config):
        """Test authentication connection test success"""
        mock_config.return_value = {"issuer": "https://test-auth.com"}
        mock_jwks.return_value = {"keys": [{"kid": "key1"}, {"kid": "key2"}]}
        
        result = await test_auth_connection()
        
        assert result["status"] == "healthy"
        assert result["oidc_config_loaded"] is True
        assert result["jwks_loaded"] is True
        assert result["keys_count"] == 2
    
    @patch('app.auth.get_oidc_configuration')
    async def test_test_auth_connection_failure(self, mock_config):
        """Test authentication connection test failure"""
        mock_config.side_effect = Exception("Connection failed")
        
        result = await test_auth_connection()
        
        assert result["status"] == "unhealthy"
        assert "error" in result
