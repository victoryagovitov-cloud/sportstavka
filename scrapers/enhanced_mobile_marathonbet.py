"""
Улучшенный парсер мобильной версии MarathonBet
Извлекает полную структуру данных как в примере пользователя
"""

import logging
import re
import time
from typing import List, Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


class EnhancedMobileMarathonBetScraper:
    """
    ФИНАЛЬНОЕ РЕШЕНИЕ для получения полных данных матчей
    
    Извлекает:
    - Названия команд (Сайхамакавн vs СИС)
    - Реальные счета (0:1) 
    - Время матча (11:15)
    - Лигу (Индия. Мизорам. Премьер-лига)
    - Все коэффициенты (1, X, 2, 1X, 12, X2, фора, тотал)
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.driver = None
        
        self.mobile_urls = {
            'football': 'https://mobile.marathonbet.ru/su/sport/live/26418',
            'tennis': 'https://mobile.marathonbet.ru/su/sport/live/22723',
            'table_tennis': 'https://mobile.marathonbet.ru/su/sport/live/414329',
            'handball': 'https://mobile.marathonbet.ru/su/sport/live/26422'
        }
    
    def _setup_driver(self):
        """Настройка Selenium"""
        if self.driver:
            return
            
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=375,812')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.logger.info("✅ Enhanced Selenium драйвер запущен")
    
    def get_complete_matches_data(self, sport: str = 'football') -> List[Dict[str, Any]]:
        """
        ГЛАВНЫЙ МЕТОД: Получает полные данные матчей как в примере
        
        Returns:
            List[Dict]: Полная структура данных для каждого матча
        """
        
        if sport not in self.mobile_urls:
            self.logger.error(f"Неподдерживаемый спорт: {sport}")
            return []
        
        url = self.mobile_urls[sport]
        self.logger.info(f"🔍 Получаем полные данные {sport} из: {url}")
        
        try:
            self._setup_driver()
            self.driver.get(url)
            
            # Ждем полной загрузки
            time.sleep(8)
            self.logger.info(f"📱 Страница загружена: {len(self.driver.page_source)} символов")
            
            # Извлекаем полные данные
            matches = self._extract_complete_match_data(sport)
            
            self.logger.info(f"✅ Извлечено {len(matches)} полных матчей")
            return matches
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения данных: {e}")
            return []
    
    def _extract_complete_match_data(self, sport: str) -> List[Dict[str, Any]]:
        """Извлекает полные данные всех матчей"""
        
        matches = []
        
        try:
            # Стратегия 1: Поиск по event контейнерам
            event_containers = self.driver.find_elements(By.CSS_SELECTOR, 
                'div[class*=\"event\"], div[class*=\"match\"], div[class*=\"game\"]')
            
            self.logger.info(f"🔍 Найдено {len(event_containers)} event контейнеров")
            
            for i, container in enumerate(event_containers):
                try:
                    match_data = self._parse_complete_match_container(container, sport, i)
                    if match_data:
                        matches.append(match_data)
                except Exception as e:
                    self.logger.debug(f"Ошибка парсинга контейнера {i}: {e}")
                    continue
            
            # Стратегия 2: Если не нашли через контейнеры, ищем в общем тексте
            if not matches:
                matches = self._extract_from_page_text(sport)
            
            # Дедуплицируем
            unique_matches = self._deduplicate_complete_matches(matches)
            
            return unique_matches
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка извлечения данных: {e}")
            return []
    
    def _parse_complete_match_container(self, container, sport: str, index: int) -> Optional[Dict[str, Any]]:
        """Парсит один контейнер матча для получения полных данных"""
        
        try:
            # Получаем весь текст контейнера
            full_text = container.text.strip()
            
            if not full_text or len(full_text) < 15:
                return None
            
            self.logger.debug(f"Анализируем контейнер {index}: {full_text[:150]}...")
            
            # Извлекаем базовую информацию
            match_info = self._extract_basic_match_info(full_text, sport)
            if not match_info:
                return None
            
            # Извлекаем коэффициенты
            odds_data = self._extract_odds_from_container(container, full_text, sport)
            
            # Пытаемся определить лигу
            league = self._extract_league_info(container, full_text)
            
            # Собираем полную структуру
            complete_match = {
                **match_info,
                'league': league,
                'odds': odds_data,
                'source': 'enhanced_mobile_marathonbet',
                'sport_type': sport,
                'raw_text': full_text[:200]  # Для отладки
            }
            
            return complete_match
            
        except Exception as e:
            self.logger.debug(f"Ошибка парсинга контейнера: {e}")
            return None
    
    def _extract_basic_match_info(self, text: str, sport: str) -> Optional[Dict[str, Any]]:
        """Извлекает базовую информацию о матче"""
        
        # Ищем счет
        score_match = re.search(r'(\\d+):(\\d+)', text)
        if not score_match:
            return None
        
        score = score_match.group(0)
        
        # Ищем время
        time_match = re.search(r'(\\d{1,2}:\\d{2})', text)
        match_time = time_match.group(0) if time_match else 'LIVE'
        
        # Извлекаем команды в зависимости от спорта
        if sport in ['tennis', 'table_tennis']:
            teams = self._extract_tennis_teams(text)
        else:
            teams = self._extract_football_teams(text)
        
        if not teams:
            return None
        
        return {
            'team1': teams[0],
            'team2': teams[1],
            'score': score,
            'time': match_time
        }
    
    def _extract_tennis_teams(self, text: str) -> Optional[List[str]]:
        """Извлекает имена теннисистов"""
        
        # Паттерны для теннисных имен
        patterns = [
            r'([А-Яа-яA-Za-z]+,\\s*[А-Яа-яA-Za-z]+).*?([А-Яа-яA-Za-z]+,\\s*[А-Яа-яA-Za-z]+)',
            r'([А-Яа-яA-Za-z\\s,-]+?)\\s+([А-Яа-яA-Za-z\\s,-]+?)\\s+\\d+:\\d+',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                team1 = self._clean_team_name(match.group(1))
                team2 = self._clean_team_name(match.group(2))
                
                if self._are_valid_teams(team1, team2):
                    return [team1, team2]
        
        return None
    
    def _extract_football_teams(self, text: str) -> Optional[List[str]]:
        """Извлекает названия футбольных команд"""
        
        lines = text.split('\\n')
        team_candidates = []
        
        for line in lines:
            line = line.strip()
            if (line and 3 <= len(line) <= 25 and
                not re.match(r'^\\d+$', line) and
                not re.match(r'^\\d+\\.\\d+$', line) and
                not re.match(r'^\\d+:\\d+$', line) and
                line not in ['1', '2', 'X', '+', '-']):
                team_candidates.append(line)
        
        # Берем первые две подходящие строки как команды
        if len(team_candidates) >= 2:
            team1 = self._clean_team_name(team_candidates[0])
            team2 = self._clean_team_name(team_candidates[1])
            
            if self._are_valid_teams(team1, team2):
                return [team1, team2]
        
        return None
    
    def _extract_odds_from_container(self, container, text: str, sport: str) -> Dict[str, Any]:
        """Извлекает все коэффициенты из контейнера"""
        
        odds = {}
        
        try:
            # Ищем все числа похожие на коэффициенты
            coeff_matches = re.findall(r'\\b(\\d+\\.\\d+)\\b', text)
            
            if coeff_matches:
                # Для футбола: 1, X, 2, 1X, 12, X2, фора, тотал
                if sport == 'football' and len(coeff_matches) >= 6:
                    odds = {
                        '1': coeff_matches[0] if len(coeff_matches) > 0 else None,
                        'X': coeff_matches[1] if len(coeff_matches) > 1 else None,
                        '2': coeff_matches[2] if len(coeff_matches) > 2 else None,
                        '1X': coeff_matches[3] if len(coeff_matches) > 3 else None,
                        '12': coeff_matches[4] if len(coeff_matches) > 4 else None,
                        'X2': coeff_matches[5] if len(coeff_matches) > 5 else None,
                    }
                    
                    # Дополнительные ставки
                    if len(coeff_matches) > 6:
                        odds['handicap'] = coeff_matches[6:8]
                        odds['total'] = coeff_matches[8:10] if len(coeff_matches) > 8 else []
                
                # Для тенниса: 1, 2, фора, тотал
                elif sport in ['tennis', 'table_tennis'] and len(coeff_matches) >= 2:
                    odds = {
                        '1': coeff_matches[0],
                        '2': coeff_matches[1],
                        'handicap': coeff_matches[2:4] if len(coeff_matches) > 2 else [],
                        'total': coeff_matches[4:6] if len(coeff_matches) > 4 else []
                    }
            
            # Попытка найти коэффициенты через элементы
            coeff_elements = container.find_elements(By.XPATH, './/*[text()]')
            for elem in coeff_elements:
                elem_text = elem.text.strip()
                if re.match(r'^\\d+\\.\\d+$', elem_text):
                    # Дополнительная логика для точного определения типа ставки
                    pass
            
        except Exception as e:
            self.logger.debug(f"Ошибка извлечения коэффициентов: {e}")
        
        return odds
    
    def _extract_league_info(self, container, text: str) -> str:
        """Извлекает информацию о лиге"""
        
        # Ищем в тексте контейнера
        league_patterns = [
            r'([А-Яа-я]+\\.\\s*[А-Яа-я\\s\\.]+)',  # Индия. Мизорам. Премьер-лига
            r'([A-Za-z]+\\.\\s*[A-Za-z\\s\\.]+)',   # English leagues
        ]
        
        for pattern in league_patterns:
            match = re.search(pattern, text)
            if match:
                league = match.group(1).strip()
                if len(league) > 5:
                    return league
        
        # Попытка найти в родительских элементах
        try:
            parent = container.find_element(By.XPATH, '..')
            parent_text = parent.text
            
            for pattern in league_patterns:
                match = re.search(pattern, parent_text)
                if match:
                    return match.group(1).strip()
        except:
            pass
        
        return 'Неизвестная лига'
    
    def _extract_from_page_text(self, sport: str) -> List[Dict[str, Any]]:
        """Fallback: извлечение из общего текста страницы"""
        
        try:
            page_text = self.driver.find_element(By.TAG_NAME, 'body').text
            
            # Разбиваем на блоки и ищем матчи
            blocks = page_text.split('\\n\\n')
            
            matches = []
            for block in blocks:
                if len(block) > 50 and ':' in block:
                    match_info = self._extract_basic_match_info(block, sport)
                    if match_info:
                        matches.append({
                            **match_info,
                            'league': 'Извлечено из текста',
                            'odds': {},
                            'source': 'page_text_fallback'
                        })
            
            return matches
            
        except Exception as e:
            self.logger.error(f"Ошибка fallback извлечения: {e}")
            return []
    
    def _clean_team_name(self, name: str) -> str:
        """Очищает название команды/игрока"""
        if not name:
            return ""
        
        # Убираем лишние символы
        name = re.sub(r'[^\\w\\s,.-]', '', name).strip()
        name = re.sub(r'\\s+', ' ', name)
        
        # Убираем числа в начале/конце
        name = re.sub(r'^\\d+\\s*', '', name)
        name = re.sub(r'\\s*\\d+$', '', name)
        
        return name
    
    def _are_valid_teams(self, team1: str, team2: str) -> bool:
        """Проверяет валидность названий команд"""
        return (team1 and team2 and 
                len(team1) >= 3 and len(team2) >= 3 and
                team1.lower() != team2.lower())
    
    def _deduplicate_complete_matches(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Убирает дубликаты матчей"""
        seen = set()
        unique = []
        
        for match in matches:
            key = f"{match.get('team1', '').lower()}_{match.get('team2', '').lower()}_{match.get('score', '')}"
            if key not in seen and len(key) > 10:
                seen.add(key)
                unique.append(match)
        
        return unique
    
    def close(self):
        """Закрывает браузер"""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("🔧 Enhanced браузер закрыт")
            except:
                pass
            finally:
                self.driver = None


# Функция тестирования
def test_enhanced_scraper():
    """Тестирование улучшенного парсера"""
    
    import logging
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    scraper = EnhancedMobileMarathonBetScraper(logger)
    
    try:
        # Тестируем футбол
        print("\\n🏈 ТЕСТИРУЕМ ФУТБОЛ:")
        football_matches = scraper.get_complete_matches_data('football')
        
        for i, match in enumerate(football_matches[:3], 1):
            print(f"\\n  Матч {i}:")
            print(f"    {match.get('team1')} vs {match.get('team2')}")
            print(f"    Счет: {match.get('score')} | Время: {match.get('time')}")
            print(f"    Лига: {match.get('league')}")
            print(f"    Коэффициенты: {match.get('odds', {})}")
        
        if football_matches:
            print(f"\\n✅ УСПЕХ! Найдено {len(football_matches)} полных матчей!")
        else:
            print("\\n❌ Полные матчи не найдены")
        
    finally:
        scraper.close()


if __name__ == "__main__":
    test_enhanced_scraper()