"""
MarathonBet парсер для live спортивных данных с коэффициентами
УЛУЧШЕННАЯ ВЕРСИЯ: поддержка футбола, тенниса, настольного тенниса, гандбола
Высокий потенциал: 157 матчей, 418 коэффициентов
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

class MarathonBetScraper:
    """
    Парсер для MarathonBet.ru - букмекерские данные с коэффициентами
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
        Получение live матчей для всех видов спорта с MarathonBet
        """
        try:
            self.logger.info(f"MarathonBet: получение live {sport}")
            
            # Используем улучшенный метод с коэффициентами
            return self.get_live_matches_with_odds(sport)
            
        except Exception as e:
            self.logger.error(f"MarathonBet {sport} ошибка: {e}")
            return []
    
    def get_live_matches_with_odds(self, sport: str = 'football') -> List[Dict[str, Any]]:
        """
        Получение live матчей с коэффициентами для всех видов спорта
        """
        try:
            self.logger.info(f"MarathonBet: получение {sport} с коэффициентами")
            
            # URL для разных видов спорта
            sport_urls = {
                'football': [
                    'https://www.marathonbet.ru/su/live/popular?',
                    'https://www.marathonbet.ru/su/live/26418',  # Футбол
                    'https://www.marathonbet.ru/su/live/football'
                ],
                'tennis': [
                    'https://www.marathonbet.ru/su/live/26420',  # Теннис
                    'https://www.marathonbet.ru/su/live/tennis'
                ],
                'table_tennis': [
                    'https://www.marathonbet.ru/su/live/26421',  # Настольный теннис
                    'https://www.marathonbet.ru/su/live/table-tennis'
                ],
                'handball': [
                    'https://www.marathonbet.ru/su/live/26422',  # Гандбол
                    'https://www.marathonbet.ru/su/live/handball'
                ]
            }
            
            urls_to_try = sport_urls.get(sport, sport_urls['football'])
            all_matches = []
            
            for url in urls_to_try:
                try:
                    matches = self._get_enhanced_matches_from_url(url, sport)
                    all_matches.extend(matches)
                    if matches:
                        self.logger.info(f"MarathonBet {sport} {url}: {len(matches)} матчей")
                except Exception as e:
                    self.logger.warning(f"MarathonBet {sport} {url} ошибка: {e}")
                    continue
                
                # Пауза между запросами
                time.sleep(1)
            
            # Убираем дубли и улучшаем данные
            unique_matches = self._deduplicate_and_enhance_matches(all_matches)
            
            self.logger.info(f"MarathonBet {sport} всего уникальных: {len(unique_matches)} матчей")
            return unique_matches
            
        except Exception as e:
            self.logger.error(f"MarathonBet {sport} общая ошибка: {e}")
            return []
    
    def _get_enhanced_matches_from_url(self, url: str, sport: str) -> List[Dict[str, Any]]:
        """
        УЛУЧШЕННОЕ получение матчей с конкретного URL
        """
        try:
            # Сначала HTTP
            response = self.session.get(url, timeout=15)
            
            if response.status_code == 200 and 'captcha' not in response.text.lower():
                matches = self._extract_enhanced_matches_from_html(response.text, url, sport)
                if matches:
                    return matches
            
            # Если HTTP не сработал, пробуем браузер
            return self._get_enhanced_via_browser_url(url, sport)
            
        except Exception as e:
            self.logger.warning(f"MarathonBet enhanced {url} ошибка: {e}")
            return []
    
    def _get_enhanced_via_browser_url(self, url: str, sport: str) -> List[Dict[str, Any]]:
        """
        УЛУЧШЕННЫЙ браузерный метод для конкретного URL
        """
        driver = None
        
        try:
            driver = webdriver.Chrome(options=self.chrome_options)
            
            # Убираем признаки автоматизации
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            driver.get(url)
            
            # Ждем загрузки
            WebDriverWait(driver, 20).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            
            # Дополнительное ожидание для AJAX загрузки
            time.sleep(8)
            
            page_source = driver.page_source
            matches = self._extract_enhanced_matches_from_html(page_source, url, sport)
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"MarathonBet enhanced браузер {url} ошибка: {e}")
            return []
        finally:
            if driver:
                driver.quit()
    
    def _extract_enhanced_matches_from_html(self, html_content: str, source_url: str, sport: str) -> List[Dict[str, Any]]:
        """
        УЛУЧШЕННОЕ извлечение матчей из HTML с лучшим алгоритмом коэффициентов
        """
        matches = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 1. УЛУЧШЕННЫЙ поиск через JSON данные
            matches.extend(self._extract_from_json_data(html_content, sport))
            
            # 2. УЛУЧШЕННЫЙ поиск через data-атрибуты
            matches.extend(self._extract_from_data_attributes(soup, sport))
            
            # 3. УЛУЧШЕННЫЙ поиск через структурные селекторы
            matches.extend(self._extract_from_structural_selectors(soup, sport))
            
            # 4. Классический поиск по паттернам (как резерв)
            matches.extend(self._extract_by_patterns(html_content, source_url, sport))
            
            # Убираем дубли и обогащаем данные
            unique_matches = self._deduplicate_and_enhance_matches(matches)
            
            return unique_matches
            
        except Exception as e:
            self.logger.warning(f"MarathonBet enhanced извлечение ошибка: {e}")
            return []
    
    def _extract_from_json_data(self, html_content: str, sport: str) -> List[Dict[str, Any]]:
        """
        НОВЫЙ: Извлечение из JSON данных в <script> тегах
        """
        matches = []
        
        try:
            # Ищем JSON данные в script тегах
            json_patterns = [
                r'\"events\":\s*\[(.*?)\]',
                r'\"matches\":\s*\[(.*?)\]',
                r'\"games\":\s*\[(.*?)\]',
                r'\"selections\":\s*\[(.*?)\]'
            ]
            
            for pattern in json_patterns:
                json_matches = re.findall(pattern, html_content, re.DOTALL)
                
                for json_data in json_matches:
                    # Ищем команды и коэффициенты в JSON
                    team_in_json = re.findall(r'\"name\":\s*\"([^\"]+)\"', json_data)
                    odds_in_json = re.findall(r'\"odds?\":\s*(\d+\.\d{1,2})', json_data)
                    
                    if len(team_in_json) >= 2 and odds_in_json:
                        for i in range(0, len(team_in_json) - 1, 2):
                            if i + 1 < len(team_in_json):
                                team1 = team_in_json[i]
                                team2 = team_in_json[i + 1]
                                
                                if self._is_valid_match_for_sport(team1, team2, sport):
                                    match_data = {
                                        'source': 'marathonbet_json',
                                        'sport': sport,
                                        'team1': team1.strip(),
                                        'team2': team2.strip(),
                                        'score': 'LIVE',
                                        'time': 'LIVE',
                                        'league': f'MarathonBet {sport.title()}',
                                        'timestamp': datetime.now().isoformat()
                                    }
                                    
                                    # Берем соответствующие коэффициенты
                                    if len(odds_in_json) >= 3:
                                        match_data['odds'] = {
                                            'П1': odds_in_json[0],
                                            'X': odds_in_json[1],
                                            'П2': odds_in_json[2]
                                        }
                                    
                                    matches.append(match_data)
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"MarathonBet JSON извлечение ошибка: {e}")
            return []
    
    def _extract_from_data_attributes(self, soup: BeautifulSoup, sport: str) -> List[Dict[str, Any]]:
        """
        НОВЫЙ: Извлечение через data-атрибуты HTML
        """
        matches = []
        
        try:
            # Ищем элементы с data-атрибутами событий
            data_selectors = [
                '[data-event-id]',
                '[data-match-id]',
                '[data-selection-id]',
                '[data-market-id]',
                '[data-outcome-id]'
            ]
            
            for selector in data_selectors:
                elements = soup.select(selector)
                
                for element in elements:
                    # Извлекаем ID события
                    event_id = (element.get('data-event-id') or 
                              element.get('data-match-id') or
                              element.get('data-selection-id'))
                    
                    if event_id:
                        # Ищем все элементы с тем же event-id
                        related_elements = soup.select(f'[data-event-id=\"{event_id}\"], [data-match-id=\"{event_id}\"]')
                        
                        # Собираем данные из связанных элементов
                        match_data = self._parse_related_elements(related_elements, sport)
                        if match_data:
                            matches.append(match_data)
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"MarathonBet data-атрибуты ошибка: {e}")
            return []
    
    def _extract_from_structural_selectors(self, soup: BeautifulSoup, sport: str) -> List[Dict[str, Any]]:
        """
        НОВЫЙ: Извлечение через структурные CSS селекторы
        """
        matches = []
        
        try:
            # Специфичные селекторы для MarathonBet
            structural_selectors = [
                '.event-row, .match-row',
                '.outcome-line, .selection-line',
                '.market-group .outcome',
                '.event-info .teams',
                '.live-event .participants',
                'tr[data-event-id]',
                'div[class*=\"live\"][class*=\"event\"]'
            ]
            
            for selector in structural_selectors:
                elements = soup.select(selector)
                
                for element in elements:
                    match_data = self._parse_structural_element(element, sport)
                    if match_data:
                        matches.append(match_data)
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"MarathonBet структурные селекторы ошибка: {e}")
            return []
    
    def _parse_related_elements(self, elements: list, sport: str) -> Dict[str, Any]:
        """
        Парсинг связанных элементов с одним event-id
        """
        try:
            teams = []
            odds = []
            time_info = None
            score_info = None
            
            for element in elements:
                text = element.get_text(strip=True)
                
                # Ищем команды
                team_matches = re.findall(r'([А-ЯA-Z][а-яa-z\s]{2,25})', text)
                teams.extend(team_matches)
                
                # Ищем коэффициенты
                odd_matches = re.findall(r'(\d+\.\d{1,2})', text)
                for odd in odd_matches:
                    if 1.01 <= float(odd) <= 50.0:
                        odds.append(odd)
                
                # Ищем время
                if not time_info:
                    time_info = self._extract_time_from_text(text)
                
                # Ищем счет
                if not score_info:
                    score_info = self._extract_score_from_text(text)
            
            # Формируем матч если есть команды
            if len(teams) >= 2:
                team1, team2 = teams[0], teams[1]
                
                if self._is_valid_match_for_sport(team1, team2, sport):
                    match_data = {
                        'source': 'marathonbet_enhanced',
                        'sport': sport,
                        'team1': team1.strip(),
                        'team2': team2.strip(),
                        'score': score_info or 'LIVE',
                        'time': time_info or 'LIVE',
                        'league': f'MarathonBet {sport.title()}',
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Добавляем коэффициенты если есть
                    if len(odds) >= 3:
                        match_data['odds'] = {
                            'П1': odds[0],
                            'X': odds[1],
                            'П2': odds[2]
                        }
                    elif len(odds) >= 2:
                        match_data['odds'] = {
                            'П1': odds[0],
                            'П2': odds[1]
                        }
                    
                    return match_data
            
            return None
            
        except Exception as e:
            return None
    
    def _parse_structural_element(self, element, sport: str) -> Dict[str, Any]:
        """
        Парсинг структурного элемента
        """
        try:
            text = element.get_text(strip=True)
            
            # Ищем команды в зависимости от вида спорта
            team_patterns = self._get_sport_team_patterns(sport)
            
            for pattern in team_patterns:
                team_match = re.search(pattern, text)
                if team_match:
                    teams = team_match.groups()
                    
                    if len(teams) >= 2:
                        team1, team2 = teams[0], teams[1]
                        
                        if self._is_valid_match_for_sport(team1, team2, sport):
                            # Ищем коэффициенты в том же элементе
                            odds = self._extract_odds_from_element(element)
                            score = self._extract_score_from_text(text)
                            time_info = self._extract_time_from_text(text)
                            
                            match_data = {
                                'source': 'marathonbet_structural',
                                'sport': sport,
                                'team1': team1.strip(),
                                'team2': team2.strip(),
                                'score': score or 'LIVE',
                                'time': time_info or 'LIVE',
                                'league': f'MarathonBet {sport.title()}',
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            if odds:
                                match_data['odds'] = odds
                            
                            return match_data
            
            return None
            
        except Exception as e:
            return None
    
    def _get_sport_team_patterns(self, sport: str) -> List[str]:
        """
        Получение паттернов для команд в зависимости от вида спорта
        """
        base_patterns = [
            r'([А-ЯA-Z][а-яa-z\s]{2,30})\s+vs\s+([А-ЯA-Z][а-яa-z\s]{2,30})',
            r'([А-ЯA-Z][а-яa-z\s]{2,30})\s+[-–—]\s+([А-ЯA-Z][а-яa-z\s]{2,30})',
        ]
        
        if sport == 'tennis':
            # Для тенниса часто используются фамилии
            base_patterns.extend([
                r'([А-ЯA-Z][а-яa-z]+\s+[А-ЯA-Z]\.?)\s+vs\s+([А-ЯA-Z][а-яa-z]+\s+[А-ЯA-Z]\.?)',
                r'([А-ЯA-Z][а-яa-z]+)\s+([А-ЯA-Z]\.?)\s+[-–—]\s+([А-ЯA-Z][а-яa-z]+)\s+([А-ЯA-Z]\.?)',
            ])
        elif sport == 'handball':
            # Для гандбола часто клубные названия
            base_patterns.extend([
                r'([А-ЯA-Z][а-яa-z\s]{2,35})\s+vs\s+([А-ЯA-Z][а-яa-z\s]{2,35})',
            ])
        
        return base_patterns
    
    def _is_valid_match_for_sport(self, team1: str, team2: str, sport: str) -> bool:
        """
        Проверка валидности матча для конкретного вида спорта
        """
        try:
            if not team1 or not team2:
                return False
            
            if len(team1) < 2 or len(team2) < 2:
                return False
            
            if team1.lower() == team2.lower():
                return False
            
            # Базовые исключения
            exclude_words = [
                'live', 'ставка', 'коэф', 'бонус', 'меню', 'войти', 'регистр',
                'marathonbet', 'марафон', 'букмекер', 'линия', 'лайв'
            ]
            
            # Специфичные исключения по видам спорта
            sport_excludes = {
                'football': ['футбол', 'football', 'soccer'],
                'tennis': ['теннис', 'tennis'],
                'table_tennis': ['настольный', 'пинг-понг', 'table'],
                'handball': ['гандбол', 'handball']
            }
            
            all_excludes = exclude_words + sport_excludes.get(sport, [])
            
            for word in all_excludes:
                if word in team1.lower() or word in team2.lower():
                    return False
            
            # Специфичная валидация по видам спорта
            if sport == 'tennis':
                # Для тенниса проверяем наличие фамилий
                if not (re.search(r'[А-ЯA-Z][а-яa-z]+', team1) and re.search(r'[А-ЯA-Z][а-яa-z]+', team2)):
                    return False
            
            return True
            
        except Exception as e:
            return False
    
    def _deduplicate_and_enhance_matches(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        УЛУЧШЕННАЯ дедупликация и обогащение матчей
        """
        seen = {}
        enhanced_matches = []
        
        for match in matches:
            try:
                team1 = match.get('team1', '').lower().strip()
                team2 = match.get('team2', '').lower().strip()
                
                signature = f"{min(team1, team2)}_{max(team1, team2)}"
                
                if signature in seen:
                    # Обогащаем существующий матч
                    existing_match = seen[signature]
                    
                    # Добавляем коэффициенты если их не было
                    if 'odds' not in existing_match and 'odds' in match:
                        existing_match['odds'] = match['odds']
                    
                    # Улучшаем время если есть более точное
                    if match.get('time') and match['time'] != 'LIVE':
                        existing_match['time'] = match['time']
                    
                    # Улучшаем счет если есть более точный
                    if match.get('score') and match['score'] != 'LIVE':
                        existing_match['score'] = match['score']
                        
                else:
                    # Новый матч
                    if len(signature) > 6:
                        seen[signature] = match
                        enhanced_matches.append(match)
                        
            except Exception as e:
                continue
        
        # Сортируем по качеству данных (матчи с коэффициентами в начале)
        enhanced_matches.sort(key=lambda m: len(m.get('odds', {})), reverse=True)
        
        return enhanced_matches
    
    def _find_enhanced_odds_for_match(self, html_content: str, team1: str, team2: str) -> Dict[str, str]:
        """
        УЛУЧШЕННЫЙ поиск коэффициентов для конкретного матча
        """
        try:
            # Стратегия 1: Расширенный контекст
            team1_positions = [m.start() for m in re.finditer(re.escape(team1), html_content, re.IGNORECASE)]
            team2_positions = [m.start() for m in re.finditer(re.escape(team2), html_content, re.IGNORECASE)]
            
            for t1_pos in team1_positions:
                for t2_pos in team2_positions:
                    if abs(t1_pos - t2_pos) < 1000:  # Увеличенный контекст
                        start_pos = min(t1_pos, t2_pos) - 500
                        end_pos = max(t1_pos, t2_pos) + 500
                        context = html_content[max(0, start_pos):min(len(html_content), end_pos)]
                        
                        odds = self._extract_odds_from_context(context)
                        if odds:
                            return odds
            
            # Стратегия 2: Поиск по ID события
            # Ищем data-event-id или похожие идентификаторы рядом с командами
            event_id_pattern = rf'{re.escape(team1)}.*?data-event-id=\"(\d+)\".*?{re.escape(team2)}'
            event_match = re.search(event_id_pattern, html_content, re.DOTALL | re.IGNORECASE)
            
            if event_match:
                event_id = event_match.group(1)
                # Ищем коэффициенты с тем же event-id
                odds_pattern = rf'data-event-id=\"{event_id}\".*?(\d+\.\d{{1,2}})'
                odds_matches = re.findall(odds_pattern, html_content)
                
                valid_odds = [odd for odd in odds_matches if 1.01 <= float(odd) <= 50.0]
                if len(valid_odds) >= 3:
                    return {
                        'П1': valid_odds[0],
                        'X': valid_odds[1],
                        'П2': valid_odds[2]
                    }
            
            # Стратегия 3: Глобальный поиск ближайших коэффициентов
            return self._find_nearest_odds(html_content, team1, team2)
            
        except Exception as e:
            return {}
    
    def _extract_odds_from_context(self, context: str) -> Dict[str, str]:
        """
        Извлечение коэффициентов из контекста
        """
        try:
            odds_matches = re.findall(r'(\d+\.\d{1,2})', context)
            
            valid_odds = []
            for odd in odds_matches:
                odd_float = float(odd)
                if 1.01 <= odd_float <= 50.0:
                    valid_odds.append(odd)
            
            if len(valid_odds) >= 3:
                return {
                    'П1': valid_odds[0],
                    'X': valid_odds[1],
                    'П2': valid_odds[2]
                }
            elif len(valid_odds) >= 2:
                return {
                    'П1': valid_odds[0],
                    'П2': valid_odds[1]
                }
            
            return {}
            
        except Exception as e:
            return {}
    
    def _find_nearest_odds(self, html_content: str, team1: str, team2: str) -> Dict[str, str]:
        """
        Поиск ближайших коэффициентов к командам
        """
        try:
            # Находим все позиции команд и коэффициентов
            team1_pos = html_content.lower().find(team1.lower())
            team2_pos = html_content.lower().find(team2.lower())
            
            if team1_pos == -1 or team2_pos == -1:
                return {}
            
            match_center = (team1_pos + team2_pos) // 2
            
            # Ищем все коэффициенты с их позициями
            odds_with_positions = []
            for match in re.finditer(r'(\d+\.\d{1,2})', html_content):
                odd_value = float(match.group(1))
                if 1.01 <= odd_value <= 50.0:
                    odds_with_positions.append((match.start(), match.group(1)))
            
            # Сортируем коэффициенты по близости к матчу
            odds_with_positions.sort(key=lambda x: abs(x[0] - match_center))
            
            # Берем 3 ближайших коэффициента
            nearest_odds = [odd[1] for odd in odds_with_positions[:3]]
            
            if len(nearest_odds) >= 3:
                return {
                    'П1': nearest_odds[0],
                    'X': nearest_odds[1],
                    'П2': nearest_odds[2]
                }
            elif len(nearest_odds) >= 2:
                return {
                    'П1': nearest_odds[0],
                    'П2': nearest_odds[1]
                }
            
            return {}
            
        except Exception as e:
            return {}
    
    def _get_matches_from_url(self, url: str) -> List[Dict[str, Any]]:
        """
        Получение матчей с конкретного URL
        """
        try:
            # Сначала HTTP
            response = self.session.get(url, timeout=15)
            
            if response.status_code == 200 and 'captcha' not in response.text.lower():
                matches = self._extract_matches_from_html(response.text, url)
                if matches:
                    return matches
            
            # Если HTTP не сработал, пробуем браузер
            return self._get_via_browser_url(url)
            
        except Exception as e:
            self.logger.warning(f"MarathonBet {url} ошибка: {e}")
            return []
    
    def _get_via_http(self) -> List[Dict[str, Any]]:
        """
        HTTP метод извлечения
        """
        try:
            url = 'https://www.marathonbet.ru/su/live/popular?'
            response = self.session.get(url, timeout=15)
            
            if response.status_code != 200:
                return []
            
            # Проверяем на CAPTCHA
            if 'captcha' in response.text.lower():
                self.logger.warning("MarathonBet HTTP: обнаружена CAPTCHA")
                return []
            
            matches = self._extract_matches_from_html(response.text, url)
            return matches
            
        except Exception as e:
            self.logger.warning(f"MarathonBet HTTP ошибка: {e}")
            return []
    
    def _get_via_browser(self) -> List[Dict[str, Any]]:
        """
        Браузерный метод для обхода CAPTCHA
        """
        return self._get_via_browser_url('https://www.marathonbet.ru/su/live/popular?')
    
    def _get_via_browser_url(self, url: str) -> List[Dict[str, Any]]:
        """
        Браузерный метод для конкретного URL
        """
        driver = None
        
        try:
            driver = webdriver.Chrome(options=self.chrome_options)
            
            # Убираем признаки автоматизации
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            driver.get(url)
            
            # Ждем загрузки
            WebDriverWait(driver, 20).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            
            # Дополнительное ожидание для AJAX загрузки
            time.sleep(10)
            
            page_source = driver.page_source
            matches = self._extract_matches_from_html(page_source, url)
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"MarathonBet браузер {url} ошибка: {e}")
            return []
        finally:
            if driver:
                driver.quit()
    
    def _extract_matches_from_html(self, html_content: str, source_url: str) -> List[Dict[str, Any]]:
        """
        Извлечение матчей из HTML
        """
        matches = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Множественные стратегии извлечения
            matches.extend(self._extract_by_selectors(soup, source_url))
            matches.extend(self._extract_by_patterns(html_content, source_url))
            matches.extend(self._extract_by_odds_context(html_content, source_url))
            
            # Убираем дубли
            unique_matches = self._deduplicate_matches(matches)
            
            return unique_matches
            
        except Exception as e:
            self.logger.warning(f"MarathonBet извлечение ошибка: {e}")
            return []
    
    def _extract_by_selectors(self, soup: BeautifulSoup, source_url: str) -> List[Dict[str, Any]]:
        """
        Извлечение по CSS селекторам
        """
        matches = []
        
        try:
            # Селекторы для MarathonBet
            selectors = [
                '[class*="event"]',
                '[class*="match"]',
                '[class*="game"]',
                '[class*="market"]',
                '[class*="outcome"]',
                '[data-*="event"]',
                '.event-row',
                '.match-row'
            ]
            
            for selector in selectors:
                elements = soup.select(selector)
                
                for element in elements:
                    match_data = self._parse_match_element(element, source_url)
                    if match_data:
                        matches.append(match_data)
            
            return matches
            
        except Exception as e:
            return []
    
    def _extract_by_patterns(self, html_content: str, source_url: str, sport: str = 'football') -> List[Dict[str, Any]]:
        """
        Извлечение по регулярным выражениям
        """
        matches = []
        
        try:
            # Получаем паттерны для конкретного вида спорта
            team_patterns = self._get_sport_team_patterns(sport)
            
            for pattern in team_patterns:
                pattern_matches = re.findall(pattern, html_content)
                
                for match_groups in pattern_matches:
                    match_data = self._process_pattern_match(match_groups, source_url, sport)
                    if match_data:
                        # УЛУЧШЕННЫЙ поиск коэффициентов
                        odds = self._find_enhanced_odds_for_match(html_content, match_data['team1'], match_data['team2'])
                        if odds:
                            match_data['odds'] = odds
                        
                        matches.append(match_data)
            
            return matches
            
        except Exception as e:
            return []
    
    def _extract_by_odds_context(self, html_content: str, source_url: str) -> List[Dict[str, Any]]:
        """
        Извлечение через контекст коэффициентов
        """
        matches = []
        
        try:
            # Ищем коэффициенты и команды рядом с ними
            odds_pattern = r'(\d+\.\d{1,2})'
            odds_matches = re.finditer(odds_pattern, html_content)
            
            for odds_match in odds_matches:
                odd_value = float(odds_match.group(1))
                
                # Фильтруем разумные коэффициенты
                if 1.01 <= odd_value <= 50.0:
                    # Ищем контекст вокруг коэффициента
                    start_pos = max(0, odds_match.start() - 200)
                    end_pos = min(len(html_content), odds_match.end() + 200)
                    context = html_content[start_pos:end_pos]
                    
                    # Ищем команды в контексте
                    team_pattern = r'([А-ЯA-Z][а-яa-z\s]{2,25})\s+[-–—vs]\s+([А-ЯA-Z][а-яa-z\s]{2,25})'
                    team_match = re.search(team_pattern, context)
                    
                    if team_match:
                        team1, team2 = team_match.groups()
                        
                        if self._is_valid_match(team1, team2):
                            # Ищем все коэффициенты для этого матча
                            match_odds = self._find_odds_for_match(context, team1, team2)
                            
                            match_data = {
                                'source': 'marathonbet_odds',
                                'sport': 'football',
                                'team1': team1.strip(),
                                'team2': team2.strip(),
                                'score': 'LIVE',
                                'time': 'LIVE',
                                'league': 'MarathonBet Live',
                                'url': source_url,
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            if match_odds:
                                match_data['odds'] = match_odds
                            
                            matches.append(match_data)
            
            return matches
            
        except Exception as e:
            return []
    
    def _parse_match_element(self, element, source_url: str) -> Dict[str, Any]:
        """
        Парсинг элемента с матчем
        """
        try:
            text = element.get_text(strip=True)
            
            # Ищем команды
            team_pattern = r'([А-ЯA-Z][а-яa-z\s]{2,25})\s+[-–—vs]\s+([А-ЯA-Z][а-яa-z\s]{2,25})'
            team_match = re.search(team_pattern, text)
            
            if team_match:
                team1, team2 = team_match.groups()
                
                if self._is_valid_match(team1, team2):
                    # Ищем дополнительную информацию
                    score = self._extract_score_from_text(text)
                    time_info = self._extract_time_from_text(text)
                    odds = self._extract_odds_from_element(element)
                    
                    match_data = {
                        'source': 'marathonbet',
                        'sport': 'football',
                        'team1': team1.strip(),
                        'team2': team2.strip(),
                        'score': score or 'LIVE',
                        'time': time_info or 'LIVE',
                        'league': 'MarathonBet Live',
                        'url': source_url,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    if odds:
                        match_data['odds'] = odds
                    
                    return match_data
            
            return None
            
        except Exception as e:
            return None
    
    def _process_pattern_match(self, match_groups: tuple, source_url: str, sport: str = 'football') -> Dict[str, Any]:
        """
        Обработка результата регулярного выражения
        """
        try:
            if len(match_groups) == 2:
                team1, team2 = match_groups
                score = 'LIVE'
                time_info = 'LIVE'
            elif len(match_groups) == 3:
                if ':' in match_groups[1]:
                    team1, score, team2 = match_groups
                    time_info = 'LIVE'
                else:
                    team1, team2, time_info = match_groups
                    score = 'LIVE'
            else:
                return None
            
            if self._is_valid_match_for_sport(team1, team2, sport):
                return {
                    'source': 'marathonbet_pattern',
                    'sport': sport,
                    'team1': team1.strip(),
                    'team2': team2.strip(),
                    'score': score.strip() if score != 'LIVE' else 'LIVE',
                    'time': time_info.strip() if time_info != 'LIVE' else 'LIVE',
                    'league': f'MarathonBet {sport.title()}',
                    'url': source_url,
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
    
    def _extract_odds_from_element(self, element) -> Dict[str, str]:
        """
        Извлечение коэффициентов из элемента
        """
        try:
            text = element.get_text()
            
            # Ищем коэффициенты
            odds_matches = re.findall(r'(\d+\.\d{1,2})', text)
            
            # Фильтруем валидные коэффициенты
            valid_odds = []
            for odd in odds_matches:
                odd_float = float(odd)
                if 1.01 <= odd_float <= 50.0:
                    valid_odds.append(odd)
            
            if len(valid_odds) >= 3:
                return {
                    'П1': valid_odds[0],
                    'X': valid_odds[1],
                    'П2': valid_odds[2]
                }
            elif len(valid_odds) >= 2:
                return {
                    'П1': valid_odds[0],
                    'П2': valid_odds[1]
                }
            
            return {}
            
        except Exception as e:
            return {}
    
    def _find_odds_for_match(self, context: str, team1: str, team2: str) -> Dict[str, str]:
        """
        Поиск коэффициентов для конкретного матча
        """
        try:
            # Ищем коэффициенты в контексте
            odds_matches = re.findall(r'(\d+\.\d{1,2})', context)
            
            # Фильтруем валидные коэффициенты
            valid_odds = []
            for odd in odds_matches:
                odd_float = float(odd)
                if 1.01 <= odd_float <= 50.0:
                    valid_odds.append(odd)
            
            if len(valid_odds) >= 3:
                return {
                    'П1': valid_odds[0],
                    'X': valid_odds[1], 
                    'П2': valid_odds[2]
                }
            elif len(valid_odds) >= 2:
                return {
                    'П1': valid_odds[0],
                    'П2': valid_odds[1]
                }
            
            return {}
            
        except Exception as e:
            return {}
    
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
                'live', 'ставка', 'коэф', 'бонус', 'меню', 'войти', 'регистр',
                'marathonbet', 'марафон', 'букмекер', 'линия', 'лайв', 'спорт',
                'футбол', 'football', 'матч', 'событие', 'игра'
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
        Проверка доступности MarathonBet
        """
        try:
            response = self.session.get('https://www.marathonbet.ru/', timeout=10)
            return response.status_code == 200
        except:
            return False