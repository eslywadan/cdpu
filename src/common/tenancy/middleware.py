# src/common/tenancy/middleware.py
from flask import request, g, abort
from functools import wraps
from typing import Optional, Callable
import jwt
import re

class TenantMiddleware:
    """Middleware for tenant context injection"""
    
    def __init__(self, app=None, tenant_manager: TenantManager = None):
        self.app = app
        self.tenant_manager = tenant_manager
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize middleware with Flask app"""
        self.app = app
        app.before_request(self.before_request)
        app.teardown_appcontext(self.teardown)
    
    def before_request(self):
        """Extract and validate tenant context"""
        
        # Extract tenant from various sources
        tenant_id = self._extract_tenant_id()
        
        if tenant_id:
            # Load tenant
            tenant = self.tenant_manager.get_tenant(tenant_id)
            
            if not tenant:
                abort(404, f"Tenant {tenant_id} not found")
            
            if tenant.status != TenantStatus.ACTIVE:
                abort(403, f"Tenant {tenant_id} is not active")
            
            # Set tenant context
            g.tenant = tenant
            g.tenant_id = tenant_id
            
            # Set database schema if needed
            if tenant.isolation_level == TenantIsolationLevel.SCHEMA:
                self._set_database_schema(tenant.database_schema)
    
    def teardown(self, exception=None):
        """Cleanup tenant context"""
        g.pop('tenant', None)
        g.pop('tenant_id', None)
    
    def _extract_tenant_id(self) -> Optional[str]:
        """Extract tenant ID from request"""
        
        # 1. From subdomain (e.g., tenant1.app.com)
        host = request.host.lower()
        subdomain_match = re.match(r'^([a-z0-9-]+)\.', host)
        if subdomain_match and subdomain_match.group(1) != 'www':
            return subdomain_match.group(1)
        
        # 2. From header
        if 'X-Tenant-ID' in request.headers:
            return request.headers['X-Tenant-ID']
        
        # 3. From JWT token
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                payload = jwt.decode(token, 
                                   self.app.config['SECRET_KEY'],
                                   algorithms=['HS256'])
                return payload.get('tenant_id')
            except jwt.InvalidTokenError:
                pass
        
        # 4. From query parameter (least preferred)
        return request.args.get('tenant_id')
    
    def _set_database_schema(self, schema: str):
        """Set database schema for tenant"""
        from flask_sqlalchemy import SQLAlchemy
        
        if hasattr(self.app, 'db'):
            db: SQLAlchemy = self.app.db
            
            # Set search path for PostgreSQL
            with db.engine.connect() as conn:
                conn.execute(text(f"SET search_path TO {schema}, public"))

def tenant_required(f: Callable) -> Callable:
    """Decorator to require tenant context"""
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'tenant'):
            abort(400, "Tenant context required")
        return f(*args, **kwargs)
    
    return decorated_function

def tenant_isolation(isolation_level: TenantIsolationLevel = None):
    """Decorator to enforce tenant isolation level"""
    
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'tenant'):
                abort(400, "Tenant context required")
            
            if isolation_level and g.tenant.isolation_level != isolation_level:
                abort(403, f"This operation requires {isolation_level.value} isolation")
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator