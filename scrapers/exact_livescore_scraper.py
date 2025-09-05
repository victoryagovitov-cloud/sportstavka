"""
Точный LiveScore скрапер для региональных турниров
Создан для извлечения именно тех матчей, что показывает сайт
"""
import time
import re
import json
from typing import List, Dict, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class ExactLiveScoreScraper:
    """
    Точный скрапер для LiveScore с фокусом на региональные турниры
    """
    
    def __init__(self, logger):
        self.logger = logger
        self.driver = None
        
        # Настройки Chrome
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--disable-gpu')
        self.chrome_options.add_argument('--window-size=1920,1080')
        self.chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)
        self.chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    def get_exact_live_matches(self, sport: str = 'football') -> List[Dict[str, Any]]:
        """
        Получение точных live матчей с LiveScore
        """
        try:
            self.logger.info(f"Точное извлечение live {sport} с LiveScore")
            
            self.driver = webdriver.Chrome(options=self.chrome_options)
            
            # Убираем детекцию автоматизации
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Переходим на live футбол
            live_url = 'https://www.livescore.com/en/football/live/'
            self.driver.get(live_url)
            self.logger.info("Загружена страница LiveScore live football")
            
            # Увеличенное ожидание для загрузки JavaScript
            time.sleep(12)
            
            # Пробуем разные методы извлечения
            matches = []
            
            # Метод 1: Поиск структурированных данных
            structured_matches = self._extract_structured_data()
            matches.extend(structured_matches)
            
            # Метод 2: Поиск через визуальные элементы
            if not matches:
                visual_matches = self._extract_visual_elements()
                matches.extend(visual_matches)
            
            # Метод 3: Парсинг через текстовое содержимое
            if not matches:
                text_matches = self._extract_from_page_text()
                matches.extend(text_matches)
            
            unique_matches = self._remove_duplicates(matches)
            
            self.logger.info(f"LiveScore точное: найдено {len(unique_matches)} матчей")
            return unique_matches
            
        except Exception as e:
            self.logger.error(f"Ошибка точного извлечения LiveScore: {e}")
            return []
        finally:
            if self.driver:
                self.driver.quit()
    
    def _extract_structured_data(self) -> List[Dict[str, Any]]:
        """
        Извлечение из структурированных данных (JSON в скриптах)
        """
        matches = []
        
        try:
            # Ищем JSON данные в скриптах
            script_elements = self.driver.find_elements(By.TAG_NAME, 'script')
            
            for script in script_elements:
                script_content = script.get_attribute('innerHTML')
                if not script_content:
                    continue
                
                # Ищем паттерны с данными матчей
                if any(keyword in script_content.lower() for keyword in ['match', 'event', 'fixture', 'live']):
                    json_matches = self._parse_livescore_json(script_content)
                    matches.extend(json_matches)
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения структурированных данных: {e}")
            return []
    
    def _parse_livescore_json(self, script_content: str) -> List[Dict[str, Any]]:
        """
        Парсинг JSON данных LiveScore
        """
        matches = []
        
        try:
            # Паттерны для LiveScore JSON структуры
            json_patterns = [
                r'"Stages":\\s*(\\[.*?\\])',
                r'"Events":\\s*(\\[.*?\\])',
                r'"Matches":\\s*(\\[.*?\\])',
                r'"fixtures":\\s*(\\[.*?\\])'
            ]
            
            for pattern in json_patterns:
                json_match = re.search(pattern, script_content, re.DOTALL)
                if json_match:
                    try:
                        data = json.loads(json_match.group(1))
                        
                        if isinstance(data, list):
                            for item in data:
                                if isinstance(item, dict):
                                    # LiveScore структура
                                    if 'Events' in item:
                                        for event in item['Events']:
                                            match_data = self._parse_livescore_event(event)
                                            if match_data:
                                                matches.append(match_data)
                                    else:
                                        match_data = self._parse_livescore_event(item)
                                        if match_data:
                                            matches.append(match_data)
                                            
                    except json.JSONDecodeError:
                        continue
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка парсинга LiveScore JSON: {e}")
            return []
    
    def _parse_livescore_event(self, event: Dict) -> Dict[str, Any]:
        """
        Парсинг события LiveScore в матч
        """
        try:
            match_data = {
                'source': 'livescore_exact',
                'sport': 'football'
            }
            
            # Команды в формате LiveScore
            if 'T1' in event and 'T2' in event:
                t1_data = event['T1']
                t2_data = event['T2']
                
                if isinstance(t1_data, list) and len(t1_data) > 0:
                    match_data['team1'] = t1_data[0].get('Nm', '')
                if isinstance(t2_data, list) and len(t2_data) > 0:
                    match_data['team2'] = t2_data[0].get('Nm', '')
            
            # Счет
            score1 = event.get('Tr1', '')
            score2 = event.get('Tr2', '')
            
            if score1 != '' and score2 != '':
                match_data['score'] = f"{score1}:{score2}"
            else:
                match_data['score'] = 'LIVE'
            
            # Время
            time_info = event.get('Eps', event.get('time', 'LIVE'))
            match_data['time'] = str(time_info)
            
            # ID матча
            if 'Eid' in event:
                match_data['match_id'] = str(event['Eid'])
                match_data['url'] = f"https://www.livescore.com/match/{event['Eid']}"
            
            return match_data if match_data.get('team1') and match_data.get('team2') else None
            
        except Exception as e:
            self.logger.warning(f"Ошибка парсинга LiveScore события: {e}")
            return None
    
    def _extract_visual_elements(self) -> List[Dict[str, Any]]:
        """
        Извлечение через визуальные элементы
        """
        matches = []
        
        try:
            self.logger.info("LiveScore: поиск через визуальные элементы")
            
            # LiveScore специфичные селекторы
            livescore_selectors = [
                # Основные контейнеры
                '[data-testid*="match"]',
                '[data-testid*="fixture"]',
                '[data-testid*="event"]',
                
                # Таблицы и строки
                'tr',
                '.match-row',
                '.fixture-row',
                '.event-row',
                
                # Карточки матчей
                '.match-card',
                '.fixture-card',
                '.game-card',
                
                # Общие контейнеры
                'div[class*="match"]',
                'div[class*="fixture"]',
                'div[class*="event"]'
            ]
            
            for selector in livescore_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    if elements:
                        self.logger.info(f"LiveScore визуальный: {len(elements)} элементов с {selector}")
                        
                        for element in elements[:30]:
                            match_data = self._extract_match_from_visual_element(element)
                            if match_data and self._is_valid_livescore_match(match_data):
                                matches.append(match_data)
                        
                        if matches:
                            break
                            
                except Exception as e:
                    continue
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка визуального извлечения LiveScore: {e}")
            return []
    
    def _extract_match_from_visual_element(self, element) -> Dict[str, Any]:
        """
        Извлечение матча из визуального элемента
        """
        try:
            text = element.text.strip()
            
            match_data = {
                'source': 'livescore_exact',
                'sport': 'football',
                'raw_text': text[:150]
            }
            
            # Специальные паттерны для LiveScore формата
            livescore_patterns = [
                # Формат: Team1 Team2 Score Time
                r'(.{3,30})\\s+(.{3,30})\\s+(\\d+)\\s+(\\d+)\\s*(\\d+\\'|LIVE|HT|FT)',
                
                # Формат: Team1 Team2 \n Score Time
                r'(.{3,30})\\s+(.{3,30})\\s*\\n\\s*(\\d+:\\d+)\\s*(\\d+\\'|LIVE|HT|FT)',
                
                # Формат с турниром: Tournament \n Team1 Team2 Score
                r'(.{5,50})\\n(.{3,30})\\s+(.{3,30})\\s+(\\d+)\\s+(\\d+)',
                
                # Простой формат: Team1 vs Team2
                r'(.{3,30})\\s+vs\\s+(.{3,30})',
            ]
            
            for pattern in livescore_patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    groups = match.groups()
                    
                    if len(groups) >= 2:
                        if len(groups) >= 5:  # Полный формат с турниром
                            tournament, team1, team2, score1, score2 = groups[:5]
                            match_data['league'] = tournament.strip()
                            match_data['team1'] = team1.strip()
                            match_data['team2'] = team2.strip()
                            match_data['score'] = f"{score1}:{score2}"
                        elif len(groups) >= 4:  # Формат с счетом
                            team1, team2, score, time_info = groups[:4]
                            match_data['team1'] = team1.strip()
                            match_data['team2'] = team2.strip()
                            match_data['score'] = score
                            match_data['time'] = time_info
                        else:  # Базовый формат
                            team1, team2 = groups[:2]
                            match_data['team1'] = team1.strip()
                            match_data['team2'] = team2.strip()
                            match_data['score'] = 'LIVE'
                            match_data['time'] = 'LIVE'
                        
                        break
            
            # Если паттерны не сработали, пробуем извлечь из структуры элемента
            if not match_data.get('team1'):
                child_matches = self._extract_from_child_elements(element)
                if child_matches:
                    match_data.update(child_matches)
            
            return match_data if match_data.get('team1') and match_data.get('team2') else None
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения визуального элемента: {e}")
            return None
    
    def _extract_from_child_elements(self, parent_element) -> Dict[str, Any]:
        """
        Извлечение данных из дочерних элементов
        """
        try:
            match_data = {}
            
            # Ищем команды в дочерних элементах
            team_selectors = [
                '.team-name',
                '.participant',
                '.home-team',
                '.away-team',
                '[class*="team"]',
                '[class*="participant"]'
            ]
            
            teams = []
            for selector in team_selectors:
                team_elements = parent_element.find_elements(By.CSS_SELECTOR, selector)
                for team_elem in team_elements:
                    team_text = team_elem.text.strip()
                    if team_text and len(team_text) > 2:
                        teams.append(team_text)
                
                if len(teams) >= 2:
                    break
            
            if len(teams) >= 2:
                match_data['team1'] = teams[0]
                match_data['team2'] = teams[1]
            
            # Ищем счет
            score_selectors = [
                '.score',
                '.result',
                '[class*="score"]',
                '[class*="result"]'
            ]
            
            for selector in score_selectors:
                score_elements = parent_element.find_elements(By.CSS_SELECTOR, selector)
                for score_elem in score_elements:
                    score_text = score_elem.text.strip()
                    if re.match(r'\\d+:\\d+', score_text):
                        match_data['score'] = score_text
                        break
                
                if match_data.get('score'):
                    break
            
            # Ищем время
            time_selectors = [
                '.time',
                '.minute', 
                '.status',
                '[class*="time"]',
                '[class*="minute"]'
            ]
            
            for selector in time_selectors:
                time_elements = parent_element.find_elements(By.CSS_SELECTOR, selector)
                for time_elem in time_elements:
                    time_text = time_elem.text.strip()
                    if time_text and (re.match(r'\\d+\'', time_text) or time_text in ['LIVE', 'HT', 'FT']):
                        match_data['time'] = time_text
                        break
                
                if match_data.get('time'):
                    break
            
            return match_data
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения из дочерних элементов: {e}")
            return {}
    
    def _extract_from_page_text(self) -> List[Dict[str, Any]]:
        """
        Извлечение матчей из текстового содержимого страницы
        """
        matches = []
        
        try:
            self.logger.info("LiveScore: извлечение из текста страницы")
            
            # Получаем весь текст страницы
            page_text = self.driver.find_element(By.TAG_NAME, 'body').text
            
            # Разбиваем на блоки по турнирам
            tournament_blocks = self._split_by_tournaments(page_text)
            
            for tournament_name, block_text in tournament_blocks.items():
                block_matches = self._extract_matches_from_text_block(block_text, tournament_name)
                matches.extend(block_matches)
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения из текста: {e}")
            return []
    
    def _split_by_tournaments(self, page_text: str) -> Dict[str, str]:
        """
        Разделение текста страницы по турнирам
        """
        tournaments = {}
        
        try:
            # Паттерны для названий турниров
            tournament_patterns = [
                r'(World Cup Qualification[^\\n]*)',
                r'(Primera Nacional[^\\n]*)',
                r'(Serie [AB][^\\n]*)',
                r'(Division [^\\n]*)',
                r'(USL Championship[^\\n]*)',
                r'(Liga [^\\n]*)',
                r'(Championship[^\\n]*)',
                r'([A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+)'  # Общий паттерн
            ]
            
            # Ищем блоки с турнирами
            lines = page_text.split('\\n')
            current_tournament = 'Unknown Tournament'
            current_block = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Проверяем, является ли строка названием турнира
                is_tournament = False
                for pattern in tournament_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        # Сохраняем предыдущий блок
                        if current_block:
                            tournaments[current_tournament] = '\\n'.join(current_block)
                        
                        # Начинаем новый блок
                        current_tournament = line
                        current_block = []
                        is_tournament = True
                        break
                
                if not is_tournament:
                    current_block.append(line)
            
            # Сохраняем последний блок
            if current_block:
                tournaments[current_tournament] = '\\n'.join(current_block)
            
            return tournaments
            
        except Exception as e:
            self.logger.warning(f"Ошибка разделения по турнирам: {e}")
            return {'Unknown': page_text}
    
    def _extract_matches_from_text_block(self, block_text: str, tournament: str) -> List[Dict[str, Any]]:
        """
        Извлечение матчей из текстового блока турнира
        """
        matches = []
        
        try:
            # Паттерны для извлечения матчей из текста
            match_patterns = [
                # Формат: Time Team1 Team2 Score1 Score2
                r'(\\d+\')\\s+(.{3,30})\\s+(.{3,30})\\s+(\\d+)\\s+(\\d+)',
                
                # Формат: Team1 Team2 Score Time
                r'(.{3,30})\\s+(.{3,30})\\s+(\\d+)\\s+(\\d+)\\s*(\\d+\'|HT|FT)',
                
                # Формат: Team1 Team2 \n Score
                r'(.{3,30})\\s+(.{3,30})\\s*\\n\\s*(\\d+)\\s+(\\d+)',
                
                # Простой формат: Team1 Team2
                r'(.{3,30})\\s+(.{3,30})(?=\\s|$)'
            ]
            
            lines = block_text.split('\\n')
            
            for pattern in match_patterns:
                for line in lines:
                    match = re.search(pattern, line.strip())
                    if match:
                        groups = match.groups()
                        
                        if len(groups) >= 2:
                            match_data = {
                                'source': 'livescore_exact',
                                'sport': 'football',
                                'league': tournament
                            }
                            
                            if len(groups) >= 5:  # Полный формат
                                time_info, team1, team2, score1, score2 = groups[:5]
                                match_data['time'] = time_info
                                match_data['team1'] = team1.strip()
                                match_data['team2'] = team2.strip()
                                match_data['score'] = f"{score1}:{score2}"
                            elif len(groups) >= 4:  # Формат с счетом
                                team1, team2, score1, score2 = groups[:4]
                                match_data['team1'] = team1.strip()
                                match_data['team2'] = team2.strip()
                                match_data['score'] = f"{score1}:{score2}"
                                match_data['time'] = groups[4] if len(groups) > 4 else 'LIVE'
                            else:  # Базовый формат
                                team1, team2 = groups[:2]
                                match_data['team1'] = team1.strip()
                                match_data['team2'] = team2.strip()
                                match_data['score'] = 'LIVE'
                                match_data['time'] = 'LIVE'
                            
                            if self._is_valid_livescore_match(match_data):
                                matches.append(match_data)
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения из текстового блока: {e}")
            return []
    
    def _is_valid_livescore_match(self, match_data: Dict[str, Any]) -> bool:
        """
        Проверка валидности LiveScore матча
        """
        try:
            team1 = match_data.get('team1', '').strip()
            team2 = match_data.get('team2', '').strip()
            
            # Базовые проверки
            if not team1 or not team2:
                return False
            
            if len(team1) < 3 or len(team2) < 3:
                return False
            
            if team1.lower() == team2.lower():
                return False
            
            # Исключаем служебные элементы
            invalid_keywords = ['favourites', 'advertisement', 'menu', 'login', 'search']
            
            for keyword in invalid_keywords:
                if keyword in team1.lower() or keyword in team2.lower():
                    return False
            
            return True
            
        except Exception as e:
            return False
    
    def _remove_duplicates(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Удаление дубликатов
        """
        seen = set()
        unique = []
        
        for match in matches:
            team1 = match.get('team1', '').lower().strip()
            team2 = match.get('team2', '').lower().strip()
            
            signature = f"{min(team1, team2)}_{max(team1, team2)}"
            
            if signature not in seen and len(signature) > 6:
                seen.add(signature)
                unique.append(match)
        
        return unique