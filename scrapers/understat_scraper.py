"""
Understat.com парсер для xG статистики и детальной аналитики
Высокий рейтинг: 9/10 для футбольной аналитики
"""
import requests
import time
import re
import json
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from datetime import datetime

class UnderstatScraper:
    """
    Парсер для Understat.com - специализированная футбольная аналитика
    """
    
    def __init__(self, logger):
        self.logger = logger
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive'
        })
    
    def get_team_xg_stats(self, team_name: str) -> Dict[str, Any]:
        """
        Получение xG статистики команды
        """
        try:
            self.logger.info(f"Understat: получение xG для {team_name}")
            
            # Нормализуем название команды для поиска
            normalized_name = self._normalize_team_name(team_name)
            
            # Поиск команды на Understat
            search_url = f"https://understat.com/search/{normalized_name}"
            response = self.session.get(search_url, timeout=10)
            
            if response.status_code == 200:
                team_link = self._find_team_link(response.text, team_name)
                
                if team_link:
                    # Получаем статистику команды
                    team_stats = self._get_team_stats_page(team_link)
                    return team_stats
            
            return {}
            
        except Exception as e:
            self.logger.warning(f"Understat xG статистика ошибка: {e}")
            return {}
    
    def get_match_xg_data(self, team1: str, team2: str) -> Dict[str, Any]:
        """
        Получение xG данных для конкретного матча
        """
        try:
            self.logger.info(f"Understat: xG анализ {team1} vs {team2}")
            
            match_data = {
                'team1_xg': None,
                'team2_xg': None,
                'team1_shots': [],
                'team2_shots': [],
                'key_moments': [],
                'xg_timeline': []
            }
            
            # Поиск матча
            match_link = self._find_match_link(team1, team2)
            
            if match_link:
                match_stats = self._get_match_stats_page(match_link)
                match_data.update(match_stats)
            
            return match_data
            
        except Exception as e:
            self.logger.warning(f"Understat матч xG ошибка: {e}")
            return {}
    
    def get_player_xg_stats(self, player_name: str, team: str) -> Dict[str, Any]:
        """
        Получение xG статистики игрока
        """
        try:
            self.logger.info(f"Understat: xG игрока {player_name}")
            
            player_stats = {
                'name': player_name,
                'team': team,
                'xg_total': None,
                'xa_total': None,
                'shots': None,
                'key_passes': None,
                'npg': None,  # Non-penalty goals
                'npxg': None  # Non-penalty xG
            }
            
            # Поиск игрока
            normalized_name = self._normalize_player_name(player_name)
            search_url = f"https://understat.com/search/{normalized_name}"
            
            response = self.session.get(search_url, timeout=10)
            
            if response.status_code == 200:
                player_link = self._find_player_link(response.text, player_name)
                
                if player_link:
                    player_data = self._get_player_stats_page(player_link)
                    player_stats.update(player_data)
            
            return player_stats
            
        except Exception as e:
            self.logger.warning(f"Understat игрок xG ошибка: {e}")
            return {}
    
    def _normalize_team_name(self, team_name: str) -> str:
        """
        Нормализация названия команды для поиска
        """
        try:
            # Убираем лишние слова и символы
            normalized = re.sub(r'\b(fc|cf|sc|ac|united|city|town)\b', '', team_name.lower())
            normalized = re.sub(r'[^\w\s]', '', normalized)
            normalized = re.sub(r'\s+', '+', normalized.strip())
            
            return normalized
            
        except Exception as e:
            return team_name.replace(' ', '+')
    
    def _normalize_player_name(self, player_name: str) -> str:
        """
        Нормализация имени игрока для поиска
        """
        try:
            # Убираем лишние символы
            normalized = re.sub(r'[^\w\s]', '', player_name)
            normalized = re.sub(r'\s+', '+', normalized.strip())
            
            return normalized
            
        except Exception as e:
            return player_name.replace(' ', '+')
    
    def _find_team_link(self, html_content: str, team_name: str) -> Optional[str]:
        """
        Поиск ссылки на страницу команды
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Ищем ссылки на команды
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link.get('href')
                text = link.get_text(strip=True)
                
                if team_name.lower() in text.lower() and '/team/' in href:
                    return f"https://understat.com{href}"
            
            return None
            
        except Exception as e:
            return None
    
    def _find_player_link(self, html_content: str, player_name: str) -> Optional[str]:
        """
        Поиск ссылки на страницу игрока
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link.get('href')
                text = link.get_text(strip=True)
                
                if player_name.lower() in text.lower() and '/player/' in href:
                    return f"https://understat.com{href}"
            
            return None
            
        except Exception as e:
            return None
    
    def _find_match_link(self, team1: str, team2: str) -> Optional[str]:
        """
        Поиск ссылки на конкретный матч
        """
        try:
            # Ищем на главной странице матчей
            matches_url = "https://understat.com/matches"
            response = self.session.get(matches_url, timeout=10)
            
            if response.status_code == 200:
                # Ищем матч в HTML
                if team1.lower() in response.text.lower() and team2.lower() in response.text.lower():
                    # Извлекаем ссылку на матч
                    match_pattern = rf'href=\"(/match/\d+)\".*?{re.escape(team1)}.*?{re.escape(team2)}'
                    match = re.search(match_pattern, response.text, re.IGNORECASE | re.DOTALL)
                    
                    if match:
                        return f"https://understat.com{match.group(1)}"
            
            return None
            
        except Exception as e:
            return None
    
    def _get_team_stats_page(self, team_url: str) -> Dict[str, Any]:
        """
        Получение статистики со страницы команды
        """
        try:
            response = self.session.get(team_url, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                stats = {
                    'xg_for': self._extract_xg_stat(soup, 'xG For'),
                    'xg_against': self._extract_xg_stat(soup, 'xG Against'),
                    'goals_for': self._extract_stat(soup, 'Goals For'),
                    'goals_against': self._extract_stat(soup, 'Goals Against'),
                    'shots_for': self._extract_stat(soup, 'Shots For'),
                    'shots_against': self._extract_stat(soup, 'Shots Against'),
                    'deep': self._extract_stat(soup, 'Deep'),
                    'ppda': self._extract_stat(soup, 'PPDA'),
                    'form': self._extract_team_form(soup)
                }
                
                return stats
            
            return {}
            
        except Exception as e:
            return {}
    
    def _get_match_stats_page(self, match_url: str) -> Dict[str, Any]:
        """
        Получение статистики матча
        """
        try:
            response = self.session.get(match_url, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                match_stats = {
                    'final_xg': self._extract_match_xg(soup),
                    'shots_data': self._extract_shots_data(soup),
                    'key_moments': self._extract_key_moments(soup),
                    'player_ratings': self._extract_player_ratings(soup)
                }
                
                return match_stats
            
            return {}
            
        except Exception as e:
            return {}
    
    def _get_player_stats_page(self, player_url: str) -> Dict[str, Any]:
        """
        Получение статистики игрока
        """
        try:
            response = self.session.get(player_url, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                player_stats = {
                    'season_xg': self._extract_player_xg(soup),
                    'season_xa': self._extract_player_xa(soup),
                    'goals': self._extract_player_goals(soup),
                    'assists': self._extract_player_assists(soup),
                    'shots': self._extract_player_shots(soup),
                    'key_passes': self._extract_player_key_passes(soup)
                }
                
                return player_stats
            
            return {}
            
        except Exception as e:
            return {}
    
    def _extract_xg_stat(self, soup: BeautifulSoup, stat_name: str) -> Optional[float]:
        """
        Извлечение xG статистики
        """
        try:
            # Ищем статистику по названию
            stat_elements = soup.find_all(string=re.compile(stat_name, re.IGNORECASE))
            
            for element in stat_elements:
                parent = element.parent
                if parent:
                    # Ищем число рядом
                    number_pattern = r'(\d+\.\d+)'
                    numbers = re.findall(number_pattern, parent.get_text())
                    
                    if numbers:
                        return float(numbers[0])
            
            return None
            
        except Exception as e:
            return None
    
    def _extract_stat(self, soup: BeautifulSoup, stat_name: str) -> Optional[int]:
        """
        Извлечение числовой статистики
        """
        try:
            stat_elements = soup.find_all(string=re.compile(stat_name, re.IGNORECASE))
            
            for element in stat_elements:
                parent = element.parent
                if parent:
                    number_pattern = r'(\d+)'
                    numbers = re.findall(number_pattern, parent.get_text())
                    
                    if numbers:
                        return int(numbers[0])
            
            return None
            
        except Exception as e:
            return None
    
    def _extract_team_form(self, soup: BeautifulSoup) -> List[str]:
        """
        Извлечение формы команды
        """
        try:
            form = []
            
            # Ищем индикаторы формы
            form_elements = soup.select('.form, .recent-form, [class*="form"]')
            
            for element in form_elements:
                text = element.get_text()
                # Ищем W, D, L паттерны
                form_matches = re.findall(r'[WDL]', text)
                if form_matches:
                    form.extend(form_matches[:5])
                    break
            
            return form
            
        except Exception as e:
            return []
    
    def _extract_match_xg(self, soup: BeautifulSoup) -> Dict[str, float]:
        """
        Извлечение финального xG матча
        """
        try:
            xg_data = {}
            
            # Ищем xG данные матча
            xg_pattern = r'xG:\s*(\d+\.\d+)'
            page_text = soup.get_text()
            
            xg_matches = re.findall(xg_pattern, page_text)
            
            if len(xg_matches) >= 2:
                xg_data['team1_xg'] = float(xg_matches[0])
                xg_data['team2_xg'] = float(xg_matches[1])
            
            return xg_data
            
        except Exception as e:
            return {}
    
    def _extract_shots_data(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Извлечение данных об ударах
        """
        try:
            shots = []
            
            # Ищем данные об ударах в JSON или HTML
            script_tags = soup.find_all('script')
            
            for script in script_tags:
                if script.string and 'shots' in script.string:
                    try:
                        # Пытаемся извлечь JSON данные об ударах
                        json_match = re.search(r'shots\s*=\s*(\[.*?\])', script.string, re.DOTALL)
                        if json_match:
                            shots_json = json.loads(json_match.group(1))
                            
                            for shot in shots_json:
                                shot_data = {
                                    'minute': shot.get('minute'),
                                    'xg': shot.get('xG'),
                                    'player': shot.get('player'),
                                    'result': shot.get('result')
                                }
                                shots.append(shot_data)
                    except:
                        continue
            
            return shots
            
        except Exception as e:
            return []
    
    def _extract_key_moments(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Извлечение ключевых моментов матча
        """
        try:
            moments = []
            
            # Ищем временную шкалу событий
            timeline_elements = soup.select('.timeline, .events, [class*="moment"]')
            
            for element in timeline_elements:
                text = element.get_text()
                
                # Ищем голы с xG
                goal_pattern = r'(\d+)\'.*?Goal.*?xG:\s*(\d+\.\d+)'
                goals = re.findall(goal_pattern, text)
                
                for minute, xg in goals:
                    moments.append({
                        'minute': int(minute),
                        'type': 'goal',
                        'xg': float(xg)
                    })
            
            return moments
            
        except Exception as e:
            return []
    
    def _extract_player_ratings(self, soup: BeautifulSoup) -> Dict[str, float]:
        """
        Извлечение рейтингов игроков
        """
        try:
            ratings = {}
            
            # Ищем рейтинги в таблице игроков
            player_tables = soup.select('.player-table, .lineup-table')
            
            for table in player_tables:
                rows = table.find_all('tr')
                
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        player_cell = cells[0].get_text(strip=True)
                        rating_cell = cells[-1].get_text(strip=True)
                        
                        # Проверяем, что это рейтинг
                        rating_match = re.search(r'(\d+\.\d+)', rating_cell)
                        if rating_match and player_cell:
                            rating = float(rating_match.group(1))
                            if 0 <= rating <= 10:  # Разумный диапазон рейтинга
                                ratings[player_cell] = rating
            
            return ratings
            
        except Exception as e:
            return {}
    
    def _extract_player_xg(self, soup: BeautifulSoup) -> Optional[float]:
        """
        Извлечение сезонного xG игрока
        """
        try:
            # Ищем xG в статистике игрока
            xg_elements = soup.find_all(string=re.compile(r'xG', re.IGNORECASE))
            
            for element in xg_elements:
                parent = element.parent
                if parent:
                    numbers = re.findall(r'(\d+\.\d+)', parent.get_text())
                    if numbers:
                        return float(numbers[0])
            
            return None
            
        except Exception as e:
            return None
    
    def _extract_player_xa(self, soup: BeautifulSoup) -> Optional[float]:
        """
        Извлечение сезонного xA игрока
        """
        try:
            xa_elements = soup.find_all(string=re.compile(r'xA', re.IGNORECASE))
            
            for element in xa_elements:
                parent = element.parent
                if parent:
                    numbers = re.findall(r'(\d+\.\d+)', parent.get_text())
                    if numbers:
                        return float(numbers[0])
            
            return None
            
        except Exception as e:
            return None
    
    def _extract_player_goals(self, soup: BeautifulSoup) -> Optional[int]:
        """
        Извлечение количества голов игрока
        """
        try:
            goals_elements = soup.find_all(string=re.compile(r'Goals?', re.IGNORECASE))
            
            for element in goals_elements:
                parent = element.parent
                if parent:
                    numbers = re.findall(r'(\d+)', parent.get_text())
                    if numbers:
                        goals = int(numbers[0])
                        if 0 <= goals <= 100:  # Разумный диапазон
                            return goals
            
            return None
            
        except Exception as e:
            return None
    
    def _extract_player_assists(self, soup: BeautifulSoup) -> Optional[int]:
        """
        Извлечение количества передач игрока
        """
        try:
            assists_elements = soup.find_all(string=re.compile(r'Assists?', re.IGNORECASE))
            
            for element in assists_elements:
                parent = element.parent
                if parent:
                    numbers = re.findall(r'(\d+)', parent.get_text())
                    if numbers:
                        assists = int(numbers[0])
                        if 0 <= assists <= 50:  # Разумный диапазон
                            return assists
            
            return None
            
        except Exception as e:
            return None
    
    def _extract_player_shots(self, soup: BeautifulSoup) -> Optional[int]:
        """
        Извлечение количества ударов игрока
        """
        try:
            shots_elements = soup.find_all(string=re.compile(r'Shots?', re.IGNORECASE))
            
            for element in shots_elements:
                parent = element.parent
                if parent:
                    numbers = re.findall(r'(\d+)', parent.get_text())
                    if numbers:
                        shots = int(numbers[0])
                        if 0 <= shots <= 200:  # Разумный диапазон
                            return shots
            
            return None
            
        except Exception as e:
            return None
    
    def _extract_player_key_passes(self, soup: BeautifulSoup) -> Optional[int]:
        """
        Извлечение ключевых передач игрока
        """
        try:
            kp_elements = soup.find_all(string=re.compile(r'Key.*Pass', re.IGNORECASE))
            
            for element in kp_elements:
                parent = element.parent
                if parent:
                    numbers = re.findall(r'(\d+)', parent.get_text())
                    if numbers:
                        key_passes = int(numbers[0])
                        if 0 <= key_passes <= 100:
                            return key_passes
            
            return None
            
        except Exception as e:
            return None
    
    def verify_connection(self) -> bool:
        """
        Проверка доступности Understat
        """
        try:
            response = self.session.get('https://understat.com/', timeout=10)
            return response.status_code == 200
        except:
            return False