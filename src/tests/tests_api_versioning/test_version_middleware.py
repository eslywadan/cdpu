# tests/test_version_middleware.py
import pytest
from flask import Flask, g, request
from common.api.versioning import APIVersionManager

class TestVersionMiddleware:
    """Test version-related middleware"""
    
    def test_before_request_version_extraction(self, app):
        """Test version extraction in before_request"""
        manager = APIVersionManager(app)
        
        with app.test_request_context('/api/v1/test'):
            # Manually call the before_request handler to simulate Flask behavior
            manager._before_request()
            assert hasattr(request, 'api_version')
            assert request.api_version == 'v1'
    
    def test_after_request_headers(self, app):
        """Test headers added in after_request"""
        manager = APIVersionManager(app)
        
        # Create and register version
        from flask import Blueprint
        v1 = Blueprint('v1', __name__)
        manager.register_version('v1', v1)
        
        with app.test_request_context('/api/v1/test'):
            request.api_version = 'v1'
            
            # Create response
            from flask import make_response
            response = make_response('test')
            
            # Process response
            response = manager._after_request(response)
            
            assert response.headers.get('API-Version') == 'v1'
    
    def test_invalid_version_handling(self, app, client):
        """Test handling of invalid version"""
        manager = APIVersionManager(app)
        
        # Request non-existent version
        response = client.get('/api/v99/test')
        
        # Should return 404 as route doesn't exist
        assert response.status_code == 404
    
    def test_version_context_preservation(self, app):
        """Test version context is preserved through request"""
        manager = APIVersionManager(app)
        
        from flask import Blueprint
        v1 = Blueprint('v1', __name__)
        
        captured_version = None
        
        @v1.route('/test')
        def test_endpoint():
            nonlocal captured_version
            captured_version = getattr(request, 'api_version', None)
            return 'ok'
        
        manager.register_version('v1', v1)
        
        with app.test_client() as client:
            client.get('/api/v1/test')
            
        assert captured_version == 'v1'