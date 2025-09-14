"""
Unit tests for configuration module.

DEMO PURPOSE: Tests the unified configuration system that replaces
4 different configuration approaches across services.
"""

import os
import tempfile
import pytest
from pydantic import ValidationError

from bookverse_core.config import BaseConfig, ConfigLoader
from bookverse_core.config.validation import (
    validate_environment,
    validate_log_level,
    sanitize_config_for_logging
)


class DemoDemoTestConfig(BaseConfig):
    """Test configuration class."""
    test_string: str = "default_value"
    test_int: int = 42
    test_bool: bool = True
    test_list: list = ["default"]


class TestBaseConfig:
    """Test BaseConfig functionality."""
    
    def test_base_config_defaults(self):
        """Test BaseConfig with default values."""
        config = BaseConfig()
        
        assert config.service_name == "BookVerse Service"
        assert config.service_version == "1.0.0"
        assert config.environment == "development"
        assert config.debug is False
        assert config.log_level == "INFO"
        assert config.auth_enabled is True
    
    def test_base_config_custom_values(self):
        """Test BaseConfig with custom values."""
        config = BaseConfig(
            service_name="Custom Service",
            service_version="2.0.0",
            environment="production",
            debug=True,
            log_level="DEBUG"
        )
        
        assert config.service_name == "Custom Service"
        assert config.service_version == "2.0.0"
        assert config.environment == "production"
        assert config.debug is True
        assert config.log_level == "DEBUG"
    
    def test_base_config_validation(self):
        """Test BaseConfig validation."""
        # Valid log level
        config = BaseConfig(log_level="WARNING")
        assert config.log_level == "WARNING"
        
        # BaseConfig accepts any string for log_level (validation happens at runtime)
        config = BaseConfig(log_level="INVALID")
        assert config.log_level == "INVALID"
    
    def test_config_to_dict(self):
        """Test converting config to dictionary."""
        config = BaseConfig(service_name="Test Service")
        config_dict = config.to_dict()
        
        assert isinstance(config_dict, dict)
        assert config_dict["service_name"] == "Test Service"
        assert "service_version" in config_dict
        assert "environment" in config_dict


class DemoTestConfigLoader:
    """Test ConfigLoader functionality."""
    
    def test_config_loader_defaults_only(self):
        """Test ConfigLoader with defaults only."""
        loader = ConfigLoader(DemoDemoTestConfig)
        config = loader.load_from()
        
        assert config.test_string == "default_value"
        assert config.test_int == 42
        assert config.test_bool is True
        assert config.test_list == ["default"]
    
    def test_config_loader_with_overrides(self):
        """Test ConfigLoader with direct overrides."""
        loader = ConfigLoader(DemoTestConfig)
        config = loader.load_from(
            defaults={
                "test_string": "override_value",
                "test_int": 100,
                "test_bool": False
            }
        )
        
        assert config.test_string == "override_value"
        assert config.test_int == 100
        assert config.test_bool is False
    
    def test_config_loader_with_yaml_file(self, temp_config_file):
        """Test ConfigLoader with YAML file."""
        loader = ConfigLoader(BaseConfig)
        config = loader.load_from(yaml_file=temp_config_file)
        
        # Values from temp_config_file fixture
        assert config.service_name == "Test Service from YAML"
        assert config.debug is False
        assert config.log_level == "INFO"
    
    def test_config_loader_with_env_vars(self):
        """Test ConfigLoader with environment variables."""
        # Set test environment variables
        test_env = {
            "TEST_TEST_STRING": "env_value",
            "TEST_TEST_INT": "200",
            "TEST_TEST_BOOL": "false"
        }
        
        original_env = {}
        for key, value in test_env.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        try:
            loader = ConfigLoader(DemoTestConfig)
            config = loader.load_from(env_prefix="TEST_")
            
            assert config.test_string == "env_value"
            assert config.test_int == 200
            assert config.test_bool is False
        finally:
            # Cleanup environment variables
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value
    
    def test_config_loader_precedence(self, temp_config_file):
        """Test ConfigLoader precedence: defaults < yaml < env < overrides."""
        # Set environment variable
        os.environ["TEST_SERVICE_NAME"] = "From Environment"
        
        try:
            loader = ConfigLoader(BaseConfig)
            config = loader.load_from(
                yaml_file=temp_config_file,  # Has "Test Service from YAML"
                env_prefix="TEST_",  # Has "From Environment"
                defaults={"service_name": "From Defaults"},
                overrides={"service_name": "From Overrides"}  # Highest priority
            )
            
            # Override should win
            assert config.service_name == "From Overrides"
        finally:
            os.environ.pop("TEST_SERVICE_NAME", None)
    
    def test_config_loader_missing_yaml_file(self):
        """Test ConfigLoader with missing YAML file."""
        loader = ConfigLoader(DemoTestConfig)
        # Should not raise error, just use defaults
        config = loader.load_from(yaml_file="nonexistent.yaml")
        
        assert config.test_string == "default_value"
    
    def test_config_loader_invalid_yaml_file(self):
        """Test ConfigLoader with invalid YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name
        
        try:
            loader = ConfigLoader(DemoTestConfig)
            # Should handle invalid YAML gracefully
            config = loader.load_from(yaml_file=temp_path)
            assert config.test_string == "default_value"
        finally:
            os.unlink(temp_path)
    
    def test_config_loader_caching(self):
        """Test ConfigLoader caching mechanism."""
        loader = ConfigLoader(DemoTestConfig)
        
        # First load
        config1 = loader.load_from(defaults={"test_string": "cached_value"})
        
        # Second load with same parameters should return cached result
        config2 = loader.load_from(defaults={"test_string": "cached_value"})
        
        assert config1 is config2  # Same object reference
        assert config1.test_string == "cached_value"
    
    def test_config_loader_cache_invalidation(self):
        """Test ConfigLoader cache invalidation with different parameters."""
        loader = ConfigLoader(DemoTestConfig)
        
        # First load
        config1 = loader.load_from(defaults={"test_string": "value1"})
        
        # Second load with different parameters should create new config
        config2 = loader.load_from(defaults={"test_string": "value2"})
        
        assert config1 is not config2  # Different objects
        assert config1.test_string == "value1"
        assert config2.test_string == "value2"


class DemoTestConfigValidation:
    """Test configuration validation utilities."""
    
    def test_validate_environment_valid(self):
        """Test environment validation with valid values."""
        assert validate_environment("development") is True
        assert validate_environment("staging") is True
        assert validate_environment("production") is True
    
    def test_validate_environment_invalid(self):
        """Test environment validation with invalid values."""
        assert validate_environment("invalid") is False
        assert validate_environment("") is False
        assert validate_environment(None) is False
    
    def test_validate_log_level_valid(self):
        """Test log level validation with valid values."""
        assert validate_log_level("DEBUG") is True
        assert validate_log_level("INFO") is True
        assert validate_log_level("WARNING") is True
        assert validate_log_level("ERROR") is True
        assert validate_log_level("CRITICAL") is True
    
    def test_validate_log_level_invalid(self):
        """Test log level validation with invalid values."""
        assert validate_log_level("INVALID") is False
        assert validate_log_level("debug") is False  # Case sensitive
        assert validate_log_level("") is False
        assert validate_log_level(None) is False
    
    def test_sanitize_config_for_logging(self):
        """Test config sanitization for logging."""
        config_dict = {
            "service_name": "Test Service",
            "database_url": "postgresql://user:password@host:5432/db",
            "api_key": "secret-api-key",
            "auth_secret": "super-secret",
            "debug": True,
            "log_level": "INFO"
        }
        
        sanitized = sanitize_config_for_logging(config_dict)
        
        # Non-sensitive values should remain
        assert sanitized["service_name"] == "Test Service"
        assert sanitized["debug"] is True
        assert sanitized["log_level"] == "INFO"
        
        # Sensitive values should be masked
        assert sanitized["database_url"] == "***"
        assert sanitized["api_key"] == "***"
        assert sanitized["auth_secret"] == "***"
    
    def test_sanitize_config_nested_dict(self):
        """Test config sanitization with nested dictionaries."""
        config_dict = {
            "service": {
                "name": "Test Service",
                "secret_key": "secret-value"
            },
            "database": {
                "host": "localhost",
                "password": "secret-password"
            }
        }
        
        sanitized = sanitize_config_for_logging(config_dict)
        
        # Non-sensitive nested values should remain
        assert sanitized["service"]["name"] == "Test Service"
        assert sanitized["database"]["host"] == "localhost"
        
        # Sensitive nested values should be masked
        assert sanitized["service"]["secret_key"] == "***"
        assert sanitized["database"]["password"] == "***"


class DemoTestConfigIntegration:
    """Integration tests for configuration system."""
    
    def test_full_config_loading_workflow(self, temp_config_file):
        """Test complete configuration loading workflow."""
        # Set environment variables
        os.environ["DEMO_DEBUG"] = "true"
        os.environ["DEMO_LOG_LEVEL"] = "DEBUG"
        
        try:
            loader = ConfigLoader(BaseConfig)
            config = loader.load_from(
                yaml_file=temp_config_file,
                env_prefix="DEMO_",
                defaults={"service_description": "Default description"},
                overrides={"environment": "test"}
            )
            
            # Check precedence is working correctly
            assert config.service_name == "Test Service from YAML"  # From YAML
            assert config.debug is True  # From environment (overrides YAML)
            assert config.log_level == "DEBUG"  # From environment
            assert config.service_description == "Default description"  # From defaults
            assert config.environment == "test"  # From overrides (highest priority)
            
        finally:
            os.environ.pop("DEMO_DEBUG", None)
            os.environ.pop("DEMO_LOG_LEVEL", None)
