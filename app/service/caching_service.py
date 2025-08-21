from app.config.settings import get_settings
from typing import Optional, Any, Callable
import redis
import json


class CachingService():
    def __init__(self):
        redis_setting = get_settings().redis

        self.redis = redis.Redis(
            host=redis_setting.host,
            port=int(redis_setting.port),
            password=redis_setting.password,
            decode_responses=True,
            username="default",
        )

    # string helper
    async def get_str(self, key: str) -> Optional[str]:
        return self.redis.get(key)
    

    async def set_str(self, key: str, value: str, ttl_seconds: Optional[int] = None) -> bool:
        if ttl_seconds is not None:
            return bool(self.redis.set(name=key, value=value, ex=ttl_seconds))
        
        return bool(self.redis.set(name=key, value=value))
    
    # json helper
    async def get_json(self, key: str) -> Optional[Any]:
        raw = self.redis.get(key)
        if raw is None:
            return None

        try: 
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
    

    async def set_json(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        if ttl_seconds is not None:
            return bool(self.redis.set(name=key, value=payload, ex=ttl_seconds))
        
        return bool(self.redis.set(name=key, value=payload))
        

    # compute-if-miss helper
    async def get_or_set_json(self, key: str, producer: Callable[[], Any], ttl_seconds: int) -> Any:
        cached = await self.get_json(key)
        if cached is not None:
            return cached
        value = producer()
        if value is not None:
            await self.set_json(key, value, ttl_seconds=ttl_seconds)
        return value

    # maintenance
    async def delete(self, *keys: str) -> int:
        if not keys:
            return 0
        return int(self.redis.delete(*keys))

    async def exists(self, key: str) -> bool:
        return bool(self.redis.exists(key))

    async def expire(self, key: str, ttl_seconds: int) -> bool:
        return bool(self.redis.expire(name=key, time=ttl_seconds))

    async def ttl(self, key: str) -> int:
        return int(self.redis.ttl(name=key))