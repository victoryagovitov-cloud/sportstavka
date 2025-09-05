"""
HTML-only парсер для обхода JavaScript защиты
Фокус на извлечении из чистого HTML без выполнения JS
"""
import requests
import time
import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup
import json

class HTMLOnlyScraper:
    """
    Парсер работающий только с HTML (без JavaScript)
    """
    
    def __init__(self, logger):
        self.logger = logger
        
        # Сессия с ротацией заголовков
        self.session = requests.Session()
        self.headers_pool = [
            {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'no-cache'
            },
            {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-GB,en;q=0.5',
                'Connection': 'keep-alive',
                'Pragma': 'no-cache',
                'Cache-Control': 'no-cache'
            }
        ]
    
    def get_html_live_matches(self, sport: str = 'football') -> List[Dict[str, Any]]:
        """
        Получение live матчей через чистый HTML
        """
        try:
            self.logger.info(f"HTML-only извлечение live {sport}")
            
            # Пробуем разные URL и заголовки
            urls_to_try = [
                f'https://www.sofascore.com/{sport}/live',
                f'https://www.sofascore.com/{sport}',
                'https://www.sofascore.com/',
                f'https://m.sofascore.com/{sport}/live',  # Мобильная версия
                f'https://www.livescore.com/en/{sport}/live/',
            ]
            
            matches = []
            
            for url in urls_to_try:
                for headers in self.headers_pool:
                    try:
                        # Добавляем заголовки против кэширования
                        headers_no_cache = headers.copy()
                        headers_no_cache.update({
                            'Cache-Control': 'no-cache, no-store, must-revalidate',
                            'Pragma': 'no-cache',
                            'Expires': '0'
                        })
                        
                        response = self.session.get(url, headers=headers_no_cache, timeout=15)
                        
                        if response.status_code == 200:
                            self.logger.info(f"HTML успех: {url} (размер: {len(response.text)})")
                            
                            # Парсим HTML
                            html_matches = self._parse_html_content(response.text, sport, url)
                            
                            if html_matches:
                                self.logger.info(f"Найдено {len(html_matches)} матчей в HTML с {url}")
                                matches.extend(html_matches)
                                break
                        
                        time.sleep(1)  # Задержка между запросами
                        
                    except Exception as e:
                        self.logger.warning(f"Ошибка с {url}: {e}")
                        continue
                
                if matches:
                    break
            
            # Убираем дубликаты
            unique_matches = self._remove_html_duplicates(matches)
            
            self.logger.info(f"HTML-only: итого {len(unique_matches)} уникальных матчей")
            return unique_matches
            
        except Exception as e:
            self.logger.error(f"Ошибка HTML-only извлечения: {e}")
            return []
    
    def _parse_html_content(self, html_content: str, sport: str, source_url: str) -> List[Dict[str, Any]]:
        """
        Парсинг HTML контента
        """
        matches = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Метод 1: Поиск в JSON данных внутри HTML
            json_matches = self._extract_from_html_json(html_content, sport)
            matches.extend(json_matches)
            
            # Метод 2: Поиск через BeautifulSoup селекторы
            if not matches:
                soup_matches = self._extract_from_soup_elements(soup, sport)
                matches.extend(soup_matches)
            
            # Метод 3: Поиск по тексту с регулярными выражениями
            if not matches:
                regex_matches = self._extract_from_html_text(html_content, sport)
                matches.extend(regex_matches)
            
            # Добавляем метаданные
            for match in matches:
                match['source_url'] = source_url
                match['extraction_method'] = 'html_only'
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка парсинга HTML: {e}")
            return []
    
    def _extract_from_html_json(self, html_content: str, sport: str) -> List[Dict[str, Any]]:
        """
        Поиск JSON данных в HTML
        """
        matches = []
        
        try:
            # Паттерны для поиска JSON с live данными
            json_patterns = [
                r'__NEXT_DATA__[^>]*>([^<]+)</script>',
                r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
                r'"liveEvents":\s*(\[.*?\])',
                r'"events":\s*(\[.*?\])',
                r'"matches":\s*(\[.*?\])',
                r'"fixtures":\s*(\[.*?\])'
            ]
            
            for pattern in json_patterns:
                json_matches = re.findall(pattern, html_content, re.DOTALL)
                
                for json_str in json_matches:
                    try:
                        if json_str.startswith('{'):
                            data = json.loads(json_str)
                        elif json_str.startswith('['):
                            data = json.loads(json_str)
                        else:
                            continue
                        
                        # Извлекаем матчи из JSON
                        json_extracted = self._extract_matches_from_json_data(data, sport)
                        matches.extend(json_extracted)
                        
                    except json.JSONDecodeError:
                        continue
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения JSON из HTML: {e}")
            return []
    
    def _extract_from_soup_elements(self, soup: BeautifulSoup, sport: str) -> List[Dict[str, Any]]:
        """
        Извлечение через BeautifulSoup селекторы
        """
        matches = []
        
        try:
            # Селекторы для поиска матчей
            selectors = [
                'a[href*="/match/"]',  # Ссылки на матчи
                'div[data-testid]',    # React элементы
                '.event',              # События
                '.match',              # Матчи
                '.fixture',            # Фикстуры
                'tr',                  # Строки таблиц
                'td'                   # Ячейки таблиц
            ]
            
            for selector in selectors:
                elements = soup.select(selector)
                
                if elements:
                    self.logger.info(f"BeautifulSoup: найдено {len(elements)} элементов с {selector}")
                    
                    for element in elements[:30]:
                        match_data = self._extract_from_soup_element(element, sport)
                        if match_data:
                            matches.append(match_data)
                    
                    if matches:
                        break
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка BeautifulSoup извлечения: {e}")
            return []
    
    def _extract_from_soup_element(self, element, sport: str) -> Dict[str, Any]:
        """
        Извлечение матча из BeautifulSoup элемента
        """
        try:
            text = element.get_text(strip=True)
            
            if not text or len(text) < 10:
                return None
            
            # Используем текстовый парсер
            return self._parse_text_for_match(text, sport)
            
        except Exception as e:
            return None
    
    def _extract_from_html_text(self, html_content: str, sport: str) -> List[Dict[str, Any]]:
        """
        Извлечение через регулярные выражения по HTML тексту
        """
        matches = []
        
        try:
            # Убираем HTML теги для чистого текста
            clean_text = re.sub(r'<[^>]+>', ' ', html_content)
            clean_text = re.sub(r'\s+', ' ', clean_text)
            
            # Ищем известные команды и турниры
            known_entities = {
                'football': ['Bermuda', 'Jamaica', 'Paysandu', 'Volta Redonda', 'Colegiales', 'San Martin', 'Luqueno', 'Guarani'],
                'tennis': ['Prachar', 'Mishiro', 'Fullana', 'Reasco', 'Kakhniuk', 'Bowden', 'Sandrone', 'Rebec'],
                'handball': ['PSG', 'Barcelona', 'Kiel', 'Flensburg', 'Montpellier', 'Nantes']
            }
            
            entities = known_entities.get(sport, [])
            
            for entity in entities:
                if entity in clean_text:
                    self.logger.info(f"Найдена известная команда/игрок: {entity}")
                    
                    # Ищем контекст вокруг известной команды
                    entity_matches = self._extract_context_around_entity(clean_text, entity, sport)
                    matches.extend(entity_matches)
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения из HTML текста: {e}")
            return []
    
    def _extract_context_around_entity(self, text: str, entity: str, sport: str) -> List[Dict[str, Any]]:
        """
        Извлечение контекста вокруг известной команды/игрока
        """
        matches = []
        
        try:
            # Находим позиции упоминаний
            entity_positions = [m.start() for m in re.finditer(re.escape(entity), text, re.IGNORECASE)]
            
            for pos in entity_positions:
                # Берем контекст ±300 символов
                start = max(0, pos - 300)
                end = min(len(text), pos + 300)
                context = text[start:end]
                
                # Парсим контекст
                context_match = self._parse_text_for_match(context, sport)
                if context_match:
                    matches.append(context_match)
            
            return matches
            
        except Exception as e:
            return []
    
    def _parse_text_for_match(self, text: str, sport: str) -> Dict[str, Any]:
        """
        Парсинг текста для извлечения данных матча
        """
        try:
            if sport == 'football':
                return self._parse_football_text(text)
            elif sport == 'tennis':
                return self._parse_tennis_text(text)
            elif sport == 'handball':
                return self._parse_handball_text(text)
            
            return None
            
        except Exception as e:
            return None
    
    def _parse_football_text(self, text: str) -> Dict[str, Any]:
        """
        Парсинг футбольного текста
        """
        try:
            # Паттерны для футбола
            patterns = [
                r'([A-Z][a-zA-Z\s]{2,25})\s+([A-Z][a-zA-Z\s]{2,25})\s+(\d+)\s+(\d+)',
                r'([A-Z][a-zA-Z\s]{2,25})\s+vs\s+([A-Z][a-zA-Z\s]{2,25})',
                r'(Bermuda|Jamaica|Paysandu|Volta Redonda|Colegiales|San Martin|Luqueno|Guarani)\s+([A-Z][a-zA-Z\s]{2,30})'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    groups = match.groups()
                    
                    if len(groups) >= 2:
                        return {
                            'source': 'html_only',
                            'sport': 'football',
                            'team1': groups[0].strip(),
                            'team2': groups[1].strip(),
                            'score': f"{groups[2]}:{groups[3]}" if len(groups) >= 4 else 'LIVE',
                            'time': 'LIVE'
                        }
            
            return None
            
        except Exception as e:
            return None
    
    def _parse_tennis_text(self, text: str) -> Dict[str, Any]:
        """
        Парсинг теннисного текста
        """
        try:
            # Теннисные паттерны
            patterns = [
                r'([A-Z]\.\s[A-Z][a-z]+)\s+([A-Z]\.\s[A-Z][a-z]+)',
                r'([A-Z][a-z]+\s[A-Z]\.)\s+([A-Z][a-z]+\s[A-Z]\.)',
                r'(Prachar|Mishiro|Fullana|Reasco|Kakhniuk|Bowden)\s+([A-Z]\.|[A-Z][a-z]+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    groups = match.groups()
                    
                    if len(groups) >= 2:
                        return {
                            'source': 'html_only',
                            'sport': 'tennis',
                            'team1': groups[0].strip(),
                            'team2': groups[1].strip(),
                            'score': 'LIVE',
                            'time': 'LIVE'
                        }
            
            return None
            
        except Exception as e:
            return None
    
    def _extract_matches_from_json_data(self, data, sport: str) -> List[Dict[str, Any]]:
        """
        Извлечение матчей из JSON данных
        """
        matches = []
        
        try:
            # Рекурсивный поиск в JSON структуре
            if isinstance(data, dict):
                for key, value in data.items():
                    if key.lower() in ['events', 'matches', 'fixtures', 'liveevents']:
                        if isinstance(value, list):
                            for item in value:
                                if isinstance(item, dict):
                                    match_data = self._parse_json_match_item(item, sport)
                                    if match_data:
                                        matches.append(match_data)
                    elif isinstance(value, (dict, list)):
                        # Рекурсивный поиск
                        nested_matches = self._extract_matches_from_json_data(value, sport)
                        matches.extend(nested_matches)
            
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        match_data = self._parse_json_match_item(item, sport)
                        if match_data:
                            matches.append(match_data)
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения из JSON: {e}")
            return []
    
    def _parse_json_match_item(self, item: Dict, sport: str) -> Dict[str, Any]:
        """
        Парсинг отдельного JSON элемента матча
        """
        try:
            match_data = {
                'source': 'html_only_json',
                'sport': sport
            }
            
            # Поиск команд в JSON
            team_keys = ['homeTeam', 'awayTeam', 'participant1', 'participant2', 'team1', 'team2']
            
            teams = []
            for key in team_keys:
                if key in item:
                    team_data = item[key]
                    if isinstance(team_data, dict):
                        team_name = team_data.get('name', team_data.get('shortName', ''))
                    else:
                        team_name = str(team_data)
                    
                    if team_name:
                        teams.append(team_name)
            
            if len(teams) >= 2:
                match_data['team1'] = teams[0]
                match_data['team2'] = teams[1]
                
                # Поиск счета
                score_keys = ['homeScore', 'awayScore', 'score1', 'score2']
                scores = []
                
                for key in score_keys:
                    if key in item and item[key] is not None:
                        scores.append(str(item[key]))
                
                if len(scores) >= 2:
                    match_data['score'] = f"{scores[0]}:{scores[1]}"
                else:
                    match_data['score'] = 'LIVE'
                
                # Поиск времени
                time_keys = ['minute', 'time', 'status', 'period']
                for key in time_keys:
                    if key in item and item[key]:
                        match_data['time'] = str(item[key])
                        break
                
                if 'time' not in match_data:
                    match_data['time'] = 'LIVE'
                
                return match_data
            
            return None
            
        except Exception as e:
            return None
    
    def _remove_html_duplicates(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Удаление дубликатов HTML матчей
        """
        seen = set()
        unique = []
        
        for match in matches:
            try:
                team1 = match.get('team1', '').lower().strip()
                team2 = match.get('team2', '').lower().strip()
                
                # Нормализация
                team1 = re.sub(r'[^\w]', '', team1)
                team2 = re.sub(r'[^\w]', '', team2)
                
                signature = f"{min(team1, team2)}_{max(team1, team2)}"
                
                if signature not in seen and len(signature) > 4:
                    seen.add(signature)
                    unique.append(match)
                    
            except Exception as e:
                continue
        
        return unique