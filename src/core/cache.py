"""
Redis 缓存模块

提供统一的缓存接口，支持优雅降级：
- Redis 可用时：使用 Redis 作为缓存后端
- Redis 不可用时：自动降级到内存字典缓存

使用方式：
    from src.core.cache import cache

    # 写入缓存（默认 300 秒过期）
    cache.set("key", "value", ttl=300)

    # 读取缓存
    value = cache.get("key")

    # 删除缓存
    cache.delete("key")

    # 按前缀批量删除
    cache.delete_pattern("stock:*")
"""

import json
import time
from typing import Any

from src.core.config import config_loader
from src.core.logger import get_logger

logger = get_logger("Cache")


class CacheBase:
    """缓存基类"""

    def get(self, key: str) -> Any:
        raise NotImplementedError

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        raise NotImplementedError

    def delete(self, key: str) -> bool:
        raise NotImplementedError

    def delete_pattern(self, pattern: str) -> int:
        raise NotImplementedError

    def exists(self, key: str) -> bool:
        raise NotImplementedError


class RedisCache(CacheBase):
    """Redis 缓存实现"""

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        import redis

        self._client = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        self._client.ping()
        logger.info("Redis cache initialized", host=host, port=port, db=db)

    def get(self, key: str) -> Any:
        raw = self._client.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        try:
            self._client.setex(key, ttl, json.dumps(value, default=str))
            return True
        except Exception as e:
            logger.warning("Redis set failed", key=key, error=str(e))
            return False

    def delete(self, key: str) -> bool:
        return self._client.delete(key) > 0

    def delete_pattern(self, pattern: str) -> int:
        keys = self._client.keys(pattern)
        if keys:
            return self._client.delete(*keys)
        return 0

    def exists(self, key: str) -> bool:
        return self._client.exists(key) > 0


class MemoryCache(CacheBase):
    """内存缓存降级实现（Redis 不可用时自动启用）"""

    def __init__(self):
        self._store: dict[str, tuple[Any, float]] = {}
        logger.warning("Using in-memory cache fallback (Redis not available)")

    def get(self, key: str) -> Any:
        item = self._store.get(key)
        if item is None:
            return None
        value, expire_at = item
        if time.time() > expire_at:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        self._store[key] = (value, time.time() + ttl)
        return True

    def delete(self, key: str) -> bool:
        return self._store.pop(key, None) is not None

    def delete_pattern(self, pattern: str) -> int:
        import fnmatch

        keys_to_delete = [k for k in self._store if fnmatch.fnmatch(k, pattern)]
        for k in keys_to_delete:
            self._store.pop(k, None)
        return len(keys_to_delete)

    def exists(self, key: str) -> bool:
        return self.get(key) is not None


def _create_cache() -> CacheBase:
    """工厂方法：优先创建 Redis 缓存，失败则降级到内存缓存"""
    redis_config = config_loader.get("cache.redis", {})
    host = redis_config.get("host", "localhost")
    port = redis_config.get("port", 6379)
    db = redis_config.get("db", 0)

    try:
        return RedisCache(host=host, port=port, db=db)
    except Exception as e:
        logger.warning(f"Redis connection failed, falling back to memory cache: {e}")
        return MemoryCache()


cache = _create_cache()
