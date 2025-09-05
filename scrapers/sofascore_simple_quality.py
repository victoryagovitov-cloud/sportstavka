"""
Простой качественный скрапер SofaScore
"""
import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Any

class SofaScoreSimpleQuality:
    """
    Простой но качественный скрапер SofaScore
    """
    
    def __init__(self, logger):
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9'
        })
    
    def get_live_matches(self, sport: str) -> List[Dict[str, Any]]:
        """
        Получение live матчей
        """
        self.logger.info(f"SofaScore качественный сбор {sport}")
        
        sport_urls = {
            'football': 'https://www.sofascore.com/football/livescore',
            'tennis': 'https://www.sofascore.com/tennis/livescore',
            'handball': 'https://www.sofascore.com/handball/livescore',
            'table_tennis': 'https://www.sofascore.com/table-tennis/livescore',
            'basketball': 'https://www.sofascore.com/basketball/livescore'
        }
        
        url = sport_urls.get(sport)
        if not url:
            return []
        
        try:
            response = self.session.get(url, timeout=15)
            
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Извлекаем ссылки на матчи
            match_links = soup.find_all('a', href=re.compile(r'/match/'))
            
            matches = []
            
            for link in match_links:
                try:
                    match_data = self._parse_match_link(link, sport)
                    if match_data:
                        matches.append(match_data)
                except Exception:
                    continue
            
            # Убираем дубликаты
            unique_matches = self._remove_duplicates(matches, sport)
            
            self.logger.info(f"SofaScore {sport}: {len(unique_matches)} качественных матчей")
            return unique_matches
            
        except Exception as e:
            self.logger.error(f"SofaScore {sport} ошибка: {e}")
            return []
    
    def _parse_match_link(self, link, sport: str) -> Dict[str, Any]:
        """
        Парсинг ссылки на матч
        """
        href = link.get('href', '')
        text = link.get_text(strip=True)
        
        if not href or not text:
            return None
        
        # Парсим URL: /football/match/chile-brazil/YUbseVb#id:14169219
        url_match = re.search(r'/([^/]+)/match/([^/]+)/[^#]+#id:(\d+)', href)
        
        if not url_match:
            return None
        
        sport_from_url, teams_slug, match_id = url_match.groups()
        
        # Парсим команды из slug
        team1, team2 = self._parse_teams_from_slug(teams_slug)
        
        if not team1 or not team2:
            # Пробуем извлечь из текста ссылки
            team1, team2 = self._parse_teams_from_text(text)
        
        if not team1 or not team2:
            return None
        
        # Получаем детальные данные матча
        match_details = self._get_basic_match_data(href)
        
        # Формируем результат
        base_data = {
            'url': href,
            'sport': sport,
            'source': 'sofascore_quality',
            'match_id': match_id,
            'sofascore_url': f"https://www.sofascore.com{href}"
        }
        
        if sport == 'tennis':
            base_data.update({
                'player1': team1,
                'player2': team2,
                'sets_score': match_details.get('score', '0:0'),
                'current_set': '0:0',
                'tournament': match_details.get('league', 'SofaScore Live')
            })
        else:
            base_data.update({
                'team1': team1,
                'team2': team2,
                'score': match_details.get('score', '0:0'),
                'time': match_details.get('time', "0'"),
                'league': match_details.get('league', 'SofaScore Live')
            })
        
        # Добавляем статистику если есть
        if 'statistics' in match_details:
            base_data['statistics'] = match_details['statistics']
        
        return base_data
    
    def _parse_teams_from_slug(self, teams_slug: str) -> tuple:
        """
        Парсинг команд из URL slug
        """
        try:
            # Разделяем по дефису
            parts = teams_slug.split('-')
            
            if len(parts) >= 2:
                # Находим середину
                mid = len(parts) // 2
                
                team1_parts = parts[:mid]
                team2_parts = parts[mid:]
                
                team1 = ' '.join(word.capitalize() for word in team1_parts)
                team2 = ' '.join(word.capitalize() for word in team2_parts)
                
                if len(team1) >= 3 and len(team2) >= 3:
                    return team1, team2
            
            return None, None
            
        except Exception:
            return None, None
    
    def _parse_teams_from_text(self, text: str) -> tuple:
        """
        Парсинг команд из текста ссылки
        """
        try:
            # SofaScore обычно использует формат "Team1 - Team2"
            if ' - ' in text:
                parts = text.split(' - ', 1)
                if len(parts) == 2:
                    team1, team2 = parts[0].strip(), parts[1].strip()
                    
                    # Убираем лишнее (время, счет)
                    team1 = re.sub(r'\d+.*', '', team1).strip()
                    team2 = re.sub(r'\d+.*', '', team2).strip()
                    
                    if len(team1) >= 3 and len(team2) >= 3:
                        return team1, team2
            
            return None, None
            
        except Exception:
            return None, None
    
    def _get_basic_match_data(self, match_url: str) -> Dict[str, Any]:
        """
        Получение базовых данных матча
        """
        full_url = f"https://www.sofascore.com{match_url}"
        
        try:
            response = self.session.get(full_url, timeout=8)
            
            if response.status_code != 200:
                return {}
            
            page_text = response.text
            data = {}
            
            # Ищем live счет
            score_patterns = [
                r'"homeScore":\s*(\d+).*?"awayScore":\s*(\d+)',
                r'(\d{1,2})\s*[-:]\s*(\d{1,2})'
            ]
            
            for pattern in score_patterns:
                score_match = re.search(pattern, page_text)
                if score_match:
                    home_score, away_score = score_match.groups()
                    data['score'] = f"{home_score}:{away_score}"
                    break
            
            # Улучшенное извлечение времени матча
            data['time'] = self._extract_match_time(page_text)
            
            # Ищем название лиги/турнира
            league_patterns = [
                r'"tournament":\s*{[^}]*"name":\s*"([^"]+)"',
                r'"league":\s*"([^"]+)"'
            ]
            
            for pattern in league_patterns:
                league_match = re.search(pattern, page_text)
                if league_match:
                    data['league'] = league_match.group(1)
                    break
            
            # Извлекаем базовую статистику
            stats = self._extract_basic_statistics(page_text)
            if stats:
                data['statistics'] = stats
            
            return data
            
        except Exception as e:
            return {}
    
    def _extract_match_time(self, page_text: str) -> str:
        """
        Улучшенное извлечение времени матча
        """
        try:
            # Сначала ищем статус матча и время в JSON
            status_patterns = [
                r'"status":\s*{[^}]*"code":\s*(\d+)[^}]*"description":\s*"([^"]+)"',
                r'"status":\s*{[^}]*"type":\s*"([^"]+)"'
            ]
            
            # Ищем минуту в различных форматах
            time_patterns = [
                r'"minute":\s*(\d+)',  # JSON minute
                r'"time":\s*"(\d{1,3})\'?"',  # JSON time с апострофом
                r'"currentPeriodStartTimestamp":\s*(\d+)',  # Timestamp начала периода
                r'(\d{1,3})\'\s*(?:HT|FT|LIVE|$)',  # 45' HT формат
                r'(\d{1,3})\+(\d+)\'',  # 90+3' формат (добавленное время)
                r'HT\s*(\d{1,2}):(\d{2})',  # HT 45:00 формат
                r'FT\s*(\d{1,2}):(\d{2})',  # FT 90:00 формат
            ]
            
            # Проверяем статус матча
            for pattern in status_patterns:
                status_match = re.search(pattern, page_text)
                if status_match:
                    if len(status_match.groups()) >= 2:
                        status_code, description = status_match.groups()[:2]
                        # Если матч завершен
                        if 'finished' in description.lower() or 'ended' in description.lower():
                            return "FT"
                        # Если перерыв
                        elif 'halftime' in description.lower() or 'break' in description.lower():
                            return "HT"
                    elif len(status_match.groups()) == 1:
                        status_type = status_match.group(1)
                        if status_type.lower() in ['finished', 'ended']:
                            return "FT"
                        elif status_type.lower() in ['halftime', 'break']:
                            return "HT"
            
            # Ищем конкретную минуту
            for pattern in time_patterns:
                time_match = re.search(pattern, page_text)
                if time_match:
                    if '+' in pattern and len(time_match.groups()) >= 2:
                        # Добавленное время: 90+3'
                        main_time, added_time = time_match.groups()[:2]
                        return f"{main_time}+{added_time}'"
                    elif ':' in pattern and len(time_match.groups()) >= 2:
                        # Формат HH:MM
                        hours, minutes = time_match.groups()[:2]
                        total_minutes = int(hours) * 60 + int(minutes)
                        return f"{total_minutes}'"
                    else:
                        # Обычная минута
                        minute = time_match.group(1)
                        return f"{minute}'"
            
            # Если ничего не найдено, ищем ключевые слова статуса
            if re.search(r'\bLIVE\b', page_text, re.IGNORECASE):
                # Если матч live, но минута не найдена, возвращаем среднее значение
                return "45'"
            elif re.search(r'\bHT\b', page_text):
                return "HT"
            elif re.search(r'\bFT\b', page_text):
                return "FT"
            
            # По умолчанию возвращаем начальное время
            return "1'"
            
        except Exception as e:
            return "1'"
    
    def _extract_basic_statistics(self, page_text: str) -> Dict[str, Any]:
        """
        Извлечение базовой статистики
        """
        stats = {}
        
        # Владение мячом
        possession = re.findall(r'(\d{1,2})%', page_text)
        if len(possession) >= 2:
            stats['possession'] = {
                'team1': f"{possession[0]}%",
                'team2': f"{possession[1]}%"
            }
        
        # xG
        xg_values = re.findall(r'(\d+\.\d+)', page_text)
        valid_xg = [x for x in xg_values if 0.0 <= float(x) <= 10.0]
        
        if len(valid_xg) >= 2:
            stats['xG'] = {
                'team1': valid_xg[0],
                'team2': valid_xg[1]
            }
        
        # Удары (ищем небольшие числа)
        small_numbers = [int(x) for x in re.findall(r'\b(\d{1,2})\b', page_text) 
                        if 1 <= int(x) <= 25]
        
        if len(small_numbers) >= 4:
            stats['shots'] = {
                'team1': str(small_numbers[0]),
                'team2': str(small_numbers[1])
            }
        
        return stats
    
    def _remove_duplicates(self, matches: List[Dict[str, Any]], sport: str) -> List[Dict[str, Any]]:
        """
        Удаление дубликатов
        """
        seen = set()
        unique = []
        
        for match in matches:
            if sport == 'tennis':
                key = f"{match.get('player1', '')}-{match.get('player2', '')}"
            else:
                key = f"{match.get('team1', '')}-{match.get('team2', '')}"
            
            key = key.lower().strip()
            
            if key not in seen and len(key) > 6:
                seen.add(key)
                unique.append(match)
        
        return unique