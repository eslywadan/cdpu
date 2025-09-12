# src/common/tenancy/models.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import uuid

class TenantIsolationLevel(Enum):
    """Tenant isolation levels"""
    LOGICAL = "logical"          # Shared database with tenant_id
    SCHEMA = "schema"            # Database schema per tenant
    DATABASE = "database"        # Separate database per tenant
    NAMESPACE = "namespace"      # Kubernetes namespace isolation

class TenantStatus(Enum):
    """Tenant lifecycle status"""
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETING = "deleting"
    DELETED = "deleted"

@dataclass
class TenantQuota:
    """Resource quotas for tenant"""
    max_users: int = 100
    max_storage_gb: int = 100
    max_cpu_cores: int = 4
    max_memory_gb: int = 16
    max_api_calls_per_day: int = 100000
    max_tasks_per_day: int = 1000
    max_databases: int = 5
    
    def to_k8s_resource_quota(self) -> Dict:
        """Convert to Kubernetes ResourceQuota"""
        return {
            "hard": {
                "requests.cpu": str(self.max_cpu_cores),
                "requests.memory": f"{self.max_memory_gb}Gi",
                "requests.storage": f"{self.max_storage_gb}Gi",
                "persistentvolumeclaims": str(self.max_databases),
                "pods": "50",
                "services": "10"
            }
        }

@dataclass
class Tenant:
    """Tenant model"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    display_name: str = ""
    description: str = ""
    isolation_level: TenantIsolationLevel = TenantIsolationLevel.LOGICAL
    status: TenantStatus = TenantStatus.PROVISIONING
    quota: TenantQuota = field(default_factory=TenantQuota)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Computed properties
    @property
    def namespace(self) -> str:
        """Kubernetes namespace for tenant"""
        return f"tenant-{self.name.lower()}"
    
    @property
    def database_schema(self) -> str:
        """Database schema for tenant"""
        return f"tenant_{self.name.lower()}"
    
    @property
    def redis_prefix(self) -> str:
        """Redis key prefix for tenant"""
        return f"tenant:{self.id}"