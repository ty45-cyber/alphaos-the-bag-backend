import json
import logging
from typing import Any, AsyncIterator
import redis.asyncio as aioredis
from app.config import get_settings

logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None

SIGNAL_CHANNEL = "alphaos:signals:live"
WHALE_ALERT_CHANNEL = "alphaos:alerts:whale"
BREAKOUT_CHANNEL = "alphaos:alerts:breakout"


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = await aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
        logger.info("Redis connection established")
    return _redis


async def publish_signal(channel: str, payload: dict[str, Any]) -> None:
    """Publish a signal event to a Redis pub/sub channel."""
    redis = await get_redis()
    try:
        await redis.publish(channel, json.dumps(payload))
    except Exception as exc:
        logger.error("Redis publish failed on channel %s: %s", channel, exc)
        raise


async def cache_set(key: str, value: Any, ttl_seconds: int = 300) -> None:
    redis = await get_redis()
    await redis.set(key, json.dumps(value), ex=ttl_seconds)


async def cache_get(key: str) -> Any | None:
    redis = await get_redis()
    raw = await redis.get(key)
    if raw is None:
        return None
    return json.loads(raw)


async def cache_delete(key: str) -> None:
    redis = await get_redis()
    await redis.delete(key)


async def subscribe_to_channel(channel: str) -> AsyncIterator[dict[str, Any]]:
    """
    Async generator that yields parsed messages from a Redis pub/sub channel.
    Used by the WebSocket endpoint to stream signals to connected clients.
    """
    redis = await get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe(channel)
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    yield json.loads(message["data"])
                except json.JSONDecodeError as exc:
                    logger.warning("Malformed signal message: %s", exc)
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()