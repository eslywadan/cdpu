# tests/test_version_performance.py
import pytest
import time
from common.api.transformers import VersionTransformer
from common.api.versioning import APIVersionManager

class TestVersionPerformance:
    """Test performance of version transformations"""
    
    def test_transformation_performance(self):
        """Test transformation performance with large dataset"""
        transformer = VersionTransformer()
        
        # Create large dataset
        large_dataset = [
            {
                'client_id': f'client_{i}',
                'user_id': f'user_{i}',
                'permission': 'READ|WRITE|DELETE',
                'registry': '/ds,/ml,/eng,/data',
                'create_dttm': '2024-01-01 10:00:00'
            }
            for i in range(1000)
        ]
        
        start_time = time.time()
        result = transformer.transform(large_dataset, 'v1', 'v2')
        end_time = time.time()
        
        # Should transform 1000 items in under 1 second
        assert (end_time - start_time) < 1.0
        assert len(result) == 1000
        
        # Verify transformation
        assert all('clientId' in item for item in result)
        assert all(isinstance(item['permission'], list) for item in result)
    
    def test_caching_efficiency(self, app):
        """Test version manager caching"""
        manager = APIVersionManager(app)
        
        # Register many versions
        for i in range(10):
            from flask import Blueprint
            bp = Blueprint(f'v{i}', __name__)
            manager.register_version(f'v{i}', bp)
        
        # Test repeated lookups
        start_time = time.time()
        for _ in range(1000):
            version = manager._extract_version('/api/v5/test')
            assert version == 'v5'
        end_time = time.time()
        
        # Should complete 1000 lookups in under 0.1 seconds
        assert (end_time - start_time) < 0.1