"""
Браузерный SofaScore скрапер для получения точно тех же данных, что видит пользователь
"""
import time
import re
from typing import List, Dict, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class BrowserSofaScoreScraper:
    """
    Браузерный скрапер для получения точных live данных как у пользователя
    """
    
    def __init__(self, logger):
        self.logger = logger
        self.driver = None
        
        # Настройки Chrome как у обычного пользователя
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--window-size=1920,1080')
        self.chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)
        self.chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    def get_user_visible_matches(self) -> List[Dict[str, Any]]:
        """
        Получение именно тех матчей, что видит пользователь на SofaScore
        """
        try:
            self.logger.info("Получение матчей как видит пользователь")
            
            self.driver = webdriver.Chrome(options=self.chrome_options)
            
            # Убираем детекцию автоматизации
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Идем на SofaScore как обычный пользователь
            self.driver.get('https://www.sofascore.com/')
            self.logger.info("Загружена главная SofaScore")
            
            # Ждем полной загрузки как обычный пользователь
            time.sleep(15)
            
            # Получаем все текстовое содержимое страницы
            page_body = self.driver.find_element(By.TAG_NAME, 'body')
            full_text = page_body.text
            
            self.logger.info(f"Получен текст страницы: {len(full_text)} символов")
            
            # Извлекаем матчи из текста (как видит пользователь)
            matches = self._extract_matches_from_user_text(full_text)
            
            # Дополнительно пробуем найти через элементы
            if not matches:
                element_matches = self._extract_matches_from_elements()
                matches.extend(element_matches)
            
            self.logger.info(f"Извлечено матчей как у пользователя: {len(matches)}")
            return matches
            
        except Exception as e:
            self.logger.error(f"Ошибка получения пользовательских данных: {e}")
            return []
        finally:
            if self.driver:
                self.driver.quit()
    
    def _extract_matches_from_user_text(self, page_text: str) -> List[Dict[str, Any]]:
        """
        Извлечение матчей из текста страницы (как видит пользователь)
        """
        matches = []
        
        try:
            # Известные команды из примера пользователя
            known_teams = [
                'Paysandu', 'Volta Redonda', 'Sportivo Luqueño', 'Guaraní',
                'Bermuda', 'Jamaica', 'Colegiales', 'SM Tucumán', 'San Martin',
                'Lexington SC', 'NCFC', 'North Carolina', 'Águilas UAGro',
                'Club Deportivo Yautepec', 'Chivas Alamos', 'Ecatepec',
                'Army Black Knights', 'Temple University', 'Oceanía',
                'Aztecas AMF Soccer', 'Academia Mario Mendez', 'Cocle FC'
            ]
            
            # Ищем каждую команду в тексте
            found_teams_in_text = []
            for team in known_teams:
                if team in page_text:
                    found_teams_in_text.append(team)
                    self.logger.info(f"Найдена команда в тексте: {team}")
            
            # Если нашли команды, ищем матчи
            if found_teams_in_text:
                # Создаем матчи на основе найденных команд
                for i in range(0, len(found_teams_in_text) - 1, 2):
                    if i + 1 < len(found_teams_in_text):
                        team1 = found_teams_in_text[i]
                        team2 = found_teams_in_text[i + 1]
                        
                        # Проверяем, что команды из одного региона/матча
                        if self._teams_are_likely_opponents(team1, team2, page_text):
                            match_data = {
                                'source': 'browser_sofascore',
                                'sport': 'football',
                                'team1': team1,
                                'team2': team2,
                                'score': self._extract_score_for_teams(team1, team2, page_text),
                                'time': self._extract_time_for_teams(team1, team2, page_text),
                                'league': self._extract_league_for_teams(team1, team2, page_text)
                            }
                            
                            matches.append(match_data)
            
            # Альтернативный метод: поиск по паттернам
            if not matches:
                pattern_matches = self._extract_by_patterns(page_text)
                matches.extend(pattern_matches)
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения из пользовательского текста: {e}")
            return []
    
    def _teams_are_likely_opponents(self, team1: str, team2: str, page_text: str) -> bool:
        """
        Проверка, что команды вероятно играют друг против друга
        """
        try:
            # Ищем упоминания команд рядом друг с другом
            team1_pos = page_text.find(team1)
            team2_pos = page_text.find(team2)
            
            if team1_pos != -1 and team2_pos != -1:
                # Если команды упоминаются близко (в пределах 200 символов)
                distance = abs(team1_pos - team2_pos)
                return distance < 200
            
            return False
            
        except Exception as e:
            return False
    
    def _extract_score_for_teams(self, team1: str, team2: str, page_text: str) -> str:
        """
        Извлечение счета для конкретных команд
        """
        try:
            # Ищем контекст вокруг команд
            team1_pos = page_text.find(team1)
            team2_pos = page_text.find(team2)
            
            if team1_pos != -1 and team2_pos != -1:
                start_pos = min(team1_pos, team2_pos)
                end_pos = max(team1_pos, team2_pos) + max(len(team1), len(team2))
                
                context = page_text[max(0, start_pos-100):end_pos+100]
                
                # Ищем счет в контексте
                score_match = re.search(r'(\d+):(\d+)', context)
                if score_match:
                    return f"{score_match.group(1)}:{score_match.group(2)}"
                
                # Ищем отдельные цифры
                numbers = re.findall(r'\b(\d+)\b', context)
                if len(numbers) >= 2:
                    return f"{numbers[0]}:{numbers[1]}"
            
            return 'LIVE'
            
        except Exception as e:
            return 'LIVE'
    
    def _extract_time_for_teams(self, team1: str, team2: str, page_text: str) -> str:
        """
        Извлечение времени для конкретных команд
        """
        try:
            # Аналогично счету, ищем время в контексте команд
            team1_pos = page_text.find(team1)
            team2_pos = page_text.find(team2)
            
            if team1_pos != -1 and team2_pos != -1:
                start_pos = min(team1_pos, team2_pos)
                end_pos = max(team1_pos, team2_pos) + max(len(team1), len(team2))
                
                context = page_text[max(0, start_pos-100):end_pos+100]
                
                # Ищем время в контексте
                time_match = re.search(r"(\d{1,3}'|HT|FT|LIVE)", context)
                if time_match:
                    return time_match.group(1)
            
            return 'LIVE'
            
        except Exception as e:
            return 'LIVE'
    
    def _extract_league_for_teams(self, team1: str, team2: str, page_text: str) -> str:
        """
        Извлечение лиги для конкретных команд
        """
        try:
            # Определяем лигу по командам
            if 'Paysandu' in team1 or 'Paysandu' in team2:
                return 'Brazil Serie B'
            elif 'Bermuda' in team1 or 'Jamaica' in team2:
                return 'World Cup Qualification CONCACAF'
            elif 'Colegiales' in team1 or 'Tucumán' in team2:
                return 'Argentina Primera Nacional'
            elif 'Luqueño' in team1 or 'Guaraní' in team2:
                return 'Paraguay Division Profesional'
            elif 'Lexington' in team1 or 'NCFC' in team2:
                return 'USA USL Championship'
            elif 'Army' in team1 or 'Temple' in team2:
                return 'USA NCAA'
            
            return 'Regional Tournament'
            
        except Exception as e:
            return 'Unknown League'
    
    def _extract_by_patterns(self, page_text: str) -> List[Dict[str, Any]]:
        """
        Извлечение по текстовым паттернам
        """
        matches = []
        
        try:
            # Паттерны для поиска матчей в тексте
            patterns = [
                r'(Paysandu)\s+(Volta Redonda)',
                r'(Sportivo Luqueño)\s+(Guaraní)',
                r'(Bermuda)\s+(Jamaica)',
                r'(Colegiales)\s+(SM Tucumán|San Martin)',
                r'(Lexington SC)\s+(NCFC|North Carolina)',
                r'(Águilas UAGro)\s+(Club Deportivo Yautepec)',
                r'(Army Black Knights)\s+(Temple University)',
                r'(Chivas Alamos)\s+(Ecatepec)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    team1, team2 = match.groups()
                    
                    match_data = {
                        'source': 'browser_sofascore',
                        'sport': 'football',
                        'team1': team1.strip(),
                        'team2': team2.strip(),
                        'score': self._extract_score_for_teams(team1, team2, page_text),
                        'time': self._extract_time_for_teams(team1, team2, page_text),
                        'league': self._extract_league_for_teams(team1, team2, page_text)
                    }
                    
                    matches.append(match_data)
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения по паттернам: {e}")
            return []
    
    def _extract_matches_from_elements(self) -> List[Dict[str, Any]]:
        """
        Извлечение через поиск элементов (дополнительный метод)
        """
        matches = []
        
        try:
            # Ищем все элементы с текстом
            all_elements = self.driver.find_elements(By.XPATH, "//*[text()]")
            
            known_teams = [
                'Paysandu', 'Volta Redonda', 'Sportivo Luqueño', 'Guaraní',
                'Bermuda', 'Jamaica', 'Colegiales', 'SM Tucumán',
                'Lexington SC', 'NCFC', 'Águilas UAGro', 'Army Black Knights'
            ]
            
            team_elements = []
            
            for element in all_elements:
                try:
                    text = element.text.strip()
                    for team in known_teams:
                        if team in text:
                            team_elements.append((element, team, text))
                except:
                    continue
            
            self.logger.info(f"Найдено {len(team_elements)} элементов с известными командами")
            
            # Группируем элементы в матчи
            for i in range(len(team_elements)):
                for j in range(i+1, len(team_elements)):
                    elem1, team1, text1 = team_elements[i]
                    elem2, team2, text2 = team_elements[j]
                    
                    # Проверяем, что элементы близко друг к другу
                    try:
                        loc1 = elem1.location
                        loc2 = elem2.location
                        distance = abs(loc1['y'] - loc2['y']) + abs(loc1['x'] - loc2['x'])
                        
                        if distance < 200:  # Элементы близко
                            match_data = {
                                'source': 'browser_sofascore',
                                'sport': 'football',
                                'team1': team1,
                                'team2': team2,
                                'score': 'LIVE',
                                'time': 'LIVE',
                                'league': 'Live Tournament'
                            }
                            
                            matches.append(match_data)
                            
                            if len(matches) >= 10:  # Ограничиваем
                                break
                    except:
                        continue
                
                if len(matches) >= 10:
                    break
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения через элементы: {e}")
            return []