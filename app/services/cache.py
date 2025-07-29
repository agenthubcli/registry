"""
Cache service for AgentHub Registry using Redis.
"""

import json
import pickle
from typing import Any, Dict, List, Optional, Union

import redis.asyncio as redis
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class CacheService:
    """Service for managing Redis cache operations."""
    
    def __init__(self):
        """Initialize Redis client with configuration."""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=False,  # Handle both text and binary data
                retry_on_timeout=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            self.default_ttl = settings.REDIS_CACHE_TTL
            self.key_prefix = "agenthub:"
            
            logger.info("Redis cache client initialized", url=settings.REDIS_URL)
            
        except Exception as e:
            logger.error("Failed to initialize Redis client", error=str(e))
            raise
    
    def _make_key(self, key: str) -> str:
        """Create a prefixed cache key."""
        return f"{self.key_prefix}{key}"
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get a value from cache."""
        try:
            prefixed_key = self._make_key(key)
            data = await self.redis_client.get(prefixed_key)
            
            if data is None:
                return default
            
            # Try to deserialize as JSON first, then pickle
            try:
                return json.loads(data.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return pickle.loads(data)
                
        except Exception as e:
            logger.warning("Failed to get cache value", key=key, error=str(e))
            return default
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in cache with optional TTL."""
        try:
            prefixed_key = self._make_key(key)
            ttl = ttl or self.default_ttl
            
            # Try to serialize as JSON first, then pickle
            try:
                data = json.dumps(value).encode('utf-8')
            except (TypeError, ValueError):
                data = pickle.dumps(value)
            
            await self.redis_client.setex(prefixed_key, ttl, data)
            return True
            
        except Exception as e:
            logger.error("Failed to set cache value", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        try:
            prefixed_key = self._make_key(key)
            deleted = await self.redis_client.delete(prefixed_key)
            return deleted > 0
            
        except Exception as e:
            logger.error("Failed to delete cache key", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        try:
            prefixed_key = self._make_key(key)
            return await self.redis_client.exists(prefixed_key) > 0
            
        except Exception as e:
            logger.error("Failed to check cache key existence", key=key, error=str(e))
            return False
    
    async def increment(self, key: str, amount: int = 1, ttl: Optional[int] = None) -> int:
        """Increment a numeric value in cache."""
        try:
            prefixed_key = self._make_key(key)
            
            # Use pipeline for atomic operations
            async with self.redis_client.pipeline() as pipe:
                await pipe.incr(prefixed_key, amount)
                if ttl:
                    await pipe.expire(prefixed_key, ttl)
                results = await pipe.execute()
                
            return results[0]
            
        except Exception as e:
            logger.error("Failed to increment cache value", key=key, error=str(e))
            return 0
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache."""
        try:
            prefixed_keys = [self._make_key(key) for key in keys]
            values = await self.redis_client.mget(prefixed_keys)
            
            result = {}
            for i, (original_key, data) in enumerate(zip(keys, values)):
                if data is not None:
                    try:
                        result[original_key] = json.loads(data.decode('utf-8'))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        result[original_key] = pickle.loads(data)
                        
            return result
            
        except Exception as e:
            logger.error("Failed to get multiple cache values", keys=keys, error=str(e))
            return {}
    
    async def set_many(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set multiple values in cache."""
        try:
            ttl = ttl or self.default_ttl
            
            # Prepare data for pipeline
            serialized_data = {}
            for key, value in mapping.items():
                prefixed_key = self._make_key(key)
                try:
                    data = json.dumps(value).encode('utf-8')
                except (TypeError, ValueError):
                    data = pickle.dumps(value)
                serialized_data[prefixed_key] = data
            
            # Use pipeline for atomic operations
            async with self.redis_client.pipeline() as pipe:
                await pipe.mset(serialized_data)
                for prefixed_key in serialized_data.keys():
                    await pipe.expire(prefixed_key, ttl)
                await pipe.execute()
                
            return True
            
        except Exception as e:
            logger.error("Failed to set multiple cache values", error=str(e))
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern."""
        try:
            prefixed_pattern = self._make_key(pattern)
            keys = []
            
            # Scan for matching keys
            async for key in self.redis_client.scan_iter(match=prefixed_pattern):
                keys.append(key)
            
            if keys:
                deleted = await self.redis_client.delete(*keys)
                logger.info("Deleted cache keys by pattern", pattern=pattern, count=deleted)
                return deleted
            
            return 0
            
        except Exception as e:
            logger.error("Failed to delete cache keys by pattern", pattern=pattern, error=str(e))
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            info = await self.redis_client.info()
            return {
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_connections_received": info.get("total_connections_received"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(
                    info.get("keyspace_hits", 0),
                    info.get("keyspace_misses", 0)
                )
            }
            
        except Exception as e:
            logger.error("Failed to get cache stats", error=str(e))
            return {}
    
    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """Calculate cache hit rate."""
        total = hits + misses
        if total == 0:
            return 0.0
        return round((hits / total) * 100, 2)
    
    async def health_check(self) -> bool:
        """Check if Redis is healthy."""
        try:
            await self.redis_client.ping()
            return True
        except Exception as e:
            logger.error("Redis health check failed", error=str(e))
            return False
    
    async def flush_all(self) -> bool:
        """Flush all cache data. Use with caution!"""
        try:
            await self.redis_client.flushall()
            logger.warning("All cache data flushed")
            return True
        except Exception as e:
            logger.error("Failed to flush cache", error=str(e))
            return False
    
    async def close(self):
        """Close Redis connection."""
        try:
            await self.redis_client.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error("Error closing Redis connection", error=str(e))


# Global cache service instance
cache_service = CacheService() 