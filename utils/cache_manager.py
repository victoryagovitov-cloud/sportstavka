"""
Менеджер кэширования с поддержкой множественных backend'ов
Поддерживает Redis, дисковый кэш и кэш в памяти
"""

import asyncio
import json
import time
import hashlib
from typing import Any, Optional, Dict, Union, Callable, Awaitable
from dataclasses import dataclass
from enum import Enum
import logging

# Импорты для разных типов кэша
try:
    import redis.asyncio as aioredis
    from redis.exceptions import ConnectionError as RedisConnectionError
except ImportError:
    aioredis = None
    RedisConnectionError = Exception

try:
    import diskcache
except ImportError:
    diskcache = None

try:
    from cachetools import TTLCache, LRUCache
except ImportError:
    TTLCache = None
    LRUCache = None

class CacheBackend(Enum):
    """Типы кэш backend'ов"""
    MEMORY = "memory"
    DISK = "disk"
    REDIS = "redis"

@dataclass
class CacheConfig:
    """Конфигурация кэша"""
    # Redis настройки
    redis_url: str = "redis://localhost:6379/0"
    redis_timeout: int = 5
    
    # Дисковый кэш
    disk_cache_dir: str = "./cache"
    disk_cache_size: int = 1024 * 1024 * 100  # 100MB
    
    # Кэш в памяти
    memory_cache_size: int = 1000
    memory_cache_ttl: int = 300  # 5 минут
    
    # Общие настройки
    default_ttl: int = 300
    key_prefix: str = "sportsbet"
    compression: bool = True

class CacheManager:
    """
    Менеджер кэширования с множественными backend'ами
    """
    
    def __init__(self, config: Optional[CacheConfig] = None, logger: Optional[logging.Logger] = None):
        self.config = config or CacheConfig()
        self.logger = logger or logging.getLogger(__name__)
        
        # Backend'ы кэша
        self.redis_client: Optional[aioredis.Redis] = None
        self.disk_cache: Optional[diskcache.Cache] = None
        self.memory_cache: Optional[Union[TTLCache, LRUCache]] = None
        
        # Статистика
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "errors": 0,
            "backend_usage": {backend.value: 0 for backend in CacheBackend}
        }
        
        # Инициализация backend'ов
        self._init_backends()
    
    def _init_backends(self):
        """Инициализация всех доступных backend'ов"""
        # Redis
        if aioredis:
            try:
                self.redis_client = aioredis.from_url(
                    self.config.redis_url,
                    socket_timeout=self.config.redis_timeout,
                    socket_connect_timeout=self.config.redis_timeout,
                    decode_responses=True
                )
                self.logger.info("Redis backend инициализирован")
            except Exception as e:
                self.logger.warning(f"Не удалось инициализировать Redis: {e}")
        
        # Дисковый кэш
        if diskcache:
            try:
                self.disk_cache = diskcache.Cache(
                    self.config.disk_cache_dir,
                    size_limit=self.config.disk_cache_size
                )
                self.logger.info("Дисковый кэш инициализирован")
            except Exception as e:
                self.logger.warning(f"Не удалось инициализировать дисковый кэш: {e}")
        
        # Кэш в памяти
        if TTLCache:
            try:
                self.memory_cache = TTLCache(
                    maxsize=self.config.memory_cache_size,
                    ttl=self.config.memory_cache_ttl
                )
                self.logger.info("Кэш в памяти инициализирован")
            except Exception as e:
                self.logger.warning(f"Не удалось инициализировать кэш в памяти: {e}")
    
    def _make_key(self, key: str) -> str:
        """Создание полного ключа с префиксом"""
        return f"{self.config.key_prefix}:{key}"
    
    def _hash_key(self, key: str) -> str:
        """Хэширование длинных ключей"""
        if len(key) > 200:  # Лимит для Redis
            return hashlib.md5(key.encode()).hexdigest()
        return key
    
    def _serialize_value(self, value: Any) -> str:
        """Сериализация значения"""
        try:
            return json.dumps(value, ensure_ascii=False, separators=(',', ':'))
        except (TypeError, ValueError) as e:
            self.logger.error(f"Ошибка сериализации: {e}")
            return json.dumps(str(value))
    
    def _deserialize_value(self, value: str) -> Any:
        """Десериализация значения"""
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError) as e:
            self.logger.error(f"Ошибка десериализации: {e}")
            return value
    
    async def get(self, key: str, backend: Optional[CacheBackend] = None) -> Optional[Any]:
        """
        Получение значения из кэша
        """
        full_key = self._make_key(self._hash_key(key))
        
        # Определяем порядок backend'ов для проверки
        if backend:
            backends = [backend]
        else:
            backends = [CacheBackend.MEMORY, CacheBackend.REDIS, CacheBackend.DISK]
        
        for cache_backend in backends:
            try:
                value = await self._get_from_backend(full_key, cache_backend)
                if value is not None:
                    self.stats["hits"] += 1
                    self.stats["backend_usage"][cache_backend.value] += 1
                    self.logger.debug(f"Кэш попадание: {key} из {cache_backend.value}")
                    return self._deserialize_value(value)
            except Exception as e:
                self.logger.error(f"Ошибка получения из {cache_backend.value}: {e}")
                self.stats["errors"] += 1
                continue
        
        self.stats["misses"] += 1
        self.logger.debug(f"Кэш промах: {key}")
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None, 
                 backend: Optional[CacheBackend] = None) -> bool:
        """
        Сохранение значения в кэш
        """
        full_key = self._make_key(self._hash_key(key))
        serialized_value = self._serialize_value(value)
        ttl = ttl or self.config.default_ttl
        
        # Определяем backend'ы для сохранения
        if backend:
            backends = [backend]
        else:
            backends = [CacheBackend.MEMORY, CacheBackend.REDIS, CacheBackend.DISK]
        
        success = False
        for cache_backend in backends:
            try:
                await self._set_to_backend(full_key, serialized_value, ttl, cache_backend)
                success = True
                self.logger.debug(f"Сохранено в кэш: {key} -> {cache_backend.value}")
            except Exception as e:
                self.logger.error(f"Ошибка сохранения в {cache_backend.value}: {e}")
                self.stats["errors"] += 1
        
        if success:
            self.stats["sets"] += 1
        
        return success
    
    async def _get_from_backend(self, key: str, backend: CacheBackend) -> Optional[str]:
        """Получение из конкретного backend'а"""
        if backend == CacheBackend.REDIS and self.redis_client:
            try:
                return await self.redis_client.get(key)
            except RedisConnectionError:
                self.logger.warning("Redis недоступен")
                return None
        
        elif backend == CacheBackend.DISK and self.disk_cache:
            return self.disk_cache.get(key)
        
        elif backend == CacheBackend.MEMORY and self.memory_cache:
            return self.memory_cache.get(key)
        
        return None
    
    async def _set_to_backend(self, key: str, value: str, ttl: int, backend: CacheBackend):
        """Сохранение в конкретный backend"""
        if backend == CacheBackend.REDIS and self.redis_client:
            try:
                await self.redis_client.setex(key, ttl, value)
            except RedisConnectionError:
                self.logger.warning("Redis недоступен для записи")
                raise
        
        elif backend == CacheBackend.DISK and self.disk_cache:
            self.disk_cache.set(key, value, expire=time.time() + ttl)
        
        elif backend == CacheBackend.MEMORY and self.memory_cache:
            self.memory_cache[key] = value
    
    async def delete(self, key: str, backend: Optional[CacheBackend] = None) -> bool:
        """Удаление из кэша"""
        full_key = self._make_key(self._hash_key(key))
        
        if backend:
            backends = [backend]
        else:
            backends = [CacheBackend.MEMORY, CacheBackend.REDIS, CacheBackend.DISK]
        
        success = False
        for cache_backend in backends:
            try:
                await self._delete_from_backend(full_key, cache_backend)
                success = True
            except Exception as e:
                self.logger.error(f"Ошибка удаления из {cache_backend.value}: {e}")
        
        return success
    
    async def _delete_from_backend(self, key: str, backend: CacheBackend):
        """Удаление из конкретного backend'а"""
        if backend == CacheBackend.REDIS and self.redis_client:
            await self.redis_client.delete(key)
        elif backend == CacheBackend.DISK and self.disk_cache:
            self.disk_cache.delete(key)
        elif backend == CacheBackend.MEMORY and self.memory_cache:
            self.memory_cache.pop(key, None)
    
    async def get_or_set(self, key: str, fetch_func: Callable[[], Awaitable[Any]], 
                        ttl: Optional[int] = None, backend: Optional[CacheBackend] = None) -> Any:
        """
        Получение из кэша или вызов функции для получения значения
        """
        # Пробуем получить из кэша
        cached_value = await self.get(key, backend)
        if cached_value is not None:
            return cached_value
        
        # Получаем значение через функцию
        try:
            value = await fetch_func()
            if value is not None:
                await self.set(key, value, ttl, backend)
            return value
        except Exception as e:
            self.logger.error(f"Ошибка в fetch_func для ключа {key}: {e}")
            raise
    
    async def clear(self, backend: Optional[CacheBackend] = None):
        """Очистка кэша"""
        if backend:
            backends = [backend]
        else:
            backends = [CacheBackend.MEMORY, CacheBackend.REDIS, CacheBackend.DISK]
        
        for cache_backend in backends:
            try:
                if cache_backend == CacheBackend.REDIS and self.redis_client:
                    # Удаляем только ключи с нашим префиксом
                    pattern = f"{self.config.key_prefix}:*"
                    async for key in self.redis_client.scan_iter(match=pattern):
                        await self.redis_client.delete(key)
                
                elif cache_backend == CacheBackend.DISK and self.disk_cache:
                    self.disk_cache.clear()
                
                elif cache_backend == CacheBackend.MEMORY and self.memory_cache:
                    self.memory_cache.clear()
                
                self.logger.info(f"Кэш {cache_backend.value} очищен")
                
            except Exception as e:
                self.logger.error(f"Ошибка очистки {cache_backend.value}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики кэша"""
        total_operations = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_operations * 100) if total_operations > 0 else 0
        
        return {
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "sets": self.stats["sets"],
            "errors": self.stats["errors"],
            "hit_rate": round(hit_rate, 2),
            "backend_usage": self.stats["backend_usage"],
            "available_backends": self._get_available_backends()
        }
    
    def _get_available_backends(self) -> List[str]:
        """Получение списка доступных backend'ов"""
        available = []
        if self.redis_client:
            available.append("redis")
        if self.disk_cache:
            available.append("disk")
        if self.memory_cache:
            available.append("memory")
        return available
    
    def reset_stats(self):
        """Сброс статистики"""
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "errors": 0,
            "backend_usage": {backend.value: 0 for backend in CacheBackend}
        }
    
    async def close(self):
        """Закрытие соединений"""
        if self.redis_client:
            await self.redis_client.close()
        
        if self.disk_cache:
            self.disk_cache.close()
        
        self.logger.info("CacheManager закрыт")

# Фабричная функция
def create_cache_manager(config: Optional[CacheConfig] = None, 
                        logger: Optional[logging.Logger] = None) -> CacheManager:
    """Создание настроенного менеджера кэша"""
    return CacheManager(config, logger)

# Глобальный менеджер кэша
_global_cache_manager: Optional[CacheManager] = None

def get_global_cache_manager() -> CacheManager:
    """Получение глобального менеджера кэша"""
    global _global_cache_manager
    if _global_cache_manager is None:
        _global_cache_manager = CacheManager()
    return _global_cache_manager