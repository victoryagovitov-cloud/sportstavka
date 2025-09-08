"""
Конфигурация системы оптимизации
Централизованные настройки для CAPTCHA обхода, асинхронности и кэширования
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from utils.async_http_client import ClientConfig
from utils.cache_manager import CacheConfig

@dataclass
class CaptchaConfig:
    """Конфигурация обхода CAPTCHA"""
    # Методы обхода в порядке предпочтения
    preferred_methods: List[str] = field(default_factory=lambda: [
        "http_simple",
        "undetected_chrome", 
        "playwright",
        "stealth_selenium",
        "selenium_wire"
    ])
    
    # User-Agent'ы для ротации
    user_agents: List[str] = field(default_factory=lambda: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
    ])
    
    # Прокси серверы (пустой список = без прокси)
    proxy_list: List[str] = field(default_factory=list)
    
    # Задержки между запросами
    min_delay: float = 1.0
    max_delay: float = 3.0
    
    # Таймауты для разных методов
    method_timeouts: Dict[str, int] = field(default_factory=lambda: {
        "http_simple": 10,
        "undetected_chrome": 30,
        "stealth_selenium": 25,
        "selenium_wire": 35,
        "playwright": 20
    })

@dataclass
class AsyncConfig:
    """Конфигурация асинхронной обработки"""
    # Общие настройки
    max_concurrent_requests: int = 10
    default_timeout: int = 30
    
    # Настройки для разных источников
    source_configs: Dict[str, ClientConfig] = field(default_factory=lambda: {
        "sofascore": ClientConfig(
            timeout=15,
            max_connections=20,
            rate_limit=15.0,
            max_retries=2
        ),
        "flashscore": ClientConfig(
            timeout=25,
            max_connections=15,
            rate_limit=8.0,
            max_retries=3
        ),
        "scores24": ClientConfig(
            timeout=35,
            max_connections=10,
            rate_limit=5.0,
            max_retries=3
        ),
        "marathonbet": ClientConfig(
            timeout=40,
            max_connections=12,
            rate_limit=6.0,
            max_retries=2
        )
    })

@dataclass
class CacheOptimizationConfig:
    """Конфигурация кэширования для оптимизации"""
    # Основной конфиг кэша
    cache_config: CacheConfig = field(default_factory=lambda: CacheConfig(
        redis_url="redis://localhost:6379/0",
        default_ttl=300,  # 5 минут по умолчанию
        key_prefix="sportsbet_optimized"
    ))
    
    # TTL для разных типов данных
    ttl_settings: Dict[str, int] = field(default_factory=lambda: {
        "live_matches": 30,      # 30 секунд для live данных
        "team_stats": 3600,      # 1 час для статистики команд
        "player_stats": 7200,    # 2 часа для статистики игроков
        "league_info": 86400,    # 24 часа для информации о лигах
        "odds": 60,              # 1 минута для коэффициентов
        "match_urls": 1800,      # 30 минут для URL матчей
        "search_results": 600    # 10 минут для результатов поиска
    })
    
    # Кэширование для каждого источника
    source_cache_enabled: Dict[str, bool] = field(default_factory=lambda: {
        "sofascore": True,
        "flashscore": True,
        "scores24": True,
        "marathonbet": True
    })

@dataclass
class OptimizationConfig:
    """Главная конфигурация оптимизации"""
    # Подконфигурации
    captcha: CaptchaConfig = field(default_factory=CaptchaConfig)
    async_config: AsyncConfig = field(default_factory=AsyncConfig)
    cache: CacheOptimizationConfig = field(default_factory=CacheOptimizationConfig)
    
    # Общие настройки
    enable_optimization: bool = True
    enable_captcha_bypass: bool = True
    enable_async_processing: bool = True
    enable_caching: bool = True
    
    # Мониторинг и логирование
    enable_performance_monitoring: bool = True
    log_level: str = "INFO"
    enable_stats_collection: bool = True
    
    # Настройки для разных источников
    source_optimization: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "sofascore": {
            "priority": 1,
            "enable_captcha_bypass": False,  # Обычно не нужно
            "enable_caching": True,
            "cache_ttl": 300,
            "max_retries": 2
        },
        "flashscore": {
            "priority": 2,
            "enable_captcha_bypass": True,
            "enable_caching": True,
            "cache_ttl": 180,
            "max_retries": 3
        },
        "scores24": {
            "priority": 3,
            "enable_captcha_bypass": True,  # Критично важно
            "enable_caching": True,
            "cache_ttl": 120,
            "max_retries": 3
        },
        "marathonbet": {
            "priority": 2,
            "enable_captcha_bypass": True,
            "enable_caching": True,
            "cache_ttl": 240,
            "max_retries": 2
        }
    })

# Глобальная конфигурация
DEFAULT_OPTIMIZATION_CONFIG = OptimizationConfig()

def get_optimization_config() -> OptimizationConfig:
    """Получение конфигурации оптимизации"""
    return DEFAULT_OPTIMIZATION_CONFIG

def get_source_config(source_name: str) -> Dict[str, Any]:
    """Получение конфигурации для конкретного источника"""
    config = get_optimization_config()
    return config.source_optimization.get(source_name, {})

def is_captcha_bypass_enabled(source_name: str) -> bool:
    """Проверка, включен ли обход CAPTCHA для источника"""
    source_config = get_source_config(source_name)
    return source_config.get("enable_captcha_bypass", False)

def is_caching_enabled(source_name: str) -> bool:
    """Проверка, включено ли кэширование для источника"""
    source_config = get_source_config(source_name)
    return source_config.get("enable_caching", True)

def get_cache_ttl(data_type: str) -> int:
    """Получение TTL для типа данных"""
    config = get_optimization_config()
    return config.cache.ttl_settings.get(data_type, config.cache.cache_config.default_ttl)