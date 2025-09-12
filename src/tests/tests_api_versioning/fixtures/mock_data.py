# tests/fixtures/mock_data.py
"""
Mock data factory functions for testing API versioning, deprecation, metrics, and diagnostics.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import random
import uuid
import json


def create_mock_client(client_id: str = None, 
                       name: str = None,
                       email: str = None,
                       webhook_url: str = None,
                       request_count: int = None) -> Dict[str, Any]:
    """
    Create mock client data for testing.
    
    Args:
        client_id: Client identifier (auto-generated if not provided)
        name: Client name (auto-generated if not provided)
        email: Client email (auto-generated if not provided)
        webhook_url: Webhook URL (auto-generated if not provided)
        request_count: Number of API requests (random if not provided)
    
    Returns:
        Dictionary containing client data
    """
    if not client_id:
        client_id = f'client_{uuid.uuid4().hex[:8]}'
    
    if not name:
        name = f'Test Client {client_id[-4:]}'
    
    if not email:
        email = f'{client_id}@example.com'
    
    if not webhook_url:
        webhook_url = f'https://webhook.example.com/{client_id}'
    
    if request_count is None:
        request_count = random.randint(100, 10000)
    
    return {
        'client_id': client_id,
        'client_name': name,
        'email': email,
        'webhook_url': webhook_url,
        'request_count': request_count,
        'created_at': datetime.now() - timedelta(days=random.randint(30, 365)),
        'last_active': datetime.now() - timedelta(hours=random.randint(1, 72)),
        'api_key': f'key_{uuid.uuid4().hex}',
        'tier': random.choice(['free', 'basic', 'premium', 'enterprise'])
    }


def create_mock_version_stats(version: str = 'v1',
                             requests: int = None,
                             unique_clients: int = None,
                             error_rate: float = None,
                             avg_latency_ms: float = None,
                             period_days: int = 30) -> Dict[str, Any]:
    """
    Create mock version statistics for testing.
    
    Args:
        version: API version
        requests: Total number of requests (random if not provided)
        unique_clients: Number of unique clients (random if not provided)
        error_rate: Error rate percentage (random if not provided)
        avg_latency_ms: Average latency in milliseconds (random if not provided)
        period_days: Statistics period in days
    
    Returns:
        Dictionary containing version statistics
    """
    if requests is None:
        requests = random.randint(100, 100000)
    
    if unique_clients is None:
        unique_clients = random.randint(5, 100)
    
    if error_rate is None:
        error_rate = random.uniform(0.001, 0.01)  # 0.1% to 1%
    
    if avg_latency_ms is None:
        avg_latency_ms = random.uniform(50, 500)
    
    # Generate top endpoints
    endpoints = ['/accounts', '/users', '/products', '/orders', '/reports']
    top_endpoints = []
    remaining_requests = requests
    
    for i, endpoint in enumerate(random.sample(endpoints, min(len(endpoints), 3))):
        if i == 2:  # Last endpoint gets remaining requests
            count = remaining_requests
        else:
            count = random.randint(1, remaining_requests // 2)
            remaining_requests -= count
        top_endpoints.append((endpoint, count))
    
    # Generate daily trends
    daily_trends = []
    for i in range(min(period_days, 7)):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y%m%d')
        daily_requests = random.randint(requests // period_days - 100, 
                                       requests // period_days + 100)
        daily_trends.append({
            'date': date,
            'requests': daily_requests,
            'errors': int(daily_requests * error_rate),
            'avg_latency_ms': avg_latency_ms + random.uniform(-50, 50)
        })
    
    return {
        'version': version,
        'period_days': period_days,
        'total_requests': requests,
        'unique_clients': unique_clients,
        'top_endpoints': top_endpoints,
        'error_rate': error_rate,
        'avg_latency_ms': avg_latency_ms,
        'daily_trends': daily_trends,
        'p50_latency_ms': avg_latency_ms * 0.7,
        'p95_latency_ms': avg_latency_ms * 1.5,
        'p99_latency_ms': avg_latency_ms * 2.0,
        'success_rate': 1 - error_rate,
        'total_errors': int(requests * error_rate)
    }


def create_mock_request(version: str = 'v1',
                       endpoint: str = None,
                       method: str = None,
                       status: int = None,
                       client_id: str = None):
    """Create mock request data for testing"""
    import time
    import random
    
    return {
        'version': version,
        'endpoint': endpoint or f'/api/{version}/test',
        'method': method or 'GET',
        'status_code': status or 200,
        'client_id': client_id or f'client_{random.randint(1, 1000)}',
        'timestamp': time.time(),
        'latency_ms': random.randint(10, 500),
        'user_agent': 'test-client/1.0'
    }