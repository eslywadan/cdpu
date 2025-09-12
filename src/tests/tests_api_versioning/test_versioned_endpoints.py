# tests/test_versioned_endpoints.py
import pytest
import json
from flask import Blueprint, jsonify, request
from common.api.blueprints import create_versioned_blueprint, versioned_route
from common.api.versioning import APIVersionManager
from common.api.transformers import VersionTransformer

class TestVersionedEndpoints:
    """Test versioned API endpoints"""
    
    def test_versioned_blueprint_creation(self, app):
        """Test creating versioned blueprint"""
        bp = create_versioned_blueprint('v1', 'test')
        
        assert bp.name == 'test_v1'
        assert bp.version == 'v1'
        
        # Register blueprint
        app.register_blueprint(bp, url_prefix='/api/v1')
        
        # Test info endpoint
        with app.test_client() as client:
            response = client.get('/api/v1/info')
            assert response.status_code == 200
            
            data = response.get_json()
            assert data['version'] == 'v1'
            assert data['status'] == 'active'
    
    def test_versioned_route_decorator(self, app):
        """Test versioned route decorator"""
        bp = Blueprint('test', __name__)
        
        @bp.route('/endpoint1')
        @versioned_route(['v1', 'v2'])
        def endpoint_v1_v2():
            return jsonify({'data': 'available in v1 and v2'})
        
        @bp.route('/endpoint2')
        @versioned_route(['v2'])
        def endpoint_v2_only():
            return jsonify({'data': 'available in v2 only'})
        
        # Register for both versions
        app.register_blueprint(bp, url_prefix='/api/v1', name='test_v1')
        app.register_blueprint(bp, url_prefix='/api/v2', name='test_v2')
        
        with app.test_request_context('/api/v1/endpoint1'):
            request.api_version = 'v1'
            response = endpoint_v1_v2()
            assert response.status_code == 200
        
        with app.test_request_context('/api/v1/endpoint2'):
            request.api_version = 'v1'
            response = endpoint_v2_only()
            assert response.status_code == 404
            data = json.loads(response.data)
            assert 'not available' in data['error']
        
        with app.test_request_context('/api/v2/endpoint2'):
            request.api_version = 'v2'
            response = endpoint_v2_only()
            assert response.status_code == 200
    
    def test_full_integration(self, app, client):
        """Test full integration with multiple versions"""
        manager = APIVersionManager(app)
        transformer = VersionTransformer()
        
        # Create v1 endpoints
        v1 = create_versioned_blueprint('v1', 'accounts')
        
        @v1.route('/accounts/<client_id>')
        def get_account_v1(client_id):
            # Simulate database fetch
            account = {
                'client_id': client_id,
                'user_id': 'USER001',
                'create_dttm': '2024-01-01 10:00:00',
                'permission': 'QUERY|DEBUG',
                'registry': '/ds,/ml'
            }
            return jsonify(account)
        
        @v1.route('/accounts')
        def list_accounts_v1():
            accounts = [
                {
                    'client_id': 'client_001',
                    'user_id': 'USER001',
                    'permission': 'QUERY'
                },
                {
                    'client_id': 'client_002',
                    'user_id': 'USER002',
                    'permission': 'QUERY|DEBUG'
                }
            ]
            return jsonify({'accounts': accounts})
        
        # Create v2 endpoints
        v2 = create_versioned_blueprint('v2', 'accounts')
        
        @v2.route('/accounts/<client_id>')
        def get_account_v2(client_id):
            # Get v1 data
            account_v1 = {
                'client_id': client_id,
                'user_id': 'USER001',
                'create_dttm': '2024-01-01 10:00:00',
                'permission': 'QUERY|DEBUG',
                'registry': '/ds,/ml'
            }
            # Transform to v2
            account_v2 = transformer.transform(account_v1, 'v1', 'v2')
            return jsonify(account_v2)
        
        @v2.route('/accounts')
        def list_accounts_v2():
            accounts_v1 = [
                {
                    'client_id': 'client_001',
                    'user_id': 'USER001',
                    'permission': 'QUERY'
                },
                {
                    'client_id': 'client_002',
                    'user_id': 'USER002',
                    'permission': 'QUERY|DEBUG'
                }
            ]
            accounts_v2 = transformer.transform(accounts_v1, 'v1', 'v2')
            return jsonify({'accounts': accounts_v2})
        
        # Register versions
        manager.register_version('v1', v1, deprecated=True, successor='v2')
        manager.register_version('v2', v2)
        
        # Test v1 endpoint
        response = client.get('/api/v1/accounts/test_client')
        assert response.status_code == 200
        data = response.get_json()
        assert 'client_id' in data
        assert data['client_id'] == 'test_client'
        assert isinstance(data['permission'], str)
        
        # Check deprecation headers
        assert response.headers.get('Deprecation') == 'true'
        assert 'Sunset' in response.headers
        
        # Test v2 endpoint
        response = client.get('/api/v2/accounts/test_client')
        assert response.status_code == 200
        data = response.get_json()
        assert 'clientId' in data
        assert data['clientId'] == 'test_client'
        assert isinstance(data['permission'], list)
        assert data['apiVersion'] == 'v2'
        
        # Test list endpoints
        response = client.get('/api/v1/accounts')
        assert response.status_code == 200
        data = response.get_json()
        assert 'client_id' in data['accounts'][0]
        
        response = client.get('/api/v2/accounts')
        assert response.status_code == 200
        data = response.get_json()
        assert 'clientId' in data['accounts'][0]
        assert isinstance(data['accounts'][0]['permission'], list)