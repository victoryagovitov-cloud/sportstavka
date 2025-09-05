"""
Продвинутый LiveScore парсер для автоматического извлечения актуальных данных
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

class AdvancedLiveScoreScraper:
    """
    Продвинутый автоматический парсер LiveScore
    """
    
    def __init__(self, logger):
        self.logger = logger
        self.driver = None
        
        # Настройки для обхода защиты LiveScore
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--window-size=1920,1080')
        
        # Обход антибот систем
        self.chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Реалистичные настройки браузера
        self.chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        self.chrome_options.add_argument('--accept-language=en-US,en;q=0.9')
        self.chrome_options.add_argument('--disable-extensions')
    
    def get_automatic_live_matches(self, sport: str = 'football') -> List[Dict[str, Any]]:
        """
        Автоматическое получение live матчей с LiveScore
        """
        try:
            self.logger.info(f"Автоматическое извлечение live {sport} с LiveScore")
            
            self.driver = webdriver.Chrome(options=self.chrome_options)
            
            # Маскируем автоматизацию
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Переходим на LiveScore
            if sport == 'football':
                url = 'https://www.livescore.com/en/football/live/'
            elif sport == 'tennis':
                url = 'https://www.livescore.com/en/tennis/live/'
            else:
                url = f'https://www.livescore.com/en/{sport}/live/'
            
            self.driver.get(url)
            self.logger.info(f"Загружена LiveScore {sport}")
            
            # Имитируем пользователя
            self._simulate_real_user()
            
            # Ждем загрузки данных
            time.sleep(12)
            
            # Извлекаем матчи
            matches = []
            
            # Метод 1: Поиск в таблицах
            table_matches = self._extract_from_tables()
            matches.extend(table_matches)
            
            # Метод 2: Поиск через JavaScript
            if not matches:
                js_matches = self._extract_via_livescore_js()
                matches.extend(js_matches)
            
            # Метод 3: Текстовый анализ
            if not matches:
                text_matches = self._extract_from_page_text()
                matches.extend(text_matches)
            
            validated_matches = self._validate_livescore_matches(matches, sport)
            
            self.logger.info(f"LiveScore автоматически: найдено {len(validated_matches)} {sport} матчей")
            return validated_matches
            
        except Exception as e:
            self.logger.error(f"Ошибка автоматического LiveScore: {e}")
            return []
        finally:
            if self.driver:
                self.driver.quit()
    
    def _simulate_real_user(self):
        """
        Имитация реального пользователя для обхода защиты
        """
        try:
            # Прокрутка как у пользователя
            self.driver.execute_script("window.scrollTo(0, 300)")
            time.sleep(2)
            
            # Движение мыши
            actions = ActionChains(self.driver)
            body = self.driver.find_element(By.TAG_NAME, 'body')
            actions.move_to_element(body).perform()
            time.sleep(1)
            
            # Клик в случайное место (имитация активности)
            self.driver.execute_script("document.body.click()")
            time.sleep(1)
            
            # Возврат наверх
            self.driver.execute_script("window.scrollTo(0, 0)")
            time.sleep(2)
            
        except Exception as e:
            self.logger.warning(f"Ошибка имитации пользователя: {e}")
    
    def _extract_from_tables(self) -> List[Dict[str, Any]]:
        """
        Извлечение из таблиц LiveScore
        """
        matches = []
        
        try:
            # LiveScore использует таблицы для отображения матчей
            table_selectors = [
                'table',
                'tbody',
                'tr',
                '.fixture-row',
                '.match-row',
                '[data-testid*="match"]',
                '[data-testid*="fixture"]'
            ]
            
            for selector in table_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    if elements:
                        self.logger.info(f"LiveScore таблицы: найдено {len(elements)} элементов с {selector}")
                        
                        for element in elements:
                            match_data = self._extract_from_table_element(element)
                            if match_data:
                                matches.append(match_data)
                        
                        if matches:
                            break
                            
                except Exception as e:
                    continue
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения из таблиц: {e}")
            return []
    
    def _extract_from_table_element(self, element) -> Dict[str, Any]:
        """
        Извлечение матча из элемента таблицы
        """
        try:
            text = element.text.strip()
            
            # Проверяем что элемент содержит данные матча
            if not text or len(text) < 10:
                return None
            
            # Ищем дочерние элементы с командами
            team_elements = element.find_elements(By.CSS_SELECTOR, 'td, .team, .participant, span, div')
            
            teams = []
            scores = []
            times = []
            
            for child in team_elements:
                child_text = child.text.strip()
                
                if child_text:
                    # Проверяем что это команда
                    if len(child_text) > 2 and len(child_text) < 50 and not child_text.isdigit():
                        teams.append(child_text)
                    
                    # Проверяем что это счет
                    if re.match(r'^\d+$', child_text):
                        scores.append(child_text)
                    
                    # Проверяем что это время
                    if re.match(r'^\d+\'$|^(HT|FT|LIVE)$', child_text):
                        times.append(child_text)
            
            # Создаем матч если есть минимум 2 команды
            if len(teams) >= 2:
                match_data = {
                    'source': 'advanced_livescore',
                    'sport': 'football',
                    'team1': teams[0],
                    'team2': teams[1],
                    'score': f"{scores[0]}:{scores[1]}" if len(scores) >= 2 else 'LIVE',
                    'time': times[0] if times else 'LIVE'
                }
                
                return match_data
            
            return None
            
        except Exception as e:
            return None
    
    def _extract_via_livescore_js(self) -> List[Dict[str, Any]]:
        """
        Извлечение через JavaScript API LiveScore
        """
        matches = []
        
        try:
            # JavaScript для поиска данных LiveScore
            js_commands = [
                # Поиск в глобальных переменных
                "return window.liveScoreData || window.matchData || window.fixtureData || null;",
                
                # Поиск в React props
                """
                var reactData = [];
                var allElements = document.querySelectorAll('*');
                for (var i = 0; i < allElements.length; i++) {
                    var elem = allElements[i];
                    if (elem._reactInternalFiber || elem._reactInternalInstance) {
                        var text = elem.textContent;
                        if (text && text.includes('vs') || text.includes(':')) {
                            reactData.push(text);
                        }
                    }
                }
                return reactData.slice(0, 20);
                """,
                
                # Поиск всех элементов с live данными
                """
                var liveElements = [];
                var textElements = document.querySelectorAll('*');
                for (var i = 0; i < textElements.length; i++) {
                    var text = textElements[i].textContent || '';
                    if ((text.includes('vs') || text.match(/\\d+:\\d+/)) && text.length > 5 && text.length < 100) {
                        liveElements.push(text);
                    }
                }
                return [...new Set(liveElements)].slice(0, 30);
                """
            ]
            
            for js_command in js_commands:
                try:
                    result = self.driver.execute_script(js_command)
                    
                    if result:
                        self.logger.info(f"JavaScript LiveScore: получено {len(result) if isinstance(result, list) else 1} элементов")
                        
                        if isinstance(result, list):
                            for item in result:
                                if isinstance(item, str):
                                    match_data = self._parse_livescore_text(item)
                                    if match_data:
                                        matches.append(match_data)
                        
                        if matches:
                            break
                            
                except Exception as e:
                    continue
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка JavaScript LiveScore: {e}")
            return []
    
    def _parse_livescore_text(self, text: str) -> Dict[str, Any]:
        """
        Парсинг текста LiveScore в данные матча
        """
        try:
            # Паттерны LiveScore
            patterns = [
                # Формат: Team1 Team2 Score1 Score2 Time
                r'([A-Z][a-zA-Z\s]{2,25})\s+([A-Z][a-zA-Z\s]{2,25})\s+(\d+)\s+(\d+)\s*(\d+\'|HT|FT)',
                
                # Формат: Team1 vs Team2
                r'([A-Z][a-zA-Z\s]{2,25})\s+vs\s+([A-Z][a-zA-Z\s]{2,25})',
                
                # Поиск известных команд
                r'(Bermuda|Jamaica|Paysandu|Volta Redonda|Colegiales|San Martin|Luqueno|Guarani)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    groups = match.groups()
                    
                    if len(groups) >= 2:
                        match_data = {
                            'source': 'advanced_livescore',
                            'sport': 'football',
                            'team1': groups[0].strip(),
                            'team2': groups[1].strip() if len(groups) > 1 else '',
                            'score': f"{groups[2]}:{groups[3]}" if len(groups) >= 4 else 'LIVE',
                            'time': groups[4] if len(groups) > 4 else 'LIVE'
                        }
                        
                        return match_data
            
            return None
            
        except Exception as e:
            return None
    
    def _extract_from_page_text(self) -> List[Dict[str, Any]]:
        """
        Извлечение из общего текста страницы
        """
        matches = []
        
        try:
            # Получаем весь текст страницы
            page_text = self.driver.find_element(By.TAG_NAME, 'body').text
            
            self.logger.info(f"LiveScore текст страницы: {len(page_text)} символов")
            
            # Разбиваем на строки и ищем матчи
            lines = page_text.split('\\n')
            
            for line in lines:
                line = line.strip()
                if len(line) > 10 and len(line) < 100:
                    match_data = self._parse_livescore_text(line)
                    if match_data:
                        matches.append(match_data)
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения из текста страницы: {e}")
            return []
    
    def _validate_livescore_matches(self, matches: List[Dict[str, Any]], sport: str) -> List[Dict[str, Any]]:
        """
        Валидация матчей LiveScore
        """
        valid_matches = []
        
        for match in matches:
            try:
                # Базовая валидация
                team1 = match.get('team1', '').strip()
                team2 = match.get('team2', '').strip()
                
                if team1 and team2 and len(team1) > 2 and len(team2) > 2:
                    if team1.lower() != team2.lower():
                        valid_matches.append(match)
                        
            except Exception as e:
                continue
        
        return valid_matches[:15]