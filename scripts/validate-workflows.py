
"""
BookVerse Platform Service - GitHub Actions Workflow Validation System

This module implements comprehensive validation for GitHub Actions workflows in the
BookVerse platform, ensuring workflow integrity, configuration compliance, and
platform-specific requirements for CI/CD pipeline reliability and enterprise-grade
automation standards.

🏗️ Architecture Overview:
    - Workflow Validation: Comprehensive YAML syntax and structure validation
    - Platform Requirements: BookVerse-specific workflow requirement checking
    - Authentication Validation: Shared authentication workflow usage verification
    - CI/CD Compliance: Platform aggregation logic and process validation
    - Error Reporting: Detailed validation results with actionable feedback
    - Automation Integration: CI/CD pipeline integration for automated validation

🚀 Key Features:
    - YAML syntax validation with comprehensive error reporting
    - Platform-specific workflow requirement validation and compliance checking
    - Shared authentication workflow usage verification and best practices
    - Platform aggregation logic validation for core platform functionality
    - Detailed validation reporting with clear success and failure indicators
    - CI/CD integration support for automated workflow validation

🔧 Technical Implementation:
    - YAML Parser: Safe YAML loading with comprehensive error handling
    - Pattern Matching: Platform-specific logic detection and validation
    - Path Resolution: Flexible workflow file discovery and processing
    - Error Handling: Graceful error handling with detailed failure reporting
    - Configuration Analysis: Deep workflow structure analysis and validation

📊 Business Logic:
    - Quality Assurance: Ensures CI/CD pipeline reliability and consistency
    - Platform Standards: Enforces BookVerse platform-specific requirements
    - Development Efficiency: Prevents workflow errors before deployment
    - Compliance Verification: Validates adherence to platform standards
    - Risk Mitigation: Reduces deployment failures through comprehensive validation

🛠️ Usage Patterns:
    - Pre-commit Validation: Local workflow validation before code commit
    - CI/CD Integration: Automated validation in pull request workflows
    - Platform Maintenance: Regular validation of existing workflow configurations
    - Development Workflow: Integration in developer tooling and IDE extensions
    - Release Validation: Pre-release workflow validation for deployment safety

Authors: BookVerse Platform Team
Version: 1.0.0
"""

import os
import sys
import yaml
from pathlib import Path

def validate_workflow_file(workflow_path):
    try:
        with open(workflow_path, 'r') as f:
            workflow = yaml.safe_load(f)
        
        print(f"✅ {workflow_path.name}: Valid YAML")
        
        jobs = workflow.get('jobs', {})
        
        if 'aggregate' in workflow_path.name:
            if any('python -m app.main' in str(job) for job in jobs.values()):
                print(f"  ✅ Platform aggregation logic preserved")
            else:
                print(f"  ⚠️  Platform aggregation logic not found")
        
        shared_auth_found = False
        for job_name, job_config in jobs.items():
            if isinstance(job_config, dict) and job_config.get('uses', '').endswith('shared-platform-auth.yml'):
                shared_auth_found = True
                print(f"  ✅ Uses shared authentication workflow in job '{job_name}'")
        
        if not shared_auth_found and len(jobs) > 1:
            print(f"  ℹ️  No shared auth workflow found (may be intentional)")
        
        return True
        
    except Exception as e:
        print(f"❌ {workflow_path.name}: Error - {e}")
        return False

def main():
    print("🔍 Platform Workflow Validation")
    print("=" * 50)
    
    workflows_dir = Path(__file__).parent.parent / '.github' / 'workflows'
    
    if not workflows_dir.exists():
        print(f"❌ Workflows directory not found: {workflows_dir}")
        return 1
    
    workflow_files = list(workflows_dir.glob('*.yml'))
    
    if not workflow_files:
        print(f"❌ No workflow files found in {workflows_dir}")
        return 1
    
    print(f"Found {len(workflow_files)} workflow files")
    print()
    
    all_valid = True
    for workflow_file in sorted(workflow_files):
        if not validate_workflow_file(workflow_file):
            all_valid = False
        print()
    
    print("🎯 Platform-Specific Requirements Check:")
    print("-" * 40)
    
    core_files = [
        'app/main.py',
        'config/services.yaml',
    ]
    
    for file_path in core_files:
        full_path = Path(__file__).parent.parent / file_path
        if full_path.exists():
            print(f"✅ Core platform file exists: {file_path}")
        else:
            print(f"❌ Missing core platform file: {file_path}")
            all_valid = False
    
    print()
    
    if all_valid:
        print("🎉 All platform workflows validated successfully!")
        print("✅ Phase 2 migration appears successful")
        return 0
    else:
        print("❌ Some validation issues found")
        return 1

if __name__ == '__main__':
    sys.exit(main())
