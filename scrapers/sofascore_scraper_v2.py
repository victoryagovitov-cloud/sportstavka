"""
Рабочий скрапер SofaScore.com
"""
import requests
from bs4 import BeautifulSoup
import re
import json
from typing import List, Dict, Any

class SofaScoreScraperV2:
    """
    Рабочий скрапер SofaScore для извлечения максимума live данных
    """
    
    def __init__(self, logger):
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.7339.80 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache'
        })
    
    def get_live_matches(self, sport: str) -> List[Dict[str, Any]]:
        """
        Получение live матчей конкретного вида спорта
        """
        self.logger.info(f"SofaScore сбор {sport} данных")
        
        sport_urls = {
            'football': 'https://www.sofascore.com/football/livescore',
            'tennis': 'https://www.sofascore.com/tennis/livescore',
            'handball': 'https://www.sofascore.com/handball/livescore',
            'table_tennis': 'https://www.sofascore.com/table-tennis/livescore'
        }
        
        url = sport_urls.get(sport)
        if not url:
            return []
        
        try:
            response = self.session.get(url, timeout=15)
            
            if response.status_code != 200:
                self.logger.error(f"SofaScore {sport} HTTP ошибка: {response.status_code}")
                return []
            
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            
            self.logger.info(f"SofaScore {sport} HTML: {len(html):,} символов")
            
            matches = []
            
            # Метод 1: Извлечение из JSON данных в скриптах
            json_matches = self._extract_from_json_scripts(soup, sport)
            if json_matches:
                matches.extend(json_matches)
                self.logger.info(f"JSON метод: найдено {len(json_matches)} матчей")
            
            # Метод 2: Парсинг HTML элементов
            if not matches:
                html_matches = self._extract_from_html_elements(soup, sport)
                if html_matches:
                    matches.extend(html_matches)
                    self.logger.info(f"HTML метод: найдено {len(html_matches)} матчей")
            
            # Метод 3: Текстовый анализ
            if not matches:
                text_matches = self._extract_from_page_text(soup, sport)
                if text_matches:
                    matches.extend(text_matches)
                    self.logger.info(f"Text метод: найдено {len(text_matches)} матчей")
            
            # Очистка и валидация
            clean_matches = self._clean_and_validate_matches(matches, sport)
            
            self.logger.info(f"SofaScore {sport} итого: {len(clean_matches)} матчей")
            return clean_matches
            
        except Exception as e:
            self.logger.error(f"SofaScore {sport} ошибка: {e}")
            return []
    
    def _extract_from_json_scripts(self, soup: BeautifulSoup, sport: str) -> List[Dict[str, Any]]:
        """
        Извлечение из JSON данных в скриптах
        """
        matches = []
        
        # Ищем скрипты с JSON данными
        scripts = soup.find_all('script')
        
        for script in scripts:
            if script.string and len(script.string) > 1000:
                script_text = script.string
                
                # Ищем события в JSON
                if 'events' in script_text or 'tournaments' in script_text:
                    
                    # Паттерны для поиска JSON структур
                    json_patterns = [
                        r'"events"\s*:\s*(\[.+?\])',
                        r'"tournaments"\s*:\s*(\[.+?\])',
                        r'"matches"\s*:\s*(\[.+?\])',
                        r'"data"\s*:\s*(\{.+?\})'
                    ]
                    
                    for pattern in json_patterns:
                        json_matches = re.findall(pattern, script_text, re.DOTALL)
                        
                        for json_str in json_matches:
                            try:
                                data = json.loads(json_str)
                                parsed_matches = self._parse_json_events(data, sport)
                                if parsed_matches:
                                    matches.extend(parsed_matches)
                                    return matches  # Если нашли данные, возвращаем
                                    
                            except json.JSONDecodeError:
                                continue
        
        return matches
    
    def _parse_json_events(self, data, sport: str) -> List[Dict[str, Any]]:
        """
        Парсинг JSON событий SofaScore
        """
        matches = []
        
        if isinstance(data, list):
            # Прямой массив событий
            for event in data:
                if isinstance(event, dict):
                    match = self._parse_sofascore_event(event, sport)
                    if match:
                        matches.append(match)
        
        elif isinstance(data, dict):
            # Ищем события в объекте
            for key, value in data.items():
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            # Проверяем, это турнир с событиями или прямое событие
                            if 'events' in item and isinstance(item['events'], list):
                                # Турнир с событиями
                                for event in item['events']:
                                    match = self._parse_sofascore_event(event, sport)
                                    if match:
                                        matches.append(match)
                            else:
                                # Прямое событие
                                match = self._parse_sofascore_event(item, sport)
                                if match:
                                    matches.append(match)
        
        return matches
    
    def _parse_sofascore_event(self, event: dict, sport: str) -> Dict[str, Any]:
        """
        Парсинг события SofaScore в структуру для Claude AI
        """
        try:
            # Проверяем, что это live событие
            status = event.get('status', {})
            if isinstance(status, dict):
                status_type = status.get('type', status.get('code', ''))
                if status_type not in ['inprogress', 'live', '1', 'started']:
                    return None  # Пропускаем не live события
            
            # Команды/игроки
            home_team = event.get('homeTeam', {})
            away_team = event.get('awayTeam', {})
            
            if isinstance(home_team, dict):
                team1 = home_team.get('name', home_team.get('shortName', ''))
            else:
                team1 = str(home_team)
            
            if isinstance(away_team, dict):
                team2 = away_team.get('name', away_team.get('shortName', ''))
            else:
                team2 = str(away_team)
            
            if not team1 or not team2:
                return None
            
            # Счет
            home_score_obj = event.get('homeScore', {})
            away_score_obj = event.get('awayScore', {})
            
            if isinstance(home_score_obj, dict):
                home_score = home_score_obj.get('current', home_score_obj.get('display', 0))
            else:
                home_score = home_score_obj or 0
            
            if isinstance(away_score_obj, dict):
                away_score = away_score_obj.get('current', away_score_obj.get('display', 0))
            else:
                away_score = away_score_obj or 0
            
            score = f"{home_score}:{away_score}"
            
            # Время/статус
            if isinstance(status, dict):
                match_time = status.get('description', status.get('type', "0'"))
            else:
                match_time = str(status) if status else "0'"
            
            # Турнир/лига
            tournament = event.get('tournament', {})
            if isinstance(tournament, dict):
                league_name = tournament.get('name', tournament.get('uniqueName', 'SofaScore Live'))
                country = tournament.get('category', {})
                if isinstance(country, dict):
                    country_name = country.get('name', '')
                    if country_name:
                        league_name = f"{country_name} {league_name}"
            else:
                league_name = 'SofaScore Live'
            
            # ID и URL
            match_id = event.get('id', event.get('customId', ''))
            url = f"/match/{match_id}" if match_id else ''
            
            # Дополнительные данные SofaScore
            additional_data = {
                'sofascore_id': match_id,
                'start_timestamp': event.get('startTimestamp'),
                'round_info': event.get('roundInfo'),
                'venue': event.get('venue'),
                'referee': event.get('referee')
            }
            
            # Статистика (если доступна)
            if 'statistics' in event:
                additional_data['live_statistics'] = event['statistics']
            
            # Формируем результат
            base_match = {
                'url': url,
                'sport': sport,
                'source': 'sofascore',
                'sofascore_data': additional_data
            }
            
            if sport == 'tennis':
                # Для тенниса ищем счет по сетам
                sets_score = score
                if 'homeScore' in event and 'awayScore' in event:
                    home_sets = event['homeScore'].get('period1', 0) if isinstance(event['homeScore'], dict) else 0
                    away_sets = event['awayScore'].get('period1', 0) if isinstance(event['awayScore'], dict) else 0
                    sets_score = f"{home_sets}:{away_sets}"
                
                base_match.update({
                    'player1': team1,
                    'player2': team2,
                    'sets_score': sets_score,
                    'current_set': score,  # Текущий счет в сете
                    'tournament': league_name
                })
            else:
                base_match.update({
                    'team1': team1,
                    'team2': team2,
                    'score': score,
                    'time': match_time,
                    'league': league_name
                })
            
            return base_match
            
        except Exception as e:
            return None
    
    def _extract_from_html_elements(self, soup: BeautifulSoup, sport: str) -> List[Dict[str, Any]]:
        """
        Извлечение из HTML элементов
        """
        matches = []
        
        # SofaScore специфичные селекторы
        selectors = [
            '[data-testid*="event"]',
            '[data-testid*="match"]',
            '[class*="event"]',
            '[class*="match"]',
            'div[data-event-id]',
            'a[href*="/match/"]'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            
            if len(elements) > 5:
                self.logger.info(f"SofaScore селектор {selector}: {len(elements)} элементов")
                
                for element in elements[:20]:
                    match_data = self._parse_html_element(element, sport)
                    if match_data:
                        matches.append(match_data)
                
                if matches:
                    break
        
        return matches
    
    def _parse_html_element(self, element, sport: str) -> Dict[str, Any]:
        """
        Парсинг HTML элемента
        """
        try:
            text = element.get_text(strip=True)
            
            # Базовая проверка на матч
            if not self._looks_like_match(text):
                return None
            
            # Извлекаем команды
            team_patterns = [
                r'([A-Za-zА-Яа-я\s\.]{3,30})\s*[-–vs]\s*([A-Za-zА-Яа-я\s\.]{3,30})',
                r'([A-Za-zА-Яа-я\s\.]{3,30})\s+([A-Za-zА-Яа-я\s\.]{3,30})'
            ]
            
            teams = None
            for pattern in team_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    team1, team2 = match.group(1).strip(), match.group(2).strip()
                    if (len(team1) >= 3 and len(team2) >= 3 and 
                        team1.lower() != team2.lower()):
                        teams = (team1, team2)
                        break
            
            if not teams:
                return None
            
            # Счет
            score_match = re.search(r'(\d+[:-]\d+)', text)
            score = score_match.group(1) if score_match else '0:0'
            
            # Время
            time_match = re.search(r"(\d+)'", text)
            match_time = time_match.group(0) if time_match else "0'"
            
            # URL
            url = element.get('href', '')
            if not url:
                link = element.find('a')
                url = link.get('href', '') if link else ''
            
            # ID события
            event_id = (element.get('data-event-id') or 
                       element.get('data-match-id') or
                       element.get('data-id'))
            
            # Формируем данные
            if sport == 'tennis':
                return {
                    'player1': teams[0],
                    'player2': teams[1],
                    'sets_score': score,
                    'current_set': '0:0',
                    'tournament': 'SofaScore Live',
                    'url': url,
                    'sport': sport,
                    'source': 'sofascore_html',
                    'event_id': event_id
                }
            else:
                return {
                    'team1': teams[0],
                    'team2': teams[1],
                    'score': score,
                    'time': match_time,
                    'league': 'SofaScore Live',
                    'url': url,
                    'sport': sport,
                    'source': 'sofascore_html',
                    'event_id': event_id
                }
                
        except Exception:
            return None
    
    def _extract_from_page_text(self, soup: BeautifulSoup, sport: str) -> List[Dict[str, Any]]:
        """
        Извлечение из текста страницы
        """
        matches = []
        
        try:
            page_text = soup.get_text()
            lines = [line.strip() for line in page_text.split('\n') if line.strip()]
            
            for line in lines:
                if self._looks_like_match(line):
                    match_data = self._parse_text_line(line, sport)
                    if match_data:
                        matches.append(match_data)
            
            return matches
            
        except Exception:
            return []
    
    def _parse_text_line(self, line: str, sport: str) -> Dict[str, Any]:
        """
        Парсинг строки текста
        """
        try:
            # Команды
            team_match = re.search(r'([A-Za-zА-Яа-я\s\.]{3,25})\s*[-–vs]\s*([A-Za-zА-Яа-я\s\.]{3,25})', line, re.IGNORECASE)
            
            if not team_match:
                return None
            
            team1, team2 = team_match.group(1).strip(), team_match.group(2).strip()
            
            # Счет
            score_match = re.search(r'(\d+[:-]\d+)', line)
            score = score_match.group(1) if score_match else '0:0'
            
            # Время
            time_match = re.search(r"(\d+)'", line)
            match_time = time_match.group(0) if time_match else "0'"
            
            if sport == 'tennis':
                return {
                    'player1': team1,
                    'player2': team2,
                    'sets_score': score,
                    'current_set': '0:0',
                    'tournament': 'SofaScore Live',
                    'url': '',
                    'sport': sport,
                    'source': 'sofascore_text'
                }
            else:
                return {
                    'team1': team1,
                    'team2': team2,
                    'score': score,
                    'time': match_time,
                    'league': 'SofaScore Live',
                    'url': '',
                    'sport': sport,
                    'source': 'sofascore_text'
                }
                
        except Exception:
            return None
    
    def _looks_like_match(self, text: str) -> bool:
        """
        Проверка на матч
        """
        if not text or len(text) < 8 or len(text) > 150:
            return False
        
        exclude_keywords = [
            'sofascore', 'cookie', 'subscribe', 'download', 'app',
            'login', 'register', 'follow', 'notification'
        ]
        
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in exclude_keywords):
            return False
        
        # Признаки матча
        has_score = bool(re.search(r'\d+[:-]\d+', text))
        has_teams = bool(re.search(r'[A-Za-zА-Яа-я]{3,}.*[A-Za-zА-Яа-я]{3,}', text))
        has_vs = ' - ' in text or ' vs ' in text.lower()
        has_time = bool(re.search(r"\d+'", text))
        
        return sum([has_score, has_teams, has_vs, has_time]) >= 2
    
    def _clean_and_validate_matches(self, matches: List[Dict[str, Any]], sport: str) -> List[Dict[str, Any]]:
        """
        Очистка и валидация матчей
        """
        # Убираем дубликаты
        seen = set()
        unique_matches = []
        
        for match in matches:
            # Создаем ключ для дедупликации
            if sport == 'tennis':
                key = f"{match.get('player1', '')}-{match.get('player2', '')}"
            else:
                key = f"{match.get('team1', '')}-{match.get('team2', '')}"
            
            key = key.lower().strip()
            
            if key not in seen and len(key) > 6:
                seen.add(key)
                
                # Валидация данных
                if self._validate_match(match, sport):
                    unique_matches.append(match)
        
        return unique_matches
    
    def _validate_match(self, match: Dict[str, Any], sport: str) -> bool:
        """
        Валидация матча
        """
        if sport == 'tennis':
            p1 = match.get('player1', '').strip()
            p2 = match.get('player2', '').strip()
            return (len(p1) >= 3 and len(p2) >= 3 and 
                   p1.lower() != p2.lower() and
                   not p1.isdigit() and not p2.isdigit())
        else:
            t1 = match.get('team1', '').strip()
            t2 = match.get('team2', '').strip()
            return (len(t1) >= 3 and len(t2) >= 3 and 
                   t1.lower() != t2.lower() and
                   not t1.isdigit() and not t2.isdigit())
    
    def get_match_statistics(self, match_url: str) -> Dict[str, Any]:
        """
        Получение детальной статистики матча
        """
        if not match_url.startswith('http'):
            full_url = f"https://www.sofascore.com{match_url}"
        else:
            full_url = match_url
        
        try:
            response = self.session.get(full_url, timeout=10)
            
            if response.status_code != 200:
                return {}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text()
            
            statistics = {}
            
            # Владение мячом
            possession_matches = re.findall(r'(\d{1,2})%', page_text)
            if len(possession_matches) >= 2:
                statistics['possession'] = {
                    'team1': f"{possession_matches[0]}%",
                    'team2': f"{possession_matches[1]}%"
                }
            
            # xG данные
            xg_matches = re.findall(r'(\d+\.\d+)', page_text)
            if len(xg_matches) >= 2:
                statistics['xG'] = {
                    'team1': xg_matches[0],
                    'team2': xg_matches[1]
                }
            
            # Удары
            small_numbers = [int(num) for num in re.findall(r'\b(\d{1,2})\b', page_text) if int(num) <= 20]
            if len(small_numbers) >= 4:
                statistics['shots'] = {
                    'team1_total': str(small_numbers[0]),
                    'team1_on_target': str(small_numbers[1]),
                    'team2_total': str(small_numbers[2]), 
                    'team2_on_target': str(small_numbers[3])
                }
            
            return {'statistics': statistics} if statistics else {}
            
        except Exception as e:
            self.logger.warning(f"Ошибка получения статистики: {e}")
            return {}