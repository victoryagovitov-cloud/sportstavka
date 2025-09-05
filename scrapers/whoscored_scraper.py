"""
Скрапер для WhoScored.com - рейтинги игроков и детальная аналитика
"""
import requests
import json
import re
from typing import List, Dict, Any
from datetime import datetime
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from scrapers.base_scraper import BaseScraper

class WhoScoredScraper(BaseScraper):
    """
    Скрапер для WhoScored.com с акцентом на рейтинги и аналитику
    """
    
    def __init__(self, logger):
        super().__init__(logger)
        self.base_url = "https://www.whoscored.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.whoscored.com/',
            'Connection': 'keep-alive'
        })
    
    def get_live_matches(self, sport: str = 'football') -> List[Dict[str, Any]]:
        """
        Получение live матчей с WhoScored (в основном футбол)
        """
        try:
            self.logger.info(f"WhoScored: сбор live матчей")
            
            # WhoScored в основном фокусируется на футболе
            live_url = f"{self.base_url}/LiveScores"
            
            self.setup_driver()
            self.driver.get(live_url)
            time.sleep(5)  # WhoScored может загружаться медленно
            
            matches = []
            
            # Селекторы для live матчей
            match_selectors = [
                ".fixture",
                ".match-row",
                "[class*='live-match']",
                ".tournament-fixture"
            ]
            
            match_elements = []
            for selector in match_selectors:
                elements = self.safe_find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    match_elements = elements
                    self.logger.info(f"WhoScored: найдено {len(elements)} матчей с селектором {selector}")
                    break
            
            for element in match_elements[:15]:  # Ограничиваем количество
                match_data = self._extract_whoscored_match(element)
                if match_data:
                    matches.append(match_data)
            
            self.logger.info(f"WhoScored: извлечено {len(matches)} матчей")
            return matches
            
        except Exception as e:
            self.logger.error(f"WhoScored ошибка: {e}")
            return []
        finally:
            self.close_driver()
    
    def _extract_whoscored_match(self, element) -> Dict[str, Any]:
        """
        Извлечение данных матча из WhoScored элемента
        """
        try:
            match_data = {
                'source': 'whoscored',
                'sport': 'football',
                'timestamp': datetime.now().isoformat()
            }
            
            # Команды
            team_elements = element.find_elements(By.CSS_SELECTOR, ".team, [class*='team-name'], .home, .away")
            teams = []
            for team_elem in team_elements:
                team_text = self.safe_get_text(team_elem)
                if team_text and len(team_text) > 1:
                    teams.append(team_text)
            
            if len(teams) >= 2:
                match_data['team1'] = teams[0]
                match_data['team2'] = teams[1]
            
            # Счет
            score_elem = element.find_elements(By.CSS_SELECTOR, ".result, .score, [class*='score']")
            if score_elem:
                score_text = self.safe_get_text(score_elem[0])
                score_match = re.search(r'(\d+)\s*-\s*(\d+)', score_text)
                if score_match:
                    match_data['score'] = f"{score_match.group(1)}:{score_match.group(2)}"
            
            # Время
            time_elem = element.find_elements(By.CSS_SELECTOR, ".time, .minute, [class*='time']")
            if time_elem:
                match_data['time'] = self.safe_get_text(time_elem[0])
            
            # URL матча
            link_elem = element.find_elements(By.TAG_NAME, "a")
            if link_elem:
                href = self.safe_get_attribute(link_elem[0], "href")
                if href:
                    match_data['url'] = href if href.startswith('http') else f"{self.base_url}{href}"
            
            # Лига
            league_elem = element.find_elements(By.CSS_SELECTOR, ".tournament, .league, [class*='competition']")
            if league_elem:
                match_data['league'] = self.safe_get_text(league_elem[0])
            
            return match_data if match_data.get('team1') and match_data.get('team2') else None
            
        except Exception as e:
            self.logger.warning(f"WhoScored извлечение матча ошибка: {e}")
            return None
    
    def get_match_ratings(self, match_url: str) -> Dict[str, Any]:
        """
        Получение рейтингов игроков для матча
        """
        try:
            self.logger.info(f"WhoScored: получение рейтингов для {match_url}")
            
            self.setup_driver()
            self.driver.get(match_url)
            time.sleep(5)
            
            ratings_data = {
                'url': match_url,
                'source': 'whoscored',
                'timestamp': datetime.now().isoformat()
            }
            
            # Переходим на вкладку с рейтингами
            ratings_tab = self.safe_find_element(By.CSS_SELECTOR, "[data-tab='player-ratings'], .tab-ratings, [href*='ratings']")
            if ratings_tab:
                self.safe_click(ratings_tab)
                time.sleep(3)
            
            # Извлекаем рейтинги игроков
            player_ratings = self._extract_player_ratings()
            if player_ratings:
                ratings_data['player_ratings'] = player_ratings
            
            # Средние рейтинги команд
            team_ratings = self._extract_team_ratings()
            if team_ratings:
                ratings_data['team_ratings'] = team_ratings
            
            # Ключевые статистики
            key_stats = self._extract_key_statistics()
            if key_stats:
                ratings_data['key_statistics'] = key_stats
            
            return ratings_data
            
        except Exception as e:
            self.logger.error(f"WhoScored рейтинги ошибка: {e}")
            return {'url': match_url, 'error': str(e)}
        finally:
            self.close_driver()
    
    def _extract_player_ratings(self) -> Dict[str, Any]:
        """
        Извлечение рейтингов игроков
        """
        try:
            ratings = {'team1_players': [], 'team2_players': []}
            
            # Селекторы для рейтингов игроков
            player_selectors = [
                ".player-rating",
                "[class*='rating']",
                ".player-row",
                ".lineup-player"
            ]
            
            for selector in player_selectors:
                player_elements = self.safe_find_elements(By.CSS_SELECTOR, selector)
                if player_elements:
                    break
            
            for element in player_elements:
                player_data = self._extract_single_player_rating(element)
                if player_data:
                    # Определяем команду по позиции или другим признакам
                    team_key = 'team1_players' if len(ratings['team1_players']) <= len(ratings['team2_players']) else 'team2_players'
                    ratings[team_key].append(player_data)
            
            return ratings
            
        except Exception as e:
            self.logger.warning(f"WhoScored извлечение рейтингов игроков ошибка: {e}")
            return {}
    
    def _extract_single_player_rating(self, element) -> Dict[str, Any]:
        """
        Извлечение рейтинга отдельного игрока
        """
        try:
            player_data = {}
            
            # Имя игрока
            name_elem = element.find_elements(By.CSS_SELECTOR, ".player-name, .name, [class*='player-name']")
            if name_elem:
                player_data['name'] = self.safe_get_text(name_elem[0])
            
            # Рейтинг (обычно число от 1 до 10)
            rating_elem = element.find_elements(By.CSS_SELECTOR, ".rating, .score, [class*='rating-score']")
            if rating_elem:
                rating_text = self.safe_get_text(rating_elem[0])
                rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                if rating_match:
                    player_data['rating'] = float(rating_match.group(1))
            
            # Позиция
            position_elem = element.find_elements(By.CSS_SELECTOR, ".position, .pos")
            if position_elem:
                player_data['position'] = self.safe_get_text(position_elem[0])
            
            return player_data if player_data.get('name') and player_data.get('rating') else None
            
        except Exception as e:
            self.logger.warning(f"WhoScored извлечение рейтинга игрока ошибка: {e}")
            return None
    
    def _extract_team_ratings(self) -> Dict[str, Any]:
        """
        Извлечение средних рейтингов команд
        """
        try:
            team_ratings = {}
            
            # Ищем средние рейтинги команд
            team_rating_selectors = [
                ".team-rating",
                "[class*='team-average']",
                ".average-rating"
            ]
            
            for selector in team_rating_selectors:
                rating_elements = self.safe_find_elements(By.CSS_SELECTOR, selector)
                if len(rating_elements) >= 2:
                    team1_rating = self.safe_get_text(rating_elements[0])
                    team2_rating = self.safe_get_text(rating_elements[1])
                    
                    # Извлекаем числовые значения
                    team1_match = re.search(r'(\d+\.?\d*)', team1_rating)
                    team2_match = re.search(r'(\d+\.?\d*)', team2_rating)
                    
                    if team1_match and team2_match:
                        team_ratings['team1_average'] = float(team1_match.group(1))
                        team_ratings['team2_average'] = float(team2_match.group(1))
                    break
            
            return team_ratings
            
        except Exception as e:
            self.logger.warning(f"WhoScored извлечение рейтингов команд ошибка: {e}")
            return {}
    
    def _extract_key_statistics(self) -> Dict[str, Any]:
        """
        Извлечение ключевой статистики матча
        """
        try:
            stats = {}
            
            # Переходим на вкладку статистики
            stats_tab = self.safe_find_element(By.CSS_SELECTOR, "[data-tab='stats'], .tab-stats, [href*='statistics']")
            if stats_tab:
                self.safe_click(stats_tab)
                time.sleep(2)
            
            # Извлекаем статистику
            stat_rows = self.safe_find_elements(By.CSS_SELECTOR, ".stat-row, [class*='statistic-row']")
            
            for row in stat_rows:
                stat_name_elem = row.find_elements(By.CSS_SELECTOR, ".stat-name, .statistic-name")
                stat_values = row.find_elements(By.CSS_SELECTOR, ".stat-value, .statistic-value")
                
                if stat_name_elem and len(stat_values) >= 2:
                    stat_name = self.safe_get_text(stat_name_elem[0])
                    team1_value = self.safe_get_text(stat_values[0])
                    team2_value = self.safe_get_text(stat_values[1])
                    
                    stats[stat_name] = {
                        'team1': team1_value,
                        'team2': team2_value
                    }
            
            return stats
            
        except Exception as e:
            self.logger.warning(f"WhoScored извлечение статистики ошибка: {e}")
            return {}
    
    def get_team_rankings(self, league_url: str) -> Dict[str, Any]:
        """
        Получение рейтингов команд в лиге
        """
        try:
            self.logger.info(f"WhoScored: получение рейтингов команд {league_url}")
            
            self.setup_driver()
            self.driver.get(league_url)
            time.sleep(3)
            
            rankings = {}
            
            # Ищем таблицу с рейтингами команд
            table_rows = self.safe_find_elements(By.CSS_SELECTOR, ".table-row, tr, [class*='team-row']")
            
            for row in table_rows:
                team_name_elem = row.find_elements(By.CSS_SELECTOR, ".team-name, .team, [class*='team-name']")
                rating_elem = row.find_elements(By.CSS_SELECTOR, ".rating, .score, [class*='rating']")
                position_elem = row.find_elements(By.CSS_SELECTOR, ".position, .rank")
                
                if team_name_elem and rating_elem:
                    team_name = self.safe_get_text(team_name_elem[0])
                    rating = self.safe_get_text(rating_elem[0])
                    position = self.safe_get_text(position_elem[0]) if position_elem else ''
                    
                    rankings[team_name] = {
                        'rating': rating,
                        'position': position
                    }
            
            return rankings
            
        except Exception as e:
            self.logger.error(f"WhoScored рейтинги команд ошибка: {e}")
            return {}
        finally:
            self.close_driver()
    
    def filter_matches(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Фильтрация матчей WhoScored (базовая реализация)
        """
        filtered = []
        
        for match in matches:
            # Базовые проверки
            if not match.get('team1') or not match.get('team2'):
                continue
            
            # Проверяем что команды не одинаковые
            if match.get('team1', '').lower() == match.get('team2', '').lower():
                continue
            
            # WhoScored в основном для детальной аналитики, пропускаем все валидные матчи
            filtered.append(match)
        
        return filtered
    
    def collect_match_data(self, match_url: str) -> Dict[str, Any]:
        """
        Сбор детальных данных матча (делегируем к get_match_ratings)
        """
        return self.get_match_ratings(match_url)
    
    def verify_connection(self) -> bool:
        """
        Проверка подключения к WhoScored
        """
        try:
            response = self.session.get(f"{self.base_url}/LiveScores", timeout=5)
            return response.status_code == 200
        except:
            return False