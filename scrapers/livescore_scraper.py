"""
Скрапер для LiveScore.com - быстрые live обновления
"""
import requests
import json
import re
from typing import List, Dict, Any
from datetime import datetime
import time

class LiveScoreScraper:
    """
    Быстрый скрапер для получения live данных с LiveScore.com
    """
    
    def __init__(self, logger):
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.livescore.com/',
            'Origin': 'https://www.livescore.com'
        })
        
        # API endpoints для разных видов спорта
        self.api_endpoints = {
            'football': 'https://www.livescore.com/api/app/stage/soccer/live',
            'tennis': 'https://www.livescore.com/api/app/stage/tennis/live',
            'handball': 'https://www.livescore.com/api/app/stage/handball/live',
            'basketball': 'https://www.livescore.com/api/app/stage/basketball/live'
        }
    
    def get_live_matches(self, sport: str) -> List[Dict[str, Any]]:
        """
        Получение live матчей для указанного вида спорта
        """
        try:
            self.logger.info(f"LiveScore: получение live матчей {sport}")
            
            endpoint = self.api_endpoints.get(sport)
            if not endpoint:
                self.logger.warning(f"LiveScore: неподдерживаемый спорт {sport}")
                return []
            
            response = self.session.get(endpoint, timeout=10)
            
            if response.status_code != 200:
                self.logger.warning(f"LiveScore: HTTP {response.status_code} для {sport}")
                return []
            
            data = response.json()
            matches = self._parse_live_data(data, sport)
            
            self.logger.info(f"LiveScore: найдено {len(matches)} live матчей {sport}")
            return matches
            
        except Exception as e:
            self.logger.error(f"LiveScore ошибка для {sport}: {e}")
            return []
    
    def _parse_live_data(self, data: Dict, sport: str) -> List[Dict[str, Any]]:
        """
        Парсинг JSON данных от LiveScore API
        """
        matches = []
        
        try:
            # LiveScore API структура может варьироваться
            stages = data.get('Stages', [])
            
            for stage in stages:
                events = stage.get('Events', [])
                league_name = stage.get('Snm', 'Unknown League')
                
                for event in events:
                    match_data = self._extract_match_data(event, sport, league_name)
                    if match_data:
                        matches.append(match_data)
                        
        except Exception as e:
            self.logger.warning(f"LiveScore парсинг ошибка: {e}")
        
        return matches
    
    def _extract_match_data(self, event: Dict, sport: str, league: str) -> Dict[str, Any]:
        """
        Извлечение данных матча из события
        """
        try:
            # Базовые данные
            match_data = {
                'source': 'livescore',
                'sport': sport,
                'league': league,
                'url': f"https://www.livescore.com/match/{event.get('Eid', '')}",
                'match_id': str(event.get('Eid', '')),
                'timestamp': datetime.now().isoformat()
            }
            
            # Команды
            if sport == 'tennis':
                match_data['player1'] = event.get('T1', [{}])[0].get('Nm', '')
                match_data['player2'] = event.get('T2', [{}])[0].get('Nm', '')
                match_data['team1'] = match_data['player1']  # Для совместимости
                match_data['team2'] = match_data['player2']
            else:
                match_data['team1'] = event.get('T1', [{}])[0].get('Nm', '') if event.get('T1') else ''
                match_data['team2'] = event.get('T2', [{}])[0].get('Nm', '') if event.get('T2') else ''
            
            # Счет
            if sport == 'football':
                score1 = event.get('Tr1', '')
                score2 = event.get('Tr2', '')
                match_data['score'] = f"{score1}:{score2}" if score1 != '' and score2 != '' else "0:0"
            elif sport == 'tennis':
                # Теннисный счет более сложный
                sets_score = self._parse_tennis_score(event)
                match_data['score'] = sets_score
            else:
                score1 = event.get('Tr1', '0')
                score2 = event.get('Tr2', '0')
                match_data['score'] = f"{score1}:{score2}"
            
            # Время матча
            match_data['time'] = self._extract_match_time(event, sport)
            
            # Статус матча
            match_data['status'] = self._get_match_status(event)
            
            return match_data
            
        except Exception as e:
            self.logger.warning(f"LiveScore извлечение данных ошибка: {e}")
            return None
    
    def _parse_tennis_score(self, event: Dict) -> str:
        """
        Парсинг теннисного счета
        """
        try:
            # Получаем счет по сетам
            tr1_sets = event.get('Tr1', '')
            tr2_sets = event.get('Tr2', '')
            
            # Текущий счет в сете
            current_score1 = event.get('Tsc1', '')
            current_score2 = event.get('Tsc2', '')
            
            if tr1_sets and tr2_sets:
                sets_score = f"{tr1_sets}:{tr2_sets}"
                if current_score1 and current_score2:
                    sets_score += f" ({current_score1}:{current_score2})"
                return sets_score
            
            return f"{current_score1 or '0'}:{current_score2 or '0'}"
            
        except:
            return "0:0"
    
    def _extract_match_time(self, event: Dict, sport: str) -> str:
        """
        Извлечение времени матча
        """
        try:
            # Время в минутах
            minute = event.get('Eps', '')
            
            if minute:
                if sport == 'football':
                    if minute == 'FT':
                        return 'FT'
                    elif minute == 'HT':
                        return 'HT'
                    else:
                        return f"{minute}'"
                else:
                    return str(minute)
            
            # Статус матча как время
            status = event.get('Epr', '')
            if status:
                return status
            
            return "LIVE"
            
        except:
            return "LIVE"
    
    def _get_match_status(self, event: Dict) -> str:
        """
        Получение статуса матча
        """
        try:
            status_code = event.get('Eps', '')
            
            status_map = {
                '1': 'LIVE_1H',
                '2': 'LIVE_2H', 
                'HT': 'HALFTIME',
                'FT': 'FINISHED',
                'LIVE': 'LIVE'
            }
            
            return status_map.get(status_code, 'LIVE')
            
        except:
            return 'LIVE'
    
    def get_quick_scores(self, sport: str) -> Dict[str, Any]:
        """
        Быстрое получение только счетов (для частых обновлений)
        """
        try:
            matches = self.get_live_matches(sport)
            
            quick_data = {}
            for match in matches:
                match_id = match.get('match_id', '')
                if match_id:
                    quick_data[match_id] = {
                        'score': match.get('score', '0:0'),
                        'time': match.get('time', 'LIVE'),
                        'status': match.get('status', 'LIVE'),
                        'updated': match.get('timestamp', '')
                    }
            
            return quick_data
            
        except Exception as e:
            self.logger.error(f"LiveScore быстрые счета ошибка: {e}")
            return {}
    
    def verify_connection(self) -> bool:
        """
        Проверка подключения к LiveScore
        """
        try:
            response = self.session.get('https://www.livescore.com/api/app/stage/soccer/live', timeout=5)
            return response.status_code == 200
        except:
            return False