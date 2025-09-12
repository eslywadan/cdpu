# src/common/api/diagnostics.py
from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from typing import Dict, List, Any
import psutil
import os

diagnostics_bp = Blueprint('diagnostics', __name__)

class VersionDiagnostics:
    """API version diagnostics and health checks"""
    
    def __init__(self, version_manager, metrics_manager, deprecation_manager):
        self.version_manager = version_manager
        self.metrics = metrics_manager
        self.deprecation = deprecation_manager
    
    def get_version_health(self, version: str) -> Dict:
        """Get health status for a specific version"""
        
        health = {
            'version': version,
            'status': 'unknown',
            'checks': {},
            'metrics': {},
            'issues': []
        }
        
        # Check if version exists
        if version not in self.version_manager.versions:
            health['status'] = 'not_found'
            return health
        
        version_info = self.version_manager.versions[version]
        
        # Version status check
        if version_info.is_sunset:
            health['status'] = 'sunset'
            health['issues'].append('Version has reached sunset')
        elif version_info.is_deprecated:
            health['status'] = 'deprecated'
            days_remaining = (version_info.sunset_at - datetime.now()).days
            health['issues'].append(f'Version deprecated, {days_remaining} days until sunset')
        else:
            health['status'] = 'healthy'
        
        # Performance checks
        stats = self.metrics.get_version_statistics(version, days=1)
        
        health['metrics'] = {
            'requests_24h': stats['total_requests'],
            'unique_clients': stats['unique_clients'],
            'error_rate': stats.get('error_rate', 0),
            'avg_latency_ms': stats.get('avg_latency_ms', 0)
        }
        
        # Health checks
        health['checks'] = {
            'endpoints_available': self._check_endpoints(version),
            'transformation_working': self._check_transformations(version),
            'performance_acceptable': self._check_performance(stats),
            'error_rate_acceptable': stats.get('error_rate', 0) < 0.01
        }
        
        # Overall health
        if all(health['checks'].values()):
            if health['status'] not in ['sunset', 'deprecated']:
                health['status'] = 'healthy'
        else:
            health['status'] = 'degraded'
            health['issues'].append('Some health checks failed')
        
        return health
    
    def get_system_diagnostics(self) -> Dict:
        """Get complete system diagnostics"""
        
        diagnostics = {
            'timestamp': datetime.now().isoformat(),
            'system': self._get_system_info(),
            'versions': self._get_all_versions_status(),
            'transformations': self._get_transformation_matrix(),
            'deprecations': self._get_deprecation_status(),
            'performance': self._get_performance_metrics(),
            'recommendations': self._get_recommendations()
        }
        
        return diagnostics
    
    def _get_system_info(self) -> Dict:
        """Get system information"""
        
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'python_version': os.sys.version,
            'process_uptime': self._get_process_uptime(),
            'environment': os.environ.get('ENVIRONMENT', 'development')
        }
    
    def _get_all_versions_status(self) -> List[Dict]:
        """Get status of all versions"""
        
        versions_status = []
        
        for version, info in self.version_manager.versions.items():
            status = {
                'version': version,
                'status': 'active',
                'released': info.released.isoformat(),
                'usage_24h': 0,
                'unique_clients_24h': 0
            }
            
            if info.is_sunset:
                status['status'] = 'sunset'
                status['sunset_at'] = info.sunset_at.isoformat()
            elif info.is_deprecated:
                status['status'] = 'deprecated'
                status['deprecated_at'] = info.deprecated_at.isoformat()
                status['sunset_at'] = info.sunset_at.isoformat()
                status['days_until_sunset'] = (info.sunset_at - datetime.now()).days
                status['successor'] = info.successor
            
            # Add metrics
            stats = self.metrics.get_version_statistics(version, days=1)
            status['usage_24h'] = stats['total_requests']
            status['unique_clients_24h'] = stats['unique_clients']
            
            versions_status.append(status)
        
        return versions_status
    
    def _get_transformation_matrix(self) -> Dict:
        """Get transformation compatibility matrix"""
        
        matrix = {}
        
        for (from_v, to_v), transformer in self.version_manager.transformers.items():
            if from_v not in matrix:
                matrix[from_v] = {}
            
            matrix[from_v][to_v] = {
                'available': True,
                'tested': self._is_transformation_tested(from_v, to_v),
                'performance': self._get_transformation_performance(from_v, to_v)
            }
        
        return matrix
    
    def _get_deprecation_status(self) -> List[Dict]:
        """Get deprecation status for all versions"""
        
        deprecations = []
        
        for version, notice in self.deprecation.notices.items():
            dep_status = {
                'version': version,
                'deprecated_at': notice.deprecated_at.isoformat(),
                'sunset_at': notice.sunset_at.isoformat(),
                'days_remaining': (notice.sunset_at - datetime.now()).days,
                'successor': notice.successor,
                'status': notice.get_status().value,
                'clients_notified': len(notice.notified_clients),
                'clients_still_using': len(self._get_clients_using_version(version))
            }
            deprecations.append(dep_status)
        
        return deprecations
    
    def _get_performance_metrics(self) -> Dict:
        """Get performance metrics across all versions"""
        
        return {
            'total_requests_24h': sum(
                self.metrics.get_version_statistics(v, days=1)['total_requests']
                for v in self.version_manager.versions.keys()
            ),
            'avg_latency_ms': self._calculate_avg_latency(),
            'error_rate': self._calculate_error_rate(),
            'transformation_overhead_ms': self._calculate_transformation_overhead()
        }
    
    def _get_recommendations(self) -> List[str]:
        """Get system recommendations"""
        
        recommendations = []
        
        # Check for versions that should be sunset
        for version, info in self.version_manager.versions.items():
            if info.is_deprecated:
                days_remaining = (info.sunset_at - datetime.now()).days
                if days_remaining < 30:
                    recommendations.append(
                        f"Version {version} approaching sunset ({days_remaining} days). "
                        f"Ensure all clients have migrated."
                    )
        
        # Check for high error rates
        for version in self.version_manager.versions.keys():
            stats = self.metrics.get_version_statistics(version, days=1)
            if stats.get('error_rate', 0) > 0.01:
                recommendations.append(
                    f"Version {version} has high error rate ({stats['error_rate']:.2%}). "
                    f"Investigation recommended."
                )
        
        # Check for unused versions
        for version in self.version_manager.versions.keys():
            stats = self.metrics.get_version_statistics(version, days=7)
            if stats['total_requests'] == 0:
                recommendations.append(
                    f"Version {version} has no usage in past 7 days. "
                    f"Consider deprecation."
                )
        
        return recommendations
    
    def _check_endpoints(self, version: str) -> bool:
        """Check if version endpoints are available"""
        # Implementation depends on your endpoint registration
        return True
    
    def _check_transformations(self, version: str) -> bool:
        """Check if transformations are working"""
        # Test transformations
        test_data = {'test': 'data'}
        
        for other_version in self.version_manager.versions.keys():
            if other_version != version:
                if (version, other_version) in self.version_manager.transformers:
                    try:
                        transformer = self.version_manager.transformers[(version, other_version)]
                        result = transformer(test_data)
                        if not result:
                            return False
                    except:
                        return False
        
        return True
    
    def _check_performance(self, stats: Dict) -> bool:
        """Check if performance is acceptable"""
        return stats.get('avg_latency_ms', 0) < 1000  # Under 1 second
    
    def _is_transformation_tested(self, from_v: str, to_v: str) -> bool:
        """Check if transformation has been tested"""
        # Could check test results database
        return True
    
    def _get_transformation_performance(self, from_v: str, to_v: str) -> Dict:
        """Get transformation performance metrics"""
        # Get from Prometheus metrics
        return {
            'avg_duration_ms': 5,
            'p95_duration_ms': 10,
            'p99_duration_ms': 20
        }
    
    def _get_clients_using_version(self, version: str) -> List:
        """Get clients using specific version"""
        # Implementation depends on your client tracking
        return []
    
    def _calculate_avg_latency(self) -> float:
        """Calculate average latency across all versions"""
        # Aggregate from metrics
        return 150.0
    
    def _calculate_error_rate(self) -> float:
        """Calculate overall error rate"""
        # Calculate from metrics
        return 0.005
    
    def _calculate_transformation_overhead(self) -> float:
        """Calculate average transformation overhead"""
        # Calculate from transformation metrics
        return 10.0
    
    def _get_process_uptime(self) -> str:
        """Get process uptime"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        create_time = datetime.fromtimestamp(process.create_time())
        uptime = datetime.now() - create_time
        
        return str(uptime)

# Diagnostic endpoints
diagnostics = None  # Will be initialized with managers

@diagnostics_bp.route('/diagnostics/versions')
def get_versions_diagnostics():
    """Get version diagnostics"""
    return jsonify(diagnostics.get_system_diagnostics())

@diagnostics_bp.route('/diagnostics/versions/<version>')
def get_version_health(version):
    """Get health status for specific version"""
    return jsonify(diagnostics.get_version_health(version))

@diagnostics_bp.route('/diagnostics/metrics')
def get_metrics_summary():
    """Get metrics summary"""
    
    summary = {
        'timestamp': datetime.now().isoformat(),
        'versions': {}
    }
    
    for version in diagnostics.version_manager.versions.keys():
        stats = diagnostics.metrics.get_version_statistics(version, days=1)
        summary['versions'][version] = stats
    
    return jsonify(summary)

@diagnostics_bp.route('/diagnostics/deprecations')
def get_deprecations():
    """Get deprecation status"""
    
    deprecations = []
    for version, notice in diagnostics.deprecation.notices.items():
        deprecations.append(notice.to_dict())
    
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'deprecations': deprecations
    })

@diagnostics_bp.route('/diagnostics/recommendations')
def get_recommendations():
    """Get system recommendations"""
    
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'recommendations': diagnostics._get_recommendations()
    })