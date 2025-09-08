"""
Scores24.live парсер для футбольных live данных
Высокий потенциал: 3,333 временных меток, 2,836 счетов, 1,210 упоминаний футбола
"""
import requests
import time
import re
from typing import List, Dict, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from datetime import datetime

class Scores24Scraper:
    """
    Парсер для Scores24.live - очень перспективный источник футбольных данных
    """
    
    def __init__(self, logger):
        self.logger = logger
        
        # HTTP сессия
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache'
        })
        
        # Chrome настройки для обхода CAPTCHA
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--window-size=1920,1080')
        self.chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)
        self.chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    def get_live_matches(self, sport: str = 'football') -> List[Dict[str, Any]]:
        """
        Получение live футбольных матчей с Scores24.live
        """
        try:
            self.logger.info(f"Scores24: получение live {sport}")
            
            # Сначала пробуем HTTP
            http_matches = self._get_via_http()
            
            if http_matches:
                self.logger.info(f"Scores24 HTTP: {len(http_matches)} матчей")
                return http_matches
            
            # Если HTTP не сработал, используем браузер для обхода CAPTCHA
            browser_matches = self._get_via_browser()
            
            self.logger.info(f"Scores24 итого: {len(browser_matches)} матчей")
            return browser_matches
            
        except Exception as e:
            self.logger.error(f"Scores24 ошибка: {e}")
            return []
    
    def _get_via_http(self) -> List[Dict[str, Any]]:
        """
        HTTP метод извлечения
        """
        try:
            url = 'https://scores24.live/ru/soccer?matchesFilter=live'
            response = self.session.get(url, timeout=15)
            
            if response.status_code != 200:
                return []
            
            # Проверяем на CAPTCHA
            if 'captcha' in response.text.lower():
                self.logger.warning("Scores24 HTTP: обнаружена CAPTCHA")
                return []
            
            matches = self._extract_matches_from_html(response.text)
            return matches
            
        except Exception as e:
            self.logger.warning(f"Scores24 HTTP ошибка: {e}")
            return []
    
    def _get_via_browser(self) -> List[Dict[str, Any]]:
        """
        Браузерный метод для обхода CAPTCHA
        """
        driver = None
        
        try:
            driver = webdriver.Chrome(options=self.chrome_options)
            
            # Убираем признаки автоматизации
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            url = 'https://scores24.live/ru/soccer?matchesFilter=live'
            driver.get(url)
            
            # Ждем загрузки страницы
            WebDriverWait(driver, 20).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            
            # Дополнительное ожидание для загрузки данных
            time.sleep(5)
            
            # Пытаемся найти элементы матчей
            try:
                # Ждем появления элементов с матчами
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
                )
            except:
                pass
            
            page_source = driver.page_source
            matches = self._extract_matches_from_html(page_source)
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Scores24 браузер ошибка: {e}")
            return []
        finally:
            if driver:
                driver.quit()
    
    def _extract_matches_from_html(self, html_content: str) -> List[Dict[str, Any]]:
        """
        Извлечение матчей из HTML контента
        """
        matches = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Множественные стратегии поиска матчей
            matches.extend(self._extract_by_selectors(soup))
            matches.extend(self._extract_by_patterns(html_content))
            matches.extend(self._extract_by_structure(soup))
            
            # Убираем дубли
            unique_matches = self._deduplicate_matches(matches)
            
            self.logger.info(f"Scores24: извлечено {len(unique_matches)} уникальных матчей")
            return unique_matches
            
        except Exception as e:
            self.logger.warning(f"Scores24 извлечение ошибка: {e}")
            return []
    
    def _extract_by_selectors(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Извлечение по CSS селекторам
        """
        matches = []
        
        try:
            # Селекторы для поиска элементов матчей
            selectors = [
                '[class*="match"]',
                '[class*="game"]', 
                '[class*="event"]',
                '[class*="fixture"]',
                '[class*="live"]',
                '[data-*="match"]',
                '.match-row',
                '.game-row',
                '.event-row'
            ]
            
            for selector in selectors:
                elements = soup.select(selector)
                
                for element in elements:
                    match_data = self._parse_match_element(element)
                    if match_data:
                        matches.append(match_data)
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Scores24 селекторы ошибка: {e}")
            return []
    
    def _extract_by_patterns(self, html_content: str) -> List[Dict[str, Any]]:
        """
        УЛУЧШЕННОЕ извлечение по регулярным выражениям с именованными группами
        """
        matches = []
        
        try:
            # УЛУЧШЕННЫЕ ПАТТЕРНЫ с именованными группами для разных видов спорта
            improved_patterns = [
                # ФУТБОЛ: Live матчи с временем
                re.compile(r'(?P<team1>[А-ЯA-Z][а-яa-z\s]{2,25})\s+(?P<score>\d+:\d+)\s+(?P<team2>[А-ЯA-Z][а-яa-z\s]{2,25})\s+(?P<time>\d+[\'′]|LIVE|HT|FT)', re.MULTILINE),
                
                # УНИВЕРСАЛЬНЫЙ: Команда vs Команда
                re.compile(r'(?P<team1>[А-ЯA-Z][а-яa-z\s\.]{2,25})\s+vs\s+(?P<team2>[А-ЯA-Z][а-яa-z\s\.]{2,25})(?:\s+(?P<score>\d+:\d+))?(?:\s+(?P<time>\d+[\'′]|LIVE|HT|FT))?', re.MULTILINE | re.IGNORECASE),
                
                # УНИВЕРСАЛЬНЫЙ: Команда - Команда
                re.compile(r'(?P<team1>[А-ЯA-Z][а-яa-z\s\.]{2,25})\s+[-–—]\s+(?P<team2>[А-ЯA-Z][а-яa-z\s\.]{2,25})(?:\s+(?P<score>\d+:\d+))?(?:\s+(?P<time>\d+[\'′]|LIVE|HT|FT))?', re.MULTILINE | re.IGNORECASE),
                
                # ТЕННИС: Матчи с сетами
                re.compile(r'(?P<team1>[А-ЯA-Z][а-яa-z\s\.]{2,25})\s+(?P<sets>\d+-\d+)\s+(?P<team2>[А-ЯA-Z][а-яa-z\s\.]{2,25})\s+(?P<time>Set\s+\d+|LIVE)', re.MULTILINE | re.IGNORECASE),
                
                # ГАНДБОЛ: Высокие счета
                re.compile(r'(?P<team1>[А-ЯA-Z][а-яa-z\s]{2,25})\s+(?P<score>\d{2}:\d{2})\s+(?P<team2>[А-ЯA-Z][а-яa-z\s]{2,25})\s+(?P<time>\d+[\'′]|LIVE|HT)', re.MULTILINE),
                
                # НАСТОЛЬНЫЙ ТЕННИС: Быстрые матчи
                re.compile(r'(?P<team1>[А-ЯA-Z][а-яa-z\s\.]{2,25})\s+(?P<games>\d+:\d+)\s+(?P<team2>[А-ЯA-Z][а-яa-z\s\.]{2,25})\s+(?P<time>Game\s+\d+|LIVE)', re.MULTILINE | re.IGNORECASE)
            ]
            
            # ВАЛИДАТОРЫ ДЛЯ КАЖДОГО ПОЛЯ
            field_validators = {
                'team1': lambda x: len(x.strip()) >= 3 and not x.strip().isdigit() and bool(re.match(r'^[А-ЯA-Za-z]', x.strip())),
                'team2': lambda x: len(x.strip()) >= 3 and not x.strip().isdigit() and bool(re.match(r'^[А-ЯA-Za-z]', x.strip())),
                'score': lambda x: re.match(r'^\d+[:-]\d+$', x.strip()) if x else True,
                'time': lambda x: x.strip() in ['LIVE', 'HT', 'FT'] or re.match(r'^\d+[\'′]?$', x.strip()) if x else True,
                'sets': lambda x: re.match(r'^\d+-\d+$', x.strip()) if x else True,
                'games': lambda x: re.match(r'^\d+:\d+$', x.strip()) if x else True
            }
            
            # ПРОБУЕМ ПАТТЕРНЫ ПО ПРИОРИТЕТУ
            for i, pattern in enumerate(improved_patterns):
                pattern_matches = list(pattern.finditer(html_content))
                
                self.logger.debug(f"Scores24 паттерн {i+1}: найдено {len(pattern_matches)} совпадений")
                
                for match_obj in pattern_matches:
                    # Извлекаем именованные группы
                    match_data = match_obj.groupdict()
                    
                    # ВАЛИДАЦИЯ КАЖДОГО ПОЛЯ
                    if self._validate_extracted_match_improved(match_data, field_validators):
                        # ОБОГАЩЕНИЕ ДАННЫХ
                        enriched_match = self._enrich_match_data_improved(match_data, i+1)
                        matches.append(enriched_match)
                        
                        # РАННИЙ ВЫХОД при достижении цели
                        if len(matches) >= 15:
                            self.logger.info(f"Scores24: ранний выход на паттерне {i+1} - найдено {len(matches)} матчей")
                            return self._deduplicate_matches_improved(matches)
            
            # ДЕДУПЛИКАЦИЯ по командам
            unique_matches = self._deduplicate_matches_improved(matches)
            
            self.logger.info(f"Scores24 паттерны: извлечено {len(unique_matches)} уникальных матчей")
            return unique_matches
            
        except Exception as e:
            self.logger.warning(f"Scores24 паттерны ошибка: {e}")
            return []
    
    def _validate_extracted_match_improved(self, match_data: Dict[str, str], 
                                          field_validators: Dict[str, callable]) -> bool:
        """
        Улучшенная валидация извлеченного матча
        """
        # Проверяем обязательные поля
        if not match_data.get('team1') or not match_data.get('team2'):
            return False
        
        # Команды должны быть разными
        team1 = match_data['team1'].lower().strip()
        team2 = match_data['team2'].lower().strip()
        if team1 == team2:
            return False
        
        # Валидация каждого поля
        for field, validator in field_validators.items():
            value = match_data.get(field, '')
            if value and not validator(value):
                self.logger.debug(f"Scores24: поле {field} не прошло валидацию: {value}")
                return False
        
        return True
    
    def _enrich_match_data_improved(self, match_data: Dict[str, str], pattern_number: int) -> Dict[str, Any]:
        """
        Обогащение данных матча дополнительной информацией
        """
        enriched = {
            'source': f'scores24_pattern_{pattern_number}',
            'sport': 'football',  # По умолчанию, можно улучшить автоопределением
            'timestamp': datetime.now().isoformat()
        }
        
        # Копируем основные данные
        enriched['team1'] = match_data['team1'].strip()
        enriched['team2'] = match_data['team2'].strip()
        
        # Обрабатываем счет
        if 'score' in match_data and match_data['score']:
            enriched['score'] = match_data['score'].strip()
        elif 'sets' in match_data and match_data['sets']:
            enriched['score'] = match_data['sets'].strip()
            enriched['sport'] = 'tennis'
        elif 'games' in match_data and match_data['games']:
            enriched['score'] = match_data['games'].strip()
            enriched['sport'] = 'table_tennis'
        else:
            enriched['score'] = 'LIVE'
        
        # Обрабатываем время
        if 'time' in match_data and match_data['time']:
            enriched['time'] = match_data['time'].strip()
        else:
            enriched['time'] = 'LIVE'
        
        # Определяем лигу (базовое)
        enriched['league'] = 'Scores24 Live'
        
        # Добавляем метаданные
        enriched['extraction_method'] = f'improved_pattern_{pattern_number}'
        enriched['validation_passed'] = True
        
        return enriched
    
    def _deduplicate_matches_improved(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Улучшенная дедупликация матчей по командам
        """
        unique_matches = []
        seen_pairs = set()
        
        for match in matches:
            team1 = match.get('team1', '').lower().strip()
            team2 = match.get('team2', '').lower().strip()
            
            # Создаем уникальную пару команд (в алфавитном порядке)
            team_pair = tuple(sorted([team1, team2]))
            
            if team_pair not in seen_pairs and team1 != team2:
                seen_pairs.add(team_pair)
                unique_matches.append(match)
        
        return unique_matches
    
    def _extract_by_structure(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Извлечение по структуре HTML (таблицы, строки)
        """
        matches = []
        
        try:
            # Поиск в таблицах
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        match_data = self._parse_table_row(cells)
                        if match_data:
                            matches.append(match_data)
            
            # Поиск в списках
            lists = soup.find_all(['ul', 'ol'])
            for list_elem in lists:
                items = list_elem.find_all('li')
                for item in items:
                    match_data = self._parse_list_item(item)
                    if match_data:
                        matches.append(match_data)
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Scores24 структура ошибка: {e}")
            return []
    
    def _parse_match_element(self, element) -> Dict[str, Any]:
        """
        Парсинг отдельного элемента матча
        """
        try:
            text = element.get_text(strip=True)
            
            # Ищем команды в тексте
            team_pattern = r'([А-ЯA-Z][а-яa-z\s]{2,25})\s+[-–—vs]\s+([А-ЯA-Z][а-яa-z\s]{2,25})'
            team_match = re.search(team_pattern, text)
            
            if team_match:
                team1, team2 = team_match.groups()
                
                if self._is_valid_match(team1, team2):
                    # Ищем дополнительную информацию
                    score = self._extract_score_from_text(text)
                    time_info = self._extract_time_from_text(text)
                    
                    return {
                        'source': 'scores24',
                        'sport': 'football',
                        'team1': team1.strip(),
                        'team2': team2.strip(),
                        'score': score or 'LIVE',
                        'time': time_info or 'LIVE',
                        'league': 'Scores24 Live',
                        'timestamp': datetime.now().isoformat()
                    }
            
            return None
            
        except Exception as e:
            return None
    
    def _process_pattern_match(self, match_groups: tuple) -> Dict[str, Any]:
        """
        Обработка результата регулярного выражения
        """
        try:
            if len(match_groups) == 2:
                # Простой паттерн: команда vs команда
                team1, team2 = match_groups
                if self._is_valid_match(team1, team2):
                    return {
                        'source': 'scores24_pattern',
                        'sport': 'football',
                        'team1': team1.strip(),
                        'team2': team2.strip(),
                        'score': 'LIVE',
                        'time': 'LIVE',
                        'league': 'Scores24 Live',
                        'timestamp': datetime.now().isoformat()
                    }
            
            elif len(match_groups) == 3:
                # Сложный паттерн с дополнительной информацией
                if ':' in match_groups[1] or '-' in match_groups[1]:
                    # Команда Счет Команда
                    team1, score, team2 = match_groups
                else:
                    # Команда Команда Время
                    team1, team2, time_info = match_groups
                    score = 'LIVE'
                
                if self._is_valid_match(team1, team2):
                    return {
                        'source': 'scores24_pattern',
                        'sport': 'football',
                        'team1': team1.strip(),
                        'team2': team2.strip(),
                        'score': score.strip() if 'score' in locals() else 'LIVE',
                        'time': time_info.strip() if 'time_info' in locals() else 'LIVE',
                        'league': 'Scores24 Live',
                        'timestamp': datetime.now().isoformat()
                    }
            
            return None
            
        except Exception as e:
            return None
    
    def _parse_table_row(self, cells) -> Dict[str, Any]:
        """
        Парсинг строки таблицы
        """
        try:
            if len(cells) < 2:
                return None
            
            # Извлекаем текст из ячеек
            cell_texts = [cell.get_text(strip=True) for cell in cells]
            combined_text = ' '.join(cell_texts)
            
            # Ищем команды
            team_pattern = r'([А-ЯA-Z][а-яa-z\s]{2,25})'
            teams = re.findall(team_pattern, combined_text)
            
            if len(teams) >= 2:
                team1, team2 = teams[0], teams[1]
                
                if self._is_valid_match(team1, team2):
                    score = self._extract_score_from_text(combined_text)
                    time_info = self._extract_time_from_text(combined_text)
                    
                    return {
                        'source': 'scores24_table',
                        'sport': 'football',
                        'team1': team1.strip(),
                        'team2': team2.strip(),
                        'score': score or 'LIVE',
                        'time': time_info or 'LIVE',
                        'league': 'Scores24 Live',
                        'timestamp': datetime.now().isoformat()
                    }
            
            return None
            
        except Exception as e:
            return None
    
    def _parse_list_item(self, item) -> Dict[str, Any]:
        """
        Парсинг элемента списка
        """
        try:
            text = item.get_text(strip=True)
            
            # Ищем команды
            team_pattern = r'([А-ЯA-Z][а-яa-z\s]{2,25})\s+[-–—vs]\s+([А-ЯA-Z][а-яa-z\s]{2,25})'
            team_match = re.search(team_pattern, text)
            
            if team_match:
                team1, team2 = team_match.groups()
                
                if self._is_valid_match(team1, team2):
                    score = self._extract_score_from_text(text)
                    time_info = self._extract_time_from_text(text)
                    
                    return {
                        'source': 'scores24_list',
                        'sport': 'football',
                        'team1': team1.strip(),
                        'team2': team2.strip(),
                        'score': score or 'LIVE',
                        'time': time_info or 'LIVE',
                        'league': 'Scores24 Live',
                        'timestamp': datetime.now().isoformat()
                    }
            
            return None
            
        except Exception as e:
            return None
    
    def _extract_score_from_text(self, text: str) -> str:
        """
        Извлечение счета из текста
        """
        try:
            score_patterns = [
                r'(\d+)\s*[-:]\s*(\d+)',
                r'(\d+)\s*-\s*(\d+)',
                r'Score:\s*(\d+)\s*-\s*(\d+)'
            ]
            
            for pattern in score_patterns:
                match = re.search(pattern, text)
                if match:
                    return f"{match.group(1)}-{match.group(2)}"
            
            return None
            
        except Exception as e:
            return None
    
    def _extract_time_from_text(self, text: str) -> str:
        """
        Извлечение времени из текста
        """
        try:
            time_patterns = [
                r"(\d{1,2}[''′])",
                r'(\d{1,2}:\d{2})',
                r'(HT|FT|LIVE)',
                r'(\d{1,2}\s*мин)',
                r'(\d{1,2}[\'\'′]\\s*\\+\\s*\d+)'
            ]
            
            for pattern in time_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return match.group(1)
            
            return None
            
        except Exception as e:
            return None
    
    def _is_valid_match(self, team1: str, team2: str) -> bool:
        """
        Проверка валидности матча
        """
        try:
            if not team1 or not team2:
                return False
            
            if len(team1) < 3 or len(team2) < 3:
                return False
            
            if team1.lower() == team2.lower():
                return False
            
            # Исключаем служебные элементы
            exclude_words = [
                'live', 'результат', 'счет', 'матч', 'футбол', 'soccer',
                'scores24', 'сегодня', 'вчера', 'завтра', 'время'
            ]
            
            for word in exclude_words:
                if word in team1.lower() or word in team2.lower():
                    return False
            
            return True
            
        except Exception as e:
            return False
    
    def _deduplicate_matches(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Удаление дубликатов матчей
        """
        seen = set()
        unique_matches = []
        
        for match in matches:
            try:
                team1 = match.get('team1', '').lower().strip()
                team2 = match.get('team2', '').lower().strip()
                
                signature = f"{min(team1, team2)}_{max(team1, team2)}"
                
                if signature not in seen and len(signature) > 6:
                    seen.add(signature)
                    unique_matches.append(match)
                    
            except Exception as e:
                continue
        
        return unique_matches
    
    def verify_connection(self) -> bool:
        """
        Проверка доступности Scores24.live
        """
        try:
            response = self.session.get('https://scores24.live/', timeout=10)
            return response.status_code == 200
        except:
            return False