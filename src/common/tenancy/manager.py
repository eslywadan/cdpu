# src/common/tenancy/manager.py
from typing import Dict, List, Optional
import logging
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.orm import sessionmaker
from kubernetes import client, config
import redis
import asyncio

logger = logging.getLogger(__name__)

class TenantManager:
    """Manages tenant lifecycle and isolation"""
    
    def __init__(self, 
                 db_url: str,
                 redis_client: redis.Redis,
                 k8s_config: Optional[Dict] = None):
        
        self.db_engine = create_engine(db_url)
        self.redis = redis_client
        self.k8s_config = k8s_config
        
        if k8s_config:
            config.load_kube_config()
            self.k8s_v1 = client.CoreV1Api()
            self.k8s_apps = client.AppsV1Api()
        
        self.tenants: Dict[str, Tenant] = {}
    
    async def create_tenant(self, 
                           name: str,
                           display_name: str,
                           isolation_level: TenantIsolationLevel,
                           quota: Optional[TenantQuota] = None) -> Tenant:
        """Create a new tenant"""
        
        # Create tenant object
        tenant = Tenant(
            name=name,
            display_name=display_name,
            isolation_level=isolation_level,
            quota=quota or TenantQuota()
        )
        
        try:
            # Provision based on isolation level
            if isolation_level == TenantIsolationLevel.LOGICAL:
                await self._provision_logical_tenant(tenant)
            elif isolation_level == TenantIsolationLevel.SCHEMA:
                await self._provision_schema_tenant(tenant)
            elif isolation_level == TenantIsolationLevel.DATABASE:
                await self._provision_database_tenant(tenant)
            elif isolation_level == TenantIsolationLevel.NAMESPACE:
                await self._provision_namespace_tenant(tenant)
            
            # Update status
            tenant.status = TenantStatus.ACTIVE
            
            # Store tenant
            self.tenants[tenant.id] = tenant
            await self._persist_tenant(tenant)
            
            logger.info(f"Created tenant: {tenant.name}")
            return tenant
            
        except Exception as e:
            logger.error(f"Failed to create tenant {name}: {e}")
            tenant.status = TenantStatus.DELETED
            raise
    
    async def _provision_logical_tenant(self, tenant: Tenant):
        """Provision logical tenant (shared resources)"""
        
        # Create tenant record in shared database
        with self.db_engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO tenants (id, name, display_name, created_at)
                VALUES (:id, :name, :display_name, :created_at)
            """), {
                'id': tenant.id,
                'name': tenant.name,
                'display_name': tenant.display_name,
                'created_at': tenant.created_at
            })
            conn.commit()
        
        # Setup Redis namespace
        self.redis.set(f"{tenant.redis_prefix}:info", 
                      json.dumps(tenant.__dict__, default=str))
    
    async def _provision_schema_tenant(self, tenant: Tenant):
        """Provision schema-isolated tenant"""
        
        schema_name = tenant.database_schema
        
        with self.db_engine.connect() as conn:
            # Create schema
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
            
            # Create tables in schema
            metadata = MetaData(schema=schema_name)
            
            # Define tables
            from sqlalchemy import Table, Column, String, DateTime, Integer
            
            accounts_table = Table('accounts', metadata,
                Column('id', Integer, primary_key=True),
                Column('client_id', String(255)),
                Column('tenant_id', String(255)),
                Column('created_at', DateTime),
                schema=schema_name
            )
            
            # Create all tables
            metadata.create_all(self.db_engine)
            
            conn.commit()
        
        logger.info(f"Created schema {schema_name} for tenant {tenant.name}")
    
    async def _provision_database_tenant(self, tenant: Tenant):
        """Provision database-isolated tenant"""
        
        db_name = f"tenant_{tenant.name.lower()}"
        
        # Create database (PostgreSQL example)
        with self.db_engine.connect() as conn:
            conn.connection.set_isolation_level(0)  # AUTOCOMMIT
            conn.execute(text(f"CREATE DATABASE {db_name}"))
        
        # Create tenant-specific connection
        tenant_db_url = self.db_engine.url.set(database=db_name)
        tenant_engine = create_engine(tenant_db_url)
        
        # Initialize tenant database
        from alembic import command
        from alembic.config import Config
        
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", str(tenant_db_url))
        command.upgrade(alembic_cfg, "head")
        
        logger.info(f"Created database {db_name} for tenant {tenant.name}")
    
    async def _provision_namespace_tenant(self, tenant: Tenant):
        """Provision Kubernetes namespace-isolated tenant"""
        
        namespace_name = tenant.namespace
        
        # Create namespace
        namespace = client.V1Namespace(
            metadata=client.V1ObjectMeta(
                name=namespace_name,
                labels={
                    "tenant-id": tenant.id,
                    "tenant-name": tenant.name,
                    "managed-by": "cdpu"
                }
            )
        )
        
        self.k8s_v1.create_namespace(namespace)
        
        # Create ResourceQuota
        resource_quota = client.V1ResourceQuota(
            metadata=client.V1ObjectMeta(
                name=f"{tenant.name}-quota",
                namespace=namespace_name
            ),
            spec=client.V1ResourceQuotaSpec(
                hard=tenant.quota.to_k8s_resource_quota()["hard"]
            )
        )
        
        self.k8s_v1.create_namespaced_resource_quota(
            namespace=namespace_name,
            body=resource_quota
        )
        
        # Create NetworkPolicy for isolation
        network_policy = client.V1NetworkPolicy(
            metadata=client.V1ObjectMeta(
                name="tenant-isolation",
                namespace=namespace_name
            ),
            spec=client.V1NetworkPolicySpec(
                pod_selector=client.V1LabelSelector(),
                policy_types=["Ingress", "Egress"],
                ingress=[
                    client.V1NetworkPolicyIngressRule(
                        from_=[
                            client.V1NetworkPolicyPeer(
                                namespace_selector=client.V1LabelSelector(
                                    match_labels={"name": namespace_name}
                                )
                            )
                        ]
                    )
                ],
                egress=[
                    client.V1NetworkPolicyEgressRule(
                        to=[
                            client.V1NetworkPolicyPeer(
                                namespace_selector=client.V1LabelSelector(
                                    match_labels={"name": namespace_name}
                                )
                            )
                        ]
                    )
                ]
            )
        )
        
        self.k8s_v1.create_namespaced_network_policy(
            namespace=namespace_name,
            body=network_policy
        )
        
        logger.info(f"Created namespace {namespace_name} for tenant {tenant.name}")
    
    async def delete_tenant(self, tenant_id: str):
        """Delete a tenant"""
        
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        tenant.status = TenantStatus.DELETING
        
        try:
            # Cleanup based on isolation level
            if tenant.isolation_level == TenantIsolationLevel.NAMESPACE:
                self.k8s_v1.delete_namespace(tenant.namespace)
            elif tenant.isolation_level == TenantIsolationLevel.SCHEMA:
                with self.db_engine.connect() as conn:
                    conn.execute(text(f"DROP SCHEMA {tenant.database_schema} CASCADE"))
                    conn.commit()
            elif tenant.isolation_level == TenantIsolationLevel.DATABASE:
                with self.db_engine.connect() as conn:
                    conn.connection.set_isolation_level(0)
                    conn.execute(text(f"DROP DATABASE tenant_{tenant.name.lower()}"))
            
            # Cleanup Redis
            keys = self.redis.keys(f"{tenant.redis_prefix}:*")
            if keys:
                self.redis.delete(*keys)
            
            tenant.status = TenantStatus.DELETED
            del self.tenants[tenant_id]
            
            logger.info(f"Deleted tenant: {tenant.name}")
            
        except Exception as e:
            logger.error(f"Failed to delete tenant {tenant_id}: {e}")
            raise