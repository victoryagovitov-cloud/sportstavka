"""
MarathonBet парсер для live футбольных данных с коэффициентами
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
        Получение live футбольных матчей с MarathonBet
        """
        try:
            self.logger.info(f"MarathonBet: получение live {sport}")
            
            # Сначала пробуем HTTP
            http_matches = self._get_via_http()
            
            if http_matches:
                self.logger.info(f"MarathonBet HTTP: {len(http_matches)} матчей")
                return http_matches
            
            # Если HTTP не сработал, используем браузер
            browser_matches = self._get_via_browser()
            
            self.logger.info(f"MarathonBet итого: {len(browser_matches)} матчей")
            return browser_matches
            
        except Exception as e:
            self.logger.error(f"MarathonBet ошибка: {e}")
            return []
    
    def get_live_matches_with_odds(self) -> List[Dict[str, Any]]:
        """
        Получение live матчей с коэффициентами
        """
        try:
            self.logger.info("MarathonBet: получение матчей с коэффициентами")
            
            # Пробуем разные страницы MarathonBet
            urls = [
                'https://www.marathonbet.ru/su/live/popular?',
                'https://www.marathonbet.ru/su/live/football',
                'https://www.marathonbet.ru/su/live'
            ]
            
            all_matches = []
            
            for url in urls:
                try:
                    matches = self._get_matches_from_url(url)
                    all_matches.extend(matches)
                    if matches:
                        self.logger.info(f"MarathonBet {url}: {len(matches)} матчей")
                except Exception as e:
                    self.logger.warning(f"MarathonBet {url} ошибка: {e}")
                    continue
                
                # Пауза между запросами
                time.sleep(2)
            
            # Убираем дубли
            unique_matches = self._deduplicate_matches(all_matches)
            
            self.logger.info(f"MarathonBet всего уникальных: {len(unique_matches)} матчей")
            return unique_matches
            
        except Exception as e:
            self.logger.error(f"MarathonBet общая ошибка: {e}")
            return []
    
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
    
    def _extract_by_patterns(self, html_content: str, source_url: str) -> List[Dict[str, Any]]:
        """
        Извлечение по регулярным выражениям
        """
        matches = []
        
        try:
            # Паттерны для команд
            team_patterns = [
                r'([А-ЯA-Z][а-яa-z\s]{2,30})\s+vs\s+([А-ЯA-Z][а-яa-z\s]{2,30})',
                r'([А-ЯA-Z][а-яa-z\s]{2,30})\s+[-–—]\s+([А-ЯA-Z][а-яa-z\s]{2,30})',
                r'([А-ЯA-Z][а-яa-z\s]{2,30})\s+(\d+:\d+)\s+([А-ЯA-Z][а-яa-z\s]{2,30})',
            ]
            
            for pattern in team_patterns:
                pattern_matches = re.findall(pattern, html_content)
                
                for match_groups in pattern_matches:
                    match_data = self._process_pattern_match(match_groups, source_url)
                    if match_data:
                        # Ищем коэффициенты для этого матча
                        odds = self._find_odds_for_match(html_content, match_data['team1'], match_data['team2'])
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
    
    def _process_pattern_match(self, match_groups: tuple, source_url: str) -> Dict[str, Any]:
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
            
            if self._is_valid_match(team1, team2):
                return {
                    'source': 'marathonbet_pattern',
                    'sport': 'football',
                    'team1': team1.strip(),
                    'team2': team2.strip(),
                    'score': score.strip() if score != 'LIVE' else 'LIVE',
                    'time': time_info.strip() if time_info != 'LIVE' else 'LIVE',
                    'league': 'MarathonBet Live',
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
                r'(\d{1,2}[''′]\s*\+\s*\d+)'
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