"""
Улучшенный скрапер теннисных матчей с BetBoom
"""
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import re
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('improved_tennis_scraper')

class ImprovedTennisScraper:
    """Улучшенный скрапер теннисных матчей с BetBoom"""
    
    def __init__(self, logger):
        self.logger = logger
        self.driver = None
    
    def setup_driver(self):
        """Настройка Chrome драйвера с дополнительными опциями"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.logger.info("✅ Chrome драйвер настроен")
            return True
        except Exception as e:
            self.logger.error(f"❌ Ошибка настройки драйвера: {e}")
            return False
    
    def close_driver(self):
        """Закрытие драйвера"""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("🔌 Драйвер закрыт")
            except Exception as e:
                self.logger.error(f"Ошибка закрытия драйвера: {e}")
    
    def navigate_to_tennis(self) -> bool:
        """Переход на страницу тенниса"""
        try:
            url = "https://betboom.ru/sport/tennis?type=live"
            self.logger.info(f"🌐 Переход на {url}")
            self.driver.get(url)
            
            # Ждем загрузки страницы
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Дополнительное ожидание для загрузки динамического контента
            time.sleep(10)
            
            self.logger.info("✅ Страница загружена")
            return True
        except Exception as e:
            self.logger.error(f"❌ Ошибка навигации: {e}")
            return False
    
    def get_page_content(self) -> Optional[str]:
        """Получение содержимого страницы"""
        try:
            self.logger.info("📄 Получение содержимого страницы...")
            content = self.driver.page_source
            self.logger.info(f"Получено {len(content)} символов")
            return content
        except Exception as e:
            self.logger.error(f"Ошибка получения контента: {e}")
            return None
    
    def extract_tennis_data_from_scripts(self) -> List[Dict[str, Any]]:
        """Извлечение теннисных данных из JavaScript"""
        try:
            self.logger.info("🔍 Поиск теннисных данных в JavaScript...")
            
            # Ищем все script теги
            scripts = self.driver.find_elements(By.TAG_NAME, "script")
            
            for script in scripts:
                try:
                    script_content = script.get_attribute("innerHTML")
                    if script_content and ("tennis" in script_content.lower() or "wta" in script_content.lower() or "atp" in script_content.lower()):
                        self.logger.info("Найден скрипт с теннисными данными")
                        
                        # Пытаемся найти JSON данные
                        json_matches = re.findall(r'\{[^{}]*"tennis"[^{}]*\}', script_content)
                        for json_match in json_matches:
                            try:
                                data = json.loads(json_match)
                                self.logger.info(f"Найдены JSON данные: {data}")
                            except:
                                pass
                        
                        # Ищем паттерны матчей
                        match_patterns = [
                            r'([A-Za-zА-Яа-я\s\.]+)\s+vs\s+([A-Za-zА-Яа-я\s\.]+)',
                            r'([A-Za-zА-Яа-я\s\.]+)\s+([A-Za-zА-Яа-я\s\.]+)\s+(\d+)\s+(\d+)',
                            r'([A-Za-zА-Яа-я\s\.]+)\s+([A-Za-zА-Яа-я\s\.]+)\s+(\d+-\d+)'
                        ]
                        
                        for pattern in match_patterns:
                            matches = re.findall(pattern, script_content)
                            if matches:
                                self.logger.info(f"Найдены матчи по паттерну: {matches}")
                                return self.parse_script_matches(matches)
                
                except Exception as e:
                    self.logger.warning(f"Ошибка обработки скрипта: {e}")
                    continue
            
            return []
            
        except Exception as e:
            self.logger.error(f"Ошибка извлечения данных из скриптов: {e}")
            return []
    
    def parse_script_matches(self, matches) -> List[Dict[str, Any]]:
        """Парсинг матчей из скриптов"""
        tennis_matches = []
        
        for match in matches:
            try:
                if len(match) >= 2:
                    player1 = match[0].strip()
                    player2 = match[1].strip()
                    
                    score = " ".join(match[2:]) if len(match) > 2 else "LIVE"
                    
                    if self.is_non_tie_score(score):
                        tennis_matches.append({
                            'player1': player1,
                            'player2': player2,
                            'score': score,
                            'status': 'LIVE',
                            'sport': 'tennis',
                            'source': 'betboom_script'
                        })
            
            except Exception as e:
                self.logger.warning(f"Ошибка парсинга матча: {e}")
                continue
        
        return tennis_matches
    
    def find_tennis_matches_in_html(self) -> List[Dict[str, Any]]:
        """Поиск теннисных матчей в HTML"""
        try:
            self.logger.info("🔍 Поиск теннисных матчей в HTML...")
            
            # Получаем HTML
            html_content = self.driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Ищем различные селекторы
            selectors = [
                '.sport-event',
                '.bet-item',
                '.match-item',
                '.game-item',
                '.event-item',
                '[class*="match"]',
                '[class*="game"]',
                '[class*="event"]',
                '[class*="live"]',
                '[class*="tennis"]',
                '[data-sport="tennis"]',
                '[data-sport="Tennis"]'
            ]
            
            found_elements = []
            
            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    self.logger.info(f"Найдено {len(elements)} элементов по селектору: {selector}")
                    found_elements.extend(elements)
            
            # Если не нашли по селекторам, ищем по тексту
            if not found_elements:
                self.logger.info("Поиск матчей по тексту...")
                all_elements = soup.find_all(text=re.compile(r'(WTA|ATP|ITF|теннис|tennis|сет|set)', re.IGNORECASE))
                for element in all_elements:
                    parent = element.parent
                    if parent and parent not in found_elements:
                        found_elements.append(parent)
            
            # Парсим найденные элементы
            matches = []
            for element in found_elements[:100]:
                try:
                    match_data = self.extract_match_data(element)
                    if match_data:
                        matches.append(match_data)
                except Exception as e:
                    self.logger.warning(f"Ошибка парсинга элемента: {e}")
                    continue
            
            return matches
            
        except Exception as e:
            self.logger.error(f"Ошибка поиска матчей в HTML: {e}")
            return []
    
    def extract_match_data(self, element) -> Optional[Dict[str, Any]]:
        """Извлечение данных матча из элемента"""
        try:
            text = element.get_text(strip=True)
            
            if len(text) < 10 or len(text) > 500:
                return None
            
            # Паттерны для теннисных матчей
            patterns = [
                r'([A-Za-zА-Яа-я\s\.]+)\s+([A-Za-zА-Яа-я\s\.]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)',
                r'([A-Za-zА-Яа-я\s\.]+)\s+([A-Za-zА-Яа-я\s\.]+)\s+(\d+-\d+)\s+(\d+-\d+)',
                r'([A-Za-zА-Яа-я\s\.]+)\s+([A-Za-zА-Яа-я\s\.]+)\s+(\d+)\s+(\d+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    groups = match.groups()
                    if len(groups) >= 2:
                        player1 = groups[0].strip()
                        player2 = groups[1].strip()
                        score = " ".join(groups[2:]) if len(groups) > 2 else "LIVE"
                        
                        if self.is_non_tie_score(score):
                            return {
                                'player1': player1,
                                'player2': player2,
                                'score': score,
                                'status': 'LIVE',
                                'sport': 'tennis',
                                'source': 'betboom_html',
                                'raw_text': text[:100] + "..." if len(text) > 100 else text
                            }
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения данных матча: {e}")
            return None
    
    def is_non_tie_score(self, score: str) -> bool:
        """Проверка, что счет неничейный по сетам"""
        try:
            score = score.strip()
            
            # Ищем паттерн сета: цифра-цифра
            set_pattern = r'\d+-\d+'
            sets = re.findall(set_pattern, score)
            
            if not sets:
                numbers = re.findall(r'\d+', score)
                if len(numbers) >= 2:
                    return len(set(numbers)) > 1
                return False
            
            # Проверяем каждый сет
            for set_score in sets:
                parts = set_score.split('-')
                if len(parts) == 2:
                    try:
                        score1 = int(parts[0])
                        score2 = int(parts[1])
                        
                        if score1 == score2:
                            return False
                        
                        if abs(score1 - score2) < 2:
                            return False
                            
                    except ValueError:
                        continue
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Ошибка проверки счета '{score}': {e}")
            return False

def scrape_tennis_matches():
    """Основная функция скрапинга теннисных матчей"""
    logger.info("🎾 Начинаем улучшенный скрапинг теннисных матчей с BetBoom")
    
    scraper = ImprovedTennisScraper(logger)
    
    try:
        # Настраиваем драйвер
        if not scraper.setup_driver():
            logger.error("❌ Не удалось настроить драйвер")
            return []
        
        logger.info("✅ Драйвер настроен успешно")
        
        # Переходим на страницу тенниса
        if not scraper.navigate_to_tennis():
            logger.error("❌ Не удалось перейти на страницу тенниса")
            return []
        
        logger.info("✅ Успешно перешли на страницу тенниса")
        
        # Создаем скриншот
        scraper.driver.save_screenshot("betboom_tennis_improved.png")
        logger.info("📸 Скриншот создан")
        
        # Получаем содержимое страницы
        content = scraper.get_page_content()
        if not content:
            logger.error("❌ Не удалось получить содержимое страницы")
            return []
        
        logger.info("✅ Содержимое страницы получено")
        
        # Сохраняем HTML для анализа
        with open("betboom_tennis_improved.html", "w", encoding="utf-8") as f:
            f.write(content)
        logger.info("💾 HTML сохранен в betboom_tennis_improved.html")
        
        # Ищем матчи в HTML
        html_matches = scraper.find_tennis_matches_in_html()
        logger.info(f"Найдено {len(html_matches)} матчей в HTML")
        
        # Ищем матчи в JavaScript
        script_matches = scraper.extract_tennis_data_from_scripts()
        logger.info(f"Найдено {len(script_matches)} матчей в JavaScript")
        
        # Объединяем результаты
        all_matches = html_matches + script_matches
        
        if all_matches:
            logger.info(f"🎾 Всего найдено {len(all_matches)} теннисных матчей")
            
            # Выводим результаты
            print("\n" + "="*100)
            print("🎾 УЛУЧШЕННЫЕ РЕЗУЛЬТАТЫ СКРАПИНГА ТЕННИСНЫХ МАТЧЕЙ С BETBOOM")
            print("="*100)
            print(f"📅 Время получения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"🌐 Источник: https://betboom.ru/sport/tennis?type=live")
            print(f"🔧 Метод: Улучшенный Selenium WebDriver")
            print("="*100)
            
            for i, match in enumerate(all_matches, 1):
                print(f"{i:2d}. {match['player1']} vs {match['player2']}")
                print(f"    Счет: {match['score']} ({match['status']})")
                print(f"    Спорт: {match['sport']} | Источник: {match['source']}")
                if 'raw_text' in match:
                    print(f"    Raw: {match['raw_text']}")
                print()
            
            print(f"✅ Всего найдено: {len(all_matches)} матчей")
            print("="*100)
        else:
            logger.warning("❌ Теннисные матчи не найдены")
            print("\n❌ Теннисные матчи не найдены на странице")
            print("💡 Возможные причины:")
            print("   - На странице нет live теннисных матчей")
            print("   - Данные загружаются через JavaScript после загрузки страницы")
            print("   - Изменилась структура сайта")
        
        return all_matches
    
    except Exception as e:
        logger.error(f"❌ Общая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    finally:
        # Закрываем драйвер
        scraper.close_driver()
        logger.info("🔌 Драйвер закрыт")

if __name__ == "__main__":
    scrape_tennis_matches()