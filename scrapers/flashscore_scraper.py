"""
Скрапер для FlashScore.com - альтернативный источник данных
Основан на анализе GitHub репозиториев FlashScore парсеров
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

class FlashScoreScraper(BaseScraper):
    """
    Скрапер для FlashScore.com с методами на основе GitHub решений
    """
    
    def __init__(self, logger):
        super().__init__(logger)
        self.base_url = "https://www.flashscore.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # URL паттерны для разных видов спорта
        self.sport_urls = {
            'football': f"{self.base_url}/football/",
            'tennis': f"{self.base_url}/tennis/",
            'handball': f"{self.base_url}/handball/",
            'basketball': f"{self.base_url}/basketball/"
        }
    
    def get_live_matches(self, sport: str) -> List[Dict[str, Any]]:
        """
        Получение live матчей с FlashScore
        """
        try:
            self.logger.info(f"FlashScore: сбор live матчей {sport}")
            
            sport_url = self.sport_urls.get(sport)
            if not sport_url:
                self.logger.warning(f"FlashScore: неподдерживаемый спорт {sport}")
                return []
            
            # Пробуем API метод
            api_matches = self._get_matches_via_api(sport)
            if api_matches:
                return api_matches
            
            # Если API не работает, используем веб-скрапинг
            return self._get_matches_via_web(sport)
            
        except Exception as e:
            self.logger.error(f"FlashScore ошибка для {sport}: {e}")
            return []
    
    def _get_matches_via_api(self, sport: str) -> List[Dict[str, Any]]:
        """
        Получение матчей через FlashScore API (если доступно)
        """
        try:
            # FlashScore использует внутренние API endpoints
            api_endpoints = {
                'football': f"{self.base_url}/x/feed/f_1_0_2_en_1",
                'tennis': f"{self.base_url}/x/feed/f_13_0_2_en_1",
                'handball': f"{self.base_url}/x/feed/f_16_0_2_en_1"
            }
            
            endpoint = api_endpoints.get(sport)
            if not endpoint:
                return []
            
            response = self.session.get(endpoint, timeout=10)
            if response.status_code != 200:
                return []
            
            # FlashScore API возвращает специальный формат
            matches = self._parse_flashscore_api_response(response.text, sport)
            
            if matches:
                self.logger.info(f"FlashScore API: найдено {len(matches)} матчей {sport}")
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"FlashScore API ошибка: {e}")
            return []
    
    def _parse_flashscore_api_response(self, response_text: str, sport: str) -> List[Dict[str, Any]]:
        """
        Парсинг ответа FlashScore API
        """
        matches = []
        
        try:
            # FlashScore API использует специальный формат с разделителями
            lines = response_text.split('~')
            
            current_match = {}
            tournament_name = ""
            
            for line in lines:
                if not line:
                    continue
                
                parts = line.split('¬')
                if len(parts) < 2:
                    continue
                
                command = parts[0]
                
                # Парсим различные команды FlashScore API
                if command == 'ZA':  # Tournament header
                    if len(parts) > 2:
                        tournament_name = parts[2]
                
                elif command == 'AA':  # Match data
                    if len(parts) > 10:
                        match_data = self._parse_match_line(parts, sport, tournament_name)
                        if match_data:
                            matches.append(match_data)
                
                elif command == 'AB':  # Live score update
                    if len(parts) > 5 and current_match:
                        self._update_match_score(current_match, parts)
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"FlashScore API парсинг ошибка: {e}")
            return []
    
    def _parse_match_line(self, parts: List[str], sport: str, tournament: str) -> Dict[str, Any]:
        """
        Парсинг строки данных матча из FlashScore API
        """
        try:
            match_data = {
                'source': 'flashscore',
                'sport': sport,
                'league': tournament,
                'timestamp': datetime.now().isoformat()
            }
            
            # FlashScore API структура (может варьироваться)
            if len(parts) > 10:
                match_data['match_id'] = parts[1]
                match_data['team1'] = parts[4] if len(parts) > 4 else ''
                match_data['team2'] = parts[5] if len(parts) > 5 else ''
                
                # Счет
                score1 = parts[6] if len(parts) > 6 else '0'
                score2 = parts[7] if len(parts) > 7 else '0'
                match_data['score'] = f"{score1}:{score2}"
                
                # Время/статус
                match_data['time'] = parts[8] if len(parts) > 8 else 'LIVE'
                match_data['status'] = parts[9] if len(parts) > 9 else 'LIVE'
                
                # URL матча
                match_data['url'] = f"{self.base_url}/match/{match_data['match_id']}"
            
            return match_data if match_data.get('team1') and match_data.get('team2') else None
            
        except Exception as e:
            self.logger.warning(f"FlashScore парсинг строки ошибка: {e}")
            return None
    
    def _update_match_score(self, match: Dict, parts: List[str]):
        """
        Обновление счета матча
        """
        try:
            if len(parts) > 3:
                score1 = parts[2]
                score2 = parts[3]
                match['score'] = f"{score1}:{score2}"
                match['updated'] = datetime.now().isoformat()
        except:
            pass
    
    def _get_matches_via_web(self, sport: str) -> List[Dict[str, Any]]:
        """
        Получение матчей через веб-скрапинг (резервный метод)
        """
        try:
            self.setup_driver()
            sport_url = self.sport_urls[sport]
            
            self.driver.get(sport_url)
            time.sleep(3)
            
            matches = []
            
            # Селекторы на основе анализа FlashScore
            match_selectors = [
                ".event__match",
                "[class*='event']",
                ".sportName",
                "[data-testid*='match']"
            ]
            
            for selector in match_selectors:
                match_elements = self.safe_find_elements(By.CSS_SELECTOR, selector)
                if match_elements:
                    self.logger.info(f"FlashScore: найдено {len(match_elements)} элементов с селектором {selector}")
                    break
            
            for element in match_elements[:20]:  # Ограничиваем количество
                match_data = self._extract_match_from_element(element, sport)
                if match_data:
                    matches.append(match_data)
            
            self.logger.info(f"FlashScore веб: извлечено {len(matches)} матчей {sport}")
            return matches
            
        except Exception as e:
            self.logger.error(f"FlashScore веб-скрапинг ошибка: {e}")
            return []
        finally:
            self.close_driver()
    
    def _extract_match_from_element(self, element, sport: str) -> Dict[str, Any]:
        """
        Извлечение данных матча из веб-элемента
        """
        try:
            match_data = {
                'source': 'flashscore',
                'sport': sport,
                'timestamp': datetime.now().isoformat()
            }
            
            # Извлекаем текст элемента для анализа
            full_text = self.safe_get_text(element)
            
            # Команды (различные селекторы)
            team_selectors = [
                ".participant__participantName",
                ".team-name",
                "[class*='participant']",
                "[class*='team']"
            ]
            
            teams = []
            for selector in team_selectors:
                team_elements = element.find_elements(By.CSS_SELECTOR, selector)
                for team_elem in team_elements:
                    team_text = self.safe_get_text(team_elem)
                    if team_text and len(team_text) > 1:
                        teams.append(team_text)
                if len(teams) >= 2:
                    break
            
            if len(teams) >= 2:
                match_data['team1'] = teams[0]
                match_data['team2'] = teams[1]
            else:
                # Парсим команды из текста
                team_pattern = r'(.+?)\s*-\s*(.+?)(?:\s+\d+:\d+|\s+$)'
                team_match = re.search(team_pattern, full_text)
                if team_match:
                    match_data['team1'] = team_match.group(1).strip()
                    match_data['team2'] = team_match.group(2).strip()
            
            # Счет
            score_selectors = [
                ".event__score",
                "[class*='score']",
                ".result"
            ]
            
            score = ""
            for selector in score_selectors:
                score_elem = element.find_elements(By.CSS_SELECTOR, selector)
                if score_elem:
                    score = self.safe_get_text(score_elem[0])
                    if re.match(r'\d+:\d+', score):
                        break
            
            if not score:
                score_match = re.search(r'(\d+:\d+)', full_text)
                if score_match:
                    score = score_match.group(1)
            
            match_data['score'] = score or "0:0"
            
            # Время
            time_selectors = [
                ".event__time",
                "[class*='time']",
                ".minute"
            ]
            
            match_time = ""
            for selector in time_selectors:
                time_elem = element.find_elements(By.CSS_SELECTOR, selector)
                if time_elem:
                    match_time = self.safe_get_text(time_elem[0])
                    if match_time:
                        break
            
            match_data['time'] = match_time or "LIVE"
            
            # URL матча
            link_elem = element.find_elements(By.TAG_NAME, "a")
            if link_elem:
                href = self.safe_get_attribute(link_elem[0], "href")
                if href:
                    match_data['url'] = href if href.startswith('http') else f"{self.base_url}{href}"
            
            return match_data if match_data.get('team1') and match_data.get('team2') else None
            
        except Exception as e:
            self.logger.warning(f"FlashScore извлечение элемента ошибка: {e}")
            return None
    
    def get_match_details(self, match_url: str) -> Dict[str, Any]:
        """
        Получение детальных данных матча
        """
        try:
            self.setup_driver()
            self.driver.get(match_url)
            time.sleep(3)
            
            details = {
                'url': match_url,
                'source': 'flashscore',
                'timestamp': datetime.now().isoformat()
            }
            
            # Детальная статистика
            stats_button = self.safe_find_element(By.CSS_SELECTOR, "[data-testid='tab-statistics'], .tabs__tab:contains('Statistics')")
            if stats_button:
                self.safe_click(stats_button)
                time.sleep(2)
                
                # Извлекаем статистику
                stat_elements = self.safe_find_elements(By.CSS_SELECTOR, ".stat__row, [class*='statistic']")
                statistics = {}
                
                for stat_elem in stat_elements:
                    stat_name = self.safe_get_text(self.safe_find_element(stat_elem, By.CSS_SELECTOR, ".stat__categoryName"))
                    stat_values = self.safe_find_elements(stat_elem, By.CSS_SELECTOR, ".stat__homeValue, .stat__awayValue")
                    
                    if stat_name and len(stat_values) >= 2:
                        statistics[stat_name] = {
                            'team1': self.safe_get_text(stat_values[0]),
                            'team2': self.safe_get_text(stat_values[1])
                        }
                
                details['statistics'] = statistics
            
            return details
            
        except Exception as e:
            self.logger.error(f"FlashScore детали матча ошибка: {e}")
            return {'url': match_url, 'error': str(e)}
        finally:
            self.close_driver()
    
    def filter_matches(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Фильтрация матчей FlashScore (базовая реализация)
        """
        filtered = []
        
        for match in matches:
            # Базовые проверки
            if not match.get('team1') or not match.get('team2'):
                continue
            
            # Проверяем что команды не одинаковые
            if match.get('team1', '').lower() == match.get('team2', '').lower():
                continue
            
            # Проверяем наличие счета
            score = match.get('score', '0:0')
            if score and score != '0:0':
                filtered.append(match)
        
        return filtered
    
    def collect_match_data(self, match_url: str) -> Dict[str, Any]:
        """
        Сбор детальных данных матча (делегируем к get_match_details)
        """
        return self.get_match_details(match_url)
    
    def verify_connection(self) -> bool:
        """
        Проверка подключения к FlashScore
        """
        try:
            response = self.session.get(f"{self.base_url}/football/", timeout=5)
            return response.status_code == 200
        except:
            return False