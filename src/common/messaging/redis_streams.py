# src/common/messaging/redis_streams.py
import redis
import json
import asyncio
import uuid
from typing import Dict, List, Any, Callable, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class MessagePriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3

@dataclass
class Message:
    """Standard message format"""
    id: str
    topic: str
    event_type: str
    payload: Dict[Any, Any]
    metadata: Dict[str, Any]
    timestamp: str
    priority: MessagePriority = MessagePriority.NORMAL
    
    @classmethod
    def create(cls, topic: str, event_type: str, payload: Dict, 
               priority: MessagePriority = MessagePriority.NORMAL):
        """Create a new message"""
        return cls(
            id=str(uuid.uuid4()),
            topic=topic,
            event_type=event_type,
            payload=payload,
            metadata={
                'source': 'cdpu',
                'version': '1.0'
            },
            timestamp=datetime.utcnow().isoformat(),
            priority=priority
        )
    
    def to_dict(self) -> Dict:
        """Convert message to dictionary"""
        data = asdict(self)
        data['priority'] = self.priority.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict):
        """Create message from dictionary"""
        data['priority'] = MessagePriority(data.get('priority', 1))
        return cls(**data)

class RedisStreamBus:
    """Redis Streams based message bus"""
    
    def __init__(self, 
                 host: str = 'localhost',
                 port: int = 6379,
                 db: int = 0,
                 password: str = None,
                 max_retries: int = 3,
                 retry_delay: int = 5):
        
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True
        )
        
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.consumer_groups: Dict[str, str] = {}
        self.handlers: Dict[str, List[Callable]] = {}
        self._running = False
        
        # Stream configuration
        self.stream_max_len = 10000  # Max messages per stream
        self.block_ms = 1000  # Block time for XREAD
        
    def publish(self, message: Message) -> str:
        """Publish message to stream"""
        stream_key = f"stream:{message.topic}"
        
        try:
            # Add to stream with automatic ID
            message_id = self.redis_client.xadd(
                stream_key,
                message.to_dict(),
                maxlen=self.stream_max_len,
                approximate=True
            )
            
            logger.info(f"Published message {message_id} to {stream_key}")
            return message_id
            
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            raise
    
    def batch_publish(self, messages: List[Message]) -> List[str]:
        """Publish multiple messages in batch"""
        pipeline = self.redis_client.pipeline()
        message_ids = []
        
        for message in messages:
            stream_key = f"stream:{message.topic}"
            pipeline.xadd(
                stream_key,
                message.to_dict(),
                maxlen=self.stream_max_len,
                approximate=True
            )
        
        results = pipeline.execute()
        return results
    
    def subscribe(self, 
                  topic: str, 
                  group: str,
                  consumer: str,
                  handler: Callable[[Message], None],
                  auto_ack: bool = True):
        """Subscribe to a topic with consumer group"""
        
        stream_key = f"stream:{topic}"
        
        # Create consumer group if not exists
        try:
            self.redis_client.xgroup_create(
                stream_key, 
                group, 
                id='0',
                mkstream=True
            )
            logger.info(f"Created consumer group {group} for {stream_key}")
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise
        
        # Store handler
        if topic not in self.handlers:
            self.handlers[topic] = []
        self.handlers[topic].append(handler)
        
        # Store consumer group info
        self.consumer_groups[topic] = group
        
        # Start consuming
        asyncio.create_task(
            self._consume_messages(topic, group, consumer, handler, auto_ack)
        )
    
    async def _consume_messages(self,
                               topic: str,
                               group: str,
                               consumer: str,
                               handler: Callable,
                               auto_ack: bool):
        """Consume messages from stream"""
        
        stream_key = f"stream:{topic}"
        self._running = True
        
        while self._running:
            try:
                # Read messages from stream
                messages = self.redis_client.xreadgroup(
                    group,
                    consumer,
                    {stream_key: '>'},
                    count=10,
                    block=self.block_ms
                )
                
                if messages:
                    for stream, stream_messages in messages:
                        for msg_id, data in stream_messages:
                            try:
                                # Parse message
                                message = Message.from_dict(data)
                                
                                # Process message
                                await self._process_message(
                                    message, handler, msg_id, 
                                    stream_key, group, auto_ack
                                )
                                
                            except Exception as e:
                                logger.error(f"Error processing message {msg_id}: {e}")
                                await self._handle_failed_message(
                                    msg_id, stream_key, group, e
                                )
                
                await asyncio.sleep(0.01)  # Small delay
                
            except Exception as e:
                logger.error(f"Consumer error: {e}")
                await asyncio.sleep(self.retry_delay)
    
    async def _process_message(self,
                              message: Message,
                              handler: Callable,
                              msg_id: str,
                              stream_key: str,
                              group: str,
                              auto_ack: bool):
        """Process a single message"""
        
        retry_count = 0
        processed = False
        
        while retry_count < self.max_retries and not processed:
            try:
                # Call handler
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
                
                processed = True
                
                # Acknowledge message if auto_ack
                if auto_ack:
                    self.redis_client.xack(stream_key, group, msg_id)
                    logger.debug(f"Acknowledged message {msg_id}")
                
            except Exception as e:
                retry_count += 1
                logger.warning(f"Retry {retry_count} for message {msg_id}: {e}")
                
                if retry_count < self.max_retries:
                    await asyncio.sleep(self.retry_delay * retry_count)
                else:
                    raise
    
    async def _handle_failed_message(self,
                                    msg_id: str,
                                    stream_key: str,
                                    group: str,
                                    error: Exception):
        """Handle failed message processing"""
        
        # Move to dead letter queue
        dlq_key = f"{stream_key}:dlq"
        
        # Get the failed message
        messages = self.redis_client.xrange(stream_key, msg_id, msg_id, count=1)
        
        if messages:
            _, data = messages[0]
            data['error'] = str(error)
            data['failed_at'] = datetime.utcnow().isoformat()
            
            # Add to DLQ
            self.redis_client.xadd(dlq_key, data)
            
            # Remove from pending
            self.redis_client.xack(stream_key, group, msg_id)
            
            logger.error(f"Moved message {msg_id} to DLQ: {error}")