#!/usr/bin/env python3
"""
Platform Aggregator Functionality Tests
Tests the core platform aggregation functionality in isolation.
"""

import os
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import unittest

# Add platform app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class TestPlatformAggregator(unittest.TestCase):
    """Test platform aggregator functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_env = {
            'JFROG_URL': 'https://test.jfrog.io',
            'JF_OIDC_TOKEN': 'test-oidc-token-123'
        }
        self.mock_services_config = [
            {
                'name': 'inventory',
                'apptrust_application': 'bookverse-inventory',
                'docker': {
                    'registry': 'test.registry.io',
                    'repository': 'bookverse-inventory-docker/inventory'
                },
                'simulated_version': '1.8.3'
            },
            {
                'name': 'recommendations',
                'apptrust_application': 'bookverse-recommendations', 
                'docker': {
                    'registry': 'test.registry.io',
                    'repository': 'bookverse-recommendations-docker/recommendations'
                },
                'simulated_version': '0.9.0'
            }
        ]
    
    def test_services_config_loading(self):
        """Test loading services configuration."""
        print("\n🧪 Testing Services Config Loading...")
        
        from app.main import load_services_config
        
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.dump({'services': self.mock_services_config}, f)
            temp_config_path = f.name
        
        try:
            services = load_services_config(Path(temp_config_path))
            self.assertEqual(len(services), 2)
            self.assertEqual(services[0]['name'], 'inventory')
            self.assertEqual(services[1]['name'], 'recommendations')
            print("✅ Services config loading works")
        finally:
            os.unlink(temp_config_path)
    
    def test_semver_computation(self):
        """Test next semantic version computation."""
        print("\n🧪 Testing SemVer Computation...")
        
        from app.main import compute_next_semver_for_application, AppTrustClient
        
        # Mock AppTrust client responses
        with patch.object(AppTrustClient, 'list_application_versions') as mock_list:
            # Test with existing versions
            mock_list.return_value = {
                'versions': [
                    {'version': '1.2.3'},
                    {'version': '1.2.2'},
                    {'version': '1.2.1'}
                ]
            }
            
            client = AppTrustClient('https://test.com', 'token')
            next_version = compute_next_semver_for_application(client, 'test-app')
            self.assertEqual(next_version, '1.2.4')
            print("✅ SemVer patch increment works")
            
            # Test with no existing versions
            mock_list.return_value = {'versions': []}
            next_version = compute_next_semver_for_application(client, 'new-app')
            # Should return seed version + 1 or fallback
            self.assertRegex(next_version, r'\d+\.\d+\.\d+')
            print("✅ SemVer fallback works")
    
    def test_version_resolution(self):
        """Test version resolution from PROD stage."""
        print("\n🧪 Testing Version Resolution...")
        
        from app.main import resolve_promoted_versions, pick_latest_prod_version, AppTrustClient
        
        # Mock AppTrust client
        with patch.object(AppTrustClient, 'list_application_versions') as mock_list:
            mock_list.return_value = {
                'versions': [
                    {'version': '1.8.3', 'release_status': 'RELEASED', 'current_stage': 'PROD'},
                    {'version': '1.8.2', 'release_status': 'RELEASED', 'current_stage': 'PROD'},
                    {'version': '1.8.1', 'release_status': 'STAGED', 'current_stage': 'STAGING'}
                ]
            }
            
            client = AppTrustClient('https://test.com', 'token')
            
            # Test latest PROD version picking
            latest = pick_latest_prod_version(client, 'bookverse-inventory')
            self.assertEqual(latest, '1.8.3')
            print("✅ Latest PROD version selection works")
            
            # Test version resolution for services
            resolved, missing = resolve_promoted_versions(self.mock_services_config, client)
            self.assertEqual(len(resolved), 2)
            self.assertEqual(len(missing), 0)
            self.assertEqual(resolved[0]['resolved_version'], '1.8.3')
            print("✅ Service version resolution works")
    
    def test_manifest_building(self):
        """Test platform manifest building."""
        print("\n🧪 Testing Manifest Building...")
        
        from app.main import build_manifest, AppTrustClient
        
        # Mock AppTrust client responses
        with patch.object(AppTrustClient, 'get_version_content') as mock_content:
            mock_content.return_value = {
                'sources': {'build_info': 'test'},
                'releasables': {'artifacts': ['test.jar']}
            }
            
            applications = [
                {
                    'name': 'inventory',
                    'apptrust_application': 'bookverse-inventory',
                    'resolved_version': '1.8.3'
                }
            ]
            
            client = AppTrustClient('https://test.com', 'token')
            manifest = build_manifest(applications, client, 'PROD')
            
            # Validate manifest structure
            self.assertIn('version', manifest)
            self.assertIn('created_at', manifest)
            self.assertIn('source_stage', manifest)
            self.assertIn('applications', manifest)
            self.assertEqual(manifest['source_stage'], 'PROD')
            self.assertEqual(len(manifest['applications']), 1)
            
            app_entry = manifest['applications'][0]
            self.assertEqual(app_entry['application_key'], 'bookverse-inventory')
            self.assertEqual(app_entry['version'], '1.8.3')
            self.assertIn('sources', app_entry)
            self.assertIn('releasables', app_entry)
            
            print("✅ Manifest building works")
    
    def test_manifest_writing(self):
        """Test manifest file writing."""
        print("\n🧪 Testing Manifest Writing...")
        
        from app.main import write_manifest
        
        test_manifest = {
            'version': '2025.09.15.120000',
            'platform_app_version': '1.4.7',
            'source_stage': 'PROD',
            'applications': [],
            'provenance': {'evidence_minimums': {'signatures_present': True}},
            'notes': 'Test manifest'
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            manifest_path = write_manifest(output_dir, test_manifest)
            
            # Verify file was written
            self.assertTrue(manifest_path.exists())
            self.assertTrue(manifest_path.name.startswith('platform-'))
            self.assertTrue(manifest_path.name.endswith('.yaml'))
            
            # Verify content
            import yaml
            with open(manifest_path, 'r') as f:
                written_manifest = yaml.safe_load(f)
            
            self.assertEqual(written_manifest['version'], test_manifest['version'])
            self.assertEqual(written_manifest['source_stage'], 'PROD')
            
            print("✅ Manifest writing works")
    
    def test_aggregator_cli_args(self):
        """Test aggregator command line argument parsing."""
        print("\n🧪 Testing Aggregator CLI Arguments...")
        
        from app.main import parse_args
        
        # Test with mock sys.argv
        test_args = [
            'app.main',
            '--config', 'test-config.yaml',
            '--output-dir', '/tmp/manifests',
            '--source-stage', 'PROD',
            '--preview',
            '--override', 'inventory=1.8.5',
            '--override', 'checkout=0.7.3'
        ]
        
        with patch('sys.argv', test_args):
            args = parse_args()
            
            self.assertEqual(args.config, 'test-config.yaml')
            self.assertEqual(args.output_dir, '/tmp/manifests')
            self.assertEqual(args.source_stage, 'PROD')
            self.assertTrue(args.preview)
            self.assertIn('inventory=1.8.5', args.override)
            self.assertIn('checkout=0.7.3', args.override)
            
            print("✅ CLI argument parsing works")
    
    def test_override_handling(self):
        """Test version override functionality."""
        print("\n🧪 Testing Version Override Handling...")
        
        from app.main import resolve_promoted_versions, AppTrustClient
        
        # Mock client (won't be called for overridden services)
        client = AppTrustClient('https://test.com', 'token')
        
        overrides = {
            'inventory': '1.8.5',
            'recommendations': '0.9.1'
        }
        
        resolved, missing = resolve_promoted_versions(
            self.mock_services_config, client, overrides
        )
        
        self.assertEqual(len(resolved), 2)
        self.assertEqual(len(missing), 0)
        
        # Find resolved services
        inventory_resolved = next(r for r in resolved if r['name'] == 'inventory')
        recommendations_resolved = next(r for r in resolved if r['name'] == 'recommendations')
        
        self.assertEqual(inventory_resolved['resolved_version'], '1.8.5')
        self.assertEqual(recommendations_resolved['resolved_version'], '0.9.1')
        
        print("✅ Version override handling works")
    
    def test_format_summary(self):
        """Test platform summary formatting."""
        print("\n🧪 Testing Summary Formatting...")
        
        from app.main import format_summary
        
        test_manifest = {
            'version': '2025.09.15.120000',
            'platform_app_version': '1.4.7',
            'applications': [
                {'application_key': 'bookverse-inventory', 'version': '1.8.3'},
                {'application_key': 'bookverse-recommendations', 'version': '0.9.0'}
            ]
        }
        
        summary = format_summary(test_manifest)
        summary_data = json.loads(summary)
        
        self.assertEqual(summary_data['platform_manifest_version'], '2025.09.15.120000')
        self.assertEqual(summary_data['platform_app_version'], '1.4.7')
        self.assertEqual(len(summary_data['applications']), 2)
        
        print("✅ Summary formatting works")

def run_aggregator_tests():
    """Run aggregator-specific tests."""
    print("🚀 Starting Platform Aggregator Functionality Testing")
    print("=" * 65)
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestPlatformAggregator)
    
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 65)
    print("🏁 Aggregator Testing Summary")
    print("-" * 35)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n🎉 All aggregator tests passed!")
        return 0
    else:
        print("\n⚠️  Some aggregator tests failed")
        return 1

if __name__ == '__main__':
    sys.exit(run_aggregator_tests())
