# run_tests.py
#!/usr/bin/env python
import pytest
import sys
import os

def run_tests():
    """Run all API versioning tests"""
    
    # Add source to path
    sys.path.insert(0, os.path.abspath('.'))
    
    # Test categories
    test_suites = {
        'unit': 'tests_api_versioning/test_api_versioning.py tests_api_versioning/test_version_transformers.py',
        'integration': 'tests_api_versioning/test_versioned_endpoints.py tests_api_versioning/test_version_middleware.py',
        'performance': 'tests_api_versioning/test_version_performance.py',
        'all': 'tests_api_versioning/'
    }
    
    # Get test suite from command line
    suite = sys.argv[1] if len(sys.argv) > 1 else 'all'
    
    # Run tests
    test_path = test_suites.get(suite, 'tests_api_versioning/')
    
    # Pytest arguments
    args = [
        '-v',  # Verbose
        '--tb=short',  # Shorter traceback
        #'--cov=common.api',  # Coverage for api module
        #'--cov-report=term-missing',  # Show missing lines
        #'--cov-report=html',  # Generate HTML report
        test_path
    ]
    
    # Run pytest
    exit_code = pytest.main(args)
    
    return exit_code

if __name__ == '__main__':
    sys.exit(run_tests())