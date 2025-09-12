# tests/test_api_versioning.py
import pytest
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from common.api.versioning import APIVersion, APIVersionManager

class TestAPIVersion:
    """Test APIVersion class"""
    
    def test_version_creation(self):
        """Test creating API version"""
        version = APIVersion('v1')
        
        assert version.version == 'v1'
        assert version.released is not None
        assert not version.is_deprecated
        assert not version.is_sunset
        assert version.deprecated_at is None
        assert version.sunset_at is None
    
    def test_version_deprecation(self):
        """Test deprecating version"""
        version = APIVersion('v1')
        version.deprecate(sunset_days=30, successor='v2')
        
        assert version.is_deprecated
        assert version.deprecated_at is not None
        assert version.sunset_at is not None
        assert version.successor == 'v2'
        
        # Check sunset date calculation
        expected_sunset = version.deprecated_at + timedelta(days=30)
        assert abs((version.sunset_at - expected_sunset).total_seconds()) < 1
    
    def test_sunset_version(self):
        """Test sunset version detection"""
        version = APIVersion('v1')
        
        # Set sunset to past
        version.deprecated_at = datetime.now() - timedelta(days=31)
        version.sunset_at = datetime.now() - timedelta(days=1)
        
        assert version.is_sunset

class TestAPIVersionManager:
    """Test APIVersionManager class"""
    
    def test_manager_initialization(self, app):
        """Test version manager initialization"""
        manager = APIVersionManager(app, default_version='v1')
        
        assert manager.app == app
        assert manager.default_version == 'v1'
        assert manager.versions == {}
        assert manager.blueprints == {}
    
    def test_register_version(self, app):
        """Test registering API version"""
        manager = APIVersionManager(app)
        
        # Create blueprint
        bp = Blueprint('test_v1', __name__)
        
        @bp.route('/test')
        def test_endpoint():
            return jsonify({'version': 'v1'})
        
        # Register version
        manager.register_version('v1', bp)
        
        assert 'v1' in manager.versions
        assert 'v1' in manager.blueprints
        assert manager.versions['v1'].version == 'v1'
    
    def test_register_deprecated_version(self, app):
        """Test registering deprecated version"""
        manager = APIVersionManager(app)
        bp = Blueprint('test_v1', __name__)
        
        manager.register_version(
            'v1', 
            bp,
            deprecated=True,
            sunset_days=60,
            successor='v2'
        )
        
        version = manager.versions['v1']
        assert version.is_deprecated
        assert version.successor == 'v2'
    
    def test_extract_version(self, app):
        """Test version extraction from URL"""
        manager = APIVersionManager(app)
        
        # Test valid paths
        assert manager._extract_version('/api/v1/accounts') == 'v1'
        assert manager._extract_version('/api/v2/users') == 'v2'
        assert manager._extract_version('/api/v10/data') == 'v10'
        
        # Test invalid paths
        assert manager._extract_version('/accounts') is None
        assert manager._extract_version('/api/accounts') is None
        assert manager._extract_version('/v1/accounts') is None
    
    def test_version_headers(self, app, client):
        """Test version headers in response"""
        manager = APIVersionManager(app)
        
        # Create and register v1
        v1 = Blueprint('v1', __name__)
        
        @v1.route('/test')
        def test_v1():
            return jsonify({'data': 'test'})
        
        manager.register_version('v1', v1)
        
        # Test request
        response = client.get('/api/v1/test')
        
        assert response.status_code == 200
        assert response.headers.get('API-Version') == 'v1'
    
    def test_deprecated_version_headers(self, app, client):
        """Test deprecated version headers"""
        manager = APIVersionManager(app)
        
        # Create and register deprecated v1
        v1 = Blueprint('v1', __name__)
        
        @v1.route('/test')
        def test_v1():
            return jsonify({'data': 'test'})
        
        manager.register_version(
            'v1', 
            v1,
            deprecated=True,
            sunset_days=30,
            successor='v2'
        )
        
        # Test request
        response = client.get('/api/v1/test')
        
        assert response.status_code == 200
        assert response.headers.get('Deprecation') == 'true'
        assert 'Sunset' in response.headers
        assert '</api/v2>; rel="successor-version"' in response.headers.get('Link', '')
    
    def test_sunset_version_blocking(self, app, client):
        """Test sunset version returns 410 Gone"""
        manager = APIVersionManager(app)
        
        # Create and register v1
        v1 = Blueprint('v1', __name__)
        
        @v1.route('/test')
        def test_v1():
            return jsonify({'data': 'test'})
        
        manager.register_version('v1', v1)
        
        # Manually set version as sunset
        version = manager.versions['v1']
        version.deprecated_at = datetime.now() - timedelta(days=100)
        version.sunset_at = datetime.now() - timedelta(days=1)
        version.successor = 'v2'
        
        # Test request
        response = client.get('/api/v1/test')
        
        assert response.status_code == 410
        data = response.get_json()
        assert 'error' in data
        assert 'no longer supported' in data['error']
        assert data['successor'] == 'v2'
    
    def test_transformer_registration(self, app):
        """Test registering transformers"""
        manager = APIVersionManager(app)
        
        def v1_to_v2_transformer(data):
            # Simple transformer
            if isinstance(data, dict):
                data['transformed'] = True
            return data
        
        manager.register_transformer('v1', 'v2', v1_to_v2_transformer)
        
        assert ('v1', 'v2') in manager.transformers
        
        # Test transformer function
        result = manager.transformers[('v1', 'v2')]({'test': 'data'})
        assert result['transformed'] is True
