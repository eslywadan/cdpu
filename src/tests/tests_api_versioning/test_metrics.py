# tests/test_metrics.py
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import json
import time

from common.api.metrics import (
    VersionMetrics, metrics_middleware,
    api_requests_total, api_request_duration,
    api_transformation_duration, api_deprecated_requests
)
from tests_api_versioning.fixtures.test_helpers import MockRedis
from tests_api_versioning.fixtures.mock_data import create_mock_version_stats

class TestVersionMetrics:
    """Test VersionMetrics class"""
    
    @pytest.fixture
    def metrics(self):
        """Create metrics instance with mock Redis"""
        redis_client = MockRedis()
        return VersionMetrics(redis_client)
    
    def test_track_request(self, metrics):
        """Test tracking API request"""
        # Track a request
        metrics.track_request(
            version='v1',
            endpoint='/accounts',
            method='GET',
            status=200,
            duration=0.150,
            client_id='client_001'
        )
        
        # Check Redis storage
        keys = metrics.redis.keys('metrics:requests:v1:*')
        assert len(keys) > 0
        
        # Check daily stats
        daily_key = f"stats:daily:v1:{datetime.now().strftime('%Y%m%d')}"
        stats = metrics.redis.hgetall(daily_key)
        assert stats['total_requests'] == 1
        assert stats['endpoint:/accounts'] == 1
        
        # Check unique clients
        clients_key = f"stats:clients:v1:{datetime.now().strftime('%Y%m%d')}"
        clients = metrics.redis.smembers(clients_key)
        assert 'client_001' in clients
    
    def test_track_transformation(self, metrics):
        """Test tracking transformation metrics"""
        # Mock Prometheus metric
        with patch('common.api.metrics.api_transformation_duration') as mock_metric:
            metrics.track_transformation('v1', 'v2', 0.005)
            
            mock_metric.labels.assert_called_once_with(
                from_version='v1',
                to_version='v2'
            )
            mock_metric.labels().observe.assert_called_once_with(0.005)
    
    def test_track_error(self, metrics):
        """Test tracking API errors"""
        with patch('common.api.metrics.api_version_errors') as mock_metric:
            metrics.track_error('v1', '/accounts', 'ValueError')
            
            mock_metric.labels.assert_called_once_with(
                version='v1',
                endpoint='/accounts',
                error_type='ValueError'
            )
            mock_metric.labels().inc.assert_called_once()
    
    def test_store_request_metrics(self, metrics):
        """Test storing detailed request metrics"""
        metrics._store_request_metrics(
            version='v1',
            endpoint='/users',
            method='POST',
            status=201,
            duration=0.200,
            client_id='client_002'
        )
        
        # Check time-series data
        key = f"metrics:requests:v1:{datetime.now().strftime('%Y%m%d')}"
        data = metrics.redis.data.get(key, [])
        assert len(data) == 1
        
        metric = json.loads(data[0])
        assert metric['version'] == 'v1'
        assert metric['endpoint'] == '/users'
        assert metric['method'] == 'POST'
        assert metric['status'] == 201
        assert metric['duration'] == 0.200
        assert metric['client_id'] == 'client_002'
    
    def test_update_aggregated_stats(self, metrics):
        """Test updating aggregated statistics"""
        metrics._update_aggregated_stats('v2', '/products', 'client_003')
        
        # Check daily stats
        daily_key = f"stats:daily:v2:{datetime.now().strftime('%Y%m%d')}"
        stats = metrics.redis.hgetall(daily_key)
        assert stats['total_requests'] == 1
        assert stats['endpoint:/products'] == 1
        
        # Check unique clients
        clients_key = f"stats:clients:v2:{datetime.now().strftime('%Y%m%d')}"
        assert metrics.redis.scard(clients_key) == 1
    
    def test_is_deprecated(self, metrics):
        """Test checking if version is deprecated"""
        # Set deprecation marker
        metrics.redis.set('deprecation:v1', 'deprecated')
        
        assert metrics._is_deprecated('v1') is True
        assert metrics._is_deprecated('v2') is False
    
    def test_get_version_statistics(self, metrics):
        """Test getting version statistics"""
        # Setup mock data
        date = datetime.now().strftime('%Y%m%d')
        daily_key = f"stats:daily:v1:{date}"
        
        metrics.redis.hset(daily_key, 'total_requests', '100')
        metrics.redis.hset(daily_key, 'endpoint:/accounts', '60')
        metrics.redis.hset(daily_key, 'endpoint:/users', '40')
        
        clients_key = f"stats:clients:v1:{date}"
        metrics.redis.sadd(clients_key, 'client_001', 'client_002')
        
        # Get statistics
        stats = metrics.get_version_statistics('v1', days=1)
        
        assert stats['version'] == 'v1'
        assert stats['total_requests'] == 100
        assert stats['unique_clients'] == 2
        assert len(stats['top_endpoints']) == 2
        assert stats['top_endpoints'][0] == ('/accounts', 60)
        assert stats['top_endpoints'][1] == ('/users', 40)

class TestMetricsMiddleware:
    """Test metrics middleware"""
    
    @patch('common.api.metrics.metrics')
    def test_metrics_middleware_success(self, mock_metrics, app):
        """Test middleware for successful request"""
        # Create mock version manager
        version_manager = Mock()
        
        # Create middleware decorator
        middleware = metrics_middleware(version_manager)
        
        # Create test function
        @middleware
        def test_endpoint():
            return Mock(status_code=200)
        
        # Use Flask app context for request
        with app.test_request_context('/test', method='GET', headers={'X-Client-ID': 'client_001'}):
            # Set api_version on the request
            from flask import request
            request.api_version = 'v1'
            
            # Execute
            response = test_endpoint()
            
            # Verify metrics tracked
            mock_metrics.track_request.assert_called_once()
            call_args = mock_metrics.track_request.call_args[0]
            assert call_args[0] == 'v1'  # version
            assert call_args[1] == '/test'  # endpoint (path)
            assert call_args[2] == 'GET'  # method
            assert call_args[3] == 200  # status
            assert call_args[5] == 'client_001'  # client_id
    
    @patch('common.api.metrics.metrics')
    def test_metrics_middleware_error(self, mock_metrics, app):
        """Test middleware for error request"""
        version_manager = Mock()
        middleware = metrics_middleware(version_manager)
        
        @middleware
        def test_endpoint():
            raise ValueError("Test error")
        
        # Use Flask app context for request
        with app.test_request_context('/test', method='POST'):
            # Set api_version on the request
            from flask import request
            request.api_version = 'v1'
            
            # Execute and expect error
            with pytest.raises(ValueError):
                test_endpoint()
            
            # Verify error tracked
            mock_metrics.track_error.assert_called_once_with(
                'v1', '/test', 'ValueError'
            )