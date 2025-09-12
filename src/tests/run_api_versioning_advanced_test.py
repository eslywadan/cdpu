# run_advanced_tests.py
#!/usr/bin/env python
import pytest
import sys
import os

def run_advanced_tests():
    """Run tests for deprecation, metrics, and diagnostics"""
    
    # Add source to path
    sys.path.insert(0, os.path.abspath('.'))
    
    # Test categories
    test_suites = {
        'deprecation': 'tests_api_versioning/test_deprecation.py',
        'metrics': 'tests_api_versioning/test_metrics.py',
        'diagnostics': 'tests_api_versioning/test_diagnostics.py',
        'integration': 'tests_api_versioning/test_integration_complete.py',
        'all': 'tests_api_versioning/test_deprecation.py tests_api_versioning/test_metrics.py tests_api_versioning/test_diagnostics.py tests_api_versioning/test_integration_complete.py'
    }
    
    # Get test suite from command line
    suite = sys.argv[1] if len(sys.argv) > 1 else 'all'
    
    # Run tests
    test_path = test_suites.get(suite, test_suites['all'])
    
    # Pytest arguments
    args = [
        '-v',  # Verbose
        '--tb=short',  # Shorter traceback
        '--cov=common.api.deprecation',  # Coverage for deprecation
        '--cov=common.api.metrics',  # Coverage for metrics
        '--cov=common.api.diagnostics',  # Coverage for diagnostics
        '--cov-report=term-missing',  # Show missing lines
        '--cov-report=html',  # Generate HTML report
        '--cov-report=xml',  # Generate XML for CI/CD
        test_path
    ]
    
    # Add markers for different test types
    if suite != 'all':
        args.extend(['-m', suite])
    
    # Run pytest
    exit_code = pytest.main(args)
    
    # Generate report summary
    if exit_code == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ Tests failed with exit code: {exit_code}")
    
    return exit_code

if __name__ == '__main__':
    sys.exit(run_advanced_tests())