"""
Redis service for ROAM.
"""

import redis
import json
from typing import Dict, Any


class RedisService:
    """Redis service for pub/sub and caching."""

    def __init__(
        self,
        host: str = "redis.roam-controller.svc.cluster.local",
        port: int = 6379,
        db: int = 0,
    ):
        self.client = redis.Redis(host=host, port=port, db=db)

    def publish(self, channel: str, message: Dict[Any, Any]) -> None:
        """Publish message to Redis channel."""
        self.client.publish(channel, json.dumps(message))

    def get(self, key: str) -> str | None:
        """Get value from Redis."""
        result = self.client.get(key)
        return result.decode() if result else None

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        """Set value in Redis with optional expiration."""
        self.client.set(key, value, ex=ex)

    def listen_to_channel_sync(self, channel: str):
        """Listen to Redis pub/sub channel synchronously."""
        pubsub = self.client.pubsub()
        pubsub.subscribe(channel)

        try:
            for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        yield json.loads(message["data"])
                    except json.JSONDecodeError:
                        # Skip malformed messages
                        continue
        finally:
            pubsub.close()


# Global Redis instance
redis_service = RedisService()
