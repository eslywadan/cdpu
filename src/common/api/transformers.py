# src/common/api/transformers.py
from typing import Dict, Any, List, Callable
from copy import deepcopy
import json

class TransformationRule:
    """Defines transformation rules between versions"""
    
    def __init__(self):
        self.field_mappings: Dict[str, str] = {}
        self.value_transformers: Dict[str, Callable] = {}
        self.removed_fields: List[str] = []
        self.added_fields: Dict[str, Any] = {}
    
    def rename_field(self, old_name: str, new_name: str):
        """Rename a field"""
        self.field_mappings[old_name] = new_name
        return self
    
    def transform_value(self, field: str, transformer: Callable):
        """Transform field value"""
        self.value_transformers[field] = transformer
        return self
    
    def remove_field(self, field: str):
        """Remove a field"""
        self.removed_fields.append(field)
        return self
    
    def add_field(self, field: str, default_value: Any):
        """Add a new field with default value"""
        self.added_fields[field] = default_value
        return self
    
    def apply(self, data: Dict) -> Dict:
        """Apply transformation rules to data"""
        result = deepcopy(data)
        
        # Remove fields
        for field in self.removed_fields:
            result.pop(field, None)
        
        # Rename fields
        for old_name, new_name in self.field_mappings.items():
            if old_name in result:
                result[new_name] = result.pop(old_name)
        
        # Transform values
        for field, transformer in self.value_transformers.items():
            if field in result:
                result[field] = transformer(result[field])
        
        # Add new fields
        result.update(self.added_fields)
        
        return result

class VersionTransformer:
    """Handles data transformation between API versions"""
    
    def __init__(self):
        self.rules: Dict[tuple, TransformationRule] = {}
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default transformation rules"""
        
        # v1 to v2 transformations
        v1_to_v2 = TransformationRule()
        v1_to_v2.rename_field('client_id', 'clientId')
        v1_to_v2.rename_field('user_id', 'userId')
        v1_to_v2.rename_field('create_dttm', 'createdAt')
        v1_to_v2.transform_value('permission', lambda x: x.split('|') if x else [])
        v1_to_v2.transform_value('registry', lambda x: x.split(',') if x else [])
        v1_to_v2.add_field('apiVersion', 'v2')
        
        self.rules[('v1', 'v2')] = v1_to_v2
        
        # v2 to v1 transformations (reverse)
        v2_to_v1 = TransformationRule()
        v2_to_v1.rename_field('clientId', 'client_id')
        v2_to_v1.rename_field('userId', 'user_id')
        v2_to_v1.rename_field('createdAt', 'create_dttm')
        v2_to_v1.transform_value('permission', lambda x: '|'.join(x) if isinstance(x, list) else x)
        v2_to_v1.transform_value('registry', lambda x: ','.join(x) if isinstance(x, list) else x)
        v2_to_v1.remove_field('apiVersion')
        
        self.rules[('v2', 'v1')] = v2_to_v1
    
    def transform(self, data: Any, from_version: str, to_version: str) -> Any:
        """Transform data between versions"""
        
        if from_version == to_version:
            return data
        
        rule = self.rules.get((from_version, to_version))
        if not rule:
            raise ValueError(f"No transformation rule from {from_version} to {to_version}")
        
        # Handle list of items
        if isinstance(data, list):
            return [rule.apply(item) if isinstance(item, dict) else item for item in data]
        
        # Handle single item
        if isinstance(data, dict):
            return rule.apply(data)
        
        return data