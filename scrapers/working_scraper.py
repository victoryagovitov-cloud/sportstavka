"""
Рабочий скрапер для scores24.live на основе анализа структуры
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time
import re
import json
from typing import List, Dict, Any
from config import CHROMEDRIVER_PATH

class WorkingScraper:
    """
    Рабочий скрапер для scores24.live
    """
    
    def __init__(self, logger):
        self.logger = logger
    
    def get_live_matches(self, url: str, sport: str) -> List[Dict[str, Any]]:
        """
        Получение live матчей с правильным парсингом
        """
        self.logger.info(f"Сбор live {sport} матчей с {url}")
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        
        service = Service(CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        try:
            driver.get(url)
            time.sleep(12)  # Ждем загрузки
            
            matches = []
            
            # Метод 1: Поиск через все элементы с текстом
            all_elements = driver.find_elements(By.XPATH, '//*[text()]')
            
            potential_matches = []
            
            for elem in all_elements:
                try:
                    text = elem.text.strip()
                    
                    # Проверяем, похож ли элемент на матч
                    if self._is_match_element(text):
                        # Извлекаем данные матча
                        match_data = self._extract_match_data(text, elem, sport)
                        if match_data:
                            potential_matches.append(match_data)
                
                except Exception:
                    continue
            
            # Убираем дубликаты
            unique_matches = self._remove_duplicates(potential_matches)
            
            self.logger.info(f"Найдено {len(unique_matches)} уникальных {sport} матчей")
            return unique_matches
            
        except Exception as e:
            self.logger.error(f"Ошибка сбора {sport} матчей: {e}")
            return []
        finally:
            driver.quit()
    
    def _is_match_element(self, text: str) -> bool:
        """
        Проверяет, содержит ли элемент информацию о матче
        """
        if not text or len(text) < 10 or len(text) > 300:
            return False
        
        # Исключаем служебную информацию
        exclude_keywords = [
            'cookie', 'реклама', 'бонус', 'регистрация', 'войти',
            'букмекер', 'ставка', 'коэффициент', 'прогноз', 'статья',
            'футбол', 'теннис', 'результаты', 'расписание', 'live'
        ]
        
        text_lower = text.lower()
        for keyword in exclude_keywords:
            if keyword in text_lower:
                return False
        
        # Ищем признаки матча
        has_score = bool(re.search(r'\\d+[:-]\\d+', text))
        has_time = bool(re.search(r'\\d+[\'мин]', text))
        has_teams = bool(re.search(r'\\b\\w{3,}\\s*[-vs]\\s*\\w{3,}\\b', text, re.IGNORECASE))
        has_live_indicator = 'live' in text_lower or '\'' in text
        
        # Нужно минимум 2 признака
        indicators = sum([has_score, has_time, has_teams, has_live_indicator])
        return indicators >= 2
    
    def _extract_match_data(self, text: str, element, sport: str) -> Dict[str, Any]:
        """
        Извлекает данные матча из текста элемента
        """
        try:
            # Ищем команды/игроков
            team_patterns = [
                r'(.{3,30})\\s*-\\s*(.{3,30})',
                r'(.{3,30})\\s*vs\\s*(.{3,30})',
                r'(.{3,30})\\s*–\\s*(.{3,30})'
            ]
            
            teams = None
            for pattern in team_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    team1 = match.group(1).strip()
                    team2 = match.group(2).strip()
                    
                    # Проверяем, что это реальные названия команд
                    if (len(team1) >= 3 and len(team2) >= 3 and 
                        team1 != team2 and 
                        not any(char.isdigit() for char in team1[:3]) and
                        not any(char.isdigit() for char in team2[:3])):
                        teams = (team1, team2)
                        break
            
            if not teams:
                return None
            
            # Ищем счет
            score_match = re.search(r'(\\d+[:-]\\d+)', text)
            score = score_match.group(1) if score_match else '0:0'
            
            # Ищем время
            time_match = re.search(r'(\\d+)[\'мин]', text)
            match_time = f"{time_match.group(1)}'" if time_match else '0\''
            
            # Ищем URL матча
            url = ''
            try:
                if element.tag_name == 'a':
                    url = element.get_attribute('href') or ''
                else:
                    link = element.find_element(By.TAG_NAME, 'a')
                    url = link.get_attribute('href') if link else ''
            except:
                pass
            
            match_data = {
                'team1' if sport != 'tennis' else 'player1': teams[0],
                'team2' if sport != 'tennis' else 'player2': teams[1],
                'score': score,
                'time': match_time,
                'league': 'Live матч',
                'url': url,
                'sport': sport,
                'source': 'working_scraper'
            }
            
            # Для тенниса добавляем специфичные поля
            if sport == 'tennis':
                if ':' in score:
                    match_data['sets_score'] = score
                    match_data['current_set'] = '0:0'  # Заглушка
                
            return match_data
            
        except Exception as e:
            return None
    
    def _remove_duplicates(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Удаляет дубликаты матчей
        """
        seen = set()
        unique_matches = []
        
        for match in matches:
            # Создаем уникальный ключ
            key_parts = [
                match.get('team1', match.get('player1', '')),
                match.get('team2', match.get('player2', '')),
                match.get('score', '')
            ]
            key = '|'.join(key_parts).lower()
            
            if key not in seen and all(part for part in key_parts):
                seen.add(key)
                unique_matches.append(match)
        
        return unique_matches