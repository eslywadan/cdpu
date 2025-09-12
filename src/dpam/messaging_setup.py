# src/dpam/messaging_setup.py
from common.messaging.redis_streams import RedisStreamBus, Message
from common.messaging.integration import ServiceMessageBus, ServiceEvent
import asyncio

# Initialize message bus for DPAM
async def setup_dpam_messaging():
    # Create Redis Streams bus
    redis_bus = RedisStreamBus(
        host='localhost',
        port=6379,
        db=1
    )
    
    # Create service message bus
    service_bus = ServiceMessageBus(redis_bus)
    service_bus.initialize('dpam')
    
    # Register event handlers
    @service_bus.on_event(ServiceEvent.ACCOUNT_CREATED)
    async def handle_account_created(data):
        print(f"Account created: {data}")
        # Send notification, update cache, etc.
    
    @service_bus.on_event(ServiceEvent.CONFIG_UPDATED)
    async def handle_config_update(data):
        print(f"Config updated: {data}")
        # Reload configuration
    
    return service_bus

# Usage in DPAM endpoints
from flask import Blueprint

dpam_api = Blueprint('dpam_api', __name__)
service_bus = None  # Will be initialized on startup

@dpam_api.route('/accounts', methods=['POST'])
async def create_account():
    # Create account logic
    account_data = {
        'client_id': 'new_client',
        'user_id': 'user123'
    }
    
    # Emit event
    await service_bus.emit_event(
        ServiceEvent.ACCOUNT_CREATED,
        account_data
    )
    
    return jsonify({'status': 'created'})