"""
Улучшенный скрапер с альтернативными методами
"""
import requests
import time
import re
import json
from typing import List, Dict, Any
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config import CHROMEDRIVER_PATH

class ImprovedScraper:
    """
    Улучшенный скрапер с несколькими методами получения данных
    """
    
    def __init__(self, logger):
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.7339.80 Safari/537.36',
            'Accept': 'application/json, text/html, */*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Cache-Control': 'no-cache'
        })
    
    def get_live_matches_multi_method(self, base_url: str, sport: str) -> List[Dict[str, Any]]:
        """
        Получение live матчей несколькими методами
        """
        matches = []
        
        # Метод 1: Попытка найти API
        try:
            api_matches = self._try_api_method(base_url, sport)
            if api_matches:
                matches.extend(api_matches)
                self.logger.info(f"API метод: найдено {len(api_matches)} матчей")
        except Exception as e:
            self.logger.warning(f"API метод не сработал: {e}")
        
        # Метод 2: Requests + regex парсинг
        if not matches:
            try:
                regex_matches = self._try_regex_method(base_url, sport)
                if regex_matches:
                    matches.extend(regex_matches)
                    self.logger.info(f"Regex метод: найдено {len(regex_matches)} матчей")
            except Exception as e:
                self.logger.warning(f"Regex метод не сработал: {e}")
        
        # Метод 3: Быстрый Selenium с умными селекторами
        if not matches:
            try:
                selenium_matches = self._try_selenium_method(base_url, sport)
                if selenium_matches:
                    matches.extend(selenium_matches)
                    self.logger.info(f"Selenium метод: найдено {len(selenium_matches)} матчей")
            except Exception as e:
                self.logger.warning(f"Selenium метод не сработал: {e}")
        
        return matches
    
    def _try_api_method(self, base_url: str, sport: str) -> List[Dict[str, Any]]:
        """
        Попытка найти API endpoint
        """
        # Возможные API endpoints
        api_urls = [
            f'https://scores24.live/api/v1/{sport}/matches/live',
            f'https://scores24.live/dapi/v3/{sport}/matches/live', 
            f'https://api.scores24.live/v1/{sport}/live',
            f'https://scores24.live/api/matches?sport={sport}&filter=live',
            f'https://scores24.live/dapi/v3/matches?sport={sport}&status=live'
        ]
        
        for api_url in api_urls:
            try:
                response = self.session.get(api_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, (list, dict)) and data:
                        self.logger.info(f"✅ Рабочий API: {api_url}")
                        return self._parse_api_response(data, sport)
            except:
                continue
        
        return []
    
    def _try_regex_method(self, base_url: str, sport: str) -> List[Dict[str, Any]]:
        """
        Парсинг через регулярные выражения
        """
        try:
            response = self.session.get(base_url, timeout=15)
            if response.status_code != 200:
                return []
            
            html = response.text
            matches = []
            
            # Ищем JSON данные в HTML
            json_patterns = [
                r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
                r'window\.__PRELOADED_STATE__\s*=\s*({.+?});',
                r'"matches"\s*:\s*(\[[^\]]+\])',
                r'"fixtures"\s*:\s*(\[[^\]]+\])',
                r'"events"\s*:\s*(\[[^\]]+\])'
            ]
            
            for pattern in json_patterns:
                json_matches = re.findall(pattern, html, re.DOTALL)
                for json_str in json_matches:
                    try:
                        data = json.loads(json_str)
                        parsed = self._parse_json_data(data, sport)
                        if parsed:
                            matches.extend(parsed)
                            break
                    except:
                        continue
                if matches:
                    break
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Regex метод ошибка: {e}")
            return []
    
    def _try_selenium_method(self, base_url: str, sport: str) -> List[Dict[str, Any]]:
        """
        Быстрый Selenium с умными селекторами
        """
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-images')
        chrome_options.add_argument('--page-load-strategy=eager')  # Не ждем полной загрузки
        
        service = Service(CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(20)
        
        try:
            driver.get(base_url)
            time.sleep(8)  # Минимальное ожидание
            
            matches = []
            
            # Универсальные селекторы для современных сайтов
            selectors = [
                'tr',  # Строки таблицы
                'div[class*="row"]',
                'div[class*="item"]',
                'a[href*="/match/"]',
                'a[href*="/event/"]',
                '[data-id]'
            ]
            
            for selector in selectors:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                
                for elem in elements[:20]:  # Проверяем первые 20 элементов
                    text = elem.text.strip()
                    
                    # Проверяем, содержит ли элемент информацию о матче
                    if self._looks_like_match(text):
                        match_data = self._extract_match_from_text(text, elem, sport)
                        if match_data:
                            matches.append(match_data)
                
                if len(matches) > 5:  # Если нашли достаточно матчей
                    break
            
            return matches
            
        finally:
            driver.quit()
    
    def _looks_like_match(self, text: str) -> bool:
        """
        Проверяет, похож ли текст на информацию о матче
        """
        if not text or len(text) < 10:
            return False
        
        # Признаки матча
        match_indicators = [
            re.search(r'\w+\s*[-vs]\s*\w+', text),  # Команды
            re.search(r'\d+[:-]\d+', text),         # Счет
            re.search(r'\d+[\'мин]', text),         # Время
            'live' in text.lower(),
            'мин' in text.lower()
        ]
        
        return sum(bool(indicator) for indicator in match_indicators) >= 2
    
    def _extract_match_from_text(self, text: str, element, sport: str) -> Dict[str, Any]:
        """
        Извлекает данные матча из текста
        """
        try:
            # Ищем команды
            team_match = re.search(r'(.+?)\s*[-vs]\s*(.+?)(?:\s|$)', text, re.IGNORECASE)
            if not team_match:
                return None
            
            team1, team2 = team_match.group(1).strip(), team_match.group(2).strip()
            
            # Ищем счет
            score_match = re.search(r'(\d+[:-]\d+)', text)
            score = score_match.group(1) if score_match else '0:0'
            
            # Ищем время
            time_match = re.search(r'(\d+[\'мин])', text)
            match_time = time_match.group(1) if time_match else '0\''
            
            # Ищем URL
            url = ''
            if element.tag_name == 'a':
                url = element.get_attribute('href') or ''
            else:
                link = element.find_element(By.TAG_NAME, 'a')
                url = link.get_attribute('href') if link else ''
            
            return {
                'team1': team1,
                'team2': team2, 
                'score': score,
                'time': match_time,
                'league': 'Определяется',
                'url': url,
                'sport': sport,
                'source': 'selenium_text'
            }
            
        except:
            return None
    
    def _parse_api_response(self, data, sport: str) -> List[Dict[str, Any]]:
        """
        Парсинг ответа API
        """
        matches = []
        
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    match = self._parse_match_item(item, sport)
                    if match:
                        matches.append(match)
        elif isinstance(data, dict):
            # Ищем массивы матчей в объекте
            for key, value in data.items():
                if isinstance(value, list) and value:
                    for item in value:
                        if isinstance(item, dict):
                            match = self._parse_match_item(item, sport)
                            if match:
                                matches.append(match)
        
        return matches
    
    def _parse_match_item(self, item: dict, sport: str) -> Dict[str, Any]:
        """
        Парсинг отдельного элемента матча из API
        """
        try:
            # Различные возможные структуры API
            team1 = (item.get('home_team') or item.get('team1') or 
                    item.get('homeTeam') or item.get('participants', [{}])[0].get('name', ''))
            team2 = (item.get('away_team') or item.get('team2') or 
                    item.get('awayTeam') or item.get('participants', [{}])[1].get('name', ''))
            
            score = (item.get('score') or item.get('result') or 
                    f"{item.get('home_score', 0)}:{item.get('away_score', 0)}")
            
            match_time = (item.get('time') or item.get('minute') or 
                         item.get('status') or '0\'')
            
            league = (item.get('league') or item.get('tournament') or 
                     item.get('competition') or 'Неизвестная лига')
            
            url = item.get('url') or item.get('link') or item.get('id', '')
            
            if team1 and team2:
                return {
                    'team1': str(team1),
                    'team2': str(team2),
                    'score': str(score),
                    'time': str(match_time),
                    'league': str(league),
                    'url': str(url),
                    'sport': sport,
                    'source': 'api'
                }
        except:
            pass
        
        return None
    
    def _parse_json_data(self, data, sport: str) -> List[Dict[str, Any]]:
        """
        Парсинг JSON данных найденных в HTML
        """
        matches = []
        
        def recursive_search(obj, depth=0):
            if depth > 5:  # Ограничиваем глубину
                return
            
            if isinstance(obj, dict):
                # Ищем ключи, связанные с матчами
                match_keys = ['matches', 'fixtures', 'events', 'games']
                for key in match_keys:
                    if key in obj and isinstance(obj[key], list):
                        for item in obj[key]:
                            match = self._parse_match_item(item, sport)
                            if match:
                                matches.append(match)
                
                # Рекурсивно ищем в подобъектах
                for value in obj.values():
                    recursive_search(value, depth + 1)
                    
            elif isinstance(obj, list):
                for item in obj:
                    recursive_search(item, depth + 1)
        
        recursive_search(data)
        return matches