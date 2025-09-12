
# src/common/messaging/event_sourcing.py
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json
from datetime import datetime

@dataclass
class Event:
    """Base event for event sourcing"""
    aggregate_id: str
    aggregate_type: str
    event_type: str
    event_data: Dict[Any, Any]
    event_version: int
    occurred_at: datetime
    user_id: Optional[str] = None
    
    def to_stream_data(self) -> Dict:
        """Convert to Redis stream format"""
        return {
            'aggregate_id': self.aggregate_id,
            'aggregate_type': self.aggregate_type,
            'event_type': self.event_type,
            'event_data': json.dumps(self.event_data),
            'event_version': self.event_version,
            'occurred_at': self.occurred_at.isoformat(),
            'user_id': self.user_id or 'system'
        }

class EventStore:
    """Event store using Redis Streams"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.stream_prefix = "events"
    
    def append_event(self, event: Event) -> str:
        """Append event to stream"""
        stream_key = f"{self.stream_prefix}:{event.aggregate_type}:{event.aggregate_id}"
        
        # Add event to stream
        event_id = self.redis.xadd(stream_key, event.to_stream_data())
        
        # Update snapshot marker
        self._update_snapshot_marker(event.aggregate_id, event.aggregate_type)
        
        return event_id
    
    def get_events(self, 
                   aggregate_id: str,
                   aggregate_type: str,
                   from_version: int = 0) -> List[Event]:
        """Get events for an aggregate"""
        
        stream_key = f"{self.stream_prefix}:{aggregate_type}:{aggregate_id}"
        
        # Read all events from stream
        events_data = self.redis.xrange(stream_key)
        
        events = []
        for event_id, data in events_data:
            if int(data['event_version']) >= from_version:
                events.append(self._parse_event(data))
        
        return events
    
    def _parse_event(self, data: Dict) -> Event:
        """Parse event from stream data"""
        return Event(
            aggregate_id=data['aggregate_id'],
            aggregate_type=data['aggregate_type'],
            event_type=data['event_type'],
            event_data=json.loads(data['event_data']),
            event_version=int(data['event_version']),
            occurred_at=datetime.fromisoformat(data['occurred_at']),
            user_id=data.get('user_id')
        )
    
    def _update_snapshot_marker(self, aggregate_id: str, aggregate_type: str):
        """Update snapshot marker for aggregate"""
        marker_key = f"snapshot_marker:{aggregate_type}:{aggregate_id}"
        self.redis.set(marker_key, datetime.utcnow().isoformat(), ex=86400)

class EventProjector:
    """Project events to read models"""
    
    def __init__(self, event_store: EventStore, redis_client: redis.Redis):
        self.event_store = event_store
        self.redis = redis_client
        self.projections = {}
    
    def register_projection(self, 
                           event_type: str,
                           projection_func: Callable[[Event], None]):
        """Register a projection function for event type"""
        if event_type not in self.projections:
            self.projections[event_type] = []
        self.projections[event_type].append(projection_func)
    
    async def project_event(self, event: Event):
        """Project event to read models"""
        if event.event_type in self.projections:
            for projection_func in self.projections[event.event_type]:
                try:
                    if asyncio.iscoroutinefunction(projection_func):
                        await projection_func(event)
                    else:
                        projection_func(event)
                except Exception as e:
                    logger.error(f"Projection failed for {event.event_type}: {e}")