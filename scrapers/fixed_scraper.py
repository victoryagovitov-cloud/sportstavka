"""
Исправленный скрапер для scores24.live с правильными селекторами
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re
import json
from typing import List, Dict, Any
from config import CHROMEDRIVER_PATH

class FixedScraper:
    """
    Исправленный скрапер с правильными селекторами
    """
    
    def __init__(self, logger):
        self.logger = logger
    
    def get_live_matches(self, url: str, sport: str) -> List[Dict[str, Any]]:
        """
        Получение live матчей с исправленными селекторами
        """
        self.logger.info(f"Сбор live {sport} матчей с {url}")
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        service = Service(CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(30)
        
        try:
            driver.get(url)
            
            # Ждем загрузки и прокручиваем для активации контента
            time.sleep(15)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            
            matches = []
            
            # Метод 1: Ищем через data-testid (найденный атрибут)
            testid_selectors = [
                '[data-testid]',
                '[data-testid*="match"]',
                '[data-testid*="fixture"]',
                '[data-testid*="event"]',
                '[data-testid*="row"]'
            ]
            
            for selector in testid_selectors:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                self.logger.info(f"Селектор {selector}: найдено {len(elements)} элементов")
                
                for elem in elements:
                    match_data = self._extract_from_element(elem, sport)
                    if match_data:
                        matches.append(match_data)
                
                if matches:
                    break
            
            # Метод 2: Поиск через текстовый контент
            if not matches:
                matches = self._extract_from_page_text(driver, sport)
            
            # Метод 3: Поиск через JavaScript данные
            if not matches:
                matches = self._extract_from_js_data(driver, sport)
            
            # Убираем дубликаты
            unique_matches = self._remove_duplicates(matches)
            
            self.logger.info(f"Найдено {len(unique_matches)} уникальных {sport} матчей")
            return unique_matches
            
        except Exception as e:
            self.logger.error(f"Ошибка сбора {sport} матчей: {e}")
            return []
        finally:
            driver.quit()
    
    def _extract_from_element(self, element, sport: str) -> Dict[str, Any]:
        """
        Извлечение данных матча из элемента
        """
        try:
            text = element.text.strip()
            
            if not self._looks_like_match(text):
                return None
            
            # Извлекаем данные
            return self._parse_match_text(text, element, sport)
            
        except Exception:
            return None
    
    def _extract_from_page_text(self, driver, sport: str) -> List[Dict[str, Any]]:
        """
        Извлечение матчей из текста страницы
        """
        try:
            # Получаем весь текст страницы
            page_text = driver.execute_script("return document.body.innerText;")
            
            # Разбиваем на строки и анализируем
            lines = page_text.split('\\n')
            matches = []
            
            for line in lines:
                line = line.strip()
                if self._looks_like_match(line):
                    match_data = self._parse_match_text(line, None, sport)
                    if match_data:
                        matches.append(match_data)
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения из текста: {e}")
            return []
    
    def _extract_from_js_data(self, driver, sport: str) -> List[Dict[str, Any]]:
        """
        Извлечение данных из JavaScript переменных
        """
        try:
            # Ищем данные в window объектах
            js_vars = [
                'window.__INITIAL_STATE__',
                'window.__PRELOADED_STATE__', 
                'window.__DATA__',
                'window.matchesData',
                'window.liveData'
            ]
            
            for var in js_vars:
                try:
                    data = driver.execute_script(f"return {var};")
                    if data:
                        matches = self._parse_js_data(data, sport)
                        if matches:
                            self.logger.info(f"Найдены данные в {var}")
                            return matches
                except:
                    continue
            
            return []
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения JS данных: {e}")
            return []
    
    def _looks_like_match(self, text: str) -> bool:
        """
        Проверяет, похож ли текст на информацию о матче
        """
        if not text or len(text) < 8 or len(text) > 200:
            return False
        
        # Исключаем служебную информацию
        exclude_keywords = [
            'cookie', 'реклама', 'бонус', 'регистрация', 'войти', 'букмекер',
            'коэффициент', 'статья', 'новости', 'результаты', 'расписание',
            'футбол', 'теннис', 'гандбол', 'live', 'scores24', 'ставка'
        ]
        
        text_lower = text.lower()
        for keyword in exclude_keywords:
            if keyword in text_lower:
                return False
        
        # Ищем признаки матча
        has_score = bool(re.search(r'\\d+[:-]\\d+', text))
        has_time = bool(re.search(r'\\d+[\'мин]', text))
        has_teams = bool(re.search(r'\\b[А-Яа-яA-Za-z]{3,}\\s*[-–vs]\\s*[А-Яа-яA-Za-z]{3,}\\b', text))
        has_vs = ' - ' in text or ' vs ' in text.lower() or ' – ' in text
        
        # Нужно минимум 2 признака или явное указание команд
        indicators = sum([has_score, has_time, has_teams, has_vs])
        return indicators >= 2 or has_teams
    
    def _parse_match_text(self, text: str, element, sport: str) -> Dict[str, Any]:
        """
        Парсинг данных матча из текста
        """
        try:
            # Ищем команды/игроков
            team_patterns = [
                r'([А-Яа-яA-Za-z\\s]{3,30})\\s*[-–]\\s*([А-Яа-яA-Za-z\\s]{3,30})',
                r'([А-Яа-яA-Za-z\\s]{3,30})\\s*vs\\s*([А-Яа-яA-Za-z\\s]{3,30})',
                r'([А-Яа-яA-Za-z\\s]{3,30})\\s*-\\s*([А-Яа-яA-Za-z\\s]{3,30})'
            ]
            
            teams = None
            for pattern in team_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    team1 = match.group(1).strip()
                    team2 = match.group(2).strip()
                    
                    # Проверяем валидность названий
                    if (len(team1) >= 3 and len(team2) >= 3 and 
                        team1 != team2 and
                        not team1.isdigit() and not team2.isdigit()):
                        teams = (team1, team2)
                        break
            
            if not teams:
                return None
            
            # Ищем счет
            score_match = re.search(r'(\\d+[:-]\\d+)', text)
            score = score_match.group(1) if score_match else '0:0'
            
            # Ищем время
            time_patterns = [
                r'(\\d+)[\'мин]',
                r'(\\d+)\\s*мин',
                r'(\\d+)\''
            ]
            
            match_time = '0\''
            for pattern in time_patterns:
                time_match = re.search(pattern, text)
                if time_match:
                    match_time = f"{time_match.group(1)}'"
                    break
            
            # Ищем URL
            url = ''
            if element:
                try:
                    if element.tag_name == 'a':
                        url = element.get_attribute('href') or ''
                    else:
                        link = element.find_element(By.TAG_NAME, 'a')
                        url = link.get_attribute('href') if link else ''
                except:
                    pass
            
            # Формируем данные
            if sport == 'tennis':
                return {
                    'player1': teams[0],
                    'player2': teams[1],
                    'sets_score': score,
                    'current_set': '0:0',
                    'tournament': 'Live турнир',
                    'url': url,
                    'sport': sport,
                    'source': 'fixed_scraper'
                }
            else:
                return {
                    'team1': teams[0],
                    'team2': teams[1],
                    'score': score,
                    'time': match_time,
                    'league': 'Live лига',
                    'url': url,
                    'sport': sport,
                    'source': 'fixed_scraper'
                }
                
        except Exception as e:
            return None
    
    def _parse_js_data(self, data, sport: str) -> List[Dict[str, Any]]:
        """
        Парсинг данных из JavaScript объектов
        """
        matches = []
        
        def search_matches(obj, depth=0):
            if depth > 5:
                return
            
            if isinstance(obj, dict):
                # Ищем ключи с матчами
                for key, value in obj.items():
                    if key.lower() in ['matches', 'fixtures', 'events', 'games'] and isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                match = self._parse_match_object(item, sport)
                                if match:
                                    matches.append(match)
                    elif isinstance(value, (dict, list)):
                        search_matches(value, depth + 1)
            elif isinstance(obj, list):
                for item in obj:
                    search_matches(item, depth + 1)
        
        search_matches(data)
        return matches
    
    def _parse_match_object(self, obj: dict, sport: str) -> Dict[str, Any]:
        """
        Парсинг объекта матча из JavaScript данных
        """
        try:
            # Возможные поля для команд
            team1 = (obj.get('homeTeam') or obj.get('home') or 
                    obj.get('team1') or obj.get('participant1') or
                    obj.get('home_team', {}).get('name') if isinstance(obj.get('home_team'), dict) else obj.get('home_team'))
            
            team2 = (obj.get('awayTeam') or obj.get('away') or 
                    obj.get('team2') or obj.get('participant2') or
                    obj.get('away_team', {}).get('name') if isinstance(obj.get('away_team'), dict) else obj.get('away_team'))
            
            if not team1 or not team2:
                return None
            
            # Счет
            score = obj.get('score') or f"{obj.get('homeScore', 0)}:{obj.get('awayScore', 0)}"
            
            # Время
            match_time = obj.get('time') or obj.get('minute') or obj.get('status') or '0\''
            
            # Лига/турнир
            league = (obj.get('league') or obj.get('tournament') or 
                     obj.get('competition') or 'Live матч')
            
            # URL
            url = obj.get('url') or obj.get('link') or obj.get('id', '')
            
            if sport == 'tennis':
                return {
                    'player1': str(team1),
                    'player2': str(team2),
                    'sets_score': str(score),
                    'current_set': '0:0',
                    'tournament': str(league),
                    'url': str(url),
                    'sport': sport,
                    'source': 'js_data'
                }
            else:
                return {
                    'team1': str(team1),
                    'team2': str(team2),
                    'score': str(score),
                    'time': str(match_time),
                    'league': str(league),
                    'url': str(url),
                    'sport': sport,
                    'source': 'js_data'
                }
                
        except Exception:
            return None
    
    def _remove_duplicates(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Удаление дубликатов
        """
        seen = set()
        unique = []
        
        for match in matches:
            key_parts = [
                match.get('team1', match.get('player1', '')),
                match.get('team2', match.get('player2', '')),
                match.get('score', match.get('sets_score', ''))
            ]
            key = '|'.join(key_parts).lower().strip()
            
            if key not in seen and all(part.strip() for part in key_parts):
                seen.add(key)
                unique.append(match)
        
        return unique