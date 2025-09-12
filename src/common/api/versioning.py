# src/common/api/versioning.py
from flask import Flask, Blueprint, request, jsonify, make_response
from functools import wraps
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
import re

class APIVersion:
    """Represents an API version with its lifecycle"""
    
    def __init__(self, version: str, released: datetime = None):
        self.version = version
        self.released = released or datetime.now()
        self.deprecated_at: Optional[datetime] = None
        self.sunset_at: Optional[datetime] = None
        self.successor: Optional[str] = None
        
    def deprecate(self, sunset_days: int = 180, successor: str = None):
        """Mark version as deprecated with sunset date"""
        self.deprecated_at = datetime.now()
        self.sunset_at = self.deprecated_at + timedelta(days=sunset_days)
        self.successor = successor
        
    @property
    def is_deprecated(self) -> bool:
        return self.deprecated_at is not None
    
    @property
    def is_sunset(self) -> bool:
        return self.sunset_at and datetime.now() > self.sunset_at

class APIVersionManager:
    """Manages multiple API versions with compatibility"""
    
    def __init__(self, app: Flask = None, default_version: str = 'v1'):
        self.app = app
        self.versions: Dict[str, APIVersion] = {}
        self.blueprints: Dict[str, Blueprint] = {}
        self.transformers: Dict[tuple, Callable] = {}
        self.default_version = default_version
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize the version manager with Flask app"""
        self.app = app
        app.before_request(self._before_request)
        app.after_request(self._after_request)
        
        # Add version extractor
        app.config['API_VERSION_EXTRACTOR'] = self._extract_version
        
    def register_version(self, 
                        version: str, 
                        blueprint: Blueprint,
                        deprecated: bool = False,
                        sunset_days: int = 180,
                        successor: str = None):
        """Register a new API version"""
        
        # Create version object
        api_version = APIVersion(version)
        if deprecated:
            api_version.deprecate(sunset_days, successor)
        
        # Store version and blueprint
        self.versions[version] = api_version
        self.blueprints[version] = blueprint
        
        # Register blueprint with versioned URL prefix
        if self.app:
            self.app.register_blueprint(
                blueprint,
                url_prefix=f'/api/{version}'
            )
    
    def register_transformer(self, 
                            from_version: str, 
                            to_version: str, 
                            transformer: Callable):
        """Register a transformation function between versions"""
        self.transformers[(from_version, to_version)] = transformer
    
    def _extract_version(self, path: str) -> Optional[str]:
        """Extract version from URL path"""
        match = re.match(r'/api/(v\d+)', path)
        return match.group(1) if match else None
    
    def _before_request(self):
        """Check version validity before processing request"""
        version = self._extract_version(request.path)
        
        if version:
            # Store version in request context
            request.api_version = version
            
            # Only check lifecycle if version is registered
            if version in self.versions:
                api_version = self.versions[version]
                
                # Block sunset versions
                if api_version.is_sunset:
                    return jsonify({
                        'error': 'API version is no longer supported',
                        'version': version,
                        'sunset_date': api_version.sunset_at.isoformat(),
                        'successor': api_version.successor
                    }), 410  # Gone
    
    def _after_request(self, response):
        """Add version headers to response"""
        version = getattr(request, 'api_version', None)
        
        if version and version in self.versions:
            api_version = self.versions[version]
            
            # Add deprecation headers
            if api_version.is_deprecated:
                response.headers['Sunset'] = api_version.sunset_at.isoformat()
                response.headers['Deprecation'] = 'true'
                if api_version.successor:
                    response.headers['Link'] = (
                        f'</api/{api_version.successor}>; '
                        f'rel="successor-version"'
                    )
            
            # Add version header
            response.headers['API-Version'] = version
        
        return response