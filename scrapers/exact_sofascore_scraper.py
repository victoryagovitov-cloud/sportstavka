"""
Точный SofaScore скрапер для извлечения актуальных live матчей
Создан на основе анализа реальной структуры сайта
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
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class ExactSofaScoreScraper:
    """
    Точный скрапер для SofaScore с фокусом на актуальные live матчи
    """
    
    def __init__(self, logger):
        self.logger = logger
        self.driver = None
        
        # Настройки Chrome для стабильной работы
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
        Получение точных актуальных live матчей
        """
        try:
            self.logger.info(f"Точное извлечение live {sport} матчей с SofaScore")
            
            self.driver = webdriver.Chrome(options=self.chrome_options)
            
            # Убираем детекцию автоматизации
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Переходим на главную SofaScore
            self.driver.get('https://www.sofascore.com/')
            self.logger.info("Загружена главная страница SofaScore")
            
            # Ждем полной загрузки с увеличенным таймаутом
            time.sleep(10)
            
            # Пробуем найти live матчи разными методами
            matches = []
            
            # Метод 1: Поиск на главной странице
            main_page_matches = self._extract_from_main_page()
            matches.extend(main_page_matches)
            
            # Метод 2: Переход на страницу live футбола
            if not matches or len(matches) < 5:
                live_page_matches = self._extract_from_live_page(sport)
                matches.extend(live_page_matches)
            
            # Метод 3: Поиск через меню навигации
            if not matches or len(matches) < 5:
                navigation_matches = self._extract_via_navigation(sport)
                matches.extend(navigation_matches)
            
            # Убираем дубликаты
            unique_matches = self._remove_duplicates(matches)
            
            self.logger.info(f"Точное извлечение: найдено {len(unique_matches)} актуальных матчей")
            return unique_matches
            
        except Exception as e:
            self.logger.error(f"Ошибка точного извлечения: {e}")
            return []
        finally:
            if self.driver:
                self.driver.quit()
    
    def _extract_from_main_page(self) -> List[Dict[str, Any]]:
        """
        Извлечение live матчей с главной страницы
        """
        matches = []
        
        try:
            self.logger.info("Поиск live матчей на главной странице")
            
            # Ждем загрузки live контента
            time.sleep(5)
            
            # Современные селекторы SofaScore 2024
            current_selectors = [
                # Основные контейнеры
                '[data-testid*="event"]',
                '[data-testid*="match"]',
                '[data-testid*="fixture"]',
                
                # Box компоненты (React)
                'div[class*="Box"]',
                'div[class*="Event"]',
                'div[class*="Match"]',
                
                # Live специфичные
                '[class*="live"]',
                '[data-sport="football"]',
                
                # Общие контейнеры
                'div[class*="event"]',
                'div[class*="match"]',
                'article',
                'section'
            ]
            
            for selector in current_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    if elements:
                        self.logger.info(f"Главная страница: найдено {len(elements)} элементов с {selector}")
                        
                        for element in elements[:50]:  # Анализируем больше элементов
                            match_data = self._extract_match_from_element(element, 'main_page')
                            if match_data and self._is_valid_match(match_data):
                                matches.append(match_data)
                        
                        # Если нашли матчи, продолжаем с этим селектором
                        if matches:
                            break
                            
                except Exception as e:
                    self.logger.warning(f"Ошибка с селектором {selector}: {e}")
                    continue
            
            return matches[:20]  # Ограничиваем количество
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения с главной страницы: {e}")
            return []
    
    def _extract_from_live_page(self, sport: str) -> List[Dict[str, Any]]:
        """
        Извлечение с dedicated live страницы
        """
        matches = []
        
        try:
            live_url = f'https://www.sofascore.com/{sport}/live'
            self.logger.info(f"Переход на {live_url}")
            
            self.driver.get(live_url)
            time.sleep(10)  # Ждем загрузки live данных
            
            # Специальные селекторы для live страницы
            live_selectors = [
                '[data-testid*="event"]',
                '[data-testid*="live"]',
                '.tournament-events',
                '.live-events',
                'div[class*="Event"]',
                'div[class*="Live"]'
            ]
            
            for selector in live_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    if elements:
                        self.logger.info(f"Live страница: найдено {len(elements)} элементов с {selector}")
                        
                        for element in elements:
                            match_data = self._extract_match_from_element(element, 'live_page')
                            if match_data and self._is_valid_match(match_data):
                                matches.append(match_data)
                        
                        if matches:
                            break
                            
                except Exception as e:
                    continue
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения с live страницы: {e}")
            return []
    
    def _extract_via_navigation(self, sport: str) -> List[Dict[str, Any]]:
        """
        Извлечение через навигационное меню
        """
        matches = []
        
        try:
            self.logger.info("Поиск через навигационное меню")
            
            # Ищем меню навигации
            nav_selectors = [
                'nav',
                '[role="navigation"]',
                '.navigation',
                '.menu',
                'header'
            ]
            
            for nav_selector in nav_selectors:
                try:
                    nav_element = self.driver.find_element(By.CSS_SELECTOR, nav_selector)
                    
                    # Ищем ссылку на live футбол
                    live_links = nav_element.find_elements(By.CSS_SELECTOR, 'a')
                    
                    for link in live_links:
                        href = link.get_attribute('href')
                        text = link.text.lower()
                        
                        if href and ('live' in href or 'football' in href) and ('live' in text or sport in text):
                            self.logger.info(f"Найдена live ссылка: {href}")
                            
                            self.driver.get(href)
                            time.sleep(8)
                            
                            # Извлекаем матчи с новой страницы
                            page_matches = self._extract_from_current_page()
                            matches.extend(page_matches)
                            
                            if matches:
                                return matches
                            
                except Exception as e:
                    continue
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка навигационного поиска: {e}")
            return []
    
    def _extract_from_current_page(self) -> List[Dict[str, Any]]:
        """
        Извлечение матчей с текущей страницы
        """
        matches = []
        
        try:
            # Получаем весь текст страницы
            page_text = self.driver.page_source
            
            # Ищем структурированные данные в скриптах
            script_elements = self.driver.find_elements(By.TAG_NAME, 'script')
            
            for script in script_elements:
                script_content = script.get_attribute('innerHTML')
                if script_content and ('event' in script_content or 'match' in script_content):
                    # Ищем JSON данные о матчах
                    json_matches = self._extract_matches_from_json(script_content)
                    matches.extend(json_matches)
            
            # Если JSON не дал результатов, парсим визуальные элементы
            if not matches:
                visual_matches = self._extract_visual_matches()
                matches.extend(visual_matches)
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения с текущей страницы: {e}")
            return []
    
    def _extract_matches_from_json(self, script_content: str) -> List[Dict[str, Any]]:
        """
        Извлечение матчей из JSON данных в скриптах
        """
        matches = []
        
        try:
            # Паттерны для поиска JSON с матчами
            json_patterns = [
                r'"events":\s*(\[.*?\])',
                r'"matches":\s*(\[.*?\])', 
                r'"fixtures":\s*(\[.*?\])',
                r'"liveEvents":\s*(\[.*?\])'
            ]
            
            for pattern in json_patterns:
                json_match = re.search(pattern, script_content, re.DOTALL)
                if json_match:
                    try:
                        events_data = json.loads(json_match.group(1))
                        
                        for event in events_data:
                            if isinstance(event, dict):
                                match_data = self._parse_json_event(event)
                                if match_data:
                                    matches.append(match_data)
                    except json.JSONDecodeError:
                        continue
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения JSON матчей: {e}")
            return []
    
    def _parse_json_event(self, event: Dict) -> Dict[str, Any]:
        """
        Парсинг JSON события в матч
        """
        try:
            match_data = {
                'source': 'sofascore_exact',
                'sport': 'football'
            }
            
            # Команды
            if 'homeTeam' in event and 'awayTeam' in event:
                home_team = event['homeTeam']
                away_team = event['awayTeam']
                
                match_data['team1'] = home_team.get('name', home_team.get('shortName', ''))
                match_data['team2'] = away_team.get('name', away_team.get('shortName', ''))
            
            # Счет
            home_score = event.get('homeScore', event.get('homeGoals', ''))
            away_score = event.get('awayScore', event.get('awayGoals', ''))
            
            if home_score != '' and away_score != '':
                match_data['score'] = f"{home_score}:{away_score}"
            else:
                match_data['score'] = 'LIVE'
            
            # Время
            if 'status' in event:
                status = event['status']
                if isinstance(status, dict):
                    match_data['time'] = status.get('description', status.get('type', 'LIVE'))
                else:
                    match_data['time'] = str(status)
            elif 'minute' in event:
                match_data['time'] = f"{event['minute']}'"
            else:
                match_data['time'] = 'LIVE'
            
            # Турнир
            if 'tournament' in event:
                tournament = event['tournament']
                if isinstance(tournament, dict):
                    match_data['league'] = tournament.get('name', tournament.get('uniqueTournament', {}).get('name', ''))
                else:
                    match_data['league'] = str(tournament)
            
            # URL матча
            if 'id' in event:
                match_data['url'] = f"/match/{event['id']}"
                match_data['match_id'] = str(event['id'])
            
            return match_data if match_data.get('team1') and match_data.get('team2') else None
            
        except Exception as e:
            self.logger.warning(f"Ошибка парсинга JSON события: {e}")
            return None
    
    def _extract_visual_matches(self) -> List[Dict[str, Any]]:
        """
        Извлечение матчей через визуальные элементы (fallback метод)
        """
        matches = []
        
        try:
            self.logger.info("Извлечение через визуальные элементы")
            
            # Расширенный список селекторов на основе анализа реального сайта
            visual_selectors = [
                # React компоненты
                'div[class*="Box"]',
                'div[data-testid]',
                
                # Контейнеры матчей
                '.match',
                '.event', 
                '.fixture',
                '.game',
                
                # Live специфичные
                '.live-match',
                '.live-event',
                '[data-live="true"]',
                
                # Общие контейнеры
                'article',
                'section',
                '.card',
                '.item'
            ]
            
            for selector in visual_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    if elements:
                        self.logger.info(f"Визуальный поиск: {len(elements)} элементов с {selector}")
                        
                        for element in elements:
                            # Проверяем, содержит ли элемент данные матча
                            if self._element_looks_like_match(element):
                                match_data = self._extract_match_from_element(element, 'visual')
                                if match_data and self._is_valid_match(match_data):
                                    matches.append(match_data)
                        
                        if len(matches) >= 10:
                            break
                            
                except Exception as e:
                    continue
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка визуального извлечения: {e}")
            return []
    
    def _element_looks_like_match(self, element) -> bool:
        """
        Проверка, выглядит ли элемент как матч
        """
        try:
            text = element.text.strip()
            
            # Базовые проверки
            if not text or len(text) < 10 or len(text) > 500:
                return False
            
            # Исключаем служебные элементы
            exclude_words = ['menu', 'login', 'search', 'advertisement', 'cookie', 
                            'privacy', 'terms', 'help', 'support', 'contact', 'about']
            
            if any(word in text.lower() for word in exclude_words):
                return False
            
            # Ищем признаки матча
            match_indicators = [
                r'\\b\\d+:\\d+\\b',  # Счет
                r'\\b\\d+\'\\b',     # Время типа 45'
                r'\\bvs\\b',         # vs между командами
                r'\\b(LIVE|FT|HT)\\b',  # Статусы
                r'\\b(\\w+)\\s+(\\w+)\\s+\\d+:\\d+',  # Команда Команда Счет
            ]
            
            match_score = 0
            for pattern in match_indicators:
                if re.search(pattern, text, re.IGNORECASE):
                    match_score += 1
            
            # Элемент похож на матч если есть минимум 1 индикатор
            return match_score >= 1
            
        except Exception as e:
            return False
    
    def _extract_match_from_element(self, element, source_method: str) -> Dict[str, Any]:
        """
        Извлечение данных матча из элемента
        """
        try:
            text = element.text.strip()
            
            match_data = {
                'source': 'sofascore_exact',
                'sport': 'football',
                'extraction_method': source_method,
                'raw_text': text[:200]  # Для отладки
            }
            
            # Улучшенные паттерны для извлечения команд
            team_patterns = [
                # Паттерн 1: Team1 vs Team2
                r'(.{2,40})\\s+vs\\s+(.{2,40})',
                
                # Паттерн 2: Team1 - Team2  
                r'(.{2,40})\\s+-\\s+(.{2,40})',
                
                # Паттерн 3: Team1 Score:Score Team2
                r'(.{2,40})\\s+(\\d+):(\\d+)\\s+(.{2,40})',
                
                # Паттерн 4: Team1 Team2 Score (новые строки)
                r'(.{2,30})\\n+(.{2,30})\\n+(\\d+:\\d+|LIVE|FT|HT)',
                
                # Паттерн 5: Многострочный формат
                r'(.{2,30})\\s*\\n\\s*(.{2,30})\\s*\\n\\s*(\\d+)\\s*\\n\\s*(\\d+)',
            ]
            
            teams_found = False
            for pattern in team_patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    groups = match.groups()
                    
                    if len(groups) >= 2:
                        team1 = groups[0].strip()
                        team2 = groups[1].strip()
                        
                        # Очищаем названия команд
                        team1 = self._clean_team_name(team1)
                        team2 = self._clean_team_name(team2)
                        
                        if team1 and team2 and team1 != team2:
                            match_data['team1'] = team1
                            match_data['team2'] = team2
                            
                            # Извлекаем счет если есть
                            if len(groups) >= 4 and groups[2] and groups[3]:
                                match_data['score'] = f"{groups[2]}:{groups[3]}"
                            elif len(groups) >= 3 and ':' in groups[2]:
                                match_data['score'] = groups[2]
                            else:
                                match_data['score'] = 'LIVE'
                            
                            teams_found = True
                            break
            
            if not teams_found:
                return None
            
            # Извлекаем время матча
            time_patterns = [
                r'(\\d{1,3}\')',  # 63'
                r'(HT|FT|LIVE)',   # Статусы
                r'(\\d{2}:\\d{2})', # 01:30 формат
                r'(\\d{1,2}\\s*мин)', # 45 мин
            ]
            
            for pattern in time_patterns:
                time_match = re.search(pattern, text, re.IGNORECASE)
                if time_match:
                    match_data['time'] = time_match.group(1)
                    break
            
            if 'time' not in match_data:
                match_data['time'] = 'LIVE'
            
            # Извлекаем турнир из контекста
            tournament_patterns = [
                r'(World Cup|Copa|Championship|League|Serie|Division|Liga|Premier)',
                r'(Brazil|Argentina|Paraguay|USA|Mexico|CONCACAF|UEFA|CONMEBOL)',
            ]
            
            tournaments_found = []
            for pattern in tournament_patterns:
                tournament_matches = re.findall(pattern, text, re.IGNORECASE)
                tournaments_found.extend(tournament_matches)
            
            if tournaments_found:
                match_data['league'] = ' '.join(tournaments_found[:3])
            else:
                match_data['league'] = 'Unknown League'
            
            return match_data
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения матча из элемента: {e}")
            return None
    
    def _clean_team_name(self, team_name: str) -> str:
        """
        Очистка названия команды
        """
        if not team_name:
            return ''
        
        # Убираем лишние символы и пробелы
        cleaned = re.sub(r'[^\\w\\s\\.-]', '', team_name)
        cleaned = re.sub(r'\\s+', ' ', cleaned).strip()
        
        # Убираем числовые префиксы/суффиксы
        cleaned = re.sub(r'^\\d+\\.?\\s*', '', cleaned)
        cleaned = re.sub(r'\\s*\\d+$', '', cleaned)
        
        return cleaned[:50]  # Ограничиваем длину
    
    def _is_valid_match(self, match_data: Dict[str, Any]) -> bool:
        """
        Проверка валидности извлеченного матча
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
            
            # Проверяем что это не служебная информация
            invalid_keywords = ['menu', 'search', 'login', 'advertisement', 'cookie', 
                               'privacy', 'terms', 'help', 'support', 'loading', 'error']
            
            for keyword in invalid_keywords:
                if keyword in team1.lower() or keyword in team2.lower():
                    return False
            
            return True
            
        except Exception as e:
            return False
    
    def _remove_duplicates(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Удаление дубликатов с улучшенным алгоритмом
        """
        seen_signatures = set()
        unique_matches = []
        
        for match in matches:
            # Создаем нормализованную сигнатуру
            team1 = match.get('team1', '').lower().strip()
            team2 = match.get('team2', '').lower().strip()
            
            # Нормализация названий команд
            team1 = re.sub(r'\\s+', '', team1)
            team2 = re.sub(r'\\s+', '', team2)
            
            # Создаем сигнатуру (порядок не важен)
            if team1 < team2:
                signature = f"{team1}_{team2}"
            else:
                signature = f"{team2}_{team1}"
            
            if signature not in seen_signatures and len(signature) > 6:
                seen_signatures.add(signature)
                unique_matches.append(match)
        
        return unique_matches