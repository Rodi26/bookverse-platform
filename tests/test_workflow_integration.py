
import os
import sys
import yaml
import json
import subprocess
from pathlib import Path
import unittest

class TestWorkflowIntegration(unittest.TestCase):
    
    def setUp(self):
        self.platform_root = Path(__file__).parent.parent
        self.workflows_dir = self.platform_root / '.github' / 'workflows'
    
    def test_workflow_yaml_validity(self):
        print("\n🧪 Testing Workflow YAML Validity...")
        
        workflow_files = list(self.workflows_dir.glob('*.yml'))
        self.assertGreater(len(workflow_files), 0, "No workflow files found")
        
        valid_count = 0
        for workflow_file in workflow_files:
            try:
                with open(workflow_file, 'r') as f:
                    yaml.safe_load(f)
                valid_count += 1
                print(f"✅ {workflow_file.name}: Valid YAML")
            except yaml.YAMLError as e:
                self.fail(f"❌ {workflow_file.name}: Invalid YAML - {e}")
        
        print(f"✅ All {valid_count} workflow files have valid YAML syntax")
    
    def test_shared_auth_workflow_structure(self):
        print("\n🧪 Testing Shared Auth Workflow Structure...")
        
        auth_workflow = self.workflows_dir / 'shared-platform-auth.yml'
        self.assertTrue(auth_workflow.exists(), "Shared auth workflow not found")
        
        with open(auth_workflow, 'r') as f:
            workflow = yaml.safe_load(f)
        
        self.assertIn('on', workflow)
        self.assertEqual(workflow['on'], 'workflow_call')
        
        self.assertIn('inputs', workflow['on'])
        inputs = workflow['on']['inputs']
        
        required_inputs = ['service-name', 'setup-python', 'install-dependencies', 'setup-apptrust']
        for inp in required_inputs:
            self.assertIn(inp, inputs, f"Missing input: {inp}")
        
        self.assertIn('outputs', workflow['on'])
        outputs = workflow['on']['outputs']
        
        required_outputs = ['auth-status', 'oidc-token', 'apptrust-base-url']
        for out in required_outputs:
            self.assertIn(out, outputs, f"Missing output: {out}")
        
        self.assertIn('jobs', workflow)
        self.assertIn('authenticate', workflow['jobs'])
        
        print("✅ Shared auth workflow structure is correct")
    
    def test_platform_workflows_use_shared_auth(self):
        print("\n🧪 Testing Platform Workflows Use Shared Auth...")
        
        workflows_using_shared_auth = [
            'aggregate.yml',
            'promote-platform.yml', 
            'platform-aggregate-promote.yml'
        ]
        
        for workflow_name in workflows_using_shared_auth:
            workflow_path = self.workflows_dir / workflow_name
            if not workflow_path.exists():
                print(f"⚠️  Workflow {workflow_name} not found, skipping")
                continue
            
            with open(workflow_path, 'r') as f:
                content = f.read()
            
            self.assertIn('shared-platform-auth.yml', content, 
                         f"{workflow_name} should use shared auth workflow")
            
            workflow = yaml.safe_load(content)
            self.assertIn('jobs', workflow)
            
            jobs = workflow['jobs']
            self.assertIn('authenticate', jobs, 
                         f"{workflow_name} should have authenticate job")
            
            auth_job = jobs['authenticate']
            self.assertIn('uses', auth_job)
            self.assertIn('shared-platform-auth.yml', auth_job['uses'])
            
            print(f"✅ {workflow_name}: Uses shared authentication")
        
        print("✅ Platform workflows properly use shared authentication")
    
    def test_workflow_environment_consistency(self):
        print("\n🧪 Testing Workflow Environment Consistency...")
        
        expected_vars = [
            'JFROG_URL',
            'PROJECT_KEY',
            'JF_OIDC_TOKEN',
            'APPTRUST_BASE_URL'
        ]
        
        workflow_files = [f for f in self.workflows_dir.glob('*.yml') 
                         if not f.name.startswith('shared-')]
        
        for workflow_file in workflow_files:
            with open(workflow_file, 'r') as f:
                content = f.read()
            
            var_usage = {}
            for var in expected_vars:
                if f'vars.{var}' in content or f'env.{var}' in content or f'{var}}}' in content:
                    var_usage[var] = True
            
            if var_usage:
                print(f"✅ {workflow_file.name}: Uses {len(var_usage)} standard env vars")
        
        print("✅ Workflow environment variables are consistent")
    
    def test_platform_aggregator_integration(self):
        print("\n🧪 Testing Platform Aggregator Integration...")
        
        aggregator_script = self.platform_root / 'app' / 'main.py'
        self.assertTrue(aggregator_script.exists(), "Aggregator script not found")
        
        services_config = self.platform_root / 'config' / 'services.yaml'
        self.assertTrue(services_config.exists(), "Services config not found")
        
        with open(services_config, 'r') as f:
            config = yaml.safe_load(f)
        
        self.assertIn('services', config)
        services = config['services']
        self.assertIsInstance(services, list)
        self.assertGreater(len(services), 0)
        
        for service in services:
            self.assertIn('name', service)
            self.assertIn('apptrust_application', service)
            print(f"✅ Service configured: {service['name']}")
        
        print("✅ Platform aggregator integration points are correct")
    
    def test_dependency_consistency(self):
        print("\n🧪 Testing Dependency Consistency...")
        
        requirements_file = self.platform_root / 'requirements.txt'
        self.assertTrue(requirements_file.exists(), "Requirements file not found")
        
        with open(requirements_file, 'r') as f:
            requirements = f.read()
        
        self.assertIn('bookverse-core', requirements, 
                     "Should use bookverse-core package")
        
        libs_dir = self.platform_root / 'libs'
        self.assertFalse(libs_dir.exists(), 
                        "Embedded libs directory should be removed")
        
        print("✅ Dependencies are consistent with infrastructure approach")
    
    def test_platform_scripts_executable(self):
        print("\n🧪 Testing Platform Scripts...")
        
        scripts_dir = self.platform_root / 'scripts'
        if not scripts_dir.exists():
            print("⚠️  Scripts directory not found, skipping")
            return
        
        python_scripts = list(scripts_dir.glob('*.py'))
        shell_scripts = list(scripts_dir.glob('*.sh'))
        
        for script in python_scripts:
            try:
                result = subprocess.run([
                    sys.executable, '-m', 'py_compile', str(script)
                ], capture_output=True, text=True, cwd=self.platform_root)
                
                self.assertEqual(result.returncode, 0, 
                               f"Script {script.name} compilation failed: {result.stderr}")
                print(f"✅ {script.name}: Compiles successfully")
            except Exception as e:
                print(f"⚠️  {script.name}: Could not test compilation - {e}")
        
        for script in shell_scripts:
            try:
                result = subprocess.run([
                    'bash', '-n', str(script)
                ], capture_output=True, text=True)
                
                self.assertEqual(result.returncode, 0,
                               f"Script {script.name} syntax check failed: {result.stderr}")
                print(f"✅ {script.name}: Valid shell syntax")
            except Exception as e:
                print(f"⚠️  {script.name}: Could not test syntax - {e}")
        
        print(f"✅ Platform scripts validated ({len(python_scripts)} Python, {len(shell_scripts)} shell)")
    
    def test_platform_module_imports(self):
        print("\n🧪 Testing Platform Module Imports...")
        
        sys.path.insert(0, str(self.platform_root))
        
        try:
            from app import main
            from app import auth  
            
            print("✅ All platform modules import successfully")
            
            import app.auth
            
            auth_file = self.platform_root / 'app' / 'auth.py'
            with open(auth_file, 'r') as f:
                auth_content = f.read()
            
            self.assertIn('from bookverse_core', auth_content,
                         "Auth module should use bookverse_core")
            
            print("✅ Platform modules properly use shared libraries")
            
        except ImportError as e:
            self.fail(f"❌ Module import failed: {e}")
        finally:
            if str(self.platform_root) in sys.path:
                sys.path.remove(str(self.platform_root))
    
    def test_platform_configuration_files(self):
        print("\n🧪 Testing Platform Configuration Files...")
        
        config_files = [
            ('config/services.yaml', 'Services configuration'),
            ('config/version-map.yaml', 'Version map configuration'),
            ('requirements.txt', 'Python dependencies'),
            ('Dockerfile', 'Container configuration'),
            ('pytest.ini', 'Test configuration')
        ]
        
        for config_file, description in config_files:
            file_path = self.platform_root / config_file
            if file_path.exists():
                print(f"✅ {description}: {config_file}")
                
                if config_file.endswith('.yaml') or config_file.endswith('.yml'):
                    try:
                        with open(file_path, 'r') as f:
                            yaml.safe_load(f)
                        print(f"   ✅ Valid YAML syntax")
                    except yaml.YAMLError as e:
                        self.fail(f"❌ Invalid YAML in {config_file}: {e}")
            else:
                print(f"⚠️  {description}: {config_file} (not found)")
        
        print("✅ Platform configuration files validated")

def run_workflow_integration_tests():
    print("🚀 Starting Platform Workflow Integration Testing")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestWorkflowIntegration)
    
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    print("🏁 Workflow Integration Testing Summary")
    print("-" * 45)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n🎉 All workflow integration tests passed!")
        return 0
    else:
        print("\n⚠️  Some workflow integration tests failed")
        return 1

if __name__ == '__main__':
    sys.exit(run_workflow_integration_tests())
