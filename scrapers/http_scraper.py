"""
Продвинутый HTTP скрапер для scores24.live
"""
import requests
import re
import json
from typing import List, Dict, Any
from bs4 import BeautifulSoup
import time

class HTTPScraper:
    """
    HTTP скрапер с продвинутыми техниками
    """
    
    def __init__(self, logger):
        self.logger = logger
        self.session = requests.Session()
        
        # Настраиваем сессию как браузер
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.7339.80 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none'
        })
    
    def get_live_matches(self, url: str, sport: str) -> List[Dict[str, Any]]:
        """
        Получение live матчей через HTTP
        """
        self.logger.info(f"HTTP сбор {sport} матчей с {url}")
        
        try:
            # Загружаем основную страницу
            response = self.session.get(url, timeout=15)
            
            if response.status_code != 200:
                self.logger.error(f"HTTP ошибка: {response.status_code}")
                return []
            
            html = response.text
            self.logger.info(f"Получен HTML размером {len(html):,} символов")
            
            matches = []
            
            # Метод 1: Поиск в JavaScript данных
            js_matches = self._extract_from_javascript(html, sport)
            if js_matches:
                matches.extend(js_matches)
                self.logger.info(f"JavaScript метод: найдено {len(js_matches)} матчей")
            
            # Метод 2: Анализ структуры HTML
            if not matches:
                html_matches = self._extract_from_html_structure(html, sport)
                if html_matches:
                    matches.extend(html_matches)
                    self.logger.info(f"HTML структура: найдено {len(html_matches)} матчей")
            
            # Метод 3: Regex поиск по тексту
            if not matches:
                text_matches = self._extract_from_text_patterns(html, sport)
                if text_matches:
                    matches.extend(text_matches)
                    self.logger.info(f"Text patterns: найдено {len(text_matches)} матчей")
            
            # Метод 4: Поиск через AJAX endpoints в HTML
            if not matches:
                ajax_matches = self._try_ajax_endpoints(html, sport)
                if ajax_matches:
                    matches.extend(ajax_matches)
                    self.logger.info(f"AJAX endpoints: найдено {len(ajax_matches)} матчей")
            
            return self._clean_matches(matches)
            
        except Exception as e:
            self.logger.error(f"HTTP скрапер ошибка: {e}")
            return []
    
    def _extract_from_javascript(self, html: str, sport: str) -> List[Dict[str, Any]]:
        """
        Извлечение данных из JavaScript переменных
        """
        matches = []
        
        # Ищем различные JS переменные с данными
        js_patterns = [
            r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
            r'window\.__PRELOADED_STATE__\s*=\s*({.+?});',
            r'window\.__DATA__\s*=\s*({.+?});',
            r'var\s+matchesData\s*=\s*({.+?});',
            r'var\s+liveData\s*=\s*({.+?});',
            r'const\s+initialData\s*=\s*({.+?});',
            r'"matches"\s*:\s*(\[.+?\])',
            r'"fixtures"\s*:\s*(\[.+?\])',
            r'"events"\s*:\s*(\[.+?\])'
        ]
        
        for pattern in js_patterns:
            js_matches = re.findall(pattern, html, re.DOTALL)
            for js_data in js_matches:
                try:
                    data = json.loads(js_data)
                    parsed_matches = self._parse_js_data(data, sport)
                    if parsed_matches:
                        matches.extend(parsed_matches)
                        self.logger.info(f"Найдены данные в JS переменной: {pattern}")
                        break
                except json.JSONDecodeError:
                    continue
            
            if matches:
                break
        
        return matches
    
    def _extract_from_html_structure(self, html: str, sport: str) -> List[Dict[str, Any]]:
        """
        Извлечение из структуры HTML
        """
        soup = BeautifulSoup(html, 'html.parser')
        matches = []
        
        # Ищем элементы с data атрибутами
        elements_with_data = soup.find_all(attrs={'data-id': True})
        elements_with_data.extend(soup.find_all(attrs={'data-match-id': True}))
        elements_with_data.extend(soup.find_all(attrs={'data-fixture-id': True}))
        
        for elem in elements_with_data:
            text = elem.get_text(strip=True)
            if self._looks_like_match(text):
                match_data = self._parse_element_text(text, elem, sport)
                if match_data:
                    matches.append(match_data)
        
        # Ищем таблицы
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                text = row.get_text(strip=True)
                if self._looks_like_match(text):
                    match_data = self._parse_element_text(text, row, sport)
                    if match_data:
                        matches.append(match_data)
        
        return matches
    
    def _extract_from_text_patterns(self, html: str, sport: str) -> List[Dict[str, Any]]:
        """
        Извлечение через текстовые паттерны
        """
        matches = []
        
        # Убираем HTML теги и получаем чистый текст
        clean_text = re.sub(r'<[^>]+>', ' ', html)
        lines = [line.strip() for line in clean_text.split('\\n') if line.strip()]
        
        for line in lines:
            if self._looks_like_match(line):
                match_data = self._parse_text_line(line, sport)
                if match_data:
                    matches.append(match_data)
        
        return matches
    
    def _try_ajax_endpoints(self, html: str, sport: str) -> List[Dict[str, Any]]:
        """
        Поиск и тестирование AJAX endpoints в HTML
        """
        # Ищем возможные AJAX URLs в JavaScript коде
        ajax_patterns = [
            r'[\"\\']([^\"\\s]*api[^\"\\s]*)[\"\\']',
            r'[\"\\']([^\"\\s]*dapi[^\"\\s]*)[\"\\']',
            r'url[\"\\']?\\s*:\\s*[\"\\']([^\"\\s]+)[\"\\']',
            r'endpoint[\"\\']?\\s*:\\s*[\"\\']([^\"\\s]+)[\"\\']'
        ]
        
        endpoints = []
        for pattern in ajax_patterns:
            found = re.findall(pattern, html)
            endpoints.extend(found)
        
        # Тестируем найденные endpoints
        for endpoint in set(endpoints):
            try:
                if not endpoint.startswith('http'):
                    if endpoint.startswith('/'):
                        test_url = f'https://scores24.live{endpoint}'
                    else:
                        test_url = f'https://scores24.live/{endpoint}'
                else:
                    test_url = endpoint
                
                response = self.session.get(test_url, timeout=5)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        matches = self._parse_js_data(data, sport)
                        if matches:
                            self.logger.info(f"Рабочий AJAX endpoint: {test_url}")
                            return matches
                    except:
                        continue
                        
            except:
                continue
        
        return []
    
    def _looks_like_match(self, text: str) -> bool:
        """
        Проверяет, похож ли текст на матч
        """
        if not text or len(text) < 8 or len(text) > 200:
            return False
        
        # Исключаем служебную информацию
        exclude_words = [
            'cookie', 'реклама', 'бонус', 'букмекер', 'ставка', 'коэффициент',
            'новости', 'статья', 'результаты', 'расписание', 'scores24',
            'футбол', 'теннис', 'гандбол', 'live', 'войти', 'регистрация'
        ]
        
        text_lower = text.lower()
        if any(word in text_lower for word in exclude_words):
            return False
        
        # Ищем признаки матча
        has_score = bool(re.search(r'\\d+[:-]\\d+', text))
        has_time = bool(re.search(r'\\d+[\'мин]', text))
        has_teams = bool(re.search(r'[А-Яа-яA-Za-z]{3,}\\s*[-–vs]\\s*[А-Яа-яA-Za-z]{3,}', text, re.IGNORECASE))
        has_separator = ' - ' in text or ' vs ' in text.lower() or ' – ' in text
        
        # Нужно минимум 2 признака
        indicators = sum([has_score, has_time, has_teams, has_separator])
        return indicators >= 2
    
    def _parse_text_line(self, line: str, sport: str) -> Dict[str, Any]:
        """
        Парсинг строки текста в данные матча
        """
        try:
            # Ищем команды/игроков
            team_patterns = [
                r'([А-Яа-яA-Za-z\\.\\s]{3,30})\\s*[-–]\\s*([А-Яа-яA-Za-z\\.\\s]{3,30})',
                r'([А-Яа-яA-Za-z\\.\\s]{3,30})\\s*vs\\s*([А-Яа-яA-Za-z\\.\\s]{3,30})',
                r'([А-Яа-яA-Za-z\\.\\s]{3,30})\\s*-\\s*([А-Яа-яA-Za-z\\.\\s]{3,30})'
            ]
            
            teams = None
            for pattern in team_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    team1 = match.group(1).strip()
                    team2 = match.group(2).strip()
                    
                    if (self._is_valid_name(team1) and 
                        self._is_valid_name(team2) and 
                        team1.lower() != team2.lower()):
                        teams = (team1, team2)
                        break
            
            if not teams:
                return None
            
            # Ищем счет
            score_match = re.search(r'(\\d+[:-]\\d+)', line)
            score = score_match.group(1) if score_match else '0:0'
            
            # Ищем время
            time_match = re.search(r'(\\d+)[\'мин]', line)
            match_time = f\"{time_match.group(1)}'\" if time_match else \"0'\"
            
            # Формируем данные
            if sport == 'tennis':
                return {
                    'player1': teams[0],
                    'player2': teams[1],
                    'sets_score': score,
                    'current_set': '0:0',
                    'tournament': 'Live турнир',
                    'url': '',
                    'sport': sport,
                    'source': 'http_text'
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
                    'source': 'http_text'
                }
                
        except Exception:
            return None
    
    def _parse_element_text(self, text: str, element, sport: str) -> Dict[str, Any]:
        """
        Парсинг текста элемента
        """
        match_data = self._parse_text_line(text, sport)
        
        if match_data and element:
            # Пробуем найти URL матча
            if hasattr(element, 'find'):
                link = element.find('a')
                if link and link.get('href'):
                    match_data['url'] = link.get('href')
            
            # Ищем дополнительные атрибуты
            if hasattr(element, 'get'):
                match_id = (element.get('data-id') or 
                           element.get('data-match-id') or 
                           element.get('data-fixture-id'))
                if match_id:
                    match_data['match_id'] = match_id
        
        return match_data
    
    def _parse_js_data(self, data, sport: str) -> List[Dict[str, Any]]:
        """
        Парсинг JavaScript данных
        """
        matches = []
        
        def search_matches(obj, depth=0):
            if depth > 5:
                return
            
            if isinstance(obj, dict):
                # Ищем ключи с матчами
                for key, value in obj.items():
                    if (key.lower() in ['matches', 'fixtures', 'events', 'games', 'data'] and 
                        isinstance(value, list)):
                        for item in value:
                            if isinstance(item, dict):
                                match = self._parse_match_object(item, sport)
                                if match:
                                    matches.append(match)
                    elif isinstance(value, (dict, list)):
                        search_matches(value, depth + 1)
                        
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, dict):
                        match = self._parse_match_object(item, sport)
                        if match:
                            matches.append(match)
                    else:
                        search_matches(item, depth + 1)
        
        search_matches(data)
        return matches
    
    def _parse_match_object(self, obj: dict, sport: str) -> Dict[str, Any]:
        """
        Парсинг объекта матча из JSON
        """
        try:
            # Различные поля для команд
            team_fields = {
                'home': ['home', 'homeTeam', 'home_team', 'team1', 'participant1'],
                'away': ['away', 'awayTeam', 'away_team', 'team2', 'participant2']
            }
            
            team1 = team2 = None
            
            for field_list in team_fields['home']:
                if field_list in obj:
                    value = obj[field_list]
                    if isinstance(value, dict):
                        team1 = value.get('name') or value.get('shortName') or value.get('title')
                    else:
                        team1 = str(value)
                    if team1:
                        break
            
            for field_list in team_fields['away']:
                if field_list in obj:
                    value = obj[field_list]
                    if isinstance(value, dict):
                        team2 = value.get('name') or value.get('shortName') or value.get('title')
                    else:
                        team2 = str(value)
                    if team2:
                        break
            
            if not team1 or not team2:
                return None
            
            # Счет
            score = '0:0'
            score_fields = ['score', 'result', 'currentScore']
            for field in score_fields:
                if field in obj:
                    score_val = obj[field]
                    if isinstance(score_val, dict):
                        home_score = score_val.get('home', score_val.get('homeScore', 0))
                        away_score = score_val.get('away', score_val.get('awayScore', 0))
                        score = f\"{home_score}:{away_score}\"
                    else:
                        score = str(score_val)
                    break
            
            # Время
            time_fields = ['time', 'minute', 'status', 'period']
            match_time = \"0'\"
            for field in time_fields:
                if field in obj:
                    time_val = str(obj[field])
                    if time_val and time_val != 'None':
                        match_time = time_val
                        break
            
            # Лига/турнир
            league_fields = ['league', 'tournament', 'competition', 'category']
            league = 'Live матч'
            for field in league_fields:
                if field in obj:
                    league_val = obj[field]
                    if isinstance(league_val, dict):
                        league = league_val.get('name', league_val.get('title', league))
                    else:
                        league = str(league_val)
                    break
            
            # URL
            url = str(obj.get('url', obj.get('link', obj.get('id', ''))))
            
            # Формируем результат
            if sport == 'tennis':
                return {
                    'player1': team1,
                    'player2': team2,
                    'sets_score': score,
                    'current_set': '0:0',
                    'tournament': league,
                    'url': url,
                    'sport': sport,
                    'source': 'http_js'
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
                    'source': 'http_js'
                }
                
        except Exception:
            return None
    
    def _is_valid_name(self, name: str) -> bool:
        """
        Проверка валидности названия
        """
        if not name or len(name) < 2 or len(name) > 40:
            return False
        
        # Должно содержать буквы
        if not re.search(r'[А-Яа-яA-Za-z]', name):
            return False
        
        # Не должно быть только цифр или служебных слов
        invalid = ['live', 'матч', 'время', 'счет', 'результат', 'vs', '-', '–']
        name_lower = name.lower().strip()
        
        if name_lower in invalid or name_lower.isdigit():
            return False
        
        return True
    
    def _clean_matches(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Очистка и дедупликация матчей
        """
        # Убираем дубликаты
        seen = set()
        clean_matches = []
        
        for match in matches:
            # Создаем ключ
            if 'player1' in match:
                key = f\"{match.get('player1', '')}-{match.get('player2', '')}-{match.get('sets_score', '')}\"
            else:
                key = f\"{match.get('team1', '')}-{match.get('team2', '')}-{match.get('score', '')}\"
            
            key = key.lower().strip()
            
            if key not in seen and len(key) > 5:
                seen.add(key)
                clean_matches.append(match)
        
        return clean_matches