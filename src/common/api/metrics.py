# src/common/api/metrics.py
from prometheus_client import Counter, Histogram, Gauge, Summary
from functools import wraps
from datetime import datetime, timedelta
import time
import redis
from typing import Dict, Any
import json

# Define Prometheus metrics
api_requests_total = Counter(
    'api_requests_total',
    'Total number of API requests',
    ['version', 'endpoint', 'method', 'status']
)

api_request_duration = Histogram(
    'api_request_duration_seconds',
    'API request duration in seconds',
    ['version', 'endpoint', 'method'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
)

api_transformation_duration = Histogram(
    'api_transformation_duration_seconds',
    'Version transformation duration in seconds',
    ['from_version', 'to_version'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1)
)

api_active_versions = Gauge(
    'api_active_versions',
    'Number of active API versions'
)

api_deprecated_requests = Counter(
    'api_deprecated_requests_total',
    'Requests to deprecated API versions',
    ['version', 'client_id']
)

api_version_errors = Counter(
    'api_version_errors_total',
    'API errors by version',
    ['version', 'endpoint', 'error_type']
)

api_clients_by_version = Gauge(
    'api_clients_by_version',
    'Number of unique clients per version',
    ['version']
)

api_sunset_days_remaining = Gauge(
    'api_sunset_days_remaining',
    'Days until version sunset',
    ['version']
)

class VersionMetrics:
    """Collects and manages version metrics"""
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.metrics_buffer = []
        self.flush_interval = 60  # seconds
        
    def track_request(self, version: str, endpoint: str, method: str, 
                     status: int, duration: float, client_id: str = None):
        """Track API request metrics"""
        
        # Update Prometheus metrics
        api_requests_total.labels(
            version=version,
            endpoint=endpoint,
            method=method,
            status=str(status)
        ).inc()
        
        api_request_duration.labels(
            version=version,
            endpoint=endpoint,
            method=method
        ).observe(duration)
        
        # Track deprecated version usage
        if self._is_deprecated(version):
            api_deprecated_requests.labels(
                version=version,
                client_id=client_id or 'unknown'
            ).inc()
        
        # Store detailed metrics in Redis
        if self.redis:
            self._store_request_metrics(version, endpoint, method, status, duration, client_id)
    
    def track_transformation(self, from_version: str, to_version: str, duration: float):
        """Track version transformation metrics"""
        
        api_transformation_duration.labels(
            from_version=from_version,
            to_version=to_version
        ).observe(duration)
    
    def track_error(self, version: str, endpoint: str, error_type: str):
        """Track API errors"""
        
        api_version_errors.labels(
            version=version,
            endpoint=endpoint,
            error_type=error_type
        ).inc()
    
    def _store_request_metrics(self, version: str, endpoint: str, method: str,
                              status: int, duration: float, client_id: str):
        """Store detailed metrics in Redis"""
        
        metric = {
            'timestamp': datetime.now().isoformat(),
            'version': version,
            'endpoint': endpoint,
            'method': method,
            'status': status,
            'duration': duration,
            'client_id': client_id
        }
        
        # Add to time-series data
        key = f"metrics:requests:{version}:{datetime.now().strftime('%Y%m%d')}"
        self.redis.lpush(key, json.dumps(metric))
        self.redis.expire(key, 86400 * 30)  # Keep for 30 days
        
        # Update aggregated stats
        self._update_aggregated_stats(version, endpoint, client_id)
    
    def _update_aggregated_stats(self, version: str, endpoint: str, client_id: str):
        """Update aggregated statistics"""
        
        # Daily request count
        daily_key = f"stats:daily:{version}:{datetime.now().strftime('%Y%m%d')}"
        self.redis.hincrby(daily_key, 'total_requests', 1)
        self.redis.hincrby(daily_key, f'endpoint:{endpoint}', 1)
        self.redis.expire(daily_key, 86400 * 90)  # Keep for 90 days
        
        # Unique clients
        if client_id:
            clients_key = f"stats:clients:{version}:{datetime.now().strftime('%Y%m%d')}"
            self.redis.sadd(clients_key, client_id)
            self.redis.expire(clients_key, 86400 * 30)
            
            # Update gauge
            unique_clients = self.redis.scard(clients_key)
            api_clients_by_version.labels(version=version).set(unique_clients)
    
    def _is_deprecated(self, version: str) -> bool:
        """Check if version is deprecated"""
        
        if self.redis:
            return self.redis.exists(f"deprecation:{version}")
        return False
    
    def get_version_statistics(self, version: str, days: int = 30) -> Dict:
        """Get comprehensive statistics for a version"""
        
        stats = {
            'version': version,
            'period_days': days,
            'total_requests': 0,
            'unique_clients': set(),
            'top_endpoints': {},
            'error_rate': 0,
            'avg_latency_ms': 0,
            'daily_trends': []
        }
        
        if not self.redis:
            return stats
        
        # Aggregate daily stats
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y%m%d')
            daily_key = f"stats:daily:{version}:{date}"
            
            daily_data = self.redis.hgetall(daily_key)
            if daily_data:
                stats['total_requests'] += int(daily_data.get('total_requests', 0))
                
                # Collect endpoint stats
                for key, value in daily_data.items():
                    if key.startswith('endpoint:'):
                        endpoint = key.replace('endpoint:', '')
                        stats['top_endpoints'][endpoint] = \
                            stats['top_endpoints'].get(endpoint, 0) + int(value)
                
                # Collect unique clients
                clients_key = f"stats:clients:{version}:{date}"
                clients = self.redis.smembers(clients_key)
                stats['unique_clients'].update(clients)
                
                # Daily trend
                stats['daily_trends'].append({
                    'date': date,
                    'requests': int(daily_data.get('total_requests', 0))
                })
        
        # Convert set to count
        stats['unique_clients'] = len(stats['unique_clients'])
        
        # Sort top endpoints
        stats['top_endpoints'] = sorted(
            stats['top_endpoints'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return stats

def metrics_middleware(version_manager):
    """Flask middleware for collecting metrics"""
    
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Extract request info
            from flask import request
            version = getattr(request, 'api_version', 'unknown')
            endpoint = request.endpoint or request.path
            method = request.method
            client_id = request.headers.get('X-Client-ID')
            
            try:
                # Execute request
                response = f(*args, **kwargs)
                status = response.status_code if hasattr(response, 'status_code') else 200
                
            except Exception as e:
                # Track error
                status = 500
                metrics.track_error(version, endpoint, type(e).__name__)
                raise
            
            finally:
                # Track metrics
                duration = time.time() - start_time
                metrics.track_request(version, endpoint, method, status, duration, client_id)
            
            return response
        
        return wrapper
    
    return decorator

# Global metrics instance
metrics = VersionMetrics()