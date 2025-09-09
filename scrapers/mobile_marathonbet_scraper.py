"""
Парсер мобильной версии MarathonBet с использованием Selenium
Получает реальные названия команд и текущие счета live матчей
"""

import logging
import re
import time
from typing import List, Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class MobileMarathonBetScraper:
    """
    РЕШЕНИЕ ПРОБЛЕМЫ СОПОСТАВЛЕНИЯ КОМАНД!
    
    Парсер мобильной версии MarathonBet который получает:
    - Точные названия команд
    - Реальные текущие счета
    - Информацию о матчах из одного источника
    
    Преимущества:
    - Нет проблем сопоставления (один источник)
    - Реальные счета вместо LIVE
    - Точные названия команд
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        
        # URLs мобильной версии для разных видов спорта
        self.mobile_urls = {
            'football': 'https://mobile.marathonbet.ru/su/sport/live/26418',
            'tennis': 'https://mobile.marathonbet.ru/su/sport/live/22723', 
            'table_tennis': 'https://mobile.marathonbet.ru/su/sport/live/414329',
            'handball': 'https://mobile.marathonbet.ru/su/sport/live/26422'
        }
        
        self.driver = None
        
    def _setup_driver(self):
        """Настройка Selenium Chrome драйвера для мобильной версии"""
        
        if self.driver:
            return
            
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=375,812')  # iPhone размер
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1')
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.logger.info("✅ Selenium Chrome драйвер запущен для мобильной версии")
        except Exception as e:
            self.logger.error(f"❌ Ошибка запуска Selenium: {e}")
            raise
    
    def get_live_matches_with_real_scores(self, sport: str = 'football') -> List[Dict[str, Any]]:
        """
        ГЛАВНЫЙ МЕТОД: Получает live матчи с реальными счетами
        
        Args:
            sport: Вид спорта ('football', 'tennis', 'table_tennis', 'handball')
            
        Returns:
            List[Dict]: Матчи с точными названиями команд и реальными счетами
        """
        
        if sport not in self.mobile_urls:
            self.logger.error(f"❌ Неподдерживаемый вид спорта: {sport}")
            return []
            
        url = self.mobile_urls[sport]
        self.logger.info(f"🔍 Получаем {sport} матчи из мобильной версии: {url}")
        
        try:
            self._setup_driver()
            
            # Загружаем страницу
            self.driver.get(url)
            self.logger.info("📱 Мобильная страница загружена")
            
            # Ждем загрузки JavaScript контента
            time.sleep(5)
            
            # Получаем размер загруженного контента
            page_source_size = len(self.driver.page_source)
            self.logger.info(f"📊 Размер контента после JS: {page_source_size} символов")
            
            # Извлекаем матчи
            matches = self._extract_matches_from_mobile_page(sport)
            
            self.logger.info(f"✅ Извлечено {len(matches)} матчей из мобильной версии")
            return matches
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения матчей: {e}")
            return []
    
    def _extract_matches_from_mobile_page(self, sport: str) -> List[Dict[str, Any]]:
        """Извлекает матчи из загруженной мобильной страницы"""
        
        matches = []
        
        try:
            # Ищем элементы с матчами
            event_elements = self.driver.find_elements(By.CSS_SELECTOR, 'div[class*="event"]')
            
            if not event_elements:
                self.logger.warning("❌ Элементы матчей не найдены")
                return []
            
            self.logger.info(f"🔍 Найдено {len(event_elements)} элементов событий")
            
            # Анализируем каждый элемент
            for i, element in enumerate(event_elements):
                try:
                    match_data = self._parse_match_element(element, sport, i)
                    if match_data:
                        matches.append(match_data)
                except Exception as e:
                    self.logger.debug(f"Ошибка парсинга элемента {i}: {e}")
                    continue
            
            # Дедуплицируем матчи
            unique_matches = self._deduplicate_matches(matches)
            
            self.logger.info(f"📊 Уникальных матчей после дедупликации: {len(unique_matches)}")
            return unique_matches
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка извлечения матчей: {e}")
            return []
    
    def _parse_match_element(self, element, sport: str, index: int) -> Optional[Dict[str, Any]]:
        """Парсит отдельный элемент матча"""
        
        try:
            element_text = element.text.strip()
            
            if not element_text or len(element_text) < 10:
                return None
            
            self.logger.debug(f"Анализируем элемент {index}: {element_text[:100]}...")
            
            # Извлекаем команды и счет в зависимости от спорта
            if sport == 'tennis' or sport == 'table_tennis':
                return self._parse_tennis_match(element_text, sport)
            elif sport == 'football':
                return self._parse_football_match(element_text)
            elif sport == 'handball':
                return self._parse_handball_match(element_text)
            else:
                return self._parse_generic_match(element_text, sport)
                
        except Exception as e:
            self.logger.debug(f"Ошибка парсинга элемента: {e}")
            return None
    
    def _parse_tennis_match(self, text: str, sport: str) -> Optional[Dict[str, Any]]:
        """Парсит теннисный матч"""
        
        # Паттерн для тенниса: "Игрок1 Игрок2 счет_по_сетам (счет_текущего_сета)"
        patterns = [
            r'([А-Яа-яA-Za-z\s,-]+?)\s+([А-Яа-яA-Za-z\s,-]+?)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+).*?\((\d+):(\d+)\)',
            r'([А-Яа-яA-Za-z\s,-]+?)\s+([А-Яа-яA-Za-z\s,-]+?).*?\((\d+):(\d+),(\d+):(\d+)\)',
            r'([А-Яа-яA-Za-z\s,-]+?)\s+([А-Яа-яA-Za-z\s,-]+?).*?\((\d+):(\d+)\)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                groups = match.groups()
                
                if len(groups) >= 4:
                    team1 = self._clean_team_name(groups[0])
                    team2 = self._clean_team_name(groups[1])
                    
                    # Извлекаем счет (по сетам)
                    if len(groups) >= 6 and 'set' not in text.lower():
                        # Формат: сеты отдельно
                        sets_home = groups[2]
                        sets_away = groups[3] 
                        score = f"{sets_home}:{sets_away}"
                    else:
                        # Формат: счет в скобках
                        score_home = groups[-2]
                        score_away = groups[-1]
                        score = f"{score_home}:{score_away}"
                    
                    if self._is_valid_match(team1, team2, score):
                        return {
                            'team1': team1,
                            'team2': team2,
                            'score': score,
                            'sport': sport,
                            'source': 'mobile_marathonbet_selenium'
                        }
        
        return None
    
    def _parse_football_match(self, text: str) -> Optional[Dict[str, Any]]:
        """Парсит футбольный матч"""
        
        patterns = [
            r'([А-Яа-яA-Za-z\s]+?)\s+([А-Яа-яA-Za-z\s]+?)\s+(\d+)\s+(\d+)',
            r'(\d+)\s+([А-Яа-яA-Za-z\s]+?)\s+(\d+)\s+([А-Яа-яA-Za-z\s]+?)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                
                if len(groups) >= 4:
                    # Определяем где команды, а где счет
                    if groups[0].isdigit():
                        # Формат: счет команда счет команда
                        score = f"{groups[0]}:{groups[2]}"
                        team1 = self._clean_team_name(groups[1])
                        team2 = self._clean_team_name(groups[3])
                    else:
                        # Формат: команда команда счет счет
                        team1 = self._clean_team_name(groups[0])
                        team2 = self._clean_team_name(groups[1])
                        score = f"{groups[2]}:{groups[3]}"
                    
                    if self._is_valid_match(team1, team2, score):
                        return {
                            'team1': team1,
                            'team2': team2,
                            'score': score,
                            'sport': 'football',
                            'source': 'mobile_marathonbet_selenium'
                        }
        
        return None
    
    def _parse_handball_match(self, text: str) -> Optional[Dict[str, Any]]:
        """Парсит гандбольный матч"""
        return self._parse_football_match(text)  # Аналогичная логика
    
    def _parse_generic_match(self, text: str, sport: str) -> Optional[Dict[str, Any]]:
        """Общий парсер для любого спорта"""
        
        # Ищем любые паттерны команд и счетов
        patterns = [
            r'([А-Яа-яA-Za-z\s,-]+?)\s+([А-Яа-яA-Za-z\s,-]+?).*?(\d+)[:-](\d+)',
            r'(\d+)[:-](\d+).*?([А-Яа-яA-Za-z\s,-]+?)\s+([А-Яа-яA-Za-z\s,-]+?)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                
                if len(groups) >= 4:
                    if groups[0].isdigit():
                        score = f"{groups[0]}:{groups[1]}"
                        team1 = self._clean_team_name(groups[2])
                        team2 = self._clean_team_name(groups[3])
                    else:
                        team1 = self._clean_team_name(groups[0])
                        team2 = self._clean_team_name(groups[1])
                        score = f"{groups[2]}:{groups[3]}"
                    
                    if self._is_valid_match(team1, team2, score):
                        return {
                            'team1': team1,
                            'team2': team2,
                            'score': score,
                            'sport': sport,
                            'source': 'mobile_marathonbet_selenium'
                        }
        
        return None
    
    def _clean_team_name(self, name: str) -> str:
        """Очищает название команды"""
        
        if not name:
            return ""
            
        # Убираем лишние символы и пробелы
        name = re.sub(r'[^\w\s,-]', '', name).strip()
        name = re.sub(r'\s+', ' ', name)
        
        # Убираем числа в начале/конце
        name = re.sub(r'^\d+\s*', '', name)
        name = re.sub(r'\s*\d+$', '', name)
        
        return name
    
    def _is_valid_match(self, team1: str, team2: str, score: str) -> bool:
        """Проверяет валидность данных матча"""
        
        if not team1 or not team2 or not score:
            return False
            
        if len(team1) < 3 or len(team2) < 3:
            return False
            
        if team1.lower() == team2.lower():
            return False
            
        if ':' not in score:
            return False
            
        try:
            home, away = map(int, score.split(':'))
            if home < 0 or away < 0 or home > 50 or away > 50:
                return False
        except ValueError:
            return False
            
        return True
    
    def _deduplicate_matches(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Убирает дубликаты матчей"""
        
        seen = set()
        unique = []
        
        for match in matches:
            key = f"{match['team1'].lower()}_{match['team2'].lower()}_{match['score']}"
            if key not in seen:
                seen.add(key)
                unique.append(match)
        
        return unique
    
    def close(self):
        """Закрывает браузер"""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("🔧 Selenium браузер закрыт")
            except Exception as e:
                self.logger.error(f"Ошибка закрытия браузера: {e}")
            finally:
                self.driver = None
    
    def __del__(self):
        """Автоматическое закрытие браузера"""
        self.close()


# Функция для тестирования
def test_mobile_scraper():
    """Тестирование мобильного парсера"""
    
    import logging
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    scraper = MobileMarathonBetScraper(logger)
    
    try:
        # Тестируем разные виды спорта
        sports = ['tennis', 'football', 'table_tennis']
        
        for sport in sports:
            print(f"\n🔍 Тестируем {sport}:")
            matches = scraper.get_live_matches_with_real_scores(sport)
            
            print(f"Найдено матчей: {len(matches)}")
            
            for i, match in enumerate(matches[:3], 1):
                print(f"  {i}. {match['team1']} vs {match['team2']}: {match['score']}")
                
    finally:
        scraper.close()


if __name__ == "__main__":
    test_mobile_scraper()