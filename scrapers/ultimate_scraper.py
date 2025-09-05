"""
Ультимативный скрапер для scores24.live с всеми возможными методами
"""
import requests
import re
import json
import time
from typing import List, Dict, Any
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from config import CHROMEDRIVER_PATH

class UltimateScraper:
    """
    Ультимативный скрапер с максимальным покрытием методов
    """
    
    def __init__(self, logger):
        self.logger = logger
    
    def get_live_matches(self, url: str, sport: str) -> List[Dict[str, Any]]:
        """
        Получение live матчей всеми возможными способами
        """
        self.logger.info(f"Ультимативный сбор {sport} матчей с {url}")
        
        matches = []
        
        # Метод 1: Быстрый requests + regex
        try:
            regex_matches = self._method_requests_regex(url, sport)
            if regex_matches:
                matches.extend(regex_matches)
                self.logger.info(f"Requests+Regex: найдено {len(regex_matches)} матчей")
        except Exception as e:
            self.logger.warning(f"Requests+Regex ошибка: {e}")
        
        # Метод 2: API endpoints
        if len(matches) < 5:  # Если мало матчей, пробуем API
            try:
                api_matches = self._method_api_endpoints(sport)
                if api_matches:
                    matches.extend(api_matches)
                    self.logger.info(f"API endpoints: найдено {len(api_matches)} матчей")
            except Exception as e:
                self.logger.warning(f"API endpoints ошибка: {e}")
        
        # Метод 3: Selenium с агрессивным поиском
        if len(matches) < 3:  # Если все еще мало
            try:
                selenium_matches = self._method_selenium_aggressive(url, sport)
                if selenium_matches:
                    matches.extend(selenium_matches)
                    self.logger.info(f"Selenium aggressive: найдено {len(selenium_matches)} матчей")
            except Exception as e:
                self.logger.warning(f"Selenium aggressive ошибка: {e}")
        
        # Убираем дубликаты и валидируем
        unique_matches = self._clean_and_validate(matches, sport)
        
        self.logger.info(f"Итого найдено {len(unique_matches)} валидных {sport} матчей")
        return unique_matches
    
    def _method_requests_regex(self, url: str, sport: str) -> List[Dict[str, Any]]:
        """
        Метод 1: Быстрый парсинг через requests + regex
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.7339.80 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return []
        
        html = response.text
        matches = []
        
        # Ищем паттерны матчей в HTML
        if sport == 'football':
            # Футбольные паттерны
            patterns = [
                r'([А-Яа-яA-Za-z\s]{3,25})\s*[-–]\s*([А-Яа-яA-Za-z\s]{3,25})\s*(\d+[:-]\d+)\s*(\d+\')?',
                r'([А-Яа-яA-Za-z\s]{3,25})\s*vs\s*([А-Яа-яA-Za-z\s]{3,25})\s*(\d+[:-]\d+)',
                r'([А-Яа-яA-Za-z\s]{3,25})\s*-\s*([А-Яа-яA-Za-z\s]{3,25})\s*(\d+[:-]\d+)'
            ]
        elif sport == 'tennis':
            patterns = [
                r'([А-Яа-яA-Za-z\.\s]{3,25})\s*[-–]\s*([А-Яа-яA-Za-z\.\s]{3,25})\s*(\d+[:-]\d+)',
                r'([А-Яа-яA-Za-z\.\s]{3,25})\s*vs\s*([А-Яа-яA-Za-z\.\s]{3,25})\s*(\d+[:-]\d+)'
            ]
        else:
            patterns = [
                r'([А-Яа-яA-Za-z\s]{3,25})\s*[-–]\s*([А-Яа-яA-Za-z\s]{3,25})\s*(\d+[:-]\d+)',
                r'([А-Яа-яA-Za-z\s]{3,25})\s*vs\s*([А-Яа-яA-Za-z\s]{3,25})\s*(\d+[:-]\d+)'
            ]
        
        for pattern in patterns:
            regex_matches = re.findall(pattern, html, re.IGNORECASE | re.MULTILINE)
            
            for match_tuple in regex_matches:
                if len(match_tuple) >= 3:
                    team1, team2, score = match_tuple[0].strip(), match_tuple[1].strip(), match_tuple[2].strip()
                    match_time = match_tuple[3] if len(match_tuple) > 3 and match_tuple[3] else "0'"
                    
                    # Валидация
                    if (self._is_valid_team_name(team1) and 
                        self._is_valid_team_name(team2) and
                        self._is_valid_score(score)):
                        
                        if sport == 'tennis':
                            match_data = {
                                'player1': team1,
                                'player2': team2,
                                'sets_score': score,
                                'current_set': '0:0',
                                'tournament': 'Live турнир',
                                'url': '',
                                'sport': sport,
                                'source': 'regex'
                            }
                        else:
                            match_data = {
                                'team1': team1,
                                'team2': team2,
                                'score': score,
                                'time': match_time,
                                'league': 'Live лига',
                                'url': '',
                                'sport': sport,
                                'source': 'regex'
                            }
                        
                        matches.append(match_data)
        
        return matches
    
    def _method_api_endpoints(self, sport: str) -> List[Dict[str, Any]]:
        """
        Метод 2: Тестирование API endpoints
        """
        # Общие API endpoints для спортивных сайтов
        base_urls = [
            'https://scores24.live',
            'https://api.scores24.live',
            'https://live-api.scores24.live'
        ]
        
        paths = [
            f'/api/v1/{sport}/live',
            f'/api/v2/{sport}/matches/live',
            f'/dapi/v3/{sport}/live',
            f'/v1/{sport}/live',
            f'/{sport}/live',
            f'/matches/{sport}/live',
            f'/live/{sport}',
            '/graphql'
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Accept': 'application/json, */*',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        for base in base_urls:
            for path in paths:
                try:
                    endpoint = f"{base}{path}"
                    response = requests.get(endpoint, headers=headers, timeout=5)
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            matches = self._parse_api_data(data, sport)
                            if matches:
                                self.logger.info(f"✅ API endpoint работает: {endpoint}")
                                return matches
                        except:
                            continue
                            
                except Exception:
                    continue
        
        return []
    
    def _method_selenium_aggressive(self, url: str, sport: str) -> List[Dict[str, Any]]:
        """
        Метод 3: Агрессивный Selenium поиск
        """
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-images')
        chrome_options.add_argument('--disable-javascript')  # Отключаем JS для ускорения
        
        service = Service(CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(20)
        
        try:
            driver.get(url)
            time.sleep(5)
            
            # Получаем весь текст страницы
            page_text = driver.execute_script("return document.body.innerText;") or driver.page_source
            
            # Разбиваем на строки и ищем матчи
            lines = page_text.split('\\n')
            matches = []
            
            for line in lines:
                line = line.strip()
                if self._looks_like_match_line(line, sport):
                    match_data = self._parse_line_to_match(line, sport)
                    if match_data:
                        matches.append(match_data)
            
            return matches
            
        finally:
            driver.quit()
    
    def _looks_like_match_line(self, line: str, sport: str) -> bool:
        """
        Проверяет, похожа ли строка на информацию о матче
        """
        if not line or len(line) < 10 or len(line) > 150:
            return False
        
        # Исключаем служебную информацию
        exclude = ['cookie', 'реклама', 'бонус', 'букмекер', 'ставка', 'коэффициент', 
                  'результаты', 'расписание', 'новости', 'статья']
        
        line_lower = line.lower()
        if any(word in line_lower for word in exclude):
            return False
        
        # Ищем признаки матча
        has_score = bool(re.search(r'\d+[:-]\d+', line))
        has_teams = bool(re.search(r'[А-Яа-яA-Za-z]{3,}\s*[-–vs]\s*[А-Яа-яA-Za-z]{3,}', line, re.IGNORECASE))
        has_time = bool(re.search(r'\d+[\'мин]', line))
        
        return has_score or has_teams or has_time
    
    def _parse_line_to_match(self, line: str, sport: str) -> Dict[str, Any]:
        """
        Парсинг строки в данные матча
        """
        try:
            # Ищем команды
            team_match = re.search(r'([А-Яа-яA-Za-z\.\s]{3,25})\s*[-–vs]\s*([А-Яа-яA-Za-z\.\s]{3,25})', line, re.IGNORECASE)
            if not team_match:
                return None
            
            team1, team2 = team_match.group(1).strip(), team_match.group(2).strip()
            
            if not self._is_valid_team_name(team1) or not self._is_valid_team_name(team2):
                return None
            
            # Ищем счет
            score_match = re.search(r'(\d+[:-]\d+)', line)
            score = score_match.group(1) if score_match else '0:0'
            
            # Ищем время
            time_match = re.search(r'(\d+)[\'мин]', line)
            match_time = f"{time_match.group(1)}'" if time_match else "0'"
            
            if sport == 'tennis':
                return {
                    'player1': team1,
                    'player2': team2,
                    'sets_score': score,
                    'current_set': '0:0',
                    'tournament': 'Live турнир',
                    'url': '',
                    'sport': sport,
                    'source': 'selenium_text'
                }
            else:
                return {
                    'team1': team1,
                    'team2': team2,
                    'score': score,
                    'time': match_time,
                    'league': 'Live лига',
                    'url': '',
                    'sport': sport,
                    'source': 'selenium_text'
                }
                
        except Exception:
            return None
    
    def _is_valid_team_name(self, name: str) -> bool:
        """
        Проверка валидности названия команды/игрока
        """
        if not name or len(name) < 3 or len(name) > 30:
            return False
        
        # Не должно быть только цифр
        if name.isdigit():
            return False
        
        # Должно содержать буквы
        if not re.search(r'[А-Яа-яA-Za-z]', name):
            return False
        
        # Исключаем служебные слова
        invalid_words = ['live', 'матч', 'игра', 'время', 'счет', 'результат']
        name_lower = name.lower()
        if any(word in name_lower for word in invalid_words):
            return False
        
        return True
    
    def _is_valid_score(self, score: str) -> bool:
        """
        Проверка валидности счета
        """
        if not score:
            return False
        
        # Должен быть формата X:X или X-X
        if not re.match(r'^\d+[:-]\d+$', score):
            return False
        
        # Парсим числа
        try:
            parts = re.split(r'[:-]', score)
            if len(parts) != 2:
                return False
            
            num1, num2 = int(parts[0]), int(parts[1])
            
            # Разумные ограничения для счета
            if sport == 'football':
                return 0 <= num1 <= 15 and 0 <= num2 <= 15
            elif sport in ['tennis', 'table_tennis']:
                return 0 <= num1 <= 7 and 0 <= num2 <= 7
            elif sport == 'handball':
                return 0 <= num1 <= 50 and 0 <= num2 <= 50
            else:
                return 0 <= num1 <= 100 and 0 <= num2 <= 100
                
        except ValueError:
            return False
    
    def _parse_api_data(self, data, sport: str) -> List[Dict[str, Any]]:
        """
        Рекурсивный парсинг API данных
        """
        matches = []
        
        def search_recursive(obj, depth=0):
            if depth > 6:
                return
            
            if isinstance(obj, dict):
                # Прямой поиск матчей
                for key in ['matches', 'fixtures', 'events', 'games', 'data', 'results']:
                    if key in obj and isinstance(obj[key], list):
                        for item in obj[key]:
                            if isinstance(item, dict):
                                match = self._parse_match_dict(item, sport)
                                if match:
                                    matches.append(match)
                
                # Рекурсивный поиск
                for value in obj.values():
                    if isinstance(value, (dict, list)):
                        search_recursive(value, depth + 1)
                        
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, dict):
                        match = self._parse_match_dict(item, sport)
                        if match:
                            matches.append(match)
                    elif isinstance(item, (dict, list)):
                        search_recursive(item, depth + 1)
        
        search_recursive(data)
        return matches
    
    def _parse_match_dict(self, match_dict: dict, sport: str) -> Dict[str, Any]:
        """
        Парсинг словаря матча из API
        """
        try:
            # Множественные варианты полей
            team_fields = ['home', 'homeTeam', 'home_team', 'team1', 'participant1', 'player1']
            away_fields = ['away', 'awayTeam', 'away_team', 'team2', 'participant2', 'player2']
            
            team1 = None
            team2 = None
            
            # Ищем названия команд/игроков
            for field in team_fields:
                if field in match_dict:
                    value = match_dict[field]
                    if isinstance(value, dict):
                        team1 = value.get('name') or value.get('title') or value.get('shortName')
                    else:
                        team1 = str(value)
                    if team1:
                        break
            
            for field in away_fields:
                if field in match_dict:
                    value = match_dict[field]
                    if isinstance(value, dict):
                        team2 = value.get('name') or value.get('title') or value.get('shortName')
                    else:
                        team2 = str(value)
                    if team2:
                        break
            
            if not team1 or not team2:
                return None
            
            # Счет
            score_fields = ['score', 'result', 'currentScore']
            score = '0:0'
            
            for field in score_fields:
                if field in match_dict:
                    score_val = match_dict[field]
                    if isinstance(score_val, dict):
                        home_score = score_val.get('home') or score_val.get('homeScore') or 0
                        away_score = score_val.get('away') or score_val.get('awayScore') or 0
                        score = f"{home_score}:{away_score}"
                    else:
                        score = str(score_val)
                    break
            
            # Время/статус
            time_fields = ['time', 'minute', 'status', 'period', 'clock']
            match_time = "0'"
            
            for field in time_fields:
                if field in match_dict:
                    time_val = str(match_dict[field])
                    if time_val and time_val != 'None':
                        match_time = time_val
                        break
            
            # Формируем результат
            if sport == 'tennis':
                return {
                    'player1': team1,
                    'player2': team2,
                    'sets_score': score,
                    'current_set': '0:0',
                    'tournament': str(match_dict.get('tournament', 'Live турнир')),
                    'url': str(match_dict.get('url', match_dict.get('id', ''))),
                    'sport': sport,
                    'source': 'api'
                }
            else:
                return {
                    'team1': team1,
                    'team2': team2,
                    'score': score,
                    'time': match_time,
                    'league': str(match_dict.get('league', match_dict.get('tournament', 'Live лига'))),
                    'url': str(match_dict.get('url', match_dict.get('id', ''))),
                    'sport': sport,
                    'source': 'api'
                }
                
        except Exception:
            return None
    
    def _clean_and_validate(self, matches: List[Dict[str, Any]], sport: str) -> List[Dict[str, Any]]:
        """
        Очистка и валидация найденных матчей
        """
        # Убираем дубликаты
        seen = set()
        unique_matches = []
        
        for match in matches:
            # Создаем ключ для дедупликации
            if sport == 'tennis':
                key = f"{match.get('player1', '')}-{match.get('player2', '')}-{match.get('sets_score', '')}"
            else:
                key = f"{match.get('team1', '')}-{match.get('team2', '')}-{match.get('score', '')}"
            
            key = key.lower().strip()
            
            if key not in seen and len(key) > 10:
                seen.add(key)
                unique_matches.append(match)
        
        # Дополнительная валидация
        validated_matches = []
        for match in unique_matches:
            if self._is_valid_match(match, sport):
                validated_matches.append(match)
        
        return validated_matches
    
    def _is_valid_match(self, match: Dict[str, Any], sport: str) -> bool:
        """
        Финальная валидация матча
        """
        if sport == 'tennis':
            player1 = match.get('player1', '').strip()
            player2 = match.get('player2', '').strip()
            return (self._is_valid_team_name(player1) and 
                   self._is_valid_team_name(player2) and
                   player1.lower() != player2.lower())
        else:
            team1 = match.get('team1', '').strip()
            team2 = match.get('team2', '').strip()
            return (self._is_valid_team_name(team1) and 
                   self._is_valid_team_name(team2) and
                   team1.lower() != team2.lower())