"""
Асинхронный HTTP клиент с продвинутыми возможностями
Поддерживает ретраи, тротлинг, пулы соединений и мониторинг
"""

import asyncio
import aiohttp
import time
import random
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

try:
    from asyncio_throttle import Throttle
except ImportError:
    Throttle = None

try:
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
except ImportError:
    retry = None

@dataclass
class RequestStats:
    """Статистика запросов"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_time: float = 0.0
    average_response_time: float = 0.0
    last_request_time: Optional[datetime] = None

@dataclass
class ClientConfig:
    """Конфигурация HTTP клиента"""
    # Основные настройки
    timeout: int = 30
    max_connections: int = 100
    max_connections_per_host: int = 10
    
    # Ретраи
    max_retries: int = 3
    retry_backoff_factor: float = 2.0
    retry_statuses: List[int] = field(default_factory=lambda: [500, 502, 503, 504])
    
    # Тротлинг
    rate_limit: float = 10.0  # запросов в секунду
    burst_limit: int = 20     # максимум запросов в burst
    
    # User-Agent ротация
    rotate_user_agent: bool = True
    user_agents: List[str] = field(default_factory=lambda: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ])
    
    # Прокси
    use_proxy: bool = False
    proxy_list: List[str] = field(default_factory=list)

class AsyncHTTPClient:
    """
    Продвинутый асинхронный HTTP клиент
    """
    
    def __init__(self, config: Optional[ClientConfig] = None, logger: Optional[logging.Logger] = None):
        self.config = config or ClientConfig()
        self.logger = logger or logging.getLogger(__name__)
        
        # Статистика
        self.stats = RequestStats()
        
        # Сессия aiohttp
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Тротлинг
        self.throttle = None
        if Throttle:
            self.throttle = Throttle(rate_limit=self.config.rate_limit)
        
        # Текущий индекс User-Agent
        self.current_ua_index = 0
        
        # Текущий индекс прокси
        self.current_proxy_index = 0
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def start(self):
        """Инициализация клиента"""
        if self.session is None:
            # Настройка коннектора
            connector = aiohttp.TCPConnector(
                limit=self.config.max_connections,
                limit_per_host=self.config.max_connections_per_host,
                enable_cleanup_closed=True,
                ttl_dns_cache=300,  # 5 минут DNS кэш
                use_dns_cache=True,
            )
            
            # Настройка таймаута
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            
            # Создание сессии
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self._get_default_headers()
            )
            
            self.logger.info("AsyncHTTPClient инициализирован")
    
    async def close(self):
        """Закрытие клиента"""
        if self.session:
            await self.session.close()
            self.session = None
            self.logger.info("AsyncHTTPClient закрыт")
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Получение базовых заголовков"""
        return {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'no-cache'
        }
    
    def _get_rotated_user_agent(self) -> str:
        """Получение User-Agent с ротацией"""
        if not self.config.rotate_user_agent or not self.config.user_agents:
            return self.config.user_agents[0] if self.config.user_agents else ""
        
        ua = self.config.user_agents[self.current_ua_index]
        self.current_ua_index = (self.current_ua_index + 1) % len(self.config.user_agents)
        return ua
    
    def _get_rotated_proxy(self) -> Optional[str]:
        """Получение прокси с ротацией"""
        if not self.config.use_proxy or not self.config.proxy_list:
            return None
        
        proxy = self.config.proxy_list[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.config.proxy_list)
        return proxy
    
    async def _make_request(self, method: str, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Внутренний метод для выполнения запроса"""
        if not self.session:
            await self.start()
        
        # Применяем тротлинг
        if self.throttle:
            async with self.throttle:
                pass
        
        # Подготавливаем заголовки
        headers = kwargs.get('headers', {})
        headers['User-Agent'] = self._get_rotated_user_agent()
        kwargs['headers'] = headers
        
        # Прокси
        if self.config.use_proxy:
            proxy = self._get_rotated_proxy()
            if proxy:
                kwargs['proxy'] = proxy
        
        # Выполняем запрос
        start_time = time.time()
        
        try:
            response = await self.session.request(method, url, **kwargs)
            execution_time = time.time() - start_time
            
            # Обновляем статистику
            self.stats.total_requests += 1
            self.stats.total_time += execution_time
            self.stats.last_request_time = datetime.now()
            
            if response.status < 400:
                self.stats.successful_requests += 1
            else:
                self.stats.failed_requests += 1
            
            # Пересчитываем среднее время
            self.stats.average_response_time = self.stats.total_time / self.stats.total_requests
            
            self.logger.debug(f"{method} {url} -> {response.status} ({execution_time:.2f}s)")
            
            return response
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.stats.total_requests += 1
            self.stats.failed_requests += 1
            self.stats.total_time += execution_time
            self.stats.last_request_time = datetime.now()
            
            if self.stats.total_requests > 0:
                self.stats.average_response_time = self.stats.total_time / self.stats.total_requests
            
            self.logger.error(f"{method} {url} -> ERROR: {e} ({execution_time:.2f}s)")
            raise
    
    async def get(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """GET запрос"""
        return await self._make_request('GET', url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """POST запрос"""
        return await self._make_request('POST', url, **kwargs)
    
    async def get_text(self, url: str, **kwargs) -> str:
        """GET запрос с получением текста"""
        async with await self.get(url, **kwargs) as response:
            if response.status >= 400:
                response.raise_for_status()
            return await response.text()
    
    async def get_json(self, url: str, **kwargs) -> Any:
        """GET запрос с получением JSON"""
        async with await self.get(url, **kwargs) as response:
            if response.status >= 400:
                response.raise_for_status()
            return await response.json()
    
    async def get_with_retry(self, url: str, max_retries: Optional[int] = None, **kwargs) -> str:
        """
        GET запрос с автоматическими ретраями
        """
        max_retries = max_retries or self.config.max_retries
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                async with await self.get(url, **kwargs) as response:
                    if response.status in self.config.retry_statuses and attempt < max_retries:
                        # Ретрай для определенных статусов
                        delay = self.config.retry_backoff_factor ** attempt
                        self.logger.warning(f"Ретрай {attempt + 1}/{max_retries} для {url} "
                                          f"(статус {response.status}), ждем {delay:.1f}с")
                        await asyncio.sleep(delay)
                        continue
                    
                    if response.status >= 400:
                        response.raise_for_status()
                    
                    return await response.text()
                    
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    delay = self.config.retry_backoff_factor ** attempt + random.uniform(0.1, 0.5)
                    self.logger.warning(f"Ретрай {attempt + 1}/{max_retries} для {url} "
                                      f"(ошибка: {e}), ждем {delay:.1f}с")
                    await asyncio.sleep(delay)
                    continue
                else:
                    break
        
        # Все попытки исчерпаны
        raise last_exception or Exception(f"Все {max_retries} попыток не удались")
    
    async def batch_get(self, urls: List[str], max_concurrent: int = 10, **kwargs) -> List[Dict[str, Any]]:
        """
        Пакетное выполнение GET запросов
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def fetch_one(url: str) -> Dict[str, Any]:
            async with semaphore:
                try:
                    content = await self.get_text(url, **kwargs)
                    return {"url": url, "success": True, "content": content, "error": None}
                except Exception as e:
                    return {"url": url, "success": False, "content": None, "error": str(e)}
        
        tasks = [fetch_one(url) for url in urls]
        results = await asyncio.gather(*tasks)
        
        successful = sum(1 for r in results if r["success"])
        self.logger.info(f"Пакетный запрос завершен: {successful}/{len(urls)} успешных")
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики клиента"""
        success_rate = 0.0
        if self.stats.total_requests > 0:
            success_rate = (self.stats.successful_requests / self.stats.total_requests) * 100
        
        return {
            "total_requests": self.stats.total_requests,
            "successful_requests": self.stats.successful_requests,
            "failed_requests": self.stats.failed_requests,
            "success_rate": round(success_rate, 2),
            "average_response_time": round(self.stats.average_response_time, 3),
            "total_time": round(self.stats.total_time, 2),
            "last_request_time": self.stats.last_request_time.isoformat() if self.stats.last_request_time else None
        }
    
    def reset_stats(self):
        """Сброс статистики"""
        self.stats = RequestStats()
        self.logger.info("Статистика клиента сброшена")

# Фабричная функция для создания клиента
def create_http_client(config: Optional[ClientConfig] = None, 
                      logger: Optional[logging.Logger] = None) -> AsyncHTTPClient:
    """Создание настроенного HTTP клиента"""
    return AsyncHTTPClient(config, logger)

# Глобальный клиент для простого использования
_global_client: Optional[AsyncHTTPClient] = None

async def get_global_client() -> AsyncHTTPClient:
    """Получение глобального HTTP клиента"""
    global _global_client
    if _global_client is None:
        _global_client = AsyncHTTPClient()
        await _global_client.start()
    return _global_client

async def close_global_client():
    """Закрытие глобального клиента"""
    global _global_client
    if _global_client:
        await _global_client.close()
        _global_client = None