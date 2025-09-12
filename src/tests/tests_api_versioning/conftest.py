# tests/conftest.py
import pytest
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from common.api.versioning import APIVersionManager, APIVersion
from common.api.transformers import VersionTransformer, TransformationRule
from common.api.blueprints import create_versioned_blueprint
import json

@pytest.fixture
def app():
    """Create Flask app for testing"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db = SQLAlchemy(app)
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture
def version_manager(app):
    """Create version manager"""
    manager = APIVersionManager(app)
    return manager

@pytest.fixture
def sample_v1_data():
    """Sample v1 format data"""
    return {
        'client_id': 'test_client_001',
        'user_id': 'USER123',
        'create_dttm': '2024-01-01 10:00:00',
        'permission': 'QUERY|DEBUG|ADMIN',
        'registry': '/ds,/ml,/eng',
        'obsolete': 0,
        'expiry': '2025-01-01'
    }

@pytest.fixture
def sample_v2_data():
    """Sample v2 format data"""
    return {
        'clientId': 'test_client_001',
        'userId': 'USER123',
        'createdAt': '2024-01-01T10:00:00Z',
        'permission': ['QUERY', 'DEBUG', 'ADMIN'],
        'registry': ['/ds', '/ml', '/eng'],
        'obsolete': False,
        'expiry': '2025-01-01T00:00:00Z',
        'apiVersion': 'v2'
    }

@pytest.fixture
def sample_v1_list():
    """Sample v1 list data"""
    return [
        {
            'client_id': 'client_001',
            'user_id': 'USER001',
            'permission': 'QUERY',
            'registry': '/ds'
        },
        {
            'client_id': 'client_002',
            'user_id': 'USER002',
            'permission': 'QUERY|DEBUG',
            'registry': '/ml,/eng'
        }
    ]