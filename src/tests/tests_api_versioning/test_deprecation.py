# tests/test_deprecation.py
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import json

from common.api.deprecation import (
    DeprecationStatus, DeprecationNotice, DeprecationManager
)
from tests_api_versioning.fixtures.test_helpers import MockRedis, MockDBEngine, MockConnection
from tests_api_versioning.fixtures.mock_data import create_mock_client

class TestDeprecationNotice:
    """Test DeprecationNotice class"""
    
    def test_notice_creation(self):
        """Test creating deprecation notice"""
        notice = DeprecationNotice(
            version='v1',
            deprecated_at=datetime(2024, 1, 1),
            sunset_at=datetime(2024, 7, 1),
            successor='v2',
            reason='Upgrading to v2'
        )
        
        assert notice.version == 'v1'
        assert notice.successor == 'v2'
        assert notice.reason == 'Upgrading to v2'
        assert notice.migration_guide_url == ''
        assert notice.affected_endpoints == []
        assert notice.notified_clients == []
    
    def test_notice_to_dict(self):
        """Test converting notice to dictionary"""
        notice = DeprecationNotice(
            version='v1',
            deprecated_at=datetime(2024, 1, 1),
            sunset_at=datetime(2024, 7, 1),
            successor='v2'
        )
        
        result = notice.to_dict()
        
        assert result['version'] == 'v1'
        assert result['successor'] == 'v2'
        assert 'deprecated_at' in result
        assert 'sunset_at' in result
        assert 'days_until_sunset' in result
        assert 'status' in result
    
    def test_get_status_deprecated(self):
        """Test status when version is deprecated"""
        notice = DeprecationNotice(
            version='v1',
            deprecated_at=datetime.now() - timedelta(days=30),
            sunset_at=datetime.now() + timedelta(days=60),
            successor='v2'
        )
        
        assert notice.get_status() == DeprecationStatus.DEPRECATED
    
    def test_get_status_sunset_warning(self):
        """Test status when approaching sunset"""
        notice = DeprecationNotice(
            version='v1',
            deprecated_at=datetime.now() - timedelta(days=150),
            sunset_at=datetime.now() + timedelta(days=15),  # Within 30 days
            successor='v2'
        )
        
        assert notice.get_status() == DeprecationStatus.SUNSET_WARNING
    
    def test_get_status_sunset(self):
        """Test status when sunset"""
        notice = DeprecationNotice(
            version='v1',
            deprecated_at=datetime.now() - timedelta(days=200),
            sunset_at=datetime.now() - timedelta(days=1),  # Past sunset
            successor='v2'
        )
        
        assert notice.get_status() == DeprecationStatus.SUNSET

class TestDeprecationManager:
    """Test DeprecationManager class"""
    
    @pytest.fixture
    def manager(self):
        """Create deprecation manager with mocks"""
        redis_client = MockRedis()
        db_engine = MockDBEngine()
        return DeprecationManager(redis_client, db_engine)
    
    def test_deprecate_version(self, manager):
        """Test deprecating a version"""
        notice = manager.deprecate_version(
            version='v1',
            sunset_days=180,
            successor='v2',
            reason='Upgrading to v2',
            affected_endpoints=['/api/v1/accounts']
        )
        
        assert notice.version == 'v1'
        assert notice.successor == 'v2'
        assert notice.reason == 'Upgrading to v2'
        assert '/api/v1/accounts' in notice.affected_endpoints
        assert 'v1' in manager.notices
        
        # Check Redis storage
        stored = manager.redis.get('deprecation:v1')
        assert stored is not None
        stored_data = json.loads(stored)
        assert stored_data['version'] == 'v1'
    
    def test_store_deprecation_in_db(self, manager):
        """Test storing deprecation in database"""
        notice = DeprecationNotice(
            version='v1',
            deprecated_at=datetime.now(),
            sunset_at=datetime.now() + timedelta(days=180),
            successor='v2',
            reason='Test reason'
        )
        
        manager._store_deprecation_in_db(notice)
        
        # Check executed queries
        assert len(manager.db_engine.executed_queries) > 0
        query, params = manager.db_engine.executed_queries[0]
        assert 'INSERT INTO api_deprecations' in query
        assert params['version'] == 'v1'
        assert params['successor'] == 'v2'
    
    @patch('common.api.deprecation.DeprecationManager._send_deprecation_email')
    @patch('common.api.deprecation.DeprecationManager._send_webhook_notification')
    def test_notify_deprecation(self, mock_webhook, mock_email, manager):
        """Test deprecation notifications"""
        # Setup mock clients
        manager.db_engine.add_mock_result([
            create_mock_client('client_001'),
            create_mock_client('client_002')
        ])
        
        notice = DeprecationNotice(
            version='v1',
            deprecated_at=datetime.now(),
            sunset_at=datetime.now() + timedelta(days=180),
            successor='v2'
        )
        
        manager._notify_deprecation(notice)
        
        # Verify notifications sent
        assert mock_email.call_count == 2
        assert mock_webhook.call_count == 2
        assert 'client_001' in notice.notified_clients
        assert 'client_002' in notice.notified_clients
    
    def test_get_clients_using_version(self, manager):
        """Test getting clients using a version"""
        # Mock database result
        manager.db_engine.add_mock_result([
            create_mock_client('client_001', 'Client One'),
            create_mock_client('client_002', 'Client Two')
        ])
        
        clients = manager._get_clients_using_version('v1')
        
        assert len(clients) == 2
        assert clients[0]['client_id'] == 'client_001'
        assert clients[1]['client_id'] == 'client_002'
    
    @patch('common.api.deprecation.logger')
    def test_send_deprecation_email(self, mock_logger, manager):
        """Test sending deprecation email"""
        client = create_mock_client('client_001')
        notice = DeprecationNotice(
            version='v1',
            deprecated_at=datetime.now(),
            sunset_at=datetime.now() + timedelta(days=180),
            successor='v2'
        )
        
        manager._send_deprecation_email(client, notice)
        
        # Verify logging
        mock_logger.info.assert_called()
        assert 'Deprecation email sent' in str(mock_logger.info.call_args)
    
    @patch('builtins.__import__')
    def test_send_webhook_notification(self, mock_import, manager):
        """Test sending webhook notification"""
        # Create mock requests module
        mock_requests = Mock()
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_requests.post.return_value = mock_response
        
        # Mock the import to return our mock requests when 'requests' is imported
        def side_effect(name, *args, **kwargs):
            if name == 'requests':
                return mock_requests
            return __import__(name, *args, **kwargs)
        
        mock_import.side_effect = side_effect
        
        client = create_mock_client('client_001')
        notice = DeprecationNotice(
            version='v1',
            deprecated_at=datetime.now(),
            sunset_at=datetime.now() + timedelta(days=180),
            successor='v2'
        )
        
        manager._send_webhook_notification(client, notice)
        
        # Verify webhook called
        mock_requests.post.assert_called_once()
        call_args = mock_requests.post.call_args
        assert call_args[0][0] == 'https://webhook.example.com/client_001'
        assert 'api.version.deprecated' in str(call_args[1]['json'])
    
    def test_check_sunset_warnings(self, manager):
        """Test checking for sunset warnings"""
        # Add notice approaching sunset
        notice = DeprecationNotice(
            version='v1',
            deprecated_at=datetime.now() - timedelta(days=150),
            sunset_at=datetime.now() + timedelta(days=15),  # Warning zone
            successor='v2'
        )
        manager.notices['v1'] = notice
        
        with patch.object(manager, '_send_sunset_warning') as mock_warn:
            manager.check_sunset_warnings()
            mock_warn.assert_called_once_with(notice)
    
    @patch('common.api.deprecation.logger')
    def test_send_sunset_warning(self, mock_logger, manager):
        """Test sending sunset warning"""
        # Fix the current time for consistent testing
        fixed_now = datetime(2024, 1, 1, 12, 0, 0)
        sunset_date = fixed_now + timedelta(days=30)  # Exactly 30 days
        
        notice = DeprecationNotice(
            version='v1',
            deprecated_at=fixed_now - timedelta(days=150),
            sunset_at=sunset_date,
            successor='v2'
        )
        
        # Mock clients still using version
        manager.db_engine.add_mock_result([create_mock_client('client_001')])
        
        with patch.object(manager, '_send_urgent_sunset_warning') as mock_urgent, \
             patch('common.api.deprecation.datetime') as mock_datetime:
            
            # Mock datetime.now() to return our fixed time
            mock_datetime.now.return_value = fixed_now
            
            manager._send_sunset_warning(notice)
            
            # Should send warning for 30-day mark
            mock_urgent.assert_called_once()
            mock_logger.warning.assert_called()