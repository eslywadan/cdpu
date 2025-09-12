# tests/test_diagnostics.py
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import json

from common.api.diagnostics import VersionDiagnostics
from common.api.versioning import APIVersion
from tests_api_versioning.fixtures.test_helpers import MockRedis
from tests_api_versioning.fixtures.mock_data import create_mock_version_stats

class TestVersionDiagnostics:
    """Test VersionDiagnostics class"""
    
    @pytest.fixture
    def diagnostics(self):
        """Create diagnostics instance with mocks"""
        version_manager = Mock()
        metrics_manager = Mock()
        deprecation_manager = Mock()
        
        # Setup mock versions
        version_manager.versions = {
            'v1': Mock(
                is_sunset=False,
                is_deprecated=True,
                deprecated_at=datetime.now() - timedelta(days=30),
                sunset_at=datetime.now() + timedelta(days=20),  # Approaching sunset
                released=datetime.now() - timedelta(days=365),
                successor='v2'
            ),
            'v2': Mock(
                is_sunset=False,
                is_deprecated=False,
                released=datetime.now() - timedelta(days=180)
            )
        }
        
        version_manager.transformers = {
            ('v1', 'v2'): Mock(),
            ('v2', 'v1'): Mock()
        }
        
        return VersionDiagnostics(version_manager, metrics_manager, deprecation_manager)
    
    def test_get_version_health_not_found(self, diagnostics):
        """Test health check for non-existent version"""
        health = diagnostics.get_version_health('v99')
        
        assert health['version'] == 'v99'
        assert health['status'] == 'not_found'
    
    def test_get_version_health_deprecated(self, diagnostics):
        """Test health check for deprecated version"""
        # Mock metrics
        diagnostics.metrics.get_version_statistics = Mock(
            return_value=create_mock_version_stats('v1', 500)
        )
        
        health = diagnostics.get_version_health('v1')
        
        assert health['version'] == 'v1'
        assert health['status'] == 'deprecated'
        assert len(health['issues']) > 0
        assert 'deprecated' in health['issues'][0].lower()
    
    def test_get_version_health_healthy(self, diagnostics):
        """Test health check for healthy version"""
        # Mock metrics
        diagnostics.metrics.get_version_statistics = Mock(
            return_value=create_mock_version_stats('v2', 1000)
        )
        
        # Mock health checks
        with patch.object(diagnostics, '_check_endpoints', return_value=True), \
             patch.object(diagnostics, '_check_transformations', return_value=True), \
             patch.object(diagnostics, '_check_performance', return_value=True):
            
            health = diagnostics.get_version_health('v2')
            
            assert health['version'] == 'v2'
            assert health['status'] == 'healthy'
            assert health['metrics']['requests_24h'] == 1000
            assert all(health['checks'].values())
    
    def test_get_system_diagnostics(self, diagnostics):
        """Test getting complete system diagnostics"""
        # Mock methods
        diagnostics._get_system_info = Mock(return_value={'cpu_percent': 50})
        diagnostics._get_all_versions_status = Mock(return_value=[])
        diagnostics._get_transformation_matrix = Mock(return_value={})
        diagnostics._get_deprecation_status = Mock(return_value=[])
        diagnostics._get_performance_metrics = Mock(return_value={})
        diagnostics._get_recommendations = Mock(return_value=[])
        
        result = diagnostics.get_system_diagnostics()
        
        assert 'timestamp' in result
        assert 'system' in result
        assert 'versions' in result
        assert 'transformations' in result
        assert 'deprecations' in result
        assert 'performance' in result
        assert 'recommendations' in result
        
        assert result['system']['cpu_percent'] == 50
    
    @patch('psutil.cpu_percent', return_value=75.5)
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_get_system_info(self, mock_disk, mock_memory, mock_cpu, diagnostics):
        """Test getting system information"""
        mock_memory.return_value = Mock(percent=60.0)
        mock_disk.return_value = Mock(percent=45.0)
        
        info = diagnostics._get_system_info()
        
        assert info['cpu_percent'] == 75.5
        assert info['memory_percent'] == 60.0
        assert info['disk_usage'] == 45.0
        assert 'python_version' in info
        assert 'process_uptime' in info
    
    def test_get_all_versions_status(self, diagnostics):
        """Test getting status of all versions"""
        # Mock metrics
        diagnostics.metrics.get_version_statistics = Mock(
            side_effect=[
                create_mock_version_stats('v1', 500),
                create_mock_version_stats('v2', 1500)
            ]
        )
        
        statuses = diagnostics._get_all_versions_status()
        
        assert len(statuses) == 2
        
        v1_status = next(s for s in statuses if s['version'] == 'v1')
        assert v1_status['status'] == 'deprecated'
        assert 'deprecated_at' in v1_status
        assert 'sunset_at' in v1_status
        assert 'days_until_sunset' in v1_status
        assert v1_status['usage_24h'] == 500
        
        v2_status = next(s for s in statuses if s['version'] == 'v2')
        assert v2_status['status'] == 'active'
        assert v2_status['usage_24h'] == 1500
    
    def test_get_transformation_matrix(self, diagnostics):
        """Test getting transformation matrix"""
        # Mock transformation testing
        diagnostics._is_transformation_tested = Mock(return_value=True)
        diagnostics._get_transformation_performance = Mock(
            return_value={'avg_duration_ms': 5, 'p95_duration_ms': 10}
        )
        
        matrix = diagnostics._get_transformation_matrix()
        
        assert 'v1' in matrix
        assert 'v2' in matrix['v1']
        assert matrix['v1']['v2']['available'] is True
        assert matrix['v1']['v2']['tested'] is True
        assert matrix['v1']['v2']['performance']['avg_duration_ms'] == 5
    
    def test_get_deprecation_status(self, diagnostics):
        """Test getting deprecation status"""
        from common.api.deprecation import DeprecationNotice, DeprecationStatus
        
        # Mock deprecation notices
        notice = DeprecationNotice(
            version='v1',
            deprecated_at=datetime.now() - timedelta(days=30),
            sunset_at=datetime.now() + timedelta(days=150),
            successor='v2'
        )
        notice.notified_clients = ['client_001', 'client_002']
        
        diagnostics.deprecation.notices = {'v1': notice}
        diagnostics._get_clients_using_version = Mock(return_value=['client_001'])
        
        statuses = diagnostics._get_deprecation_status()
        
        assert len(statuses) == 1
        assert statuses[0]['version'] == 'v1'
        assert statuses[0]['successor'] == 'v2'
        assert statuses[0]['clients_notified'] == 2
        assert statuses[0]['clients_still_using'] == 1
    
    def test_get_performance_metrics(self, diagnostics):
        """Test getting performance metrics"""
        # Mock metrics for multiple versions
        diagnostics.metrics.get_version_statistics = Mock(
            side_effect=[
                create_mock_version_stats('v1', 500),
                create_mock_version_stats('v2', 1500)
            ]
        )
        
        diagnostics._calculate_avg_latency = Mock(return_value=175.0)
        diagnostics._calculate_error_rate = Mock(return_value=0.003)
        diagnostics._calculate_transformation_overhead = Mock(return_value=12.0)
        
        metrics = diagnostics._get_performance_metrics()
        
        assert metrics['total_requests_24h'] == 2000  # 500 + 1500
        assert metrics['avg_latency_ms'] == 175.0
        assert metrics['error_rate'] == 0.003
        assert metrics['transformation_overhead_ms'] == 12.0
    
    def test_get_recommendations(self, diagnostics):
        """Test getting system recommendations"""
        # Setup conditions for recommendations
        
        # Mock high error rate for v2
        diagnostics.metrics.get_version_statistics = Mock(
            side_effect=[
                # First loop: error rate checks (days=1)
                create_mock_version_stats('v1', 500),  # v1 stats
                {'total_requests': 1000, 'error_rate': 0.02},  # v2 high error rate
                # Second loop: usage checks (days=7)
                create_mock_version_stats('v1', 500),  # v1 stats 
                {'total_requests': 0, 'error_rate': 0}  # v2 no usage
            ]
        )
        
        recommendations = diagnostics._get_recommendations()
        
        # Should have recommendations for:
        # 1. v1 approaching sunset (150 days < 180)
        # 2. v2 high error rate
        # 3. Some version with no usage
        
        assert len(recommendations) > 0
        assert any('approaching sunset' in r for r in recommendations)
        assert any('high error rate' in r for r in recommendations)
    
    def test_check_endpoints(self, diagnostics):
        """Test checking version endpoints"""
        result = diagnostics._check_endpoints('v1')
        assert result is True  # Default implementation
    
    def test_check_transformations(self, diagnostics):
        """Test checking transformations"""
        # Mock transformer
        mock_transformer = Mock(return_value={'transformed': True})
        diagnostics.version_manager.transformers = {
            ('v1', 'v2'): mock_transformer
        }
        
        result = diagnostics._check_transformations('v1')
        assert result is True
        mock_transformer.assert_called_once()
    
    def test_check_performance(self, diagnostics):
        """Test checking performance"""
        # Good performance
        stats = {'avg_latency_ms': 500}
        assert diagnostics._check_performance(stats) is True
        
        # Poor performance
        stats = {'avg_latency_ms': 1500}
        assert diagnostics._check_performance(stats) is False