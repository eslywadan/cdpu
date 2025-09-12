# src/common/tenancy/db_router.py
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool
from typing import Dict, Optional
import threading

class TenantDatabaseRouter:
    """Routes database operations to tenant-specific databases/schemas"""
    
    def __init__(self, base_db_url: str):
        self.base_db_url = base_db_url
        self.engines: Dict[str, Any] = {}
        self.sessions: Dict[str, sessionmaker] = {}
        self._local = threading.local()
    
    def get_engine(self, tenant: Tenant):
        """Get database engine for tenant"""
        
        cache_key = f"{tenant.id}:{tenant.isolation_level.value}"
        
        if cache_key not in self.engines:
            if tenant.isolation_level == TenantIsolationLevel.DATABASE:
                # Separate database
                db_url = self.base_db_url.replace(
                    '/cdpu',  # Default database
                    f'/tenant_{tenant.name.lower()}'
                )
                engine = create_engine(db_url, poolclass=NullPool)
                
            elif tenant.isolation_level == TenantIsolationLevel.SCHEMA:
                # Same database, different schema
                engine = create_engine(self.base_db_url)
                
                # Set schema on connect
                @event.listens_for(engine, "connect")
                def set_schema(dbapi_conn, connection_record):
                    with dbapi_conn.cursor() as cursor:
                        cursor.execute(f"SET search_path TO {tenant.database_schema}")
                
            else:  # LOGICAL
                # Shared database
                engine = create_engine(self.base_db_url)
            
            self.engines[cache_key] = engine
        
        return self.engines[cache_key]
    
    def get_session(self, tenant: Tenant) -> Session:
        """Get database session for tenant"""
        
        cache_key = f"{tenant.id}:{tenant.isolation_level.value}"
        
        if cache_key not in self.sessions:
            engine = self.get_engine(tenant)
            self.sessions[cache_key] = sessionmaker(bind=engine)
        
        session = self.sessions[cache_key]()
        
        # Add tenant filter for logical isolation
        if tenant.isolation_level == TenantIsolationLevel.LOGICAL:
            @event.listens_for(session, "after_bulk_insert")
            @event.listens_for(session, "after_bulk_update")
            def add_tenant_id(mapper, connection, target):
                """Automatically add tenant_id to queries"""
                if hasattr(target, 'tenant_id'):
                    target.tenant_id = tenant.id
        
        return session

# Usage in models
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, DateTime

Base = declarative_base()

class TenantAwareModel(Base):
    """Base model for tenant-aware tables"""
    __abstract__ = True
    
    tenant_id = Column(String(255), nullable=True, index=True)
    
    @classmethod
    def query_for_tenant(cls, session: Session, tenant_id: str):
        """Query filtered by tenant"""
        return session.query(cls).filter_by(tenant_id=tenant_id)