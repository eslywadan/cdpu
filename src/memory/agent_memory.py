# memory/agent_memory.py
from dsbase.tools.redis_db import RedisDb
import redis
import json

redis_client = RedisDb.default()

def log_resource_memory(resource, deleted=False):
    """Store or update the resource into Redis memory store.
        If deleted = True, flag it as deleted in the memory.
    """
    key = f"resoure:{resource.id}"
    resource_data = {
        "id": resource.id,
        "name": resource.name, 
        "type": resource.type,
        "description": resource.description,
        "metadata": resource._metadata,
        "created_at": str(resource.created_at),
        "updated_at": str(resource.updated_at),
        "deleted": deleted
    }
    
    try:
        redis_client.set(key, json.dumps(resource_data))
        print(f"[Redis Memory] {'Flagged as deleted' if deleted else 'Stored'}: {key}")
    except redis.RedisError as e:
        print(f"[Redis Error] Failed to store resources {e}")

def get_resource_memory(resource_id):
    key = f"resource:{resource_id}"
    try:
        value = redis_client.get(key)
        return json.loads(value) if value else None
    except redis_client.RedisError as e:
        print(f"[Redis Error] Failed to get resource: {e}")
        return None
    

def remove_resourcd_memory(resource_id):
    """Hard delete from Redis (if you ever need it)
    """
    key = f"resource:{resource_id}"
    try:
        redis_client.delete(key)
        print(f"[Redis Memory] Deleted key: {key}")
    except redis_client.RedisError as e:
        print(f"[Redis Error] Failed to delete memory: {e}")