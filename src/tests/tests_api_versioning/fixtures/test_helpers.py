# tests/fixtures/test_helpers.py
import redis
from unittest.mock import MagicMock, Mock, patch
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import json
import pytest

class MockRedis:
    """Mock Redis client for testing"""
    
    def __init__(self):
        self.data = {}
        self.expiry = {}
        
    def set(self, key, value, ex=None):
        self.data[key] = value
        if ex:
            self.expiry[key] = datetime.now() + timedelta(seconds=ex)
        return True
    
    def get(self, key):
        if key in self.expiry and datetime.now() > self.expiry[key]:
            del self.data[key]
            del self.expiry[key]
            return None
        return self.data.get(key)
    
    def exists(self, key):
        return key in self.data
    
    def hset(self, name, key, value):
        if name not in self.data:
            self.data[name] = {}
        self.data[name][key] = value
        return 1
    
    def hget(self, name, key):
        if name in self.data and isinstance(self.data[name], dict):
            return self.data[name].get(key)
        return None
    
    def hgetall(self, name):
        if name in self.data and isinstance(self.data[name], dict):
            return self.data[name]
        return {}
    
    def hincrby(self, name, key, amount=1):
        if name not in self.data:
            self.data[name] = {}
        if key not in self.data[name]:
            self.data[name][key] = 0
        self.data[name][key] = int(self.data[name][key]) + amount
        return self.data[name][key]
    
    def sadd(self, name, *values):
        if name not in self.data:
            self.data[name] = set()
        for value in values:
            self.data[name].add(value)
        return len(values)
    
    def scard(self, name):
        if name in self.data and isinstance(self.data[name], set):
            return len(self.data[name])
        return 0
    
    def smembers(self, name):
        if name in self.data and isinstance(self.data[name], set):
            return self.data[name]
        return set()
    
    def lpush(self, name, *values):
        if name not in self.data:
            self.data[name] = []
        for value in values:
            self.data[name].insert(0, value)
        return len(self.data[name])
    
    def expire(self, key, seconds):
        self.expiry[key] = datetime.now() + timedelta(seconds=seconds)
        return True
    
    def hdel(self, name, *keys):
        if name in self.data and isinstance(self.data[name], dict):
            for key in keys:
                self.data[name].pop(key, None)
        return len(keys)
    
    def delete(self, *keys):
        for key in keys:
            self.data.pop(key, None)
        return len(keys)
    
    def keys(self, pattern):
        import re
        regex = pattern.replace('*', '.*')
        return [k for k in self.data.keys() if re.match(regex, k)]

class MockDBEngine:
    """Mock database engine for testing"""
    
    def __init__(self):
        self.executed_queries = []
        self.mock_results = []
        
    def connect(self):
        return MockConnection(self)
    
    def add_mock_result(self, result):
        self.mock_results.append(result)

class MockConnection:
    """Mock database connection"""
    
    def __init__(self, engine):
        self.engine = engine
        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def execute(self, query, params=None):
        self.engine.executed_queries.append((str(query), params))
        if self.engine.mock_results:
            return MockResult(self.engine.mock_results.pop(0))
        return MockResult([])
    
    def commit(self):
        pass

class MockResult:
    """Mock database result"""
    
    def __init__(self, data):
        self.data = data
        
    def fetchall(self):
        return self.data
    
    def fetchone(self):
        return self.data[0] if self.data else None
    
    def scalar(self):
        if self.data and self.data[0]:
            return self.data[0][0] if isinstance(self.data[0], (list, tuple)) else self.data[0]
        return None
    
    def __iter__(self):
        return iter(self.data)

# tests/fixtures/mock_data.py
def create_mock_client(client_id='client_001', name='Test Client'):
    """Create mock client data"""
    return {
        'client_id': client_id,
        'client_name': name,
        'email': f'{client_id}@example.com',
        'webhook_url': f'https://webhook.example.com/{client_id}',
        'request_count': 1000
    }

def create_mock_version_stats(version='v1', requests=1000):
    """Create mock version statistics"""
    return {
        'version': version,
        'period_days': 30,
        'total_requests': requests,
        'unique_clients': 10,
        'top_endpoints': [('/accounts', 500), ('/users', 300)],
        'error_rate': 0.005,
        'avg_latency_ms': 150,
        'daily_trends': [
            {'date': '20240101', 'requests': 100},
            {'date': '20240102', 'requests': 120}
        ]
    }