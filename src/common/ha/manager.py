# src/common/ha/manager.py
from typing import Dict, List, Optional, Callable
from enum import Enum
import asyncio
import redis
import psycopg2
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class NodeRole(Enum):
    """Node roles in HA setup"""
    PRIMARY = "primary"
    STANDBY = "standby"
    OBSERVER = "observer"

class NodeStatus(Enum):
    """Node health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    RECOVERING = "recovering"

class HANode:
    """Represents a node in HA cluster"""
    
    def __init__(self,
                 node_id: str,
                 role: NodeRole,
                 endpoint: str):
        
        self.node_id = node_id
        self.role = role
        self.endpoint = endpoint
        self.status = NodeStatus.HEALTHY
        self.last_heartbeat = datetime.utcnow()
        self.metadata = {}
    
    @property
    def is_healthy(self) -> bool:
        """Check if node is healthy"""
        return self.status == NodeStatus.HEALTHY
    
    @property
    def is_primary(self) -> bool:
        """Check if node is primary"""
        return self.role == NodeRole.PRIMARY

class HAManager:
    """High Availability Manager"""
    
    def __init__(self,
                 node_id: str,
                 redis_client: redis.Redis,
                 db_config: Dict):
        
        self.node_id = node_id
        self.redis = redis_client
        self.db_config = db_config
        
        self.nodes: Dict[str, HANode] = {}
        self.current_role = NodeRole.STANDBY
        self.failover_handlers: List[Callable] = []
        
        self.heartbeat_interval = 5  # seconds
        self.failover_timeout = 30  # seconds
        self.election_timeout = 10  # seconds
        
        self._running = False
        self._tasks = []
    
    async def start(self):
        """Start HA manager"""
        
        self._running = True
        
        # Start background tasks
        self._tasks = [
            asyncio.create_task(self._heartbeat_loop()),
            asyncio.create_task(self._monitor_loop()),
            asyncio.create_task(self._health_check_loop())
        ]
        
        # Register node
        await self._register_node()
        
        # Perform initial election
        await self._perform_election()
        
        logger.info(f"HA Manager started for node {self.node_id}")
    
    async def stop(self):
        """Stop HA manager"""
        
        self._running = False
        
        # Cancel background tasks
        for task in self._tasks:
            task.cancel()
        
        await asyncio.gather(*self._tasks, return_exceptions=True)
        
        # Unregister node
        await self._unregister_node()
        
        logger.info(f"HA Manager stopped for node {self.node_id}")
    
    async def _register_node(self):
        """Register node in cluster"""
        
        node_data = {
            'node_id': self.node_id,
            'role': self.current_role.value,
            'endpoint': f"http://{self.node_id}:8080",
            'status': NodeStatus.HEALTHY.value,
            'registered_at': datetime.utcnow().isoformat()
        }
        
        # Store in Redis with expiry
        self.redis.hset(
            'ha:nodes',
            self.node_id,
            json.dumps(node_data)
        )
        
        self.redis.expire('ha:nodes', 3600)  # 1 hour
        
        logger.info(f"Node {self.node_id} registered")
    
    async def _unregister_node(self):
        """Unregister node from cluster"""
        
        self.redis.hdel('ha:nodes', self.node_id)
        logger.info(f"Node {self.node_id} unregistered")
    
    async def _heartbeat_loop(self):
        """Send heartbeats to cluster"""
        
        while self._running:
            try:
                # Send heartbeat
                heartbeat_data = {
                    'node_id': self.node_id,
                    'role': self.current_role.value,
                    'status': NodeStatus.HEALTHY.value,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                self.redis.setex(
                    f'ha:heartbeat:{self.node_id}',
                    self.heartbeat_interval * 3,
                    json.dumps(heartbeat_data)
                )
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(1)
    
    async def _monitor_loop(self):
        """Monitor cluster nodes"""
        
        while self._running:
            try:
                # Get all nodes
                nodes_data = self.redis.hgetall('ha:nodes')
                
                for node_id, node_json in nodes_data.items():
                    if node_id == self.node_id:
                        continue
                    
                    node_data = json.loads(node_json)
                    
                    # Check heartbeat
                    heartbeat = self.redis.get(f'ha:heartbeat:{node_id}')
                    
                    if heartbeat:
                        heartbeat_data = json.loads(heartbeat)
                        last_heartbeat = datetime.fromisoformat(
                            heartbeat_data['timestamp']
                        )
                        
                        # Check if node is healthy
                        if (datetime.utcnow() - last_heartbeat).total_seconds() > self.failover_timeout:
                            await self._handle_node_failure(node_id)
                    else:
                        await self._handle_node_failure(node_id)
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(1)
    
    async def _health_check_loop(self):
        """Perform health checks"""
        
        while self._running:
            try:
                # Check database health
                db_healthy = await self._check_database_health()
                
                # Check Redis health
                redis_healthy = await self._check_redis_health()
                
                # Check service health
                service_healthy = await self._check_service_health()
                
                # Update node status
                if all([db_healthy, redis_healthy, service_healthy]):
                    self.status = NodeStatus.HEALTHY
                else:
                    self.status = NodeStatus.DEGRADED
                    
                    # Trigger failover if primary is degraded
                    if self.current_role == NodeRole.PRIMARY:
                        await self._initiate_failover()
                
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Health check error: {e}")
                self.status = NodeStatus.FAILED
                await asyncio.sleep(1)
    
    async def _check_database_health(self) -> bool:
        """Check database health"""
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def _check_redis_health(self) -> bool:
        """Check Redis health"""
        
        try:
            self.redis.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    async def _check_service_health(self) -> bool:
        """Check service health"""
        
        try:
            # Implement service-specific health checks
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://localhost:8080/health"
                ) as response:
                    return response.status == 200
                    
        except Exception as e:
            logger.error(f"Service health check failed: {e}")
            return False
    
    async def _perform_election(self):
        """Perform leader election"""
        
        logger.info("Starting leader election")
        
        # Try to acquire leader lock
        lock_key = 'ha:leader_lock'
        lock_value = self.node_id
        
        # Use Redis SET with NX and EX for atomic lock acquisition
        acquired = self.redis.set(
            lock_key,
            lock_value,
            nx=True,  # Only set if not exists
            ex=self.election_timeout
        )
        
        if acquired:
            # Became leader
            await self._become_primary()
        else:
            # Check current leader
            current_leader = self.redis.get(lock_key)
            
            if current_leader:
                logger.info(f"Current leader is {current_leader}")
                await self._become_standby()
            else:
                # Retry election
                await asyncio.sleep(1)
                await self._perform_election()
    
    async def _become_primary(self):
        """Transition to primary role"""
        
        logger.info(f"Node {self.node_id} becoming PRIMARY")
        
        self.current_role = NodeRole.PRIMARY
        
        # Update node info
        await self._register_node()
        
        # Execute failover handlers
        for handler in self.failover_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler('promote')
                else:
                    handler('promote')
            except Exception as e:
                logger.error(f"Failover handler error: {e}")
        
        # Start leader lease renewal
        asyncio.create_task(self._renew_leader_lease())
    
    async def _become_standby(self):
        """Transition to standby role"""
        
        logger.info(f"Node {self.node_id} becoming STANDBY")
        
        self.current_role = NodeRole.STANDBY
        
        # Update node info
        await self._register_node()
        
        # Execute failover handlers
        for handler in self.failover_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler('demote')
                else:
                    handler('demote')
            except Exception as e:
                logger.error(f"Failover handler error: {e}")
    
    async def _renew_leader_lease(self):
        """Renew leader lease"""
        
        while self._running and self.current_role == NodeRole.PRIMARY:
            try:
                # Renew lease
                self.redis.expire('ha:leader_lock', self.election_timeout)
                
                await asyncio.sleep(self.election_timeout // 2)
                
            except Exception as e:
                logger.error(f"Lease renewal error: {e}")
                # Lost leadership
                await self._become_standby()
                break
    
    async def _handle_node_failure(self, failed_node_id: str):
        """Handle node failure"""
        
        logger.warning(f"Node {failed_node_id} failed")
        
        # Check if failed node was primary
        node_data = self.redis.hget('ha:nodes', failed_node_id)
        
        if node_data:
            node_info = json.loads(node_data)
            
            if node_info['role'] == NodeRole.PRIMARY.value:
                # Primary failed, initiate election
                await self._perform_election()
        
        # Remove failed node
        self.redis.hdel('ha:nodes', failed_node_id)
        self.redis.delete(f'ha:heartbeat:{failed_node_id}')
    
    def register_failover_handler(self, handler: Callable):
        """Register failover handler"""
        self.failover_handlers.append(handler)