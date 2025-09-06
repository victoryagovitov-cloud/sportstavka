"""
BetCity парсер для live спортивных данных
Новый источник для анализа и интеграции
"""
import requests
import time
import re
from typing import List, Dict, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from datetime import datetime

class BetCityScraper:
    """
    Парсер для BetCity.ru - новый источник данных
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
        
        # Chrome настройки
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--window-size=1920,1080')
        self.chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    def get_live_matches(self, sport: str = 'football') -> List[Dict[str, Any]]:
        """
        Получение live матчей с BetCity
        """
        try:
            self.logger.info(f"BetCity: получение live {sport}")
            
            # Сначала пробуем HTTP
            http_matches = self._get_via_http()
            
            if http_matches:
                self.logger.info(f"BetCity HTTP: {len(http_matches)} матчей")
                return http_matches
            
            # Если HTTP не сработал, используем браузер
            browser_matches = self._get_via_browser()
            
            self.logger.info(f"BetCity итого: {len(browser_matches)} матчей")
            return browser_matches
            
        except Exception as e:
            self.logger.error(f"BetCity ошибка: {e}")
            return []
    
    def get_live_matches_with_odds(self) -> List[Dict[str, Any]]:
        """
        Получение live матчей с коэффициентами
        """
        try:
            # Пробуем разные секции сайта
            urls = [
                'https://betcity.ru/live',
                'https://betcity.ru/sport/football/live',
                'https://betcity.ru/sport/tennis/live',
                'https://betcity.ru/live/football',
                'https://betcity.ru/live/tennis'
            ]
            
            all_matches = []
            
            for url in urls:
                try:
                    matches = self._get_matches_from_url(url)
                    all_matches.extend(matches)
                    if matches:
                        self.logger.info(f"BetCity {url}: {len(matches)} матчей")
                except Exception as e:
                    self.logger.warning(f"BetCity {url} ошибка: {e}")
                    continue
                
                # Небольшая пауза между запросами
                time.sleep(2)
            
            # Убираем дубли
            unique_matches = self._clean_betcity_matches(all_matches)
            
            self.logger.info(f"BetCity всего уникальных: {len(unique_matches)} матчей")
            return unique_matches
            
        except Exception as e:
            self.logger.error(f"BetCity общая ошибка: {e}")
            return []
    
    def _get_matches_from_url(self, url: str) -> List[Dict[str, Any]]:
        """
        Получение матчей с конкретного URL
        """
        try:
            # Сначала HTTP
            response = self.session.get(url, timeout=15)
            
            if response.status_code == 200:
                matches = self._extract_matches_from_html(response.text, url)
                if matches:
                    return matches
            
            # Если HTTP не сработал, пробуем браузер
            return self._get_via_browser_url(url)
            
        except Exception as e:
            self.logger.warning(f"BetCity {url} ошибка: {e}")
            return []
    
    def _get_via_http(self) -> List[Dict[str, Any]]:
        """
        HTTP метод извлечения
        """
        try:
            response = self.session.get('https://betcity.ru/live', timeout=15)
            
            if response.status_code != 200:
                return []
            
            page_text = response.text
            
            # Извлекаем матчи из HTML
            matches = self._extract_matches_from_html(page_text, 'https://betcity.ru/live')
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"BetCity HTTP ошибка: {e}")
            return []
    
    def _get_via_browser(self) -> List[Dict[str, Any]]:
        """
        Браузерный метод извлечения
        """
        return self._get_via_browser_url('https://betcity.ru/live')
    
    def _get_via_browser_url(self, url: str) -> List[Dict[str, Any]]:
        """
        Браузерный метод для конкретного URL
        """
        driver = None
        
        try:
            driver = webdriver.Chrome(options=self.chrome_options)
            driver.get(url)
            
            # Ждем загрузки
            time.sleep(15)
            
            # Получаем данные
            page_text = driver.find_element(By.TAG_NAME, 'body').text
            html_content = driver.page_source
            
            # Извлекаем матчи из текста и HTML
            text_matches = self._extract_matches_from_text(page_text)
            html_matches = self._extract_matches_from_html(html_content, url)
            
            # Объединяем результаты
            all_matches = text_matches + html_matches
            
            return self._clean_betcity_matches(all_matches)
            
        except Exception as e:
            self.logger.warning(f"BetCity браузер {url} ошибка: {e}")
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
            
            # Ищем различные элементы с матчами
            selectors = [
                'div[class*="match"]',
                'div[class*="event"]',
                'div[class*="game"]',
                'tr[class*="match"]',
                'tr[class*="event"]',
                '.match-row',
                '.event-row',
                '.game-row'
            ]
            
            for selector in selectors:
                elements = soup.select(selector)
                for element in elements:
                    match_data = self._parse_match_element(element, source_url)
                    if match_data:
                        matches.append(match_data)
            
            # Если специфические селекторы не сработали, ищем по тексту
            if not matches:
                potential_elements = soup.find_all(['div', 'tr', 'td', 'span'], 
                                                 string=re.compile(r'[А-ЯA-Z][а-яa-z\s]{2,20}'))
                
                for element in potential_elements[:50]:
                    text = element.get_text(strip=True)
                    match_data = self._parse_text_for_match(text, source_url)
                    if match_data:
                        matches.append(match_data)
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения из HTML: {e}")
            return []
    
    def _parse_match_element(self, element, source_url: str) -> Dict[str, Any]:
        """
        Парсинг элемента с матчем
        """
        try:
            text = element.get_text(strip=True)
            
            # Ищем команды в тексте элемента
            team_patterns = [
                r'([А-Я][а-я\s]{3,25})\s+[-–—]\s+([А-Я][а-я\s]{3,25})',
                r'([А-Я][а-я\s]{3,25})\s+vs\s+([А-Я][а-я\s]{3,25})',
                r'([A-Z][a-zA-Z\s]{3,25})\s+[-–—]\s+([A-Z][a-zA-Z\s]{3,25})',
                r'([A-Z][a-zA-Z\s]{3,25})\s+vs\s+([A-Z][a-zA-Z\s]{3,25})'
            ]
            
            for pattern in team_patterns:
                match = re.search(pattern, text)
                if match:
                    team1, team2 = match.groups()
                    
                    if self._is_valid_betcity_match(team1, team2):
                        # Ищем дополнительную информацию в элементе
                        score_info = self._extract_score_from_element(element)
                        time_info = self._extract_time_from_element(element)
                        odds_info = self._extract_odds_from_element(element)
                        
                        match_data = {
                            'source': 'betcity',
                            'sport': self._detect_sport_from_context(text),
                            'team1': team1.strip(),
                            'team2': team2.strip(),
                            'score': score_info or 'LIVE',
                            'time': time_info or 'LIVE',
                            'league': 'BetCity Live',
                            'url': source_url,
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        if odds_info:
                            match_data['odds'] = odds_info
                        
                        return match_data
            
            return None
            
        except Exception as e:
            return None
    
    def _extract_score_from_element(self, element) -> str:
        """
        Извлечение счета из элемента
        """
        try:
            text = element.get_text()
            
            # Паттерны для счета
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
    
    def _extract_time_from_element(self, element) -> str:
        """
        Извлечение времени из элемента
        """
        try:
            text = element.get_text()
            
            # Паттерны для времени
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
                if 1.01 <= odd_float <= 100.0:
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
    
    def _extract_matches_from_text(self, page_text: str) -> List[Dict[str, Any]]:
        """
        Извлечение матчей из текста страницы
        """
        matches = []
        
        try:
            # Паттерны для BetCity
            patterns = [
                r'([А-Я][а-я\s]{3,25})\s+[-–—]\s+([А-Я][а-я\s]{3,25})',
                r'([А-Я][а-я\s]{3,25})\s+vs\s+([А-Я][а-я\s]{3,25})',
                r'([A-Z][a-zA-Z\s]{3,25})\s+[-–—]\s+([A-Z][a-zA-Z\s]{3,25})',
                r'([A-Z][a-zA-Z\s]{3,25})\s+vs\s+([A-Z][a-zA-Z\s]{3,25})'
            ]
            
            for pattern in patterns:
                pattern_matches = re.findall(pattern, page_text)
                
                for team1, team2 in pattern_matches:
                    if self._is_valid_betcity_match(team1, team2):
                        # Ищем контекст вокруг матча
                        context = self._get_match_context(page_text, team1, team2)
                        
                        match_data = {
                            'source': 'betcity_text',
                            'sport': self._detect_sport_from_context(context),
                            'team1': team1.strip(),
                            'team2': team2.strip(),
                            'score': self._extract_score_from_context(context) or 'LIVE',
                            'time': self._extract_time_from_context(context) or 'LIVE',
                            'league': 'BetCity Live',
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        # Ищем коэффициенты в контексте
                        odds = self._find_odds_for_match(context, team1, team2)
                        if odds:
                            match_data['odds'] = odds
                        
                        matches.append(match_data)
                        self.logger.info(f"BetCity: найден матч {team1} vs {team2}")
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения из текста: {e}")
            return []
    
    def _get_match_context(self, page_text: str, team1: str, team2: str) -> str:
        """
        Получение контекста вокруг матча
        """
        try:
            team1_pos = page_text.find(team1)
            team2_pos = page_text.find(team2)
            
            if team1_pos != -1 and team2_pos != -1:
                start_pos = min(team1_pos, team2_pos)
                end_pos = max(team1_pos, team2_pos) + max(len(team1), len(team2))
                
                return page_text[max(0, start_pos-200):end_pos+200]
            
            return ""
            
        except Exception as e:
            return ""
    
    def _extract_score_from_context(self, context: str) -> str:
        """
        Извлечение счета из контекста
        """
        try:
            score_patterns = [
                r'(\d+)\s*[-:]\s*(\d+)',
                r'Score:\s*(\d+)\s*-\s*(\d+)'
            ]
            
            for pattern in score_patterns:
                match = re.search(pattern, context)
                if match:
                    return f"{match.group(1)}-{match.group(2)}"
            
            return None
            
        except Exception as e:
            return None
    
    def _extract_time_from_context(self, context: str) -> str:
        """
        Извлечение времени из контекста
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
                match = re.search(pattern, context, re.IGNORECASE)
                if match:
                    return match.group(1)
            
            return None
            
        except Exception as e:
            return None
    
    def _detect_sport_from_context(self, context: str) -> str:
        """
        Определение вида спорта из контекста
        """
        try:
            context_lower = context.lower()
            
            if any(word in context_lower for word in ['футбол', 'football', 'гол', 'goal']):
                return 'football'
            elif any(word in context_lower for word in ['теннис', 'tennis', 'сет', 'set']):
                return 'tennis'
            elif any(word in context_lower for word in ['баскетбол', 'basketball']):
                return 'basketball'
            elif any(word in context_lower for word in ['хоккей', 'hockey']):
                return 'hockey'
            elif any(word in context_lower for word in ['волейбол', 'volleyball']):
                return 'volleyball'
            else:
                return 'football'  # По умолчанию
                
        except Exception as e:
            return 'football'
    
    def _find_odds_for_match(self, context: str, team1: str, team2: str) -> Dict[str, str]:
        """
        Поиск коэффициентов для конкретного матча
        """
        try:
            # Ищем коэффициенты в контексте
            odds_matches = re.findall(r'(\d+\.\d{1,2})', context)
            
            # Фильтруем и берем первые 3 (П1, X, П2)
            valid_odds = []
            for odd in odds_matches:
                odd_float = float(odd)
                if 1.01 <= odd_float <= 100.0:
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
    
    def _is_valid_betcity_match(self, team1: str, team2: str) -> bool:
        """
        Проверка валидности матча BetCity
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
                'betcity', 'букмекер', 'линия', 'лайв', 'спорт', 'матч',
                'событие', 'игра', 'турнир', 'чемпионат', 'лига'
            ]
            
            for word in exclude_words:
                if word in team1.lower() or word in team2.lower():
                    return False
            
            # Проверяем, что это похоже на названия команд
            if not re.match(r'^[А-ЯA-Z][а-яa-z\s]+$', team1) or not re.match(r'^[А-ЯA-Z][а-яa-z\s]+$', team2):
                return False
            
            return True
            
        except Exception as e:
            return False
    
    def _parse_text_for_match(self, text: str, source_url: str) -> Dict[str, Any]:
        """
        Парсинг текста для извлечения матча
        """
        try:
            # Паттерны для извлечения
            patterns = [
                r'([А-Я][а-я\s]{3,25})\s+[-–—]\s+([А-Я][а-я\s]{3,25})',
                r'([А-Я][а-я\s]{3,25})\s+vs\s+([А-Я][а-я\s]{3,25})',
                r'([A-Z][a-zA-Z\s]{3,25})\s+[-–—]\s+([A-Z][a-zA-Z\s]{3,25})',
                r'([A-Z][a-zA-Z\s]{3,25})\s+vs\s+([A-Z][a-zA-Z\s]{3,25})'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    team1, team2 = match.groups()
                    
                    if self._is_valid_betcity_match(team1, team2):
                        return {
                            'source': 'betcity_text_parse',
                            'sport': self._detect_sport_from_context(text),
                            'team1': team1.strip(),
                            'team2': team2.strip(),
                            'score': 'LIVE',
                            'time': 'LIVE',
                            'league': 'BetCity Live',
                            'url': source_url,
                            'timestamp': datetime.now().isoformat()
                        }
            
            return None
            
        except Exception as e:
            return None
    
    def _clean_betcity_matches(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Очистка и дедупликация матчей
        """
        seen = set()
        clean_matches = []
        
        for match in matches:
            try:
                team1 = match.get('team1', '').lower().strip()
                team2 = match.get('team2', '').lower().strip()
                
                signature = f"{min(team1, team2)}_{max(team1, team2)}"
                
                if signature not in seen and len(signature) > 6:
                    seen.add(signature)
                    clean_matches.append(match)
                    
            except Exception as e:
                continue
        
        return clean_matches
    
    def verify_connection(self) -> bool:
        """
        Проверка доступности BetCity
        """
        try:
            response = self.session.get('https://betcity.ru/', timeout=10)
            return response.status_code == 200
        except:
            return False