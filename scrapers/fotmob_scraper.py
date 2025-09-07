"""
FotMob.com парсер для рейтингов команд и xG данных
Высокий рейтинг: 8/10 для футбольных рейтингов и аналитики
"""
import requests
import time
import re
import json
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from datetime import datetime

class FotMobScraper:
    """
    Парсер для FotMob.com - рейтинги команд и xG аналитика
    """
    
    def __init__(self, logger):
        self.logger = logger
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive'
        })
    
    def get_team_ratings(self, team_name: str) -> Dict[str, Any]:
        """
        Получение рейтингов команды с FotMob
        """
        try:
            self.logger.info(f"FotMob: получение рейтингов для {team_name}")
            
            # Поиск команды
            search_url = f"https://www.fotmob.com/api/searchapi/{team_name.replace(' ', '%20')}"
            response = self.session.get(search_url, timeout=10)
            
            if response.status_code == 200:
                try:
                    search_data = response.json()
                    team_id = self._extract_team_id(search_data, team_name)
                    
                    if team_id:
                        # Получаем детальную информацию о команде
                        team_stats = self._get_team_details(team_id)
                        return team_stats
                        
                except json.JSONDecodeError:
                    # Если JSON не парсится, пробуем HTML
                    return self._parse_html_ratings(response.text, team_name)
            
            return {}
            
        except Exception as e:
            self.logger.warning(f"FotMob рейтинги ошибка: {e}")
            return {}
    
    def get_match_analytics(self, team1: str, team2: str) -> Dict[str, Any]:
        """
        Получение аналитики матча с FotMob
        """
        try:
            self.logger.info(f"FotMob: аналитика {team1} vs {team2}")
            
            match_data = {
                'team1_rating': None,
                'team2_rating': None,
                'xg_prediction': {},
                'form_comparison': {},
                'head_to_head': {}
            }
            
            # Получаем рейтинги обеих команд
            team1_rating = self.get_team_ratings(team1)
            team2_rating = self.get_team_ratings(team2)
            
            if team1_rating:
                match_data['team1_data'] = team1_rating
            if team2_rating:
                match_data['team2_data'] = team2_rating
            
            # Поиск конкретного матча
            match_info = self._find_match_on_fotmob(team1, team2)
            if match_info:
                match_data['match_details'] = match_info
            
            return match_data
            
        except Exception as e:
            self.logger.warning(f"FotMob аналитика ошибка: {e}")
            return {}
    
    def get_live_ratings(self) -> Dict[str, Any]:
        """
        Получение live рейтингов команд
        """
        try:
            self.logger.info("FotMob: получение live рейтингов")
            
            # Главная страница с live данными
            live_url = "https://www.fotmob.com/matches"
            response = self.session.get(live_url, timeout=10)
            
            if response.status_code == 200:
                live_data = self._parse_live_data(response.text)
                return live_data
            
            return {}
            
        except Exception as e:
            self.logger.warning(f"FotMob live рейтинги ошибка: {e}")
            return {}
    
    def _extract_team_id(self, search_data: dict, team_name: str) -> Optional[str]:
        """
        Извлечение ID команды из результатов поиска
        """
        try:
            if 'teams' in search_data:
                for team in search_data['teams']:
                    if team_name.lower() in team.get('name', '').lower():
                        return str(team.get('id'))
            
            return None
            
        except Exception as e:
            return None
    
    def _get_team_details(self, team_id: str) -> Dict[str, Any]:
        """
        Получение детальной информации о команде
        """
        try:
            team_url = f"https://www.fotmob.com/api/teams?id={team_id}"
            response = self.session.get(team_url, timeout=10)
            
            if response.status_code == 200:
                team_data = response.json()
                
                stats = {
                    'team_id': team_id,
                    'name': team_data.get('details', {}).get('name'),
                    'rating': self._extract_team_rating(team_data),
                    'form': self._extract_team_form_from_json(team_data),
                    'league_position': self._extract_league_position(team_data),
                    'recent_matches': self._extract_recent_matches(team_data),
                    'top_players': self._extract_top_players_from_json(team_data)
                }
                
                return stats
            
            return {}
            
        except Exception as e:
            return {}
    
    def _parse_html_ratings(self, html_content: str, team_name: str) -> Dict[str, Any]:
        """
        Парсинг рейтингов из HTML (fallback метод)
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            ratings = {
                'team_name': team_name,
                'overall_rating': None,
                'attack_rating': None,
                'defense_rating': None,
                'form_rating': None
            }
            
            # Ищем рейтинги в HTML
            rating_pattern = r'(\d+\.\d+)'
            rating_elements = soup.find_all(string=re.compile(rating_pattern))
            
            for element in rating_elements[:4]:  # Берем первые 4 рейтинга
                rating_match = re.search(rating_pattern, element)
                if rating_match:
                    rating = float(rating_match.group(1))
                    if 0 <= rating <= 10:  # Валидный рейтинг
                        if not ratings['overall_rating']:
                            ratings['overall_rating'] = rating
                        elif not ratings['attack_rating']:
                            ratings['attack_rating'] = rating
                        elif not ratings['defense_rating']:
                            ratings['defense_rating'] = rating
                        elif not ratings['form_rating']:
                            ratings['form_rating'] = rating
            
            return ratings
            
        except Exception as e:
            return {}
    
    def _find_match_on_fotmob(self, team1: str, team2: str) -> Dict[str, Any]:
        """
        Поиск конкретного матча на FotMob
        """
        try:
            # Ищем на странице live матчей
            live_url = "https://www.fotmob.com/api/matches?date=today"
            response = self.session.get(live_url, timeout=10)
            
            if response.status_code == 200:
                matches_data = response.json()
                
                # Ищем наш матч
                for league in matches_data.get('leagues', []):
                    for match in league.get('matches', []):
                        home_team = match.get('home', {}).get('name', '')
                        away_team = match.get('away', {}).get('name', '')
                        
                        if ((team1.lower() in home_team.lower() or team1.lower() in away_team.lower()) and
                            (team2.lower() in home_team.lower() or team2.lower() in away_team.lower())):
                            
                            return {
                                'match_id': match.get('id'),
                                'home_team': home_team,
                                'away_team': away_team,
                                'status': match.get('status'),
                                'score': match.get('score'),
                                'league': league.get('name')
                            }
            
            return {}
            
        except Exception as e:
            return {}
    
    def _parse_live_data(self, html_content: str) -> Dict[str, Any]:
        """
        Парсинг live данных
        """
        try:
            live_data = {
                'live_matches': [],
                'top_rated_teams': [],
                'trending_players': []
            }
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Ищем live матчи
            match_elements = soup.select('.match, [class*="match"]')
            
            for element in match_elements[:10]:
                text = element.get_text(strip=True)
                
                # Ищем команды в элементе
                team_pattern = r'([А-ЯA-Z][а-яa-z\s]{2,25})\s+vs\s+([А-ЯA-Z][а-яa-z\s]{2,25})'
                team_match = re.search(team_pattern, text)
                
                if team_match:
                    team1, team2 = team_match.groups()
                    
                    # Ищем рейтинг в том же элементе
                    rating_pattern = r'(\d+\.\d+)'
                    rating_match = re.search(rating_pattern, text)
                    
                    match_info = {
                        'team1': team1.strip(),
                        'team2': team2.strip(),
                        'rating': float(rating_match.group(1)) if rating_match else None
                    }
                    
                    live_data['live_matches'].append(match_info)
            
            return live_data
            
        except Exception as e:
            return {}
    
    def _extract_team_rating(self, team_data: dict) -> Optional[float]:
        """
        Извлечение рейтинга команды из JSON
        """
        try:
            # Ищем рейтинг в различных секциях
            rating_paths = [
                ['details', 'rating'],
                ['overview', 'rating'],
                ['stats', 'rating'],
                ['performance', 'rating']
            ]
            
            for path in rating_paths:
                current_data = team_data
                for key in path:
                    if isinstance(current_data, dict) and key in current_data:
                        current_data = current_data[key]
                    else:
                        break
                else:
                    # Если дошли до конца пути
                    if isinstance(current_data, (int, float)):
                        return float(current_data)
            
            return None
            
        except Exception as e:
            return None
    
    def _extract_team_form_from_json(self, team_data: dict) -> List[str]:
        """
        Извлечение формы команды из JSON
        """
        try:
            form = []
            
            # Ищем форму в разных секциях
            if 'fixtures' in team_data:
                fixtures = team_data['fixtures']
                if 'allFixtures' in fixtures:
                    recent_matches = fixtures['allFixtures']['finished'][:5]
                    
                    for match in recent_matches:
                        home_score = match.get('home', {}).get('score')
                        away_score = match.get('away', {}).get('score')
                        
                        if home_score is not None and away_score is not None:
                            if home_score > away_score:
                                form.append('W')
                            elif home_score < away_score:
                                form.append('L')
                            else:
                                form.append('D')
            
            return form
            
        except Exception as e:
            return []
    
    def _extract_league_position(self, team_data: dict) -> Dict[str, Any]:
        """
        Извлечение позиции в лиге
        """
        try:
            position_data = {}
            
            if 'table' in team_data:
                table = team_data['table']
                if 'all' in table:
                    team_table_data = table['all']
                    position_data = {
                        'position': team_table_data.get('pos'),
                        'points': team_table_data.get('pts'),
                        'played': team_table_data.get('played'),
                        'wins': team_table_data.get('wins'),
                        'draws': team_table_data.get('draws'),
                        'losses': team_table_data.get('losses')
                    }
            
            return position_data
            
        except Exception as e:
            return {}
    
    def _extract_recent_matches(self, team_data: dict) -> List[Dict[str, Any]]:
        """
        Извлечение последних матчей
        """
        try:
            recent_matches = []
            
            if 'fixtures' in team_data:
                fixtures = team_data['fixtures']
                if 'allFixtures' in fixtures:
                    finished_matches = fixtures['allFixtures']['finished'][:5]
                    
                    for match in finished_matches:
                        match_info = {
                            'opponent': match.get('opponent', {}).get('name'),
                            'home': match.get('home', {}).get('score'),
                            'away': match.get('away', {}).get('score'),
                            'date': match.get('utcTime'),
                            'competition': match.get('competition', {}).get('name')
                        }
                        recent_matches.append(match_info)
            
            return recent_matches
            
        except Exception as e:
            return []
    
    def _extract_top_players_from_json(self, team_data: dict) -> List[Dict[str, Any]]:
        """
        Извлечение топ игроков из JSON
        """
        try:
            top_players = []
            
            if 'squad' in team_data:
                squad = team_data['squad']
                
                for player in squad[:10]:  # Топ 10 игроков
                    player_info = {
                        'name': player.get('name'),
                        'position': player.get('position'),
                        'rating': player.get('rating'),
                        'goals': player.get('goals'),
                        'assists': player.get('assists'),
                        'appearances': player.get('appearances')
                    }
                    
                    if player_info['name']:
                        top_players.append(player_info)
            
            return top_players
            
        except Exception as e:
            return []
    
    def get_xg_analytics(self, team1: str, team2: str) -> Dict[str, Any]:
        """
        Получение xG аналитики для матча
        """
        try:
            self.logger.info(f"FotMob: xG аналитика {team1} vs {team2}")
            
            xg_data = {
                'team1_avg_xg': None,
                'team2_avg_xg': None,
                'team1_avg_xga': None,  # xG Against
                'team2_avg_xga': None,
                'prediction': {},
                'trends': {}
            }
            
            # Получаем статистику команд для xG анализа
            team1_stats = self.get_team_ratings(team1)
            team2_stats = self.get_team_ratings(team2)
            
            # Анализируем xG тренды
            if team1_stats and team2_stats:
                xg_data['prediction'] = self._calculate_xg_prediction(team1_stats, team2_stats)
            
            return xg_data
            
        except Exception as e:
            self.logger.warning(f"FotMob xG аналитика ошибка: {e}")
            return {}
    
    def _calculate_xg_prediction(self, team1_stats: dict, team2_stats: dict) -> Dict[str, Any]:
        """
        Расчет xG предсказания на основе статистики команд
        """
        try:
            prediction = {
                'expected_goals_team1': None,
                'expected_goals_team2': None,
                'confidence': None
            }
            
            # Базовый расчет на основе доступных данных
            # Это упрощенная версия, можно расширить
            
            return prediction
            
        except Exception as e:
            return {}
    
    def get_player_ratings(self, player_name: str, team: str) -> Dict[str, Any]:
        """
        Получение рейтингов игрока
        """
        try:
            self.logger.info(f"FotMob: рейтинги игрока {player_name}")
            
            player_stats = {
                'name': player_name,
                'team': team,
                'season_rating': None,
                'match_ratings': [],
                'goals': None,
                'assists': None,
                'xg': None,
                'xa': None
            }
            
            # Поиск игрока через API
            search_url = f"https://www.fotmob.com/api/searchapi/{player_name.replace(' ', '%20')}"
            response = self.session.get(search_url, timeout=10)
            
            if response.status_code == 200:
                try:
                    search_data = response.json()
                    player_id = self._extract_player_id(search_data, player_name)
                    
                    if player_id:
                        player_details = self._get_player_details(player_id)
                        player_stats.update(player_details)
                        
                except json.JSONDecodeError:
                    pass
            
            return player_stats
            
        except Exception as e:
            self.logger.warning(f"FotMob игрок рейтинги ошибка: {e}")
            return {}
    
    def _extract_player_id(self, search_data: dict, player_name: str) -> Optional[str]:
        """
        Извлечение ID игрока
        """
        try:
            if 'players' in search_data:
                for player in search_data['players']:
                    if player_name.lower() in player.get('name', '').lower():
                        return str(player.get('id'))
            
            return None
            
        except Exception as e:
            return None
    
    def _get_player_details(self, player_id: str) -> Dict[str, Any]:
        """
        Получение детальной информации об игроке
        """
        try:
            player_url = f"https://www.fotmob.com/api/playerData?id={player_id}"
            response = self.session.get(player_url, timeout=10)
            
            if response.status_code == 200:
                player_data = response.json()
                
                details = {
                    'season_stats': self._extract_season_stats(player_data),
                    'recent_form': self._extract_player_form(player_data),
                    'position': player_data.get('meta', {}).get('position'),
                    'age': player_data.get('meta', {}).get('age')
                }
                
                return details
            
            return {}
            
        except Exception as e:
            return {}
    
    def _extract_season_stats(self, player_data: dict) -> Dict[str, Any]:
        """
        Извлечение сезонной статистики игрока
        """
        try:
            stats = {}
            
            if 'statSeasons' in player_data:
                current_season = player_data['statSeasons'][0] if player_data['statSeasons'] else {}
                
                if 'stats' in current_season:
                    season_stats = current_season['stats']
                    
                    stats = {
                        'appearances': season_stats.get('appearances'),
                        'goals': season_stats.get('goals'),
                        'assists': season_stats.get('assists'),
                        'rating': season_stats.get('rating'),
                        'minutes_played': season_stats.get('minutesPlayed')
                    }
            
            return stats
            
        except Exception as e:
            return {}
    
    def _extract_player_form(self, player_data: dict) -> List[float]:
        """
        Извлечение формы игрока (последние рейтинги)
        """
        try:
            form = []
            
            if 'recentMatches' in player_data:
                recent_matches = player_data['recentMatches'][:5]
                
                for match in recent_matches:
                    rating = match.get('rating')
                    if rating:
                        form.append(float(rating))
            
            return form
            
        except Exception as e:
            return []
    
    def verify_connection(self) -> bool:
        """
        Проверка доступности FotMob
        """
        try:
            response = self.session.get('https://www.fotmob.com/', timeout=10)
            return response.status_code == 200
        except:
            return False