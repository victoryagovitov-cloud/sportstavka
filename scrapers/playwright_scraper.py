"""
Playwright скрапер для scores24.live
"""
from playwright.sync_api import sync_playwright
import time
import re
import json
from typing import List, Dict, Any

class PlaywrightScraper:
    """
    Современный скрапер с Playwright для динамических сайтов
    """
    
    def __init__(self, logger):
        self.logger = logger
    
    def get_live_matches(self, url: str, sport: str) -> List[Dict[str, Any]]:
        """
        Получение live матчей через Playwright
        """
        self.logger.info(f"Playwright сбор {sport} матчей с {url}")
        
        with sync_playwright() as p:
            try:
                # Запускаем браузер
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.7339.80 Safari/537.36'
                )
                
                page = context.new_page()
                
                # Перехватываем API запросы
                api_responses = []
                
                def handle_response(response):
                    if ('api' in response.url or 'dapi' in response.url) and response.status == 200:
                        try:
                            content_type = response.headers.get('content-type', '')
                            if 'json' in content_type:
                                api_responses.append({
                                    'url': response.url,
                                    'data': response.json()
                                })
                        except:
                            pass
                
                page.on('response', handle_response)
                
                # Загружаем страницу и ждем загрузки
                self.logger.info("Загружаем страницу с Playwright...")
                page.goto(url, wait_until='networkidle', timeout=30000)
                
                # Дополнительное ожидание для динамического контента
                time.sleep(8)
                
                # Прокручиваем страницу
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)
                page.evaluate("window.scrollTo(0, 0)")
                time.sleep(2)
                
                matches = []
                
                # Метод 1: Анализ API ответов
                if api_responses:
                    self.logger.info(f"Перехвачено {len(api_responses)} API ответов")
                    for api_resp in api_responses:
                        api_matches = self._parse_api_data(api_resp['data'], sport)
                        if api_matches:
                            matches.extend(api_matches)
                            self.logger.info(f"API найдено {len(api_matches)} матчей")
                
                # Метод 2: Современные селекторы
                if not matches:
                    matches = self._extract_with_selectors(page, sport)
                
                # Метод 3: JavaScript состояние
                if not matches:
                    matches = self._extract_js_state(page, sport)
                
                # Метод 4: Текстовый контент
                if not matches:
                    matches = self._extract_text_content(page, sport)
                
                browser.close()
                return self._clean_matches(matches)
                
            except Exception as e:
                self.logger.error(f"Playwright ошибка: {e}")
                return []
    
    def _extract_with_selectors(self, page, sport: str) -> List[Dict[str, Any]]:
        """
        Извлечение с помощью селекторов
        """
        matches = []
        
        selectors = [
            '[data-testid*="match"]',
            '[data-testid*="fixture"]', 
            '[data-testid*="event"]',
            '[class*="match"]',
            '[class*="fixture"]',
            '[class*="live"]',
            'tr[data-id]',
            'div[data-id]',
            'article',
            'section'
        ]
        
        for selector in selectors:
            try:
                elements = page.query_selector_all(selector)
                
                if len(elements) > 3:
                    self.logger.info(f"Селектор {selector}: {len(elements)} элементов")
                    
                    for element in elements[:15]:
                        text = element.text_content() or ''
                        if self._looks_like_match(text):
                            match_data = self._parse_text_to_match(text, sport)
                            if match_data:
                                # Добавляем URL если есть
                                try:
                                    href = element.get_attribute('href')
                                    if href:
                                        match_data['url'] = href
                                    else:
                                        link = element.query_selector('a')
                                        if link:
                                            match_data['url'] = link.get_attribute('href') or ''
                                except:
                                    pass
                                
                                matches.append(match_data)
                    
                    if matches:
                        break
                        
            except Exception:
                continue
        
        return matches
    
    def _extract_js_state(self, page, sport: str) -> List[Dict[str, Any]]:
        """
        Извлечение из JavaScript состояния
        """
        matches = []
        
        js_vars = [
            'window.__INITIAL_STATE__',
            'window.__PRELOADED_STATE__',
            'window.__DATA__',
            'window.matchesData',
            'window.liveData'
        ]
        
        for var in js_vars:
            try:
                data = page.evaluate(f'() => {var}')
                if data:
                    self.logger.info(f"Найдены данные в {var}")
                    parsed = self._parse_api_data(data, sport)
                    if parsed:
                        matches.extend(parsed)
                        break
            except:
                continue
        
        return matches
    
    def _extract_text_content(self, page, sport: str) -> List[Dict[str, Any]]:
        """
        Извлечение из текстового контента
        """
        try:
            page_text = page.evaluate('() => document.body.innerText')
            if not page_text:
                return []
            
            lines = [line.strip() for line in page_text.split('\n') if line.strip()]
            matches = []
            
            self.logger.info(f"Анализируем {len(lines)} строк текста")
            
            for line in lines:
                if self._looks_like_match(line):
                    match_data = self._parse_text_to_match(line, sport)
                    if match_data:
                        matches.append(match_data)
            
            return matches
            
        except Exception:
            return []
    
    def _looks_like_match(self, text: str) -> bool:
        """
        Проверка на матч
        """
        if not text or len(text) < 8 or len(text) > 150:
            return False
        
        exclude_keywords = [
            'cookie', 'реклама', 'бонус', 'букмекер', 'ставка',
            'новости', 'статья', 'результаты', 'расписание', 'scores24',
            'войти', 'регистрация'
        ]
        
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in exclude_keywords):
            return False
        
        # Признаки матча
        has_score = bool(re.search(r'\d+[:-]\d+', text))
        has_time = bool(re.search(r'\d+[\'мин]', text))
        has_teams = bool(re.search(r'[А-Яа-яA-Za-z]{3,}\s*[-–vs]\s*[А-Яа-яA-Za-z]{3,}', text, re.IGNORECASE))
        has_separator = ' - ' in text or ' vs ' in text.lower()
        
        return sum([has_score, has_time, has_teams, has_separator]) >= 2
    
    def _parse_text_to_match(self, text: str, sport: str) -> Dict[str, Any]:
        """
        Парсинг текста в матч
        """
        try:
            # Команды
            patterns = [
                r'([А-Яа-яA-Za-z\.\s]{3,30})\s*[-–]\s*([А-Яа-яA-Za-z\.\s]{3,30})',
                r'([А-Яа-яA-Za-z\.\s]{3,30})\s*vs\s*([А-Яа-яA-Za-z\.\s]{3,30})',
                r'([А-Яа-яA-Za-z\.\s]{3,30})\s*-\s*([А-Яа-яA-Za-z\.\s]{3,30})'
            ]
            
            teams = None
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    team1, team2 = match.group(1).strip(), match.group(2).strip()
                    if (self._is_valid_name(team1) and self._is_valid_name(team2) and 
                        team1.lower() != team2.lower()):
                        teams = (team1, team2)
                        break
            
            if not teams:
                return None
            
            # Счет и время
            score_match = re.search(r'(\d+[:-]\d+)', text)
            score = score_match.group(1) if score_match else '0:0'
            
            time_match = re.search(r'(\d+)[\'мин]', text)
            match_time = f"{time_match.group(1)}'" if time_match else "0'"
            
            # Формируем результат
            if sport == 'tennis':
                return {
                    'player1': teams[0],
                    'player2': teams[1],
                    'sets_score': score,
                    'current_set': '0:0',
                    'tournament': 'Live турнир',
                    'url': '',
                    'sport': sport,
                    'source': 'playwright'
                }
            else:
                return {
                    'team1': teams[0],
                    'team2': teams[1],
                    'score': score,
                    'time': match_time,
                    'league': 'Live лига',
                    'url': '',
                    'sport': sport,
                    'source': 'playwright'
                }
                
        except Exception:
            return None
    
    def _parse_api_data(self, data, sport: str) -> List[Dict[str, Any]]:
        """
        Парсинг API данных
        """
        matches = []
        
        def search_recursive(obj, depth=0):
            if depth > 5:
                return
            
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if (key.lower() in ['matches', 'fixtures', 'events', 'games'] and 
                        isinstance(value, list)):
                        for item in value:
                            if isinstance(item, dict):
                                match = self._parse_match_object(item, sport)
                                if match:
                                    matches.append(match)
                    elif isinstance(value, (dict, list)):
                        search_recursive(value, depth + 1)
            elif isinstance(obj, list):
                for item in obj:
                    search_recursive(item, depth + 1)
        
        search_recursive(data)
        return matches
    
    def _parse_match_object(self, obj: dict, sport: str) -> Dict[str, Any]:
        """
        Парсинг объекта матча
        """
        try:
            # Поиск команд
            home_fields = ['home', 'homeTeam', 'team1', 'participant1']
            away_fields = ['away', 'awayTeam', 'team2', 'participant2']
            
            team1 = team2 = None
            
            for field in home_fields:
                if field in obj:
                    val = obj[field]
                    if isinstance(val, dict):
                        team1 = val.get('name') or val.get('shortName')
                    else:
                        team1 = str(val)
                    if team1:
                        break
            
            for field in away_fields:
                if field in obj:
                    val = obj[field]
                    if isinstance(val, dict):
                        team2 = val.get('name') or val.get('shortName')
                    else:
                        team2 = str(val)
                    if team2:
                        break
            
            if not team1 or not team2:
                return None
            
            # Счет
            score = obj.get('score', '0:0')
            if isinstance(score, dict):
                home_score = score.get('home', 0)
                away_score = score.get('away', 0)
                score = f"{home_score}:{away_score}"
            
            # Время
            match_time = str(obj.get('time', obj.get('minute', "0'")))
            
            # Лига
            league = str(obj.get('league', obj.get('tournament', 'Live матч')))
            
            # URL
            url = str(obj.get('url', obj.get('id', '')))
            
            if sport == 'tennis':
                return {
                    'player1': team1,
                    'player2': team2,
                    'sets_score': score,
                    'current_set': '0:0',
                    'tournament': league,
                    'url': url,
                    'sport': sport,
                    'source': 'playwright_api'
                }
            else:
                return {
                    'team1': team1,
                    'team2': team2,
                    'score': score,
                    'time': match_time,
                    'league': league,
                    'url': url,
                    'sport': sport,
                    'source': 'playwright_api'
                }
                
        except Exception:
            return None
    
    def _is_valid_name(self, name: str) -> bool:
        """
        Проверка валидности названия
        """
        if not name or len(name) < 2 or len(name) > 40:
            return False
        
        if not re.search(r'[А-Яа-яA-Za-z]', name):
            return False
        
        invalid_words = ['live', 'матч', 'время', 'счет', 'vs', '-']
        name_lower = name.lower().strip()
        
        return name_lower not in invalid_words and not name_lower.isdigit()
    
    def _clean_matches(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Очистка дубликатов
        """
        seen = set()
        unique = []
        
        for match in matches:
            if 'player1' in match:
                key = f"{match.get('player1', '')}-{match.get('player2', '')}"
            else:
                key = f"{match.get('team1', '')}-{match.get('team2', '')}"
            
            key = key.lower().strip()
            if key not in seen and len(key) > 5:
                seen.add(key)
                unique.append(match)
        
        return unique