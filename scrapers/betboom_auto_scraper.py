"""
Автоматический парсер BetBoom для извлечения live данных с сайта
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

class BetBoomAutoScraper:
    """
    Автоматический парсер для извлечения live данных с BetBoom
    """
    
    def __init__(self, logger):
        self.logger = logger
        
        # Настройки Chrome для обхода защиты
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--window-size=1920,1080')
        self.chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)
        self.chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    def scrape_football_live(self) -> List[Dict[str, Any]]:
        """
        АВТОМАТИЧЕСКОЕ извлечение live футбольных данных с BetBoom
        """
        driver = None
        
        try:
            self.logger.info("Автоматическое извлечение BetBoom футбол")
            
            driver = webdriver.Chrome(options=self.chrome_options)
            
            # Убираем детекцию автоматизации
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Загружаем страницу
            url = 'https://betboom.ru/sport/football?type=live'
            driver.get(url)
            
            self.logger.info("Загружена страница BetBoom футбол")
            
            # Ждем загрузки контента
            time.sleep(15)
            
            # Получаем весь текст страницы
            page_text = driver.find_element(By.TAG_NAME, 'body').text
            
            self.logger.info(f"Получен текст страницы: {len(page_text)} символов")
            
            # Автоматически извлекаем матчи
            matches = self._auto_extract_matches_from_text(page_text)
            
            # Дополнительно пробуем через DOM элементы
            if not matches:
                dom_matches = self._auto_extract_from_dom(driver)
                matches.extend(dom_matches)
            
            self.logger.info(f"Автоматически извлечено: {len(matches)} футбольных матчей")
            return matches
            
        except Exception as e:
            self.logger.error(f"Ошибка автоматического извлечения BetBoom: {e}")
            return []
        finally:
            if driver:
                driver.quit()
    
    def _auto_extract_matches_from_text(self, page_text: str) -> List[Dict[str, Any]]:
        """
        Автоматическое извлечение матчей из текста страницы
        """
        matches = []
        
        try:
            # Разбиваем текст на блоки по турнирам
            tournament_blocks = self._split_by_tournaments(page_text)
            
            for tournament_name, block_text in tournament_blocks.items():
                block_matches = self._extract_matches_from_tournament_block(tournament_name, block_text)
                matches.extend(block_matches)
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка автоматического извлечения из текста: {e}")
            return []
    
    def _split_by_tournaments(self, page_text: str) -> Dict[str, str]:
        """
        Автоматическое разделение текста по турнирам
        """
        tournaments = {}
        
        try:
            lines = page_text.split('\\n')
            current_tournament = 'Unknown Tournament'
            current_block = []
            
            # Паттерны для распознавания турниров
            tournament_patterns = [
                r'ЧМ\..*',
                r'[А-Я][а-я]+\.\s[А-Я][а-я\s]+',  # Страна. Лига
                r'[A-Z][a-zA-Z]+\.\s[A-Z][a-zA-Z\s]+',  # Country. League
                r'Лига\s[А-я]+',
                r'Кубок\s[А-я]+',
                r'Чемпионат\s[А-я]+',
                r'Примера\s[А-я]+',
                r'Серия\s[AB]'
            ]
            
            for line in lines:
                line = line.strip()
                
                # Проверяем, является ли строка турниром
                is_tournament = False
                for pattern in tournament_patterns:
                    if re.match(pattern, line):
                        # Сохраняем предыдущий блок
                        if current_block:
                            tournaments[current_tournament] = '\\n'.join(current_block)
                        
                        # Начинаем новый блок
                        current_tournament = line
                        current_block = []
                        is_tournament = True
                        break
                
                if not is_tournament and line:
                    current_block.append(line)
            
            # Сохраняем последний блок
            if current_block:
                tournaments[current_tournament] = '\\n'.join(current_block)
            
            self.logger.info(f"Найдено турниров: {len(tournaments)}")
            return tournaments
            
        except Exception as e:
            self.logger.warning(f"Ошибка разделения по турнирам: {e}")
            return {'Unknown': page_text}
    
    def _extract_matches_from_tournament_block(self, tournament: str, block_text: str) -> List[Dict[str, Any]]:
        """
        Автоматическое извлечение матчей из блока турнира
        """
        matches = []
        
        try:
            lines = block_text.split('\\n')
            
            # Состояние парсера
            current_match = {}
            teams_found = False
            
            for line in lines:
                line = line.strip()
                
                # Ищем команды (две строки подряд обычно)
                if not teams_found and len(line) > 2 and len(line) < 30:
                    # Проверяем что это похоже на название команды
                    if (re.match(r'^[А-ЯA-Z][а-яa-zA-Z\s]+$', line) and 
                        not any(word in line.lower() for word in ['исход', 'тотал', 'фора', 'ещё', 'мин'])):
                        
                        if not current_match.get('team1'):
                            current_match['team1'] = line
                        elif not current_match.get('team2'):
                            current_match['team2'] = line
                            teams_found = True
                
                # Ищем счет (4 числа подряд)
                if teams_found and re.match(r'^\d+$', line):
                    if 'scores' not in current_match:
                        current_match['scores'] = []
                    current_match['scores'].append(int(line))
                
                # Ищем время матча
                time_patterns = [
                    r'\d+Т,\s\d+\sмин',  # 2Т, 90 мин
                    r'Перерыв',
                    r'Не начался',
                    r'\d+\sмин'
                ]
                
                for pattern in time_patterns:
                    if re.search(pattern, line):
                        current_match['time'] = line
                        break
                
                # Ищем коэффициенты
                if re.match(r'^\d+\.\d+$', line) or re.match(r'^\d+\.\d+$', line.replace(',', '.')):
                    if 'odds_values' not in current_match:
                        current_match['odds_values'] = []
                    current_match['odds_values'].append(line)
                
                # Если нашли достаточно данных для матча
                if (teams_found and 
                    current_match.get('team1') and 
                    current_match.get('team2') and
                    len(current_match.get('scores', [])) >= 4):
                    
                    # Создаем структурированный матч
                    match_data = self._create_structured_match(current_match, tournament)
                    if match_data:
                        matches.append(match_data)
                    
                    # Сбрасываем состояние для следующего матча
                    current_match = {}
                    teams_found = False
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения из блока турнира: {e}")
            return []
    
    def _create_structured_match(self, raw_match: Dict, tournament: str) -> Dict[str, Any]:
        """
        Создание структурированного матча из сырых данных
        """
        try:
            scores = raw_match.get('scores', [])
            
            if len(scores) >= 4:
                match_data = {
                    'source': 'betboom_auto',
                    'sport': 'football',
                    'team1': raw_match['team1'],
                    'team2': raw_match['team2'],
                    'score': f"{scores[0]}:{scores[1]}",
                    'detailed_score': {
                        'team1_goals': scores[0],
                        'team2_goals': scores[1],
                        'team1_shots': scores[2] if len(scores) > 2 else 0,
                        'team2_shots': scores[3] if len(scores) > 3 else 0
                    },
                    'time': raw_match.get('time', 'LIVE'),
                    'league': tournament,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Определяем важность по турниру
                if 'ЧМ' in tournament or 'World Cup' in tournament:
                    match_data['importance'] = 'HIGH'
                    match_data['tournament_type'] = 'World Cup Qualification'
                elif any(word in tournament for word in ['Серия', 'Примера', 'Лига']):
                    match_data['importance'] = 'MEDIUM'
                    match_data['tournament_type'] = 'Professional League'
                else:
                    match_data['importance'] = 'LOW'
                    match_data['tournament_type'] = 'Regional League'
                
                # Определяем регион
                if any(word in tournament for word in ['Бразилия', 'Аргентина', 'Колумбия']):
                    match_data['region'] = 'South America'
                elif any(word in tournament for word in ['США', 'Канада', 'Мексика']):
                    match_data['region'] = 'North America'
                elif 'CONCACAF' in tournament:
                    match_data['region'] = 'CONCACAF'
                else:
                    match_data['region'] = 'Unknown'
                
                # Добавляем коэффициенты если есть
                odds_values = raw_match.get('odds_values', [])
                if len(odds_values) >= 3:
                    match_data['odds'] = {
                        'П1': odds_values[0],
                        'X': odds_values[1],
                        'П2': odds_values[2]
                    }
                
                return match_data
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Ошибка создания структурированного матча: {e}")
            return None
    
    def _auto_extract_from_dom(self, driver) -> List[Dict[str, Any]]:
        """
        Автоматическое извлечение через DOM элементы
        """
        matches = []
        
        try:
            # Ищем элементы с live данными
            selectors = [
                '[data-testid*="match"]',
                '[data-testid*="event"]',
                '.match',
                '.event',
                '.fixture',
                'tr',
                'td',
                'div[class*="sport"]',
                'div[class*="match"]'
            ]
            
            for selector in selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    if elements:
                        self.logger.info(f"DOM: найдено {len(elements)} элементов с {selector}")
                        
                        for element in elements[:20]:
                            match_data = self._extract_match_from_element(element)
                            if match_data:
                                matches.append(match_data)
                        
                        if matches:
                            break
                            
                except Exception as e:
                    continue
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка DOM извлечения: {e}")
            return []
    
    def _extract_match_from_element(self, element) -> Dict[str, Any]:
        """
        Извлечение матча из DOM элемента
        """
        try:
            text = element.text.strip()
            
            # Проверяем что элемент содержит данные матча
            if not text or len(text) < 10:
                return None
            
            # Ищем паттерны команд в тексте элемента
            team_patterns = [
                r'([А-Я][а-я\s]+)\s+([А-Я][а-я\s]+)\s+(\d+)\s+(\d+)',
                r'([A-Z][a-zA-Z\s]+)\s+([A-Z][a-zA-Z\s]+)\s+(\d+)\s+(\d+)',
            ]
            
            for pattern in team_patterns:
                match = re.search(pattern, text)
                if match:
                    groups = match.groups()
                    
                    if len(groups) >= 4:
                        return {
                            'source': 'betboom_auto_dom',
                            'sport': 'football',
                            'team1': groups[0].strip(),
                            'team2': groups[1].strip(),
                            'score': f"{groups[2]}:{groups[3]}",
                            'raw_text': text[:100]
                        }
            
            return None
            
        except Exception as e:
            return None
    
    def scrape_tennis_live(self) -> List[Dict[str, Any]]:
        """
        АВТОМАТИЧЕСКОЕ извлечение live теннисных данных
        """
        driver = None
        
        try:
            self.logger.info("Автоматическое извлечение BetBoom теннис")
            
            driver = webdriver.Chrome(options=self.chrome_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Загружаем теннисную страницу
            url = 'https://betboom.ru/sport/tennis?type=live'
            driver.get(url)
            
            time.sleep(15)
            
            page_text = driver.find_element(By.TAG_NAME, 'body').text
            
            # Автоматически извлекаем теннисные матчи
            tennis_matches = self._auto_extract_tennis_from_text(page_text)
            
            self.logger.info(f"Автоматически извлечено: {len(tennis_matches)} теннисных матчей")
            return tennis_matches
            
        except Exception as e:
            self.logger.error(f"Ошибка автоматического извлечения тенниса: {e}")
            return []
        finally:
            if driver:
                driver.quit()
    
    def _auto_extract_tennis_from_text(self, page_text: str) -> List[Dict[str, Any]]:
        """
        Автоматическое извлечение теннисных матчей
        """
        matches = []
        
        try:
            lines = page_text.split('\\n')
            
            # Автоматический парсер состояний
            current_tournament = ''
            current_player1 = ''
            current_player2 = ''
            current_scores = []
            current_odds = []
            
            for line in lines:
                line = line.strip()
                
                # Определяем турнир
                if any(keyword in line for keyword in ['Open', 'ITF', 'UTR', 'ATP', 'WTA']):
                    current_tournament = line
                
                # Определяем игроков (имена с точками)
                if re.match(r'^[А-ЯA-Z][а-яa-z]+\s[А-ЯA-Z]\.?$', line):
                    if not current_player1:
                        current_player1 = line
                    elif not current_player2:
                        current_player2 = line
                
                # Определяем счет (одиночные цифры)
                if re.match(r'^\d+$', line) and len(current_scores) < 6:
                    current_scores.append(int(line))
                
                # Определяем статус сета
                if re.match(r'^\d+-й\sсет$', line):
                    set_status = line
                
                # Определяем коэффициенты
                if re.match(r'^\d+\.\d+$', line):
                    current_odds.append(line)
                
                # Если собрали достаточно данных для матча
                if (current_player1 and current_player2 and 
                    len(current_scores) >= 4 and current_tournament):
                    
                    # Создаем теннисный матч
                    tennis_match = {
                        'source': 'betboom_auto_tennis',
                        'sport': 'tennis',
                        'team1': current_player1,
                        'team2': current_player2,
                        'score': f"{current_scores[0]}:{current_scores[1]}, {current_scores[2]}:{current_scores[3]}",
                        'league': current_tournament,
                        'odds': {
                            'П1': current_odds[0] if len(current_odds) > 0 else '—',
                            'П2': current_odds[1] if len(current_odds) > 1 else '—'
                        },
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    matches.append(tennis_match)
                    
                    # Сбрасываем состояние
                    current_player1 = ''
                    current_player2 = ''
                    current_scores = []
                    current_odds = []
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка автоматического извлечения тенниса: {e}")
            return []