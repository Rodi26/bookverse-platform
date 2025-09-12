#!/usr/bin/env python3
"""Tests for the platform tagging logic to ensure it meets requirements."""

import pytest
from unittest.mock import AsyncMock, MagicMock
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from tagging_service import (
    enforce_latest_tag_invariants,
    handle_rollback_tagging,
    pick_next_latest,
    sort_versions_by_semver_desc,
    AppTrustClient,
    LATEST_TAG,
    BACKUP_BEFORE_LATEST,
    BACKUP_BEFORE_QUARANTINE
)


class TestTaggingLogic:
    """Test the platform tagging logic requirements"""
    
    def test_semver_sorting(self):
        """Test that semantic version sorting works correctly"""
        versions = ["1.0.0", "2.1.0", "1.5.3", "2.0.0", "1.10.0"]
        sorted_versions = sort_versions_by_semver_desc(versions)
        expected = ["2.1.0", "2.0.0", "1.10.0", "1.5.3", "1.0.0"]
        assert sorted_versions == expected
    
    def test_pick_next_latest_excludes_quarantine(self):
        """Test that pick_next_latest excludes quarantined versions"""
        prod_versions = [
            {"version": "2.0.0", "tag": "latest"},
            {"version": "1.5.0", "tag": "quarantine-1.5.0"},
            {"version": "1.4.0", "tag": "stable"},
            {"version": "1.3.0", "tag": "version"}
        ]
        
        # Should pick 1.4.0 since 1.5.0 is quarantined and 2.0.0 is excluded
        import asyncio
        result = asyncio.run(pick_next_latest(prod_versions, "2.0.0"))
        assert result["version"] == "1.4.0"
    
    def test_pick_next_latest_no_candidates(self):
        """Test pick_next_latest when no valid candidates exist"""
        prod_versions = [
            {"version": "2.0.0", "tag": "latest"},
            {"version": "1.5.0", "tag": "quarantine-1.5.0"},
        ]
        
        import asyncio
        result = asyncio.run(pick_next_latest(prod_versions, "2.0.0"))
        assert result is None
    
    @pytest.mark.asyncio
    async def test_enforce_latest_tag_invariants_basic(self):
        """Test that latest tag is assigned to highest semver version"""
        # Mock client
        client = MagicMock(spec=AppTrustClient)
        
        # Mock prod versions with 2.0.0 having latest but 2.1.0 is newer
        prod_versions = [
            {"version": "2.1.0", "tag": "version", "release_status": "RELEASED"},
            {"version": "2.0.0", "tag": "latest", "release_status": "RELEASED"},
            {"version": "1.9.0", "tag": "stable", "release_status": "RELEASED"}
        ]
        
        # Mock the list_application_versions call
        client.list_application_versions = AsyncMock(return_value={
            "versions": prod_versions
        })
        
        # Mock the patch calls
        patch_calls = []
        async def mock_patch(app_key, version, tag=None, properties=None, delete_properties=None):
            patch_calls.append({
                "app_key": app_key,
                "version": version,
                "tag": tag,
                "properties": properties,
                "delete_properties": delete_properties
            })
            return {}
        
        client.patch_application_version = AsyncMock(side_effect=mock_patch)
        
        # Run the enforcement
        await enforce_latest_tag_invariants(client, "test-app")
        
        # Verify calls
        assert len(patch_calls) == 2
        
        # First call should assign latest to 2.1.0
        assert patch_calls[0]["version"] == "2.1.0"
        assert patch_calls[0]["tag"] == "latest"
        assert patch_calls[0]["properties"] == {BACKUP_BEFORE_LATEST: ["version"]}
        
        # Second call should restore original tag to 2.0.0
        assert patch_calls[1]["version"] == "2.0.0"
        assert patch_calls[1]["tag"] == "version"  # Should be restored to version
        assert patch_calls[1]["delete_properties"] == [BACKUP_BEFORE_LATEST]
    
    @pytest.mark.asyncio
    async def test_rollback_tagging_with_latest(self):
        """Test rollback logic when the rolled back version has latest tag"""
        # Mock client
        client = MagicMock(spec=AppTrustClient)
        
        # Mock prod versions where 2.0.0 has latest and gets rolled back
        prod_versions = [
            {"version": "2.0.0", "tag": "latest", "release_status": "RELEASED"},
            {"version": "1.9.0", "tag": "stable", "release_status": "RELEASED"},
            {"version": "1.8.0", "tag": "version", "release_status": "RELEASED"}
        ]
        
        client.list_application_versions = AsyncMock(return_value={
            "versions": prod_versions
        })
        
        # Mock the patch calls
        patch_calls = []
        async def mock_patch(app_key, version, tag=None, properties=None, delete_properties=None):
            patch_calls.append({
                "app_key": app_key,
                "version": version,
                "tag": tag,
                "properties": properties,
                "delete_properties": delete_properties
            })
            return {}
        
        client.patch_application_version = AsyncMock(side_effect=mock_patch)
        
        # Run the rollback handling
        await handle_rollback_tagging(client, "test-app", "2.0.0")
        
        # Verify calls
        assert len(patch_calls) == 2
        
        # First call should quarantine 2.0.0
        assert patch_calls[0]["version"] == "2.0.0"
        assert patch_calls[0]["tag"] == "quarantine-2.0.0"
        assert patch_calls[0]["properties"] == {BACKUP_BEFORE_QUARANTINE: ["latest"]}
        
        # Second call should promote 1.9.0 to latest
        assert patch_calls[1]["version"] == "1.9.0"
        assert patch_calls[1]["tag"] == "latest"
        assert patch_calls[1]["properties"] == {BACKUP_BEFORE_LATEST: ["stable"]}
    
    @pytest.mark.asyncio
    async def test_rollback_tagging_without_latest(self):
        """Test rollback logic when the rolled back version doesn't have latest tag"""
        # Mock client
        client = MagicMock(spec=AppTrustClient)
        
        # Mock prod versions where 1.9.0 gets rolled back but doesn't have latest
        prod_versions = [
            {"version": "2.0.0", "tag": "latest", "release_status": "RELEASED"},
            {"version": "1.9.0", "tag": "stable", "release_status": "RELEASED"},
            {"version": "1.8.0", "tag": "version", "release_status": "RELEASED"}
        ]
        
        client.list_application_versions = AsyncMock(return_value={
            "versions": prod_versions
        })
        
        # Mock the patch calls
        patch_calls = []
        async def mock_patch(app_key, version, tag=None, properties=None, delete_properties=None):
            patch_calls.append({
                "app_key": app_key,
                "version": version,
                "tag": tag,
                "properties": properties,
                "delete_properties": delete_properties
            })
            return {}
        
        client.patch_application_version = AsyncMock(side_effect=mock_patch)
        
        # Run the rollback handling
        await handle_rollback_tagging(client, "test-app", "1.9.0")
        
        # Verify only one call (quarantine)
        assert len(patch_calls) == 1
        
        # Should only quarantine 1.9.0, no latest reassignment
        assert patch_calls[0]["version"] == "1.9.0"
        assert patch_calls[0]["tag"] == "quarantine-1.9.0"
        assert patch_calls[0]["properties"] == {BACKUP_BEFORE_QUARANTINE: ["stable"]}


if __name__ == "__main__":
    # Run tests manually if needed
    test_instance = TestTaggingLogic()
    test_instance.test_semver_sorting()
    test_instance.test_pick_next_latest_excludes_quarantine()
    test_instance.test_pick_next_latest_no_candidates()
    print("✅ All synchronous tests passed!")
    print("ℹ️  Run 'pytest test_tagging_logic.py' for async tests")
