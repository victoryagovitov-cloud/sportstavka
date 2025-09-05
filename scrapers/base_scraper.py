"""
Базовый класс для всех скраперов
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import logging
from config import SELENIUM_OPTIONS

class BaseScraper(ABC):
    """
    Базовый класс для скраперов спортивных данных
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.driver = None
        self.wait = None
    
    def setup_driver(self) -> webdriver.Chrome:
        """
        Настройка Selenium WebDriver
        """
        chrome_options = Options()
        for option in SELENIUM_OPTIONS:
            chrome_options.add_argument(option)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
        return self.driver
    
    def close_driver(self):
        """
        Закрытие WebDriver
        """
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.wait = None
    
    def safe_find_element(self, by: By, value: str, timeout: int = 5) -> Optional[Any]:
        """
        Безопасный поиск элемента с обработкой исключений
        """
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except (TimeoutException, NoSuchElementException):
            self.logger.warning(f"Элемент не найден: {by}={value}")
            return None
    
    def safe_find_elements(self, by: By, value: str) -> List[Any]:
        """
        Безопасный поиск множественных элементов
        """
        try:
            return self.driver.find_elements(by, value)
        except NoSuchElementException:
            self.logger.warning(f"Элементы не найдены: {by}={value}")
            return []
    
    def safe_click(self, element) -> bool:
        """
        Безопасный клик по элементу
        """
        try:
            if element:
                self.driver.execute_script("arguments[0].click();", element)
                time.sleep(1)
                return True
        except Exception as e:
            self.logger.warning(f"Ошибка клика: {e}")
        return False
    
    def safe_get_text(self, element) -> str:
        """
        Безопасное получение текста элемента
        """
        try:
            if element:
                return element.text.strip()
        except Exception as e:
            self.logger.warning(f"Ошибка получения текста: {e}")
        return ""
    
    def safe_get_attribute(self, element, attribute: str) -> str:
        """
        Безопасное получение атрибута элемента
        """
        try:
            if element:
                return element.get_attribute(attribute) or ""
        except Exception as e:
            self.logger.warning(f"Ошибка получения атрибута {attribute}: {e}")
        return ""
    
    def load_more_results(self, button_selector: str, max_clicks: int = 10) -> int:
        """
        Загрузка дополнительных результатов через кнопку "Показать еще"
        """
        clicks = 0
        while clicks < max_clicks:
            show_more_btn = self.safe_find_element(By.CSS_SELECTOR, button_selector, timeout=3)
            if show_more_btn and show_more_btn.is_displayed():
                if self.safe_click(show_more_btn):
                    clicks += 1
                    time.sleep(2)
                else:
                    break
            else:
                break
        
        self.logger.info(f"Загружено дополнительных результатов: {clicks} кликов")
        return clicks
    
    @abstractmethod
    def get_live_matches(self, url: str) -> List[Dict[str, Any]]:
        """
        Получение списка live матчей
        """
        pass
    
    @abstractmethod
    def collect_match_data(self, match_url: str) -> Dict[str, Any]:
        """
        Сбор подробных данных по матчу
        """
        pass
    
    @abstractmethod
    def filter_matches(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Фильтрация матчей по критериям
        """
        pass