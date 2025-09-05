"""
Улучшенный SofaScore скрапер для получения актуальных live матчей
На основе анализа реальных данных с сайта
"""
import requests
import time
import re
import json
from typing import List, Dict, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class SofaScoreLiveImproved:
    """
    Улучшенный скрапер для получения актуальных live матчей с SofaScore
    """
    
    def __init__(self, logger):
        self.logger = logger
        self.driver = None
        
        # Chrome настройки
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--disable-gpu')
        self.chrome_options.add_argument('--window-size=1920,1080')
        self.chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    def get_current_live_matches(self, sport: str = 'football') -> List[Dict[str, Any]]:
        """
        Получение актуальных live матчей
        """
        try:
            self.logger.info(f"Получение актуальных live {sport} матчей с SofaScore")
            
            self.driver = webdriver.Chrome(options=self.chrome_options)
            
            # Переходим на главную страницу SofaScore
            self.driver.get('https://www.sofascore.com/')
            time.sleep(8)  # Ждем полной загрузки
            
            # Ищем live матчи на главной странице
            matches = self._extract_live_matches_from_main_page()
            
            if not matches:
                # Если на главной странице не нашли, переходим на страницу спорта
                sport_url = f'https://www.sofascore.com/{sport}/live'
                self.driver.get(sport_url)
                time.sleep(8)
                
                matches = self._extract_live_matches_from_sport_page(sport)
            
            self.logger.info(f"SofaScore актуальный: найдено {len(matches)} {sport} матчей")
            return matches
            
        except Exception as e:
            self.logger.error(f"Ошибка получения актуальных матчей: {e}")
            return []
        finally:
            if self.driver:
                self.driver.quit()
    
    def _extract_live_matches_from_main_page(self) -> List[Dict[str, Any]]:
        """
        Извлечение live матчей с главной страницы
        """
        matches = []
        
        try:
            # Современные селекторы SofaScore
            selectors_to_try = [
                '[data-testid*="event"]',
                '[class*="event"]',
                '[data-testid*="match"]',
                '[class*="match"]',
                '[class*="Box"]',
                '.live-match',
                '[data-sport="football"]',
                'div[class*="live"]'
            ]
            
            for selector in selectors_to_try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                
                if elements:
                    self.logger.info(f"Найдено {len(elements)} элементов с селектором {selector}")
                    
                    for element in elements[:30]:  # Ограничиваем анализ
                        match_data = self._extract_match_from_element(element)
                        if match_data:
                            matches.append(match_data)
                    
                    if len(matches) >= 10:  # Если нашли достаточно матчей
                        break
            
            # Убираем дубликаты
            unique_matches = self._remove_duplicates(matches)
            return unique_matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения с главной страницы: {e}")
            return []
    
    def _extract_live_matches_from_sport_page(self, sport: str) -> List[Dict[str, Any]]:
        """
        Извлечение матчей со специальной страницы спорта
        """
        matches = []
        
        try:
            # Ждем загрузки live контента
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Ищем контейнеры с live матчами
            live_containers = [
                '[data-testid*="live"]',
                '[class*="live"]',
                '[data-testid*="event"]',
                '.tournament-events',
                '.match-list',
                '.events-list'
            ]
            
            for container_selector in live_containers:
                containers = self.driver.find_elements(By.CSS_SELECTOR, container_selector)
                
                for container in containers:
                    # Ищем матчи внутри контейнера
                    match_elements = container.find_elements(By.CSS_SELECTOR, 
                        'div, [data-testid*="match"], [class*="match"], [class*="event"]')
                    
                    for element in match_elements:
                        match_data = self._extract_match_from_element(element)
                        if match_data:
                            matches.append(match_data)
            
            return self._remove_duplicates(matches)
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения со страницы спорта: {e}")
            return []
    
    def _extract_match_from_element(self, element) -> Dict[str, Any]:
        """
        Извлечение данных матча из элемента
        """
        try:
            text = element.text.strip()
            
            # Фильтруем элементы, не являющиеся матчами
            if not text or len(text) < 5 or len(text) > 300:
                return None
            
            # Исключаем служебные элементы
            exclude_keywords = ['menu', 'login', 'search', 'advertisement', 'cookie', 'accept', 
                               'privacy', 'terms', 'contact', 'about', 'help', 'support']
            
            if any(keyword in text.lower() for keyword in exclude_keywords):
                return None
            
            match_data = {
                'source': 'sofascore_live',
                'sport': 'football',
                'raw_text': text
            }
            
            # Извлекаем команды различными паттернами
            team_patterns = [
                r'(.{3,30})\s+vs\s+(.{3,30})',
                r'(.{3,30})\s+-\s+(.{3,30})',
                r'(.{3,30})\s+(\d+:\d+)\s+(.{3,30})',
                r'(.{3,30})\s+(.{3,30})\s+(\d+:\d+)',
                r'(.{3,30})\s+(.{3,30})(?:\s+LIVE|\s+FT|\s+HT)',
            ]
            
            teams_found = False
            for pattern in team_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    groups = match.groups()
                    
                    if len(groups) >= 2:
                        if len(groups) == 3 and ':' in groups[1]:
                            # Формат: Team1 2:1 Team2
                            team1, score, team2 = groups
                            match_data['team1'] = team1.strip()
                            match_data['team2'] = team2.strip()
                            match_data['score'] = score.strip()
                        elif len(groups) == 3 and ':' in groups[2]:
                            # Формат: Team1 Team2 2:1
                            team1, team2, score = groups
                            match_data['team1'] = team1.strip()
                            match_data['team2'] = team2.strip() 
                            match_data['score'] = score.strip()
                        else:
                            # Формат: Team1 vs Team2
                            team1, team2 = groups[:2]
                            match_data['team1'] = team1.strip()
                            match_data['team2'] = team2.strip()
                            match_data['score'] = 'LIVE'
                        
                        teams_found = True
                        break
            
            if not teams_found:
                return None
            
            # Извлекаем время матча
            time_patterns = [
                r"(\d{1,3}')",  # 63'
                r'(HT|FT|LIVE)',  # Статусы
                r'(\d{2}:\d{2})',  # 01:30
            ]
            
            for pattern in time_patterns:
                time_match = re.search(pattern, text)
                if time_match:
                    match_data['time'] = time_match.group(1)
                    break
            
            if 'time' not in match_data:
                match_data['time'] = 'LIVE'
            
            # Извлекаем коэффициенты если есть
            odds_pattern = r'(\d+\.\d+)'
            odds = re.findall(odds_pattern, text)
            if len(odds) >= 3:
                match_data['odds'] = {
                    '1': odds[0],
                    'X': odds[1], 
                    '2': odds[2]
                }
            
            # Проверяем валидность
            if (match_data.get('team1') and match_data.get('team2') and 
                len(match_data['team1']) > 2 and len(match_data['team2']) > 2 and
                match_data['team1'] != match_data['team2']):
                
                return match_data
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения матча: {e}")
            return None
    
    def _remove_duplicates(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Удаление дубликатов матчей
        """
        seen = set()
        unique = []
        
        for match in matches:
            signature = f"{match.get('team1', '').lower()}_{match.get('team2', '').lower()}"
            if signature not in seen:
                seen.add(signature)
                unique.append(match)
        
        return unique