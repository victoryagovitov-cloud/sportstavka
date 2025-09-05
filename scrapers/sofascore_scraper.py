"""
Скрапер для SofaScore.com - альтернативный источник live данных
"""
import requests
from bs4 import BeautifulSoup
import re
import json
from typing import List, Dict, Any

class SofaScoreScraper:
    """
    Скрапер для извлечения live матчей с SofaScore.com
    """
    
    def __init__(self, logger):
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.7339.80 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        })
    
    def get_live_matches(self, sport: str) -> List[Dict[str, Any]]:
        """
        Получение live матчей с SofaScore
        """
        self.logger.info(f"SofaScore сбор {sport} данных")
        
        # URL для разных видов спорта
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
                self.logger.error(f"SofaScore HTTP ошибка: {response.status_code}")
                return []
            
            html = response.text
            self.logger.info(f"SofaScore HTML размер: {len(html):,} символов")
            
            matches = []
            
            # Метод 1: Поиск JSON данных в HTML
            json_matches = self._extract_from_json_data(html, sport)
            if json_matches:
                matches.extend(json_matches)
                self.logger.info(f"JSON метод: найдено {len(json_matches)} матчей")
            
            # Метод 2: Парсинг HTML структуры
            if not matches:
                html_matches = self._extract_from_html_structure(html, sport)
                if html_matches:
                    matches.extend(html_matches)
                    self.logger.info(f"HTML метод: найдено {len(html_matches)} матчей")
            
            # Метод 3: Поиск API endpoints в HTML
            if not matches:
                api_matches = self._try_discovered_apis(html, sport)
                if api_matches:
                    matches.extend(api_matches)
                    self.logger.info(f"API метод: найдено {len(api_matches)} матчей")
            
            return self._clean_matches(matches, sport)
            
        except Exception as e:
            self.logger.error(f"SofaScore ошибка: {e}")
            return []
    
    def _extract_from_json_data(self, html: str, sport: str) -> List[Dict[str, Any]]:
        """
        Извлечение из JSON данных в HTML
        """
        matches = []
        
        # Ищем различные JSON структуры в HTML
        json_patterns = [
            r'window\\.__INITIAL_STATE__\\s*=\\s*({.+?});',
            r'window\\.__DATA__\\s*=\\s*({.+?});',
            r'window\\.__PRELOADED_STATE__\\s*=\\s*({.+?});',
            r'\"events\"\\s*:\\s*(\\[.+?\\])',
            r'\"matches\"\\s*:\\s*(\\[.+?\\])',
            r'\"fixtures\"\\s*:\\s*(\\[.+?\\])'
        ]
        
        for pattern in json_patterns:
            json_matches = re.findall(pattern, html, re.DOTALL)
            
            for json_str in json_matches:
                try:
                    data = json.loads(json_str)
                    parsed_matches = self._parse_json_data(data, sport)
                    if parsed_matches:
                        matches.extend(parsed_matches)
                        self.logger.info(f"Найдены данные в JSON паттерне: {pattern[:30]}...")
                        break
                except json.JSONDecodeError:
                    continue
            
            if matches:
                break
        
        return matches
    
    def _extract_from_html_structure(self, html: str, sport: str) -> List[Dict[str, Any]]:
        """
        Извлечение из HTML структуры
        """
        soup = BeautifulSoup(html, 'html.parser')
        matches = []
        
        # Ищем элементы с live матчами
        potential_selectors = [
            '[data-testid*=\"event\"]',
            '[data-testid*=\"match\"]',
            '[data-testid*=\"fixture\"]',
            '[class*=\"event\"]',
            '[class*=\"match\"]',
            '[class*=\"fixture\"]',
            '[class*=\"live\"]',
            'div[data-id]',
            'tr[data-id]',
            'article',
            'section'
        ]
        
        for selector in potential_selectors:
            try:
                elements = soup.select(selector)
                
                if len(elements) > 5:
                    self.logger.info(f"SofaScore селектор {selector}: {len(elements)} элементов")
                    
                    for element in elements[:20]:
                        text = element.get_text(strip=True)
                        if self._looks_like_match(text):
                            match_data = self._parse_element_text(text, element, sport)
                            if match_data:
                                matches.append(match_data)
                    
                    if matches:
                        break
                        
            except Exception:
                continue
        
        return matches
    
    def _try_discovered_apis(self, html: str, sport: str) -> List[Dict[str, Any]]:
        """
        Попытка использовать найденные API endpoints
        """
        matches = []
        
        # Ищем API URLs в HTML
        api_patterns = [
            r'https://api\\.sofascore\\.com[^\"\\s]*',
            r'/api/[^\"\\s]*'
        ]
        
        found_apis = []
        for pattern in api_patterns:
            apis = re.findall(pattern, html)
            found_apis.extend(apis)
        
        # Тестируем найденные API
        for api_url in set(found_apis[:10]):  # Тестируем первые 10 уникальных
            try:
                if not api_url.startswith('http'):
                    test_url = f'https://www.sofascore.com{api_url}'
                else:
                    test_url = api_url
                
                response = self.session.get(test_url, timeout=5)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        api_matches = self._parse_json_data(data, sport)
                        if api_matches:
                            self.logger.info(f"Рабочий SofaScore API: {test_url}")
                            matches.extend(api_matches)
                            break
                    except:
                        continue
                        
            except:
                continue
        
        return matches
    
    def _parse_json_data(self, data, sport: str) -> List[Dict[str, Any]]:
        """
        Парсинг JSON данных
        """
        matches = []
        
        def recursive_search(obj, depth=0):
            if depth > 6:
                return
            
            if isinstance(obj, dict):
                # Ищем ключи с событиями
                for key, value in obj.items():
                    if (key.lower() in ['events', 'matches', 'fixtures', 'games', 'data'] and 
                        isinstance(value, list)):
                        for item in value:
                            if isinstance(item, dict):
                                match = self._parse_match_object(item, sport)
                                if match:
                                    matches.append(match)
                    elif isinstance(value, (dict, list)):
                        recursive_search(value, depth + 1)
                        
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, dict):
                        match = self._parse_match_object(item, sport)
                        if match:
                            matches.append(match)
                    else:
                        recursive_search(item, depth + 1)
        
        recursive_search(data)
        return matches
    
    def _parse_match_object(self, obj: dict, sport: str) -> Dict[str, Any]:
        """
        Парсинг объекта матча из SofaScore API
        """
        try:
            # SofaScore обычно использует структуру homeTeam/awayTeam
            home_team = obj.get('homeTeam', obj.get('home', {}))
            away_team = obj.get('awayTeam', obj.get('away', {}))
            
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
            score_obj = obj.get('homeScore', {})
            if isinstance(score_obj, dict):
                home_score = score_obj.get('current', score_obj.get('display', 0))
                away_score = obj.get('awayScore', {}).get('current', obj.get('awayScore', {}).get('display', 0))
                score = f"{home_score}:{away_score}"
            else:
                score = obj.get('score', '0:0')
            
            # Статус/время
            status = obj.get('status', {})
            if isinstance(status, dict):
                match_time = status.get('description', status.get('type', "0'"))
            else:
                match_time = str(obj.get('time', obj.get('minute', '0\\')))
            
            # Турнир
            tournament = obj.get('tournament', {})
            if isinstance(tournament, dict):
                league_name = tournament.get('name', tournament.get('uniqueName', 'Live матч'))
            else:
                league_name = str(obj.get('league', 'Live матч'))
            
            # ID для URL
            match_id = obj.get('id', obj.get('customId', ''))
            url = f'/match/{match_id}' if match_id else ''
            
            # Формируем результат
            if sport == 'tennis':
                return {
                    'player1': team1,
                    'player2': team2,
                    'sets_score': score,
                    'current_set': '0:0',
                    'tournament': league_name,
                    'url': url,
                    'sport': sport,
                    'source': 'sofascore_api'
                }
            else:
                return {
                    'team1': team1,
                    'team2': team2,
                    'score': score,
                    'time': match_time,
                    'league': league_name,
                    'url': url,
                    'sport': sport,
                    'source': 'sofascore_api'
                }
                
        except Exception:
            return None
    
    def _looks_like_match(self, text: str) -> bool:
        """
        Проверка на матч
        """
        if not text or len(text) < 10 or len(text) > 200:
            return False
        
        exclude_keywords = [
            'cookie', 'реклама', 'подписка', 'уведомления', 'софаскор',
            'sofascore', 'войти', 'регистрация'
        ]
        
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in exclude_keywords):
            return False
        
        # Признаки матча
        has_score = bool(re.search(r'\d+[:-]\d+', text))
        has_time = bool(re.search(r'\d+[\'мин]', text))
        has_teams = bool(re.search(r'[А-Яа-яA-Za-z]{3,}.*[А-Яа-яA-Za-z]{3,}', text))
        has_live = 'live' in text_lower
        
        return sum([has_score, has_time, has_teams, has_live]) >= 2
    
    def _parse_element_text(self, text: str, element, sport: str) -> Dict[str, Any]:
        """
        Парсинг текста элемента
        """
        try:
            # Ищем команды/игроков
            team_patterns = [
                r'([А-Яа-яA-Za-z\s]{3,30})\s*[-–vs]\s*([А-Яа-яA-Za-z\s]{3,30})',
                r'([А-Яа-яA-Za-z\s]{3,30})\s*-\s*([А-Яа-яA-Za-z\s]{3,30})'
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
            
            # Счет и время
            score_match = re.search(r'(\d+[:-]\d+)', text)
            score = score_match.group(1) if score_match else '0:0'
            
            time_match = re.search(r'(\d+)[\'мин]', text)
            match_time = f"{time_match.group(1)}'" if time_match else "0'"
            
            # URL матча
            url = ''
            if hasattr(element, 'get'):
                href = element.get('href')
                if href:
                    url = href
                elif hasattr(element, 'find'):
                    link = element.find('a')
                    if link:
                        url = link.get('href', '')
            
            # Формируем результат
            if sport == 'tennis':
                return {
                    'player1': teams[0],
                    'player2': teams[1],
                    'sets_score': score,
                    'current_set': '0:0',
                    'tournament': 'SofaScore Live',
                    'url': url,
                    'sport': sport,
                    'source': 'sofascore_html'
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
                    'source': 'sofascore_html'
                }
                
        except Exception:
            return None
    
    def _clean_matches(self, matches: List[Dict[str, Any]], sport: str) -> List[Dict[str, Any]]:
        """
        Очистка матчей
        """
        # Убираем дубликаты
        seen = set()
        unique_matches = []
        
        for match in matches:
            if sport == 'tennis':
                key = f\"{match.get('player1', '')}-{match.get('player2', '')}\"
            else:
                key = f\"{match.get('team1', '')}-{match.get('team2', '')}\"
            
            key = key.lower().strip()
            if key not in seen and len(key) > 6:
                seen.add(key)
                unique_matches.append(match)
        
        return unique_matches