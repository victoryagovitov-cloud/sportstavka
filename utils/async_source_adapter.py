"""
Асинхронный адаптер для источников данных
Универсальный класс для адаптации существующих источников к асинхронной работе
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass
import logging

from utils.async_http_client import AsyncHTTPClient, ClientConfig
from utils.captcha_bypass import CaptchaBypassManager, BypassMethod
from utils.cache_manager import CacheManager, CacheBackend
from config.optimization_config import get_source_config, is_captcha_bypass_enabled, is_caching_enabled, get_cache_ttl

@dataclass
class AdapterStats:
    """Статистика работы адаптера"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    captcha_bypasses: int = 0
    errors: int = 0
    total_time: float = 0.0
    average_time: float = 0.0

class AsyncSourceAdapter:
    """
    Универсальный асинхронный адаптер для источников данных
    """
    
    def __init__(self, source_name: str, original_scraper: Any, logger: Optional[logging.Logger] = None):
        self.source_name = source_name
        self.original_scraper = original_scraper
        self.logger = logger or logging.getLogger(__name__)
        
        # Получаем конфигурацию для источника
        self.source_config = get_source_config(source_name)
        
        # Инициализируем компоненты
        self.http_client: Optional[AsyncHTTPClient] = None
        self.captcha_bypass: Optional[CaptchaBypassManager] = None
        self.cache_manager: Optional[CacheManager] = None
        
        # Статистика
        self.stats = AdapterStats()
        
        # Флаги включения компонентов
        self.captcha_bypass_enabled = is_captcha_bypass_enabled(source_name)
        self.caching_enabled = is_caching_enabled(source_name)
        
        self.logger.info(f"AsyncSourceAdapter для {source_name} создан "
                        f"(CAPTCHA: {self.captcha_bypass_enabled}, Cache: {self.caching_enabled})")
    
    async def initialize(self):
        """Инициализация асинхронных компонентов"""
        # HTTP клиент
        from config.optimization_config import get_optimization_config
        config = get_optimization_config()
        client_config = config.async_config.source_configs.get(self.source_name)
        
        self.http_client = AsyncHTTPClient(client_config, self.logger)
        await self.http_client.start()
        
        # CAPTCHA bypass
        if self.captcha_bypass_enabled:
            self.captcha_bypass = CaptchaBypassManager(self.logger)
        
        # Cache manager
        if self.caching_enabled:
            self.cache_manager = CacheManager(logger=self.logger)
        
        self.logger.info(f"AsyncSourceAdapter для {self.source_name} инициализирован")
    
    async def close(self):
        """Закрытие адаптера"""
        if self.http_client:
            await self.http_client.close()
        
        if self.cache_manager:
            await self.cache_manager.close()
        
        self.logger.info(f"AsyncSourceAdapter для {self.source_name} закрыт")
    
    async def get_matches_async(self, sport: str = 'football', **kwargs) -> List[Dict[str, Any]]:
        """
        Асинхронное получение матчей
        """
        cache_key = f"{self.source_name}:matches:{sport}:{hash(str(kwargs))}"
        
        return await self._execute_with_optimizations(
            cache_key=cache_key,
            fetch_func=lambda: self._fetch_matches_internal(sport, **kwargs),
            data_type="live_matches"
        )
    
    async def get_match_details_async(self, match_url: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Асинхронное получение деталей матча
        """
        cache_key = f"{self.source_name}:match_details:{hash(match_url)}"
        
        return await self._execute_with_optimizations(
            cache_key=cache_key,
            fetch_func=lambda: self._fetch_match_details_internal(match_url, **kwargs),
            data_type="match_details"
        )
    
    async def get_team_stats_async(self, team1: str, team2: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Асинхронное получение статистики команд
        """
        cache_key = f"{self.source_name}:team_stats:{hash(f'{team1}:{team2}')}"
        
        return await self._execute_with_optimizations(
            cache_key=cache_key,
            fetch_func=lambda: self._fetch_team_stats_internal(team1, team2, **kwargs),
            data_type="team_stats"
        )
    
    async def _execute_with_optimizations(self, cache_key: str, fetch_func: Callable[[], Awaitable[Any]], 
                                        data_type: str) -> Any:
        """
        Выполнение функции с применением всех оптимизаций
        """
        start_time = time.time()
        self.stats.total_requests += 1
        
        try:
            # Пробуем получить из кэша
            if self.caching_enabled and self.cache_manager:
                cached_result = await self.cache_manager.get(cache_key)
                if cached_result is not None:
                    self.stats.cache_hits += 1
                    execution_time = time.time() - start_time
                    self._update_average_time(execution_time)
                    self.logger.debug(f"Кэш попадание для {cache_key}")
                    return cached_result
                else:
                    self.stats.cache_misses += 1
            
            # Выполняем функцию получения данных
            result = await fetch_func()
            
            # Сохраняем в кэш
            if self.caching_enabled and self.cache_manager and result is not None:
                ttl = get_cache_ttl(data_type)
                await self.cache_manager.set(cache_key, result, ttl)
            
            execution_time = time.time() - start_time
            self._update_average_time(execution_time)
            
            return result
            
        except Exception as e:
            self.stats.errors += 1
            execution_time = time.time() - start_time
            self._update_average_time(execution_time)
            self.logger.error(f"Ошибка в {self.source_name}: {e}")
            raise
    
    async def _fetch_matches_internal(self, sport: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Внутренний метод получения матчей
        """
        # Проверяем, есть ли асинхронный метод у оригинального скрапера
        if hasattr(self.original_scraper, 'get_live_matches_async'):
            return await self.original_scraper.get_live_matches_async(sport, **kwargs)
        
        # Если нет асинхронного метода, пробуем разные подходы
        if hasattr(self.original_scraper, 'get_live_matches_with_odds'):
            return await self._wrap_sync_method(
                self.original_scraper.get_live_matches_with_odds, sport, **kwargs
            )
        elif hasattr(self.original_scraper, 'get_live_matches'):
            return await self._wrap_sync_method(
                self.original_scraper.get_live_matches, sport, **kwargs
            )
        else:
            raise NotImplementedError(f"Источник {self.source_name} не имеет подходящих методов")
    
    async def _fetch_match_details_internal(self, match_url: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Внутренний метод получения деталей матча
        """
        if hasattr(self.original_scraper, 'get_detailed_match_data'):
            return await self._wrap_sync_method(
                self.original_scraper.get_detailed_match_data, match_url, **kwargs
            )
        
        return None
    
    async def _fetch_team_stats_internal(self, team1: str, team2: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Внутренний метод получения статистики команд
        """
        if hasattr(self.original_scraper, 'get_team_statistics'):
            return await self._wrap_sync_method(
                self.original_scraper.get_team_statistics, team1, team2, **kwargs
            )
        
        return None
    
    async def _wrap_sync_method(self, sync_method: Callable, *args, **kwargs) -> Any:
        """
        Обертка для синхронных методов с применением оптимизаций
        """
        # Если нужен обход CAPTCHA, используем специальную логику
        if self.captcha_bypass_enabled and self.captcha_bypass:
            return await self._execute_with_captcha_bypass(sync_method, *args, **kwargs)
        else:
            # Выполняем в отдельном потоке
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: sync_method(*args, **kwargs))
    
    async def _execute_with_captcha_bypass(self, sync_method: Callable, *args, **kwargs) -> Any:
        """
        Выполнение метода с обходом CAPTCHA
        """
        self.stats.captcha_bypasses += 1
        
        # Если метод принимает URL, пробуем получить контент через CAPTCHA bypass
        if len(args) > 0 and isinstance(args[0], str) and args[0].startswith('http'):
            url = args[0]
            
            # Получаем контент через CAPTCHA bypass
            bypass_result = await self.captcha_bypass.bypass_with_multiple_methods(url)
            
            if bypass_result.success:
                # Если у скрапера есть метод для обработки HTML
                if hasattr(self.original_scraper, '_extract_matches_from_html'):
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(
                        None, 
                        lambda: self.original_scraper._extract_matches_from_html(bypass_result.content)
                    )
                elif hasattr(self.original_scraper, '_parse_html_content'):
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(
                        None,
                        lambda: self.original_scraper._parse_html_content(bypass_result.content)
                    )
            
            # Если bypass не сработал, пробуем оригинальный метод
            self.logger.warning(f"CAPTCHA bypass не сработал для {url}, используем оригинальный метод")
        
        # Fallback к оригинальному методу
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: sync_method(*args, **kwargs))
    
    def _update_average_time(self, execution_time: float):
        """Обновление средней время выполнения"""
        self.stats.total_time += execution_time
        if self.stats.total_requests > 0:
            self.stats.average_time = self.stats.total_time / self.stats.total_requests
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики адаптера"""
        cache_hit_rate = 0.0
        if (self.stats.cache_hits + self.stats.cache_misses) > 0:
            cache_hit_rate = (self.stats.cache_hits / (self.stats.cache_hits + self.stats.cache_misses)) * 100
        
        error_rate = 0.0
        if self.stats.total_requests > 0:
            error_rate = (self.stats.errors / self.stats.total_requests) * 100
        
        return {
            "source_name": self.source_name,
            "total_requests": self.stats.total_requests,
            "cache_hits": self.stats.cache_hits,
            "cache_misses": self.stats.cache_misses,
            "cache_hit_rate": round(cache_hit_rate, 2),
            "captcha_bypasses": self.stats.captcha_bypasses,
            "errors": self.stats.errors,
            "error_rate": round(error_rate, 2),
            "average_time": round(self.stats.average_time, 3),
            "total_time": round(self.stats.total_time, 2),
            "captcha_bypass_enabled": self.captcha_bypass_enabled,
            "caching_enabled": self.caching_enabled
        }
    
    def reset_stats(self):
        """Сброс статистики"""
        self.stats = AdapterStats()

# Фабричная функция
def create_async_adapter(source_name: str, original_scraper: Any, 
                        logger: Optional[logging.Logger] = None) -> AsyncSourceAdapter:
    """Создание асинхронного адаптера для источника"""
    return AsyncSourceAdapter(source_name, original_scraper, logger)