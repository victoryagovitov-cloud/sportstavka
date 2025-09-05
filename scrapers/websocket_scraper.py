"""
WebSocket скрапер для scores24.live
"""
import asyncio
import websockets
import json
import requests
import re
from typing import List, Dict, Any
import time

class WebSocketScraper:
    """
    Скрапер через WebSocket соединения
    """
    
    def __init__(self, logger):
        self.logger = logger
    
    def get_live_matches(self, base_url: str, sport: str) -> List[Dict[str, Any]]:
        """
        Получение live матчей через WebSocket или API
        """
        matches = []
        
        # Метод 1: Поиск WebSocket endpoints
        try:
            ws_matches = self._try_websocket_method(base_url, sport)
            if ws_matches:
                matches.extend(ws_matches)
                self.logger.info(f"WebSocket метод: найдено {len(ws_matches)} матчей")
        except Exception as e:
            self.logger.warning(f"WebSocket не сработал: {e}")
        
        # Метод 2: Поиск скрытых API
        if not matches:
            try:
                api_matches = self._try_hidden_api(base_url, sport)
                if api_matches:
                    matches.extend(api_matches)
                    self.logger.info(f"API метод: найдено {len(api_matches)} матчей")
            except Exception as e:
                self.logger.warning(f"API не сработал: {e}")
        
        # Метод 3: Эмуляция браузерных запросов
        if not matches:
            try:
                browser_matches = self._try_browser_emulation(base_url, sport)
                if browser_matches:
                    matches.extend(browser_matches)
                    self.logger.info(f"Browser emulation: найдено {len(browser_matches)} матчей")
            except Exception as e:
                self.logger.warning(f"Browser emulation не сработал: {e}")
        
        return matches
    
    def _try_websocket_method(self, base_url: str, sport: str) -> List[Dict[str, Any]]:
        """
        Попытка подключения к WebSocket
        """
        # Возможные WebSocket endpoints
        ws_urls = [
            'wss://scores24.live/ws',
            'wss://api.scores24.live/ws',
            'wss://live.scores24.live/ws',
            'wss://scores24.live/live',
            'ws://scores24.live/ws'
        ]
        
        for ws_url in ws_urls:
            try:
                # Пробуем подключиться (с таймаутом)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def connect_ws():
                    try:
                        async with websockets.connect(ws_url, timeout=5) as websocket:
                            # Отправляем запрос на получение live данных
                            await websocket.send(json.dumps({
                                'type': 'subscribe',
                                'sport': sport,
                                'filter': 'live'
                            }))
                            
                            # Ждем ответ
                            response = await asyncio.wait_for(websocket.recv(), timeout=5)
                            data = json.loads(response)
                            
                            if isinstance(data, (list, dict)) and data:
                                return self._parse_ws_data(data, sport)
                    except Exception:
                        return None
                
                result = loop.run_until_complete(connect_ws())
                loop.close()
                
                if result:
                    self.logger.info(f"✅ WebSocket работает: {ws_url}")
                    return result
                    
            except Exception:
                continue
        
        return []
    
    def _try_hidden_api(self, base_url: str, sport: str) -> List[Dict[str, Any]]:
        """
        Поиск скрытых API endpoints
        """
        # Возможные API endpoints
        api_endpoints = [
            f'https://scores24.live/api/v1/{sport}/live',
            f'https://scores24.live/api/v2/{sport}/matches/live',
            f'https://scores24.live/dapi/v3/{sport}/live',
            f'https://api.scores24.live/v1/{sport}/live',
            f'https://live-api.scores24.live/{sport}/matches',
            f'https://scores24.live/graphql',  # GraphQL endpoint
            f'https://scores24.live/api/matches?sport={sport}&status=live',
            f'https://scores24.live/feed/{sport}/live'
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Accept': 'application/json, */*',
            'Referer': base_url,
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        for endpoint in api_endpoints:
            try:
                response = requests.get(endpoint, headers=headers, timeout=8)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        matches = self._parse_api_data(data, sport)
                        if matches:
                            self.logger.info(f"✅ Рабочий API: {endpoint}")
                            return matches
                    except json.JSONDecodeError:
                        # Возможно HTML ответ
                        if 'json' not in response.headers.get('content-type', '').lower():
                            continue
                
            except Exception:
                continue
        
        return []
    
    def _try_browser_emulation(self, base_url: str, sport: str) -> List[Dict[str, Any]]:
        """
        Эмуляция браузерных запросов
        """
        session = requests.Session()
        
        # Устанавливаем браузерные заголовки
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.7339.80 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        try:
            # Загружаем основную страницу
            response = session.get(base_url, timeout=10)
            
            if response.status_code == 200:
                # Ищем AJAX endpoints в HTML
                html = response.text
                
                # Ищем паттерны AJAX запросов
                ajax_patterns = [
                    r'/api/[^"\\s]+',
                    r'/dapi/[^"\\s]+', 
                    r'endpoint["\\':]\\s*["\\']/[^"\\s]+',
                    r'url["\\':]\\s*["\\']/[^"\\s]+'
                ]
                
                endpoints = []
                for pattern in ajax_patterns:
                    found = re.findall(pattern, html)
                    endpoints.extend(found)
                
                # Тестируем найденные endpoints
                for endpoint in set(endpoints):
                    try:
                        clean_endpoint = endpoint.strip('"\\'')
                        if not clean_endpoint.startswith('http'):
                            full_url = f"https://scores24.live{clean_endpoint}"
                        else:
                            full_url = clean_endpoint
                        
                        api_response = session.get(full_url, timeout=5)
                        
                        if api_response.status_code == 200:
                            try:
                                data = api_response.json()
                                matches = self._parse_api_data(data, sport)
                                if matches:
                                    self.logger.info(f"✅ Найден рабочий endpoint: {full_url}")
                                    return matches
                            except:
                                continue
                                
                    except Exception:
                        continue
        
        except Exception as e:
            self.logger.warning(f"Browser emulation ошибка: {e}")
        
        return []
    
    def _parse_ws_data(self, data, sport: str) -> List[Dict[str, Any]]:
        """
        Парсинг данных из WebSocket
        """
        matches = []
        
        if isinstance(data, dict):
            if 'matches' in data:
                for match in data['matches']:
                    parsed = self._parse_match_object(match, sport)
                    if parsed:
                        matches.append(parsed)
        elif isinstance(data, list):
            for item in data:
                parsed = self._parse_match_object(item, sport)
                if parsed:
                    matches.append(parsed)
        
        return matches
    
    def _parse_api_data(self, data, sport: str) -> List[Dict[str, Any]]:
        """
        Парсинг данных из API
        """
        matches = []
        
        def recursive_search(obj, depth=0):
            if depth > 5:
                return
            
            if isinstance(obj, dict):
                # Ищем массивы матчей
                for key, value in obj.items():
                    if (key.lower() in ['matches', 'fixtures', 'events', 'games', 'data'] and 
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
        Парсинг объекта матча
        """
        try:
            # Различные поля для команд/игроков
            team1 = (obj.get('homeTeam') or obj.get('home') or obj.get('team1') or
                    obj.get('participant1') or obj.get('player1') or
                    (obj.get('home_team', {}).get('name') if isinstance(obj.get('home_team'), dict) else obj.get('home_team')))
            
            team2 = (obj.get('awayTeam') or obj.get('away') or obj.get('team2') or
                    obj.get('participant2') or obj.get('player2') or
                    (obj.get('away_team', {}).get('name') if isinstance(obj.get('away_team'), dict) else obj.get('away_team')))
            
            if not team1 or not team2:
                return None
            
            # Счет
            score = (obj.get('score') or obj.get('result') or 
                    f"{obj.get('homeScore', 0)}:{obj.get('awayScore', 0)}")
            
            # Время/статус
            match_time = (obj.get('time') or obj.get('minute') or 
                         obj.get('status') or obj.get('period') or '0\\'')
            
            # Лига/турнир
            league = (obj.get('league') or obj.get('tournament') or 
                     obj.get('competition') or 'Live матч')
            
            # URL
            url = obj.get('url') or obj.get('link') or str(obj.get('id', ''))
            
            if sport == 'tennis':
                return {
                    'player1': str(team1),
                    'player2': str(team2),
                    'sets_score': str(score),
                    'current_set': '0:0',
                    'tournament': str(league),
                    'url': str(url),
                    'sport': sport,
                    'source': 'api'
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
                    'source': 'api'
                }
                
        except Exception:
            return None