"""
Специализированный парсер MarathonBet с поддержкой выпадающих списков (ecids)
Извлекает полную структуру данных как в примере пользователя
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


class MarathonBetExpandedScraper:
    """
    ФИНАЛЬНОЕ РЕШЕНИЕ для получения полных данных MarathonBet
    
    ОСОБЕННОСТИ:
    - Поддержка выпадающих списков (ecids параметры)
    - Извлечение полной структуры: команды + счета + коэффициенты + лига
    - Автоматическое раскрытие скрытых матчей
    - Решение проблемы сопоставления команд (один источник)
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.driver = None
        
        # Базовые URL для разных видов спорта
        self.base_urls = {
            'football': 'https://www.marathonbet.ru/su/live/26418',
            'tennis': 'https://www.marathonbet.ru/su/live/22723',
            'table_tennis': 'https://www.marathonbet.ru/su/live/414329',
            'handball': 'https://www.marathonbet.ru/su/live/26422'
        }
        
    def _setup_driver(self):
        """Настройка Selenium для десктопной версии"""
        if self.driver:
            return
            
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.logger.info("✅ Selenium драйвер для expanded версии запущен")
    
    def get_all_expanded_matches(self, sport: str = 'football') -> List[Dict[str, Any]]:
        """
        ГЛАВНЫЙ МЕТОД: Получает все матчи включая скрытые в выпадающих списках
        
        Args:
            sport: Вид спорта
            
        Returns:
            List[Dict]: Полные данные всех матчей
        """
        
        if sport not in self.base_urls:
            self.logger.error(f"Неподдерживаемый спорт: {sport}")
            return []
        
        base_url = self.base_urls[sport]
        self.logger.info(f"🔍 Получаем expanded данные {sport}: {base_url}")
        
        try:
            self._setup_driver()
            
            # Шаг 1: Получаем базовую страницу и находим все ecids
            ecids = self._discover_all_ecids(base_url)
            
            # Шаг 2: Получаем данные с раскрытыми списками
            all_matches = self._get_matches_with_expanded_lists(base_url, ecids)
            
            self.logger.info(f"✅ Получено {len(all_matches)} expanded матчей")
            return all_matches
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения expanded матчей: {e}")
            return []
    
    def _discover_all_ecids(self, base_url: str) -> List[str]:
        """Находит все доступные ecids на странице"""
        
        ecids = []
        
        try:
            # Загружаем базовую страницу
            self.driver.get(base_url)
            time.sleep(3)
            
            # Ищем элементы которые могут содержать ecids
            # Обычно это кнопки раскрытия списков или data-атрибуты
            
            # Способ 1: Поиск в HTML атрибутах
            elements_with_data = self.driver.find_elements(By.XPATH, '//*[@data-event-id or @data-ecid or @data-id]')
            
            for element in elements_with_data:
                try:
                    for attr in ['data-event-id', 'data-ecid', 'data-id']:
                        value = element.get_attribute(attr)
                        if value and value.isdigit():
                            ecids.append(value)
                except:
                    continue
            
            # Способ 2: Поиск в JavaScript переменных
            page_source = self.driver.page_source
            js_ecids = re.findall(r'ecid[s]?["\']?\\s*[:=]\\s*["\']?(\\d+)', page_source)
            ecids.extend(js_ecids)
            
            # Способ 3: Поиск в URL ссылок
            links = self.driver.find_elements(By.TAG_NAME, 'a')
            for link in links:
                try:
                    href = link.get_attribute('href')
                    if href and 'ecids=' in href:
                        ecids_in_url = re.findall(r'ecids=([\\d,]+)', href)
                        for ecids_string in ecids_in_url:
                            ecids.extend(ecids_string.split(','))
                except:
                    continue
            
            # Убираем дубликаты
            unique_ecids = list(set(ecids))
            
            self.logger.info(f"🔍 Найдено {len(unique_ecids)} уникальных ecids")
            return unique_ecids[:20]  # Ограничиваем для тестирования
            
        except Exception as e:
            self.logger.error(f"Ошибка поиска ecids: {e}")
            return []
    
    def _get_matches_with_expanded_lists(self, base_url: str, ecids: List[str]) -> List[Dict[str, Any]]:
        """Получает матчи с раскрытыми выпадающими списками"""
        
        all_matches = []
        
        if not ecids:
            self.logger.warning("❌ Нет ecids для раскрытия списков")
            return []
        
        # Создаем URL с постепенно раскрывающимися списками
        expanded_urls = []
        
        # Одиночные ecids
        for ecid in ecids[:5]:  # Первые 5
            expanded_urls.append(f"{base_url}?ecids={ecid}")
        
        # Комбинированные ecids
        if len(ecids) >= 2:
            expanded_urls.append(f"{base_url}?ecids={','.join(ecids[:2])}")
        if len(ecids) >= 3:
            expanded_urls.append(f"{base_url}?ecids={','.join(ecids[:3])}")
        if len(ecids) >= 5:
            expanded_urls.append(f"{base_url}?ecids={','.join(ecids[:5])}")
        
        self.logger.info(f"🔍 Тестируем {len(expanded_urls)} expanded URL")
        
        for i, url in enumerate(expanded_urls):
            try:
                self.logger.info(f"📋 Загружаем expanded URL {i+1}: {url}")
                
                self.driver.get(url)
                time.sleep(4)
                
                # Извлекаем матчи из expanded страницы
                matches = self._extract_matches_from_expanded_page(url)
                
                if matches:
                    self.logger.info(f"✅ Из URL {i+1} извлечено {len(matches)} матчей")
                    all_matches.extend(matches)
                else:
                    self.logger.debug(f"❌ Из URL {i+1} матчи не извлечены")
                    
            except Exception as e:
                self.logger.error(f"Ошибка обработки expanded URL {i+1}: {e}")
                continue
        
        # Дедуплицируем
        unique_matches = self._deduplicate_expanded_matches(all_matches)
        
        return unique_matches
    
    def _extract_matches_from_expanded_page(self, url: str) -> List[Dict[str, Any]]:
        """Извлекает матчи из expanded страницы"""
        
        matches = []
        
        try:
            # Ищем таблицы (основная структура данных)
            tables = self.driver.find_elements(By.TAG_NAME, 'table')
            
            for table_index, table in enumerate(tables):
                try:
                    rows = table.find_elements(By.TAG_NAME, 'tr')
                    
                    for row_index, row in enumerate(rows):
                        try:
                            cells = row.find_elements(By.TAG_NAME, 'td')
                            
                            if len(cells) >= 5:  # Достаточно ячеек для полного матча
                                match_data = self._parse_table_row(cells, url, table_index, row_index)
                                if match_data:
                                    matches.append(match_data)
                        except:
                            continue
                except:
                    continue
            
            return matches
            
        except Exception as e:
            self.logger.error(f"Ошибка извлечения из expanded страницы: {e}")
            return []
    
    def _parse_table_row(self, cells, url: str, table_index: int, row_index: int) -> Optional[Dict[str, Any]]:
        """Парсит строку таблицы для извлечения данных матча"""
        
        try:
            # Получаем текст всех ячеек
            cell_texts = []
            for cell in cells:
                cell_text = cell.text.strip()
                if cell_text:
                    cell_texts.append(cell_text)
            
            if len(cell_texts) < 3:
                return None
            
            # Первая ячейка обычно содержит: счет, время, команды
            main_cell = cell_texts[0]
            
            # Извлекаем компоненты
            score_match = re.search(r'(\\d+):(\\d+)', main_cell)
            time_match = re.search(r'(\\d{1,2}:\\d{2})', main_cell)
            
            if not score_match:
                return None
            
            score = score_match.group(0)
            match_time = time_match.group(0) if time_match else 'LIVE'
            
            # Извлекаем команды из основной ячейки
            teams = self._extract_teams_from_main_cell(main_cell)
            
            if not teams or len(teams) < 2:
                return None
            
            # Извлекаем коэффициенты из остальных ячеек
            coefficients = []
            for cell_text in cell_texts[1:]:
                # Ищем числа похожие на коэффициенты
                coeff_matches = re.findall(r'\\b(\\d+\\.\\d+)\\b', cell_text)
                coefficients.extend(coeff_matches)
            
            # Создаем структурированные данные
            match_data = {
                'team1': teams[0],
                'team2': teams[1],
                'score': score,
                'time': match_time,
                'source': 'marathonbet_expanded',
                'source_url': url,
                'table_position': f'table_{table_index}_row_{row_index}',
                'raw_main_cell': main_cell
            }
            
            # Структурируем коэффициенты
            if len(coefficients) >= 6:
                match_data['odds'] = {
                    '1': coefficients[0] if len(coefficients) > 0 else None,
                    'X': coefficients[1] if len(coefficients) > 1 else None, 
                    '2': coefficients[2] if len(coefficients) > 2 else None,
                    '1X': coefficients[3] if len(coefficients) > 3 else None,
                    '12': coefficients[4] if len(coefficients) > 4 else None,
                    'X2': coefficients[5] if len(coefficients) > 5 else None
                }
                
                # Дополнительные ставки
                if len(coefficients) > 6:
                    match_data['handicap'] = coefficients[6:8]
                    match_data['total'] = coefficients[8:10] if len(coefficients) > 8 else []
            
            return match_data
            
        except Exception as e:
            self.logger.debug(f"Ошибка парсинга строки таблицы: {e}")
            return None
    
    def _extract_teams_from_main_cell(self, main_cell: str) -> Optional[List[str]]:
        """Извлекает названия команд из основной ячейки"""
        
        # Разбиваем по строкам
        lines = main_cell.split('\\n')
        
        team_candidates = []
        for line in lines:
            line = line.strip()
            
            # Пропускаем очевидно не команды
            if (line and 
                not re.match(r'^\\d+$', line) and  # Не только цифры
                not re.match(r'^\\d+\\.\\d+$', line) and  # Не коэффициент
                not re.match(r'^\\d+:\\d+$', line) and  # Не время/счет
                not line in ['1.', '2.', '+', '-', 'X'] and  # Не служебные символы
                len(line) >= 3):
                
                team_candidates.append(line)
        
        # Берем первые две подходящие строки как команды
        if len(team_candidates) >= 2:
            team1 = self._clean_team_name(team_candidates[0])
            team2 = self._clean_team_name(team_candidates[1])
            
            if team1 and team2 and team1.lower() != team2.lower():
                return [team1, team2]
        
        return None
    
    def _clean_team_name(self, name: str) -> str:
        """Очищает название команды"""
        if not name:
            return ""
        
        # Убираем номера в начале (1., 2.)
        name = re.sub(r'^\\d+\\.\\s*', '', name)
        
        # Убираем лишние символы
        name = re.sub(r'[^\\w\\s,.-]', '', name).strip()
        name = re.sub(r'\\s+', ' ', name)
        
        return name
    
    def _deduplicate_expanded_matches(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Убирает дубликаты expanded матчей"""
        
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
                self.logger.info("🔧 Expanded браузер закрыт")
            except:
                pass
            finally:
                self.driver = None


# Функция тестирования
def test_expanded_scraper():
    """Тестирование expanded парсера"""
    
    import logging
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    scraper = MarathonBetExpandedScraper(logger)
    
    try:
        print("\\n🚀 ТЕСТИРУЕМ EXPANDED ПАРСЕР:")
        print("="*40)
        
        # Тестируем футбол
        football_matches = scraper.get_all_expanded_matches('football')
        
        if football_matches:
            print(f"\\n✅ НАЙДЕНО {len(football_matches)} EXPANDED МАТЧЕЙ!")
            
            for i, match in enumerate(football_matches[:3], 1):
                print(f"\\n📊 МАТЧ {i} (полная структура как в примере):")
                print("="*60)
                
                print(f"🏟️ ОСНОВНАЯ ИНФОРМАЦИЯ:")
                print(f"   Команда 1: {match.get('team1')}")
                print(f"   Команда 2: {match.get('team2')}")
                print(f"   Счет: {match.get('score')}")
                print(f"   Время: {match.get('time')}")
                
                odds = match.get('odds', {})
                if odds:
                    print(f"\\n💰 КОЭФФИЦИЕНТЫ:")
                    print(f"   1: {odds.get('1')} | X: {odds.get('X')} | 2: {odds.get('2')}")
                    print(f"   1X: {odds.get('1X')} | 12: {odds.get('12')} | X2: {odds.get('X2')}")
                
                handicap = match.get('handicap', [])
                total = match.get('total', [])
                
                if handicap:
                    print(f"\\n📈 ДОПОЛНИТЕЛЬНЫЕ СТАВКИ:")
                    print(f"   Фора: {handicap}")
                if total:
                    print(f"   Тотал: {total}")
                
                print(f"\\n🔧 ТЕХНИЧЕСКАЯ ИНФОРМАЦИЯ:")
                print(f"   Источник: {match.get('source')}")
                print(f"   URL: {match.get('source_url')}")
                print(f"   Позиция: {match.get('table_position')}")
        
        else:
            print("\\n❌ Expanded матчи не найдены")
            
    finally:
        scraper.close()


if __name__ == "__main__":
    test_expanded_scraper()