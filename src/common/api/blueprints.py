# src/common/api/blueprints.py
from flask import Blueprint, jsonify, request
from functools import wraps
from typing import List, Dict

def versioned_route(supported_versions: List[str] = None):
    """Decorator to mark routes with supported versions"""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            current_version = getattr(request, 'api_version', 'v1')
            
            if supported_versions and current_version not in supported_versions:
                response = jsonify({
                    'error': 'Endpoint not available in this version',
                    'current_version': current_version,
                    'supported_versions': supported_versions
                })
                response.status_code = 404
                return response
            
            return f(*args, **kwargs)
        
        wrapped._supported_versions = supported_versions
        return wrapped
    return decorator

def create_versioned_blueprint(version: str, name: str) -> Blueprint:
    """Create a blueprint for a specific API version"""
    
    bp = Blueprint(f'{name}_{version}', __name__)
    bp.version = version
    
    # Add version info endpoint
    @bp.route('/info')
    def version_info():
        return jsonify({
            'version': version,
            'status': 'active',
            'endpoints': _get_endpoint_list(bp)
        })
    
    return bp

def _get_endpoint_list(blueprint: Blueprint) -> List[Dict]:
    """Get list of endpoints in blueprint"""
    endpoints = []
    # Blueprint may not be registered yet, so check if app is available
    if hasattr(blueprint, 'app') and blueprint.app:
        for rule in blueprint.app.url_map.iter_rules():
            if rule.endpoint.startswith(blueprint.name):
                endpoints.append({
                    'path': rule.rule,
                    'methods': list(rule.methods - {'HEAD', 'OPTIONS'})
                })
    return endpoints