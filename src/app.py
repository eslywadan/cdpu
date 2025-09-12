# src/app.py (Updated)
from flask import Flask
from common.api.versioning import APIVersionManager
from common.api.deprecation import DeprecationManager
from common.api.metrics import VersionMetrics, metrics_middleware
from common.api.diagnostics import VersionDiagnostics, diagnostics_bp
import redis
from sqlalchemy import create_engine

def create_app():
    app = Flask(__name__)
    
    # Initialize Redis
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    
    # Initialize database
    db_engine = create_engine('postgresql://user:pass@localhost/cdpu')
    
    # Initialize managers
    version_manager = APIVersionManager(app)
    deprecation_manager = DeprecationManager(redis_client, db_engine)
    metrics_manager = VersionMetrics(redis_client)
    
    # Initialize diagnostics
    diagnostics = VersionDiagnostics(
        version_manager,
        metrics_manager,
        deprecation_manager
    )
    
    # Set global diagnostics reference
    from common.api import diagnostics as diag_module
    diag_module.diagnostics = diagnostics
    
    # Register blueprints
    app.register_blueprint(diagnostics_bp, url_prefix='/api')
    
    # Apply metrics middleware
    for rule in app.url_map.iter_rules():
        if rule.endpoint:
            view_func = app.view_functions.get(rule.endpoint)
            if view_func:
                app.view_functions[rule.endpoint] = metrics_middleware(version_manager)(view_func)
    
    # Register versions with deprecation
    from dpam.api.v1 import dpam_v1
    from dpam.api.v2 import dpam_v2
    
    # Deprecate v1
    version_manager.register_version('v1', dpam_v1)
    deprecation_manager.deprecate_version(
        version='v1',
        sunset_days=180,
        successor='v2',
        reason='Version 1 is being phased out in favor of improved v2',
        affected_endpoints=['/api/v1/accounts', '/api/v1/users']
    )
    
    # Active v2
    version_manager.register_version('v2', dpam_v2)
    
    # Schedule periodic tasks
    from apscheduler.schedulers.background import BackgroundScheduler
    
    scheduler = BackgroundScheduler()
    
    # Check for sunset warnings every hour
    scheduler.add_job(
        func=deprecation_manager.check_sunset_warnings,
        trigger='interval',
        hours=1
    )
    
    # Update metrics every minute
    scheduler.add_job(
        func=lambda: update_version_metrics(version_manager, metrics_manager),
        trigger='interval',
        minutes=1
    )
    
    scheduler.start()
    
    return app

def update_version_metrics(version_manager, metrics_manager):
    """Update Prometheus metrics"""
    from common.api.metrics import api_active_versions, api_sunset_days_remaining
    
    # Update active versions count
    active_count = sum(
        1 for v in version_manager.versions.values()
        if not v.is_sunset
    )
    api_active_versions.set(active_count)
    
    # Update sunset days remaining
    for version, info in version_manager.versions.items():
        if info.is_deprecated and not info.is_sunset:
            days_remaining = (info.sunset_at - datetime.now()).days
            api_sunset_days_remaining.labels(version=version).set(days_remaining)