# tests/test_version_transformers.py
import pytest
from common.api.transformers import TransformationRule, VersionTransformer

class TestTransformationRule:
    """Test TransformationRule class"""
    
    def test_rename_field(self):
        """Test field renaming"""
        rule = TransformationRule()
        rule.rename_field('client_id', 'clientId')
        
        data = {'client_id': 'TEST123', 'other': 'value'}
        result = rule.apply(data)
        
        assert 'clientId' in result
        assert 'client_id' not in result
        assert result['clientId'] == 'TEST123'
        assert result['other'] == 'value'
    
    def test_transform_value(self):
        """Test value transformation"""
        rule = TransformationRule()
        rule.transform_value('permission', lambda x: x.split('|'))
        
        data = {'permission': 'READ|WRITE|DELETE'}
        result = rule.apply(data)
        
        assert result['permission'] == ['READ', 'WRITE', 'DELETE']
    
    def test_remove_field(self):
        """Test field removal"""
        rule = TransformationRule()
        rule.remove_field('obsolete')
        
        data = {'id': 1, 'obsolete': True, 'name': 'test'}
        result = rule.apply(data)
        
        assert 'obsolete' not in result
        assert result['id'] == 1
        assert result['name'] == 'test'
    
    def test_add_field(self):
        """Test field addition"""
        rule = TransformationRule()
        rule.add_field('apiVersion', 'v2')
        
        data = {'id': 1}
        result = rule.apply(data)
        
        assert result['apiVersion'] == 'v2'
        assert result['id'] == 1
    
    def test_chained_transformations(self):
        """Test multiple chained transformations"""
        rule = TransformationRule()
        rule.rename_field('client_id', 'clientId') \
            .rename_field('user_id', 'userId') \
            .transform_value('permission', lambda x: x.split('|')) \
            .remove_field('obsolete') \
            .add_field('version', 'v2')
        
        data = {
            'client_id': 'CL001',
            'user_id': 'US001',
            'permission': 'READ|WRITE',
            'obsolete': 0,
            'active': True
        }
        
        result = rule.apply(data)
        
        assert result == {
            'clientId': 'CL001',
            'userId': 'US001',
            'permission': ['READ', 'WRITE'],
            'active': True,
            'version': 'v2'
        }

class TestVersionTransformer:
    """Test VersionTransformer class"""
    
    def test_v1_to_v2_transformation(self, sample_v1_data):
        """Test v1 to v2 transformation"""
        transformer = VersionTransformer()
        result = transformer.transform(sample_v1_data, 'v1', 'v2')
        
        # Check field renaming
        assert 'clientId' in result
        assert 'userId' in result
        assert 'createdAt' in result
        assert 'client_id' not in result
        assert 'user_id' not in result
        assert 'create_dttm' not in result
        
        # Check value transformations
        assert isinstance(result['permission'], list)
        assert result['permission'] == ['QUERY', 'DEBUG', 'ADMIN']
        
        assert isinstance(result['registry'], list)
        assert result['registry'] == ['/ds', '/ml', '/eng']
        
        # Check added field
        assert result['apiVersion'] == 'v2'
    
    def test_v2_to_v1_transformation(self, sample_v2_data):
        """Test v2 to v1 transformation"""
        transformer = VersionTransformer()
        result = transformer.transform(sample_v2_data, 'v2', 'v1')
        
        # Check field renaming
        assert 'client_id' in result
        assert 'user_id' in result
        assert 'create_dttm' in result
        assert 'clientId' not in result
        assert 'userId' not in result
        assert 'createdAt' not in result
        
        # Check value transformations
        assert isinstance(result['permission'], str)
        assert result['permission'] == 'QUERY|DEBUG|ADMIN'
        
        assert isinstance(result['registry'], str)
        assert result['registry'] == '/ds,/ml,/eng'
        
        # Check removed field
        assert 'apiVersion' not in result
    
    def test_list_transformation(self, sample_v1_list):
        """Test transforming list of items"""
        transformer = VersionTransformer()
        result = transformer.transform(sample_v1_list, 'v1', 'v2')
        
        assert isinstance(result, list)
        assert len(result) == 2
        
        # Check first item
        assert result[0]['clientId'] == 'client_001'
        assert result[0]['userId'] == 'USER001'
        assert result[0]['permission'] == ['QUERY']
        assert result[0]['registry'] == ['/ds']
        
        # Check second item
        assert result[1]['clientId'] == 'client_002'
        assert result[1]['userId'] == 'USER002'
        assert result[1]['permission'] == ['QUERY', 'DEBUG']
        assert result[1]['registry'] == ['/ml', '/eng']
    
    def test_same_version_transformation(self, sample_v1_data):
        """Test transformation with same version (no-op)"""
        transformer = VersionTransformer()
        result = transformer.transform(sample_v1_data, 'v1', 'v1')
        
        assert result == sample_v1_data
    
    def test_missing_transformation_rule(self):
        """Test error when transformation rule doesn't exist"""
        transformer = VersionTransformer()
        
        with pytest.raises(ValueError) as exc_info:
            transformer.transform({'data': 'test'}, 'v1', 'v3')
        
        assert 'No transformation rule' in str(exc_info.value)
    
    def test_null_value_handling(self):
        """Test handling of null/None values"""
        transformer = VersionTransformer()
        
        data = {
            'client_id': 'TEST',
            'user_id': None,
            'permission': None,
            'registry': None
        }
        
        result = transformer.transform(data, 'v1', 'v2')
        
        assert result['clientId'] == 'TEST'
        assert result['userId'] is None
        assert result['permission'] == []  # None becomes empty list
        assert result['registry'] == []
    
    def test_empty_string_handling(self):
        """Test handling of empty strings"""
        transformer = VersionTransformer()
        
        data = {
            'client_id': 'TEST',
            'user_id': '',
            'permission': '',
            'registry': ''
        }
        
        result = transformer.transform(data, 'v1', 'v2')
        
        assert result['permission'] == []
        assert result['registry'] == []