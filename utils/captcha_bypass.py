"""
CAPTCHA Bypass Manager - Продвинутый обход защиты сайтов
Поддерживает множественные методы обхода для разных типов защиты
"""

import asyncio
import random
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import logging

# Импорты для разных методов обхода
try:
    import undetected_chromedriver as uc
except ImportError:
    uc = None

try:
    from fake_useragent import UserAgent
except ImportError:
    UserAgent = None

try:
    from selenium_stealth import stealth
except ImportError:
    stealth = None

try:
    from seleniumwire import webdriver as wire_webdriver
except ImportError:
    wire_webdriver = None

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class BypassMethod(Enum):
    """Методы обхода защиты"""
    HTTP_SIMPLE = "http_simple"
    UNDETECTED_CHROME = "undetected_chrome"
    STEALTH_SELENIUM = "stealth_selenium"
    SELENIUM_WIRE = "selenium_wire"
    PLAYWRIGHT = "playwright"
    REQUESTS_HTML = "requests_html"

@dataclass
class BypassResult:
    """Результат попытки обхода"""
    success: bool
    method: BypassMethod
    content: Optional[str] = None
    error: Optional[str] = None
    execution_time: float = 0.0

class CaptchaBypassManager:
    """
    Менеджер обхода CAPTCHA и других защитных механизмов
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.user_agent_rotator = self._init_user_agent_rotator()
        self.proxy_list = self._load_proxy_list()
        
        # Настройки для разных методов
        self.method_settings = {
            BypassMethod.HTTP_SIMPLE: {"timeout": 10, "retries": 2},
            BypassMethod.UNDETECTED_CHROME: {"timeout": 30, "retries": 1},
            BypassMethod.STEALTH_SELENIUM: {"timeout": 25, "retries": 1},
            BypassMethod.SELENIUM_WIRE: {"timeout": 35, "retries": 1},
            BypassMethod.PLAYWRIGHT: {"timeout": 20, "retries": 2},
        }
        
        # Статистика успешности методов
        self.method_stats = {method: {"attempts": 0, "successes": 0} 
                           for method in BypassMethod}
    
    def _init_user_agent_rotator(self):
        """Инициализация ротатора User-Agent"""
        if UserAgent:
            return UserAgent()
        else:
            # Fallback список User-Agent'ов
            return [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ]
    
    def _load_proxy_list(self) -> List[str]:
        """Загрузка списка прокси (можно расширить)"""
        # TODO: Загрузка из файла конфигурации или API
        return []
    
    def get_random_user_agent(self) -> str:
        """Получение случайного User-Agent"""
        if hasattr(self.user_agent_rotator, 'random'):
            return self.user_agent_rotator.random
        else:
            return random.choice(self.user_agent_rotator)
    
    def get_random_proxy(self) -> Optional[str]:
        """Получение случайного прокси"""
        return random.choice(self.proxy_list) if self.proxy_list else None
    
    async def bypass_with_multiple_methods(self, url: str, 
                                         preferred_methods: Optional[List[BypassMethod]] = None) -> BypassResult:
        """
        Попытка обхода с использованием нескольких методов
        """
        if preferred_methods is None:
            # Методы в порядке предпочтения (от быстрого к медленному)
            preferred_methods = [
                BypassMethod.HTTP_SIMPLE,
                BypassMethod.UNDETECTED_CHROME,
                BypassMethod.PLAYWRIGHT,
                BypassMethod.STEALTH_SELENIUM,
                BypassMethod.SELENIUM_WIRE
            ]
        
        self.logger.info(f"Начинаем обход для {url} с {len(preferred_methods)} методами")
        
        for method in preferred_methods:
            self.logger.info(f"Пробуем метод: {method.value}")
            
            try:
                result = await self._try_bypass_method(url, method)
                
                # Обновляем статистику
                self.method_stats[method]["attempts"] += 1
                if result.success:
                    self.method_stats[method]["successes"] += 1
                    self.logger.info(f"✅ Успешный обход методом {method.value} за {result.execution_time:.2f}с")
                    return result
                else:
                    self.logger.warning(f"❌ Метод {method.value} не сработал: {result.error}")
                    
            except Exception as e:
                self.logger.error(f"❌ Ошибка метода {method.value}: {e}")
                self.method_stats[method]["attempts"] += 1
                
                # Пауза перед следующим методом
                await asyncio.sleep(random.uniform(1, 3))
        
        return BypassResult(
            success=False,
            method=BypassMethod.HTTP_SIMPLE,
            error="Все методы обхода не сработали"
        )
    
    async def _try_bypass_method(self, url: str, method: BypassMethod) -> BypassResult:
        """Попытка обхода конкретным методом"""
        start_time = time.time()
        
        try:
            if method == BypassMethod.HTTP_SIMPLE:
                content = await self._try_http_simple(url)
            elif method == BypassMethod.UNDETECTED_CHROME:
                content = await self._try_undetected_chrome(url)
            elif method == BypassMethod.STEALTH_SELENIUM:
                content = await self._try_stealth_selenium(url)
            elif method == BypassMethod.SELENIUM_WIRE:
                content = await self._try_selenium_wire(url)
            elif method == BypassMethod.PLAYWRIGHT:
                content = await self._try_playwright(url)
            else:
                raise ValueError(f"Неподдерживаемый метод: {method}")
            
            execution_time = time.time() - start_time
            
            # Проверяем на наличие CAPTCHA в контенте
            if self._detect_captcha(content):
                return BypassResult(
                    success=False,
                    method=method,
                    error="CAPTCHA обнаружена в контенте",
                    execution_time=execution_time
                )
            
            return BypassResult(
                success=True,
                method=method,
                content=content,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return BypassResult(
                success=False,
                method=method,
                error=str(e),
                execution_time=execution_time
            )
    
    async def _try_http_simple(self, url: str) -> str:
        """Простой HTTP запрос"""
        import aiohttp
        
        headers = {
            'User-Agent': self.get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        timeout = aiohttp.ClientTimeout(total=self.method_settings[BypassMethod.HTTP_SIMPLE]["timeout"])
        
        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    raise Exception(f"HTTP {response.status}")
    
    async def _try_undetected_chrome(self, url: str) -> str:
        """Undetected ChromeDriver"""
        if not uc:
            raise Exception("undetected-chromedriver не установлен")
        
        options = uc.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument(f'--user-agent={self.get_random_user_agent()}')
        
        driver = None
        try:
            driver = uc.Chrome(options=options)
            driver.get(url)
            
            # Ждем загрузки
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            
            return driver.page_source
            
        finally:
            if driver:
                driver.quit()
    
    async def _try_stealth_selenium(self, url: str) -> str:
        """Stealth Selenium"""
        if not stealth:
            raise Exception("selenium-stealth не установлен")
        
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        driver = None
        try:
            driver = webdriver.Chrome(options=options)
            
            # Применяем stealth
            stealth(driver,
                   languages=["en-US", "en"],
                   vendor="Google Inc.",
                   platform="Win32",
                   webgl_vendor="Intel Inc.",
                   renderer="Intel Iris OpenGL Engine",
                   fix_hairline=True)
            
            driver.get(url)
            
            # Ждем загрузки
            WebDriverWait(driver, 15).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            
            # Дополнительная пауза для AJAX
            await asyncio.sleep(3)
            
            return driver.page_source
            
        finally:
            if driver:
                driver.quit()
    
    async def _try_selenium_wire(self, url: str) -> str:
        """Selenium Wire с прокси поддержкой"""
        if not wire_webdriver:
            raise Exception("seleniumwire не установлен")
        
        options = {
            'proxy': {
                'http': self.get_random_proxy(),
                'https': self.get_random_proxy(),
            } if self.get_random_proxy() else {}
        }
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        driver = None
        try:
            driver = wire_webdriver.Chrome(
                seleniumwire_options=options,
                options=chrome_options
            )
            
            driver.get(url)
            WebDriverWait(driver, 20).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            
            return driver.page_source
            
        finally:
            if driver:
                driver.quit()
    
    async def _try_playwright(self, url: str) -> str:
        """Playwright браузер"""
        if not async_playwright:
            raise Exception("playwright не установлен")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            context = await browser.new_context(
                user_agent=self.get_random_user_agent(),
                viewport={'width': 1920, 'height': 1080}
            )
            
            page = await context.new_page()
            
            try:
                await page.goto(url, wait_until='networkidle', timeout=20000)
                content = await page.content()
                return content
                
            finally:
                await browser.close()
    
    def _detect_captcha(self, content: str) -> bool:
        """Обнаружение CAPTCHA в контенте"""
        captcha_indicators = [
            'captcha',
            'recaptcha',
            'cloudflare',
            'challenge',
            'verification',
            'robot',
            'human',
            'security check',
            'please wait',
            'checking your browser'
        ]
        
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in captcha_indicators)
    
    def get_method_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Получение статистики успешности методов"""
        stats = {}
        for method, data in self.method_stats.items():
            success_rate = (data["successes"] / data["attempts"] * 100) if data["attempts"] > 0 else 0
            stats[method.value] = {
                "attempts": data["attempts"],
                "successes": data["successes"],
                "success_rate": round(success_rate, 2)
            }
        return stats
    
    async def smart_delay(self, min_delay: float = 1.0, max_delay: float = 3.0):
        """Умная задержка между запросами"""
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)

# Фабрика для создания менеджера
def create_captcha_bypass_manager(logger: logging.Logger) -> CaptchaBypassManager:
    """Создание настроенного менеджера обхода CAPTCHA"""
    return CaptchaBypassManager(logger)