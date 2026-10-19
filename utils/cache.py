import os
import redis
import json
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

redis_url = os.getenv("REDIS_URL")

try:
    if redis_url:
        redis_client = redis.from_url(redis_url, decode_responses=True)
        # Ping to check connection
        redis_client.ping()
        print("Redis cache connected successfully.")
    else:
        redis_client = None
        print("REDIS_URL not set. Running without cache.")
except Exception as e:
    print(f"Failed to connect to Redis: {e}")
    redis_client = None

def get_cache(key: str):
    """Retrieve JSON-deserialized value from cache."""
    if not redis_client:
        return None
    try:
        val = redis_client.get(key)
        return json.loads(val) if val else None
    except Exception as e:
        logger.error(f"Redis get error: {e}")
        return None

def set_cache(key: str, value, ttl_minutes: int = 60):
    """Serialize and store value in cache with a TTL."""
    if not redis_client:
        return
    try:
        redis_client.setex(
            key,
            timedelta(minutes=ttl_minutes),
            json.dumps(value)
        )
    except Exception as e:
        logger.error(f"Redis set error: {e}")
