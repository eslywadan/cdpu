# src/common/messaging/integration.py
from typing import Dict, List, Any
import asyncio
from enum import Enum

class ServiceEvent(Enum):
    """Standard service events"""
    # Account events
    ACCOUNT_CREATED = "account.created"
    ACCOUNT_UPDATED = "account.updated"
    ACCOUNT_DELETED = "account.deleted"
    ACCOUNT_LOGIN = "account.login"
    
    # Task events
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    
    # Resource events
    RESOURCE_ALLOCATED = "resource.allocated"
    RESOURCE_RELEASED = "resource.released"
    RESOURCE_SCALED = "resource.scaled"
    
    # Config events
    CONFIG_UPDATED = "config.updated"
    CONFIG_DEPLOYED = "config.deployed"

class ServiceMessageBus:
    """High-level message bus for services"""
    
    def __init__(self, redis_streams: RedisStreamBus):
        self.bus = redis_streams
        self.service_name = None
        self.event_handlers: Dict[ServiceEvent, List[Callable]] = {}
    
    def initialize(self, service_name: str):
        """Initialize for a specific service"""
        self.service_name = service_name
        
        # Subscribe to relevant events
        self._setup_subscriptions()
    
    def emit_event(self, 
                   event_type: ServiceEvent,
                   data: Dict[str, Any],
                   priority: MessagePriority = MessagePriority.NORMAL):
        """Emit a service event"""
        
        message = Message.create(
            topic=event_type.value,
            event_type=event_type.value,
            payload={
                'service': self.service_name,
                'data': data
            },
            priority=priority
        )
        
        return self.bus.publish(message)
    
    def on_event(self, event_type: ServiceEvent, handler: Callable):
        """Register event handler"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        
        # Subscribe to event stream
        self.bus.subscribe(
            topic=event_type.value,
            group=f"{self.service_name}-group",
            consumer=f"{self.service_name}-{os.getpid()}",
            handler=self._create_handler_wrapper(event_type, handler)
        )
    
    def _create_handler_wrapper(self, 
                               event_type: ServiceEvent,
                               handler: Callable) -> Callable:
        """Create wrapper for event handler"""
        
        async def wrapper(message: Message):
            try:
                # Extract service data
                service_data = message.payload.get('data', {})
                
                # Call handler
                if asyncio.iscoroutinefunction(handler):
                    await handler(service_data)
                else:
                    handler(service_data)
                    
                # Log event processing
                logger.info(f"Processed {event_type.value} from {message.payload.get('service')}")
                
            except Exception as e:
                logger.error(f"Handler error for {event_type.value}: {e}")
                raise
        
        return wrapper
    
    def _setup_subscriptions(self):
        """Setup default subscriptions based on service"""
        
        # Service-specific subscriptions
        subscriptions = {
            'dpam': [
                ServiceEvent.ACCOUNT_CREATED,
                ServiceEvent.ACCOUNT_UPDATED,
                ServiceEvent.CONFIG_UPDATED
            ],
            'dptm': [
                ServiceEvent.TASK_CREATED,
                ServiceEvent.RESOURCE_ALLOCATED,
                ServiceEvent.CONFIG_UPDATED
            ],
            'dpem': [
                # Subscribe to all events for logging
                event for event in ServiceEvent
            ],
            'dprm': [
                ServiceEvent.RESOURCE_ALLOCATED,
                ServiceEvent.TASK_STARTED,
                ServiceEvent.TASK_COMPLETED
            ]
        }
        
        # Auto-subscribe to relevant events
        if self.service_name in subscriptions:
            for event_type in subscriptions[self.service_name]:
                # Create default handler
                self.on_event(event_type, self._default_event_handler)
    
    async def _default_event_handler(self, data: Dict):
        """Default event handler for logging"""
        logger.info(f"{self.service_name} received event: {data}")