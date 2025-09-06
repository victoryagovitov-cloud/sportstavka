"""
Умный BetBoom парсер с фокусом на реальное автоматическое извлечение
"""
import time
import re
from typing import List, Dict, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from datetime import datetime

class SmartBetBoomScraper:
    """
    Умный парсер с фокусом на реальное извлечение данных
    """
    
    def __init__(self, logger):
        self.logger = logger
        
        # Оптимальные настройки Chrome
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--window-size=1920,1080')
        self.chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    def smart_extract_football(self) -> List[Dict[str, Any]]:
        """
        Умное автоматическое извлечение футбольных данных
        """
        driver = None
        
        try:
            self.logger.info("Умное извлечение BetBoom футбол")
            
            driver = webdriver.Chrome(options=self.chrome_options)
            driver.get('https://betboom.ru/sport/football?type=live')
            
            # Даем больше времени на загрузку
            time.sleep(20)
            
            # Получаем исходный код страницы
            page_source = driver.page_source
            
            # Получаем видимый текст
            page_text = driver.find_element(By.TAG_NAME, 'body').text
            
            self.logger.info(f"Получено: HTML {len(page_source)} символов, текст {len(page_text)} символов")
            
            # Комбинированный анализ HTML + текста
            matches = self._smart_parse_combined_data(page_source, page_text)
            
            self.logger.info(f"Умно извлечено: {len(matches)} матчей")
            return matches
            
        except Exception as e:
            self.logger.error(f"Ошибка умного извлечения: {e}")
            return []
        finally:
            if driver:
                driver.quit()
    
    def _smart_parse_combined_data(self, html_source: str, visible_text: str) -> List[Dict[str, Any]]:
        """
        Умный парсинг комбинированных данных
        """
        matches = []
        
        try:
            # Метод 1: Поиск в HTML исходнике
            html_matches = self._extract_from_html_source(html_source)
            matches.extend(html_matches)
            
            # Метод 2: Анализ видимого текста
            if not matches:
                text_matches = self._extract_from_visible_text(visible_text)
                matches.extend(text_matches)
            
            # Метод 3: Поиск известных паттернов
            if not matches:
                pattern_matches = self._extract_known_patterns(visible_text)
                matches.extend(pattern_matches)
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка умного парсинга: {e}")
            return []
    
    def _extract_from_html_source(self, html_source: str) -> List[Dict[str, Any]]:
        """
        Извлечение из HTML исходника
        """
        matches = []
        
        try:
            # Ищем JSON данные в HTML
            json_patterns = [
                r'\"events\":\s*(\[.*?\])',
                r'\"matches\":\s*(\[.*?\])',
                r'\"fixtures\":\s*(\[.*?\])',
                r'window\.__INITIAL_STATE__\s*=\s*({.*?});'
            ]
            
            for pattern in json_patterns:
                json_matches = re.findall(pattern, html_source, re.DOTALL)
                
                for json_str in json_matches:
                    try:
                        import json
                        data = json.loads(json_str)
                        
                        # Извлекаем матчи из JSON
                        json_extracted = self._parse_json_for_matches(data)
                        matches.extend(json_extracted)
                        
                        if matches:
                            self.logger.info(f"Извлечено из JSON: {len(matches)} матчей")
                            break
                            
                    except json.JSONDecodeError:
                        continue
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения из HTML: {e}")
            return []
    
    def _extract_from_visible_text(self, visible_text: str) -> List[Dict[str, Any]]:
        """
        Извлечение из видимого текста (как видит пользователь)
        """
        matches = []
        
        try:
            # Логируем что видим в тексте
            if 'Бермудские' in visible_text:
                self.logger.info("Найдены Бермудские О-ва в тексте")
            if 'Ямайка' in visible_text:
                self.logger.info("Найдена Ямайка в тексте")
            if 'Пайсанду' in visible_text:
                self.logger.info("Найден Пайсанду в тексте")
            
            # Разбиваем на строки для структурного анализа
            lines = visible_text.split('\\n')
            
            # Умный анализ структуры
            current_context = {
                'tournament': '',
                'teams': [],
                'scores': [],
                'time': '',
                'odds': []
            }
            
            for i, line in enumerate(lines):
                line = line.strip()
                
                # Распознаем турниры
                if self._is_tournament_name(line):
                    # Сохраняем предыдущий матч если есть
                    if len(current_context['teams']) >= 2:
                        match = self._create_match_from_context(current_context)
                        if match:
                            matches.append(match)
                    
                    # Начинаем новый контекст
                    current_context = {'tournament': line, 'teams': [], 'scores': [], 'time': '', 'odds': []}
                
                # Распознаем команды
                elif self._looks_like_team(line):
                    current_context['teams'].append(line)
                
                # Распознаем счета
                elif re.match(r'^\d+$', line) and len(current_context['scores']) < 6:
                    current_context['scores'].append(int(line))
                
                # Распознаем время
                elif self._looks_like_match_time(line):
                    current_context['time'] = line
                
                # Распознаем коэффициенты
                elif re.match(r'^\d+\.\d+$', line) and len(current_context['odds']) < 3:
                    current_context['odds'].append(line)
            
            # Обрабатываем последний матч
            if len(current_context['teams']) >= 2:
                match = self._create_match_from_context(current_context)
                if match:
                    matches.append(match)
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения из видимого текста: {e}")
            return []
    
    def _is_tournament_name(self, line: str) -> bool:
        """
        Определение названия турнира
        """
        tournament_keywords = [
            'ЧМ.', 'CONCACAF', 'Серия B', 'Примера', 'USL', 'TDP',
            'Лига', 'Кубок', 'Чемпионат', 'Division'
        ]
        
        return any(keyword in line for keyword in tournament_keywords)
    
    def _looks_like_team(self, line: str) -> bool:
        """
        Проверка похоже ли на название команды
        """
        if not line or len(line) < 3 or len(line) > 35:
            return False
        
        # Исключаем служебные строки
        exclude_words = ['исход', 'тотал', 'фора', 'ещё', 'п1', 'п2', 'мин', 'сет']
        if any(word in line.lower() for word in exclude_words):
            return False
        
        # Должно начинаться с заглавной буквы
        return re.match(r'^[А-ЯA-Z]', line) is not None
    
    def _looks_like_match_time(self, line: str) -> bool:
        """
        Проверка похоже ли на время матча
        """
        time_patterns = [
            r'\d+Т,\s\d+\sмин',
            r'Перерыв',
            r'Не начался',
            r'Начало через'
        ]
        
        return any(re.search(pattern, line) for pattern in time_patterns)
    
    def _create_match_from_context(self, context: Dict) -> Dict[str, Any]:
        """
        Создание матча из накопленного контекста
        """
        try:
            teams = context.get('teams', [])
            scores = context.get('scores', [])
            
            if len(teams) >= 2 and len(scores) >= 2:
                match_data = {
                    'source': 'smart_betboom',
                    'sport': 'football',
                    'team1': teams[0],
                    'team2': teams[1],
                    'score': f"{scores[0]}:{scores[1]}",
                    'time': context.get('time', 'LIVE'),
                    'league': context.get('tournament', 'Unknown Tournament'),
                    'timestamp': datetime.now().isoformat()
                }
                
                # Детальный счет если есть больше данных
                if len(scores) >= 4:
                    match_data['detailed_score'] = {
                        'team1_goals': scores[0],
                        'team2_goals': scores[1],
                        'team1_shots': scores[2],
                        'team2_shots': scores[3]
                    }
                
                # Коэффициенты если есть
                odds = context.get('odds', [])
                if len(odds) >= 3:
                    match_data['odds'] = {
                        'П1': odds[0],
                        'X': odds[1],
                        'П2': odds[2]
                    }
                
                return match_data
            
            return None
            
        except Exception as e:
            return None
    
    def _parse_json_for_matches(self, data) -> List[Dict[str, Any]]:
        """
        Парсинг JSON данных для поиска матчей
        """
        matches = []
        
        try:
            # Рекурсивный поиск в JSON структуре
            if isinstance(data, dict):
                for key, value in data.items():
                    if key.lower() in ['events', 'matches', 'fixtures']:
                        if isinstance(value, list):
                            for item in value:
                                if isinstance(item, dict):
                                    match_data = self._parse_json_match_item(item)
                                    if match_data:
                                        matches.append(match_data)
                    elif isinstance(value, (dict, list)):
                        nested_matches = self._parse_json_for_matches(value)
                        matches.extend(nested_matches)
            
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        match_data = self._parse_json_match_item(item)
                        if match_data:
                            matches.append(match_data)
            
            return matches
            
        except Exception as e:
            return []
    
    def _parse_json_match_item(self, item: Dict) -> Dict[str, Any]:
        """
        Парсинг JSON элемента матча
        """
        try:
            # Поиск команд в JSON
            team1 = ''
            team2 = ''
            
            # Различные ключи для команд
            team_keys = [
                ('home', 'away'), ('homeTeam', 'awayTeam'), 
                ('team1', 'team2'), ('participant1', 'participant2')
            ]
            
            for key1, key2 in team_keys:
                if key1 in item and key2 in item:
                    team1_data = item[key1]
                    team2_data = item[key2]
                    
                    if isinstance(team1_data, dict):
                        team1 = team1_data.get('name', team1_data.get('title', ''))
                    else:
                        team1 = str(team1_data)
                    
                    if isinstance(team2_data, dict):
                        team2 = team2_data.get('name', team2_data.get('title', ''))
                    else:
                        team2 = str(team2_data)
                    
                    break
            
            if team1 and team2:
                match_data = {
                    'source': 'smart_betboom_json',
                    'sport': 'football',
                    'team1': team1,
                    'team2': team2,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Поиск счета
                score_keys = ['score', 'homeScore', 'awayScore', 'goals']
                for key in score_keys:
                    if key in item:
                        match_data['score'] = str(item[key])
                        break
                
                return match_data
            
            return None
            
        except Exception as e:
            return None