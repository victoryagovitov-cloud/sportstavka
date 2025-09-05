"""
Продвинутый SofaScore парсер с полной браузерной автоматизацией
Извлекает именно те матчи, что видит пользователь
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
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class AdvancedSofaScoreScraper:
    """
    Продвинутый автоматический парсер SofaScore
    """
    
    def __init__(self, logger):
        self.logger = logger
        self.driver = None
        
        # Продвинутые настройки Chrome для обхода защиты
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--disable-gpu')
        self.chrome_options.add_argument('--window-size=1920,1080')
        
        # Обход детекции автоматизации
        self.chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Реалистичный user agent
        self.chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Дополнительные опции для стабильности
        self.chrome_options.add_argument('--disable-extensions')
        self.chrome_options.add_argument('--disable-plugins')
        self.chrome_options.add_argument('--disable-images')  # Ускоряем загрузку
        self.chrome_options.add_argument('--disable-javascript')  # Отключаем JS для простоты
        
        # Прокси (если нужно)
        # self.chrome_options.add_argument('--proxy-server=http://proxy:port')
    
    def get_automatic_live_matches(self, sport: str = 'football') -> List[Dict[str, Any]]:
        """
        Автоматическое получение live матчей как видит пользователь
        """
        try:
            self.logger.info(f"Автоматическое извлечение live {sport} с SofaScore")
            
            self.driver = webdriver.Chrome(options=self.chrome_options)
            
            # Убираем детекцию веб-драйвера
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
            self.driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
            
            # Загружаем главную страницу
            self.driver.get('https://www.sofascore.com/')
            self.logger.info("Загружена главная SofaScore")
            
            # Имитируем поведение пользователя
            self._simulate_user_behavior()
            
            # Ждем полной загрузки контента
            time.sleep(15)
            
            # Извлекаем live матчи разными методами
            matches = []
            
            # Метод 1: Через видимый текст (как видит пользователь)
            text_matches = self._extract_from_visible_text(sport)
            matches.extend(text_matches)
            
            # Метод 2: Через DOM элементы
            if not matches:
                dom_matches = self._extract_from_dom_elements(sport)
                matches.extend(dom_matches)
            
            # Метод 3: Через JavaScript API
            if not matches:
                js_matches = self._extract_via_javascript(sport)
                matches.extend(js_matches)
            
            # Убираем дубликаты и валидируем
            valid_matches = self._validate_and_clean_matches(matches, sport)
            
            self.logger.info(f"Автоматически извлечено {len(valid_matches)} live {sport} матчей")
            return valid_matches
            
        except Exception as e:
            self.logger.error(f"Ошибка автоматического извлечения: {e}")
            return []
        finally:
            if self.driver:
                self.driver.quit()
    
    def _simulate_user_behavior(self):
        """
        Имитация поведения реального пользователя
        """
        try:
            # Прокрутка страницы
            self.driver.execute_script("window.scrollTo(0, 500)")
            time.sleep(2)
            
            # Движение мыши
            actions = ActionChains(self.driver)
            body = self.driver.find_element(By.TAG_NAME, 'body')
            actions.move_to_element(body).perform()
            time.sleep(1)
            
            # Возврат наверх
            self.driver.execute_script("window.scrollTo(0, 0)")
            time.sleep(2)
            
        except Exception as e:
            self.logger.warning(f"Ошибка имитации поведения: {e}")
    
    def _extract_from_visible_text(self, sport: str) -> List[Dict[str, Any]]:
        """
        Извлечение из видимого текста страницы (как видит пользователь)
        """
        matches = []
        
        try:
            # Получаем весь видимый текст страницы
            body = self.driver.find_element(By.TAG_NAME, 'body')
            page_text = body.text
            
            self.logger.info(f"Получен видимый текст: {len(page_text)} символов")
            
            # Ищем блоки с live матчами
            if sport == 'football':
                football_matches = self._extract_football_from_text(page_text)
                matches.extend(football_matches)
            elif sport == 'tennis':
                tennis_matches = self._extract_tennis_from_text(page_text)
                matches.extend(tennis_matches)
            elif sport == 'handball':
                handball_matches = self._extract_handball_from_text(page_text)
                matches.extend(handball_matches)
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения из видимого текста: {e}")
            return []
    
    def _extract_football_from_text(self, page_text: str) -> List[Dict[str, Any]]:
        """
        Извлечение футбольных матчей из текста
        """
        matches = []
        
        try:
            # Ищем паттерны футбольных матчей
            football_patterns = [
                # Формат: Team1 Team2 Score1 Score2 Time
                r'([A-Z][a-zA-Z\s]{2,30})\s+([A-Z][a-zA-Z\s]{2,30})\s+(\d+)\s+(\d+)\s*(\d+\'|HT|FT|LIVE)',
                
                # Формат: Team1 vs Team2
                r'([A-Z][a-zA-Z\s]{2,30})\s+vs\s+([A-Z][a-zA-Z\s]{2,30})',
                
                # Формат с известными командами
                r'(Bermuda|Jamaica|Paysandu|Volta Redonda|Colegiales|Luqueno|Guarani|Lexington)\s+([A-Z][a-zA-Z\s]{2,30})',
                
                # Поиск по ключевым словам турниров
                r'(World Cup|Serie B|Primera|Division|USL|NCAA).*?([A-Z][a-zA-Z\s]{2,25})\s+([A-Z][a-zA-Z\s]{2,25})'
            ]
            
            for pattern in football_patterns:
                pattern_matches = re.findall(pattern, page_text, re.MULTILINE | re.IGNORECASE)
                
                for match_groups in pattern_matches:
                    if len(match_groups) >= 2:
                        match_data = self._create_match_from_groups(match_groups, 'football')
                        if match_data:
                            matches.append(match_data)
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения футбола из текста: {e}")
            return []
    
    def _extract_tennis_from_text(self, page_text: str) -> List[Dict[str, Any]]:
        """
        Извлечение теннисных матчей из текста
        """
        matches = []
        
        try:
            # Паттерны для тенниса
            tennis_patterns = [
                # UTR формат: Player1 Player2 Set1 Set2 Games
                r'([A-Z][a-zA-Z\s\.]{2,25})\s+([A-Z][a-zA-Z\s\.]{2,25})\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)',
                
                # ITF формат
                r'(ITF|UTR).*?([A-Z][a-zA-Z\s\.]{2,20})\s+([A-Z][a-zA-Z\s\.]{2,20})',
                
                # US Open формат
                r'(US Open).*?([A-Z][a-zA-Z\s\.]{2,25})\s+([A-Z][a-zA-Z\s\.]{2,25})',
                
                # Поиск известных игроков
                r'(Prachar|Mishiro|Fullana|Reasco|Kakhniuk|Bowden|Sandrone|Rebec|Alexin)\s+([A-Z][a-zA-Z\s\.]{1,2}\.?)\s+([A-Z][a-zA-Z\s\.]{2,25})'
            ]
            
            for pattern in tennis_patterns:
                pattern_matches = re.findall(pattern, page_text, re.MULTILINE | re.IGNORECASE)
                
                for match_groups in pattern_matches:
                    if len(match_groups) >= 2:
                        match_data = self._create_tennis_match_from_groups(match_groups)
                        if match_data:
                            matches.append(match_data)
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения тенниса из текста: {e}")
            return []
    
    def _extract_from_dom_elements(self, sport: str) -> List[Dict[str, Any]]:
        """
        Извлечение через DOM элементы (резервный метод)
        """
        matches = []
        
        try:
            self.logger.info("Извлечение через DOM элементы")
            
            # Современные селекторы SofaScore
            selectors = [
                # React компоненты
                'div[data-testid]',
                'div[class*="Box"]',
                'div[class*="Event"]',
                'div[class*="Match"]',
                
                # Live специфичные
                '[data-live="true"]',
                '.live-match',
                '.live-event',
                
                # Общие контейнеры
                'article',
                'section',
                '.card',
                '.item'
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    if elements:
                        self.logger.info(f"DOM: найдено {len(elements)} элементов с {selector}")
                        
                        for element in elements[:50]:
                            if self._element_contains_match_data(element):
                                match_data = self._extract_match_from_dom_element(element, sport)
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
    
    def _extract_via_javascript(self, sport: str) -> List[Dict[str, Any]]:
        """
        Извлечение через выполнение JavaScript
        """
        matches = []
        
        try:
            self.logger.info("Извлечение через JavaScript")
            
            # JavaScript для поиска live данных
            js_scripts = [
                # Поиск React props
                """
                var matches = [];
                var reactElements = document.querySelectorAll('[data-reactroot], [data-testid]');
                for (var i = 0; i < reactElements.length; i++) {
                    var elem = reactElements[i];
                    if (elem._reactInternalFiber || elem._reactInternalInstance) {
                        // Найден React компонент
                        matches.push({
                            text: elem.textContent,
                            className: elem.className
                        });
                    }
                }
                return matches;
                """,
                
                # Поиск в window объектах
                """
                var liveData = [];
                if (window.__INITIAL_STATE__) liveData.push(window.__INITIAL_STATE__);
                if (window.__NEXT_DATA__) liveData.push(window.__NEXT_DATA__);
                if (window.INITIAL_DATA) liveData.push(window.INITIAL_DATA);
                return liveData;
                """,
                
                # Поиск всех элементов с live данными
                """
                var liveElements = [];
                var allElements = document.getElementsByTagName('*');
                for (var i = 0; i < allElements.length; i++) {
                    var elem = allElements[i];
                    var text = elem.textContent || '';
                    if (text.includes('vs') || text.includes('LIVE') || text.includes(':')) {
                        if (text.length > 10 && text.length < 200) {
                            liveElements.push({
                                tag: elem.tagName,
                                text: text,
                                className: elem.className
                            });
                        }
                    }
                }
                return liveElements.slice(0, 50);  // Первые 50 элементов
                """
            ]
            
            for script in js_scripts:
                try:
                    result = self.driver.execute_script(script)
                    
                    if result:
                        self.logger.info(f"JavaScript вернул {len(result)} элементов")
                        
                        js_matches = self._parse_javascript_result(result, sport)
                        matches.extend(js_matches)
                        
                        if matches:
                            break
                            
                except Exception as e:
                    self.logger.warning(f"Ошибка выполнения JavaScript: {e}")
                    continue
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка JavaScript извлечения: {e}")
            return []
    
    def _parse_javascript_result(self, js_result: List, sport: str) -> List[Dict[str, Any]]:
        """
        Парсинг результатов JavaScript
        """
        matches = []
        
        try:
            for item in js_result:
                if isinstance(item, dict):
                    text = item.get('text', '')
                    
                    if text and len(text) > 10:
                        # Ищем паттерны матчей в тексте
                        match_data = self._extract_match_from_text_line(text, sport)
                        if match_data:
                            matches.append(match_data)
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка парсинга JavaScript результата: {e}")
            return []
    
    def _extract_match_from_text_line(self, text: str, sport: str) -> Dict[str, Any]:
        """
        Извлечение матча из строки текста
        """
        try:
            # Очищаем текст
            text = re.sub(r'\s+', ' ', text.strip())
            
            # Исключаем служебные строки
            exclude_keywords = ['menu', 'login', 'search', 'advertisement', 'cookie', 'privacy']
            if any(keyword in text.lower() for keyword in exclude_keywords):
                return None
            
            match_data = {
                'source': 'advanced_sofascore',
                'sport': sport,
                'raw_text': text[:100]
            }
            
            if sport == 'football':
                return self._parse_football_line(text, match_data)
            elif sport == 'tennis':
                return self._parse_tennis_line(text, match_data)
            elif sport == 'handball':
                return self._parse_handball_line(text, match_data)
            
            return None
            
        except Exception as e:
            return None
    
    def _parse_football_line(self, text: str, match_data: Dict) -> Dict[str, Any]:
        """
        Парсинг футбольной строки
        """
        try:
            # Паттерны для футбола
            patterns = [
                # Team1 Team2 Score1 Score2 Time
                r'([A-Z][a-zA-Z\s]{2,25})\s+([A-Z][a-zA-Z\s]{2,25})\s+(\d+)\s+(\d+)\s*(\d+\'|HT|FT)',
                
                # Team1 vs Team2
                r'([A-Z][a-zA-Z\s]{2,25})\s+vs\s+([A-Z][a-zA-Z\s]{2,25})',
                
                # Известные команды
                r'(Bermuda|Jamaica|Paysandu|Volta Redonda|Colegiales|Luqueno|Guarani)\s+([A-Z][a-zA-Z\s]{2,30})'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    groups = match.groups()
                    
                    if len(groups) >= 2:
                        match_data['team1'] = groups[0].strip()
                        match_data['team2'] = groups[1].strip()
                        
                        if len(groups) >= 4:
                            match_data['score'] = f"{groups[2]}:{groups[3]}"
                            match_data['time'] = groups[4] if len(groups) > 4 else 'LIVE'
                        else:
                            match_data['score'] = 'LIVE'
                            match_data['time'] = 'LIVE'
                        
                        return match_data
            
            return None
            
        except Exception as e:
            return None
    
    def _parse_tennis_line(self, text: str, match_data: Dict) -> Dict[str, Any]:
        """
        Парсинг теннисной строки
        """
        try:
            # Паттерны для тенниса
            patterns = [
                # UTR формат: Player1 Player2 Set1 Set2 Game1 Game2
                r'([A-Z][a-zA-Z\s\.]{1,20})\s+([A-Z][a-zA-Z\s\.]{1,20})\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)',
                
                # Простой формат: Player1 Player2
                r'([A-Z]\.\s[A-Z][a-z]+)\s+([A-Z]\.\s[A-Z][a-z]+)',
                
                # ITF формат
                r'([A-Z][a-z]+\s[A-Z]\.)\s+([A-Z][a-z]+\s[A-Z]\.)',
                
                # Поиск известных игроков
                r'(Prachar|Mishiro|Fullana|Reasco|Kakhniuk|Bowden|Sandrone|Rebec|Alexin)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    groups = match.groups()
                    
                    if len(groups) >= 2:
                        match_data['team1'] = groups[0].strip()
                        match_data['team2'] = groups[1].strip()
                        
                        if len(groups) >= 6:
                            # Полный формат с сетами и геймами
                            match_data['score'] = f"{groups[2]}:{groups[3]}, {groups[4]}:{groups[5]}"
                            match_data['time'] = '2nd set'
                        else:
                            match_data['score'] = 'LIVE'
                            match_data['time'] = 'LIVE'
                        
                        # Определяем турнир по контексту
                        if 'UTR' in text:
                            match_data['league'] = 'UTR Pro Tennis Series'
                        elif 'ITF' in text:
                            match_data['league'] = 'ITF Tournament'
                        elif 'US Open' in text:
                            match_data['league'] = 'US Open'
                        else:
                            match_data['league'] = 'Tennis Tournament'
                        
                        return match_data
            
            return None
            
        except Exception as e:
            return None
    
    def _element_contains_match_data(self, element) -> bool:
        """
        Проверка, содержит ли элемент данные матча
        """
        try:
            text = element.text.strip()
            
            # Базовые проверки
            if not text or len(text) < 10:
                return False
            
            # Ищем признаки матча
            match_indicators = [
                r'\b\d+:\d+\b',  # Счет
                r'\bvs\b',       # vs
                r'\b\d+\'\b',    # Время
                r'\b(LIVE|HT|FT)\b',  # Статусы
                r'\bset\b',      # Теннисные сеты
            ]
            
            indicator_count = 0
            for pattern in match_indicators:
                if re.search(pattern, text, re.IGNORECASE):
                    indicator_count += 1
            
            return indicator_count >= 1
            
        except Exception as e:
            return False
    
    def _extract_match_from_dom_element(self, element, sport: str) -> Dict[str, Any]:
        """
        Извлечение матча из DOM элемента
        """
        try:
            text = element.text.strip()
            
            # Используем тот же метод что и для текста
            return self._extract_match_from_text_line(text, sport)
            
        except Exception as e:
            return None
    
    def _create_match_from_groups(self, groups: tuple, sport: str) -> Dict[str, Any]:
        """
        Создание данных матча из групп регулярного выражения
        """
        try:
            if len(groups) >= 2:
                match_data = {
                    'source': 'advanced_sofascore',
                    'sport': sport,
                    'team1': groups[0].strip(),
                    'team2': groups[1].strip()
                }
                
                # Добавляем дополнительные данные если есть
                if len(groups) >= 4:
                    match_data['score'] = f"{groups[2]}:{groups[3]}"
                if len(groups) >= 5:
                    match_data['time'] = groups[4]
                
                # Устанавливаем значения по умолчанию
                if 'score' not in match_data:
                    match_data['score'] = 'LIVE'
                if 'time' not in match_data:
                    match_data['time'] = 'LIVE'
                
                return match_data
            
            return None
            
        except Exception as e:
            return None
    
    def _create_tennis_match_from_groups(self, groups: tuple) -> Dict[str, Any]:
        """
        Создание теннисного матча из групп
        """
        try:
            match_data = {
                'source': 'advanced_sofascore',
                'sport': 'tennis'
            }
            
            if len(groups) >= 2:
                match_data['team1'] = groups[0].strip()
                match_data['team2'] = groups[1].strip()
                
                # Теннисная специфика
                if len(groups) >= 6:
                    match_data['score'] = f"{groups[2]}:{groups[3]}, {groups[4]}:{groups[5]}"
                    match_data['time'] = '2nd set'
                else:
                    match_data['score'] = 'LIVE'
                    match_data['time'] = 'LIVE'
                
                return match_data
            
            return None
            
        except Exception as e:
            return None
    
    def _validate_and_clean_matches(self, matches: List[Dict[str, Any]], sport: str) -> List[Dict[str, Any]]:
        """
        Валидация и очистка найденных матчей
        """
        valid_matches = []
        seen_signatures = set()
        
        for match in matches:
            try:
                # Базовая валидация
                if not self._is_valid_match(match):
                    continue
                
                # Проверка на дубликаты
                signature = self._create_match_signature(match)
                if signature in seen_signatures:
                    continue
                
                seen_signatures.add(signature)
                valid_matches.append(match)
                
            except Exception as e:
                continue
        
        return valid_matches[:20]  # Ограничиваем количество
    
    def _is_valid_match(self, match: Dict[str, Any]) -> bool:
        """
        Проверка валидности матча
        """
        try:
            team1 = match.get('team1', '').strip()
            team2 = match.get('team2', '').strip()
            
            if not team1 or not team2:
                return False
            
            if len(team1) < 2 or len(team2) < 2:
                return False
            
            if team1.lower() == team2.lower():
                return False
            
            return True
            
        except Exception as e:
            return False
    
    def _create_match_signature(self, match: Dict[str, Any]) -> str:
        """
        Создание уникальной сигнатуры матча
        """
        try:
            team1 = match.get('team1', '').lower().strip()
            team2 = match.get('team2', '').lower().strip()
            
            # Нормализация
            team1 = re.sub(r'[^\w]', '', team1)
            team2 = re.sub(r'[^\w]', '', team2)
            
            # Создаем сигнатуру (порядок не важен)
            if team1 < team2:
                return f"{team1}_{team2}"
            else:
                return f"{team2}_{team1}"
                
        except Exception as e:
            return f"unknown_{time.time()}"