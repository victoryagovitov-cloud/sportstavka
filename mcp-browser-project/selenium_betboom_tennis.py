"""
Реальный скрапер теннисных матчей с BetBoom через Selenium
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
from datetime import datetime
from typing import List, Dict, Any, Optional

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('selenium_betboom_tennis')

class SeleniumBetBoomTennisScraper:
    """Скрапер теннисных матчей с BetBoom через Selenium"""
    
    def __init__(self, logger):
        self.logger = logger
        self.driver = None
    
    def setup_driver(self):
        """Настройка Chrome драйвера"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            self.driver = webdriver.Chrome(options=chrome_options)
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
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
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
    
    def take_screenshot(self, path: str = "betboom_tennis_selenium.png") -> bool:
        """Создание скриншота"""
        try:
            self.logger.info(f"📸 Создание скриншота: {path}")
            self.driver.save_screenshot(path)
            self.logger.info("✅ Скриншот создан")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка создания скриншота: {e}")
            return False
    
    def find_tennis_matches(self) -> List[Dict[str, Any]]:
        """Поиск теннисных матчей на странице"""
        try:
            self.logger.info("🔍 Поиск теннисных матчей...")
            
            # Ждем загрузки контента
            time.sleep(5)
            
            # Получаем HTML
            html_content = self.driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Ищем различные селекторы для матчей
            match_selectors = [
                '.sport-event',
                '.bet-item',
                '.match-item',
                '.game-item',
                '.event-item',
                '[class*="match"]',
                '[class*="game"]',
                '[class*="event"]',
                '[class*="live"]',
                '[class*="tennis"]'
            ]
            
            found_elements = []
            
            for selector in match_selectors:
                elements = soup.select(selector)
                if elements:
                    self.logger.info(f"Найдено {len(elements)} элементов по селектору: {selector}")
                    found_elements.extend(elements)
                    break
            
            # Если не нашли по селекторам, ищем по тексту
            if not found_elements:
                self.logger.info("Поиск матчей по тексту...")
                # Ищем все элементы с текстом, содержащим теннисные термины
                all_elements = soup.find_all(text=re.compile(r'(WTA|ATP|ITF|теннис|tennis|сет|set)', re.IGNORECASE))
                for element in all_elements:
                    parent = element.parent
                    if parent and parent not in found_elements:
                        found_elements.append(parent)
            
            # Парсим найденные элементы
            matches = []
            for element in found_elements[:100]:  # Ограничиваем количество
                try:
                    match_data = self.extract_match_data(element)
                    if match_data:
                        matches.append(match_data)
                except Exception as e:
                    self.logger.warning(f"Ошибка парсинга элемента: {e}")
                    continue
            
            return matches
            
        except Exception as e:
            self.logger.error(f"Ошибка поиска матчей: {e}")
            return []
    
    def extract_match_data(self, element) -> Optional[Dict[str, Any]]:
        """Извлечение данных матча из элемента"""
        try:
            text = element.get_text(strip=True)
            
            # Пропускаем слишком короткие или длинные тексты
            if len(text) < 10 or len(text) > 500:
                return None
            
            # Ищем паттерны теннисных матчей
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
                        
                        # Извлекаем счет
                        score = " ".join(groups[2:]) if len(groups) > 2 else "LIVE"
                        
                        # Проверяем, что это неничейный счет
                        if self.is_non_tie_score(score):
                            return {
                                'player1': player1,
                                'player2': player2,
                                'score': score,
                                'status': 'LIVE',
                                'sport': 'tennis',
                                'source': 'betboom_selenium',
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
                # Если нет паттерна сета, проверяем отдельные цифры
                numbers = re.findall(r'\d+', score)
                if len(numbers) >= 2:
                    # Проверяем, что есть разные числа
                    return len(set(numbers)) > 1
                return False
            
            # Проверяем каждый сет
            for set_score in sets:
                parts = set_score.split('-')
                if len(parts) == 2:
                    try:
                        score1 = int(parts[0])
                        score2 = int(parts[1])
                        
                        # Если счет равный, это ничья
                        if score1 == score2:
                            return False
                        
                        # Если разница меньше 2, это может быть ничья
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
    logger.info("🎾 Начинаем скрапинг теннисных матчей с BetBoom через Selenium")
    
    scraper = SeleniumBetBoomTennisScraper(logger)
    
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
        scraper.take_screenshot("betboom_tennis_selenium.png")
        
        # Получаем содержимое страницы
        content = scraper.get_page_content()
        if not content:
            logger.error("❌ Не удалось получить содержимое страницы")
            return []
        
        logger.info("✅ Содержимое страницы получено")
        
        # Сохраняем HTML для анализа
        with open("betboom_tennis_selenium.html", "w", encoding="utf-8") as f:
            f.write(content)
        logger.info("💾 HTML сохранен в betboom_tennis_selenium.html")
        
        # Ищем матчи
        matches = scraper.find_tennis_matches()
        
        if matches:
            logger.info(f"🎾 Найдено {len(matches)} теннисных матчей")
            
            # Выводим результаты
            print("\n" + "="*100)
            print("🎾 РЕАЛЬНЫЕ ТЕННИСНЫЕ МАТЧИ С BETBOOM (Selenium)")
            print("="*100)
            print(f"📅 Время получения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"🌐 Источник: https://betboom.ru/sport/tennis?type=live")
            print(f"🔧 Метод: Selenium WebDriver")
            print("="*100)
            
            for i, match in enumerate(matches, 1):
                print(f"{i:2d}. {match['player1']} vs {match['player2']}")
                print(f"    Счет: {match['score']} ({match['status']})")
                print(f"    Спорт: {match['sport']} | Источник: {match['source']}")
                print(f"    Raw: {match.get('raw_text', 'N/A')}")
                print()
            
            print(f"✅ Всего найдено: {len(matches)} матчей")
            print("="*100)
        else:
            logger.warning("❌ Теннисные матчи не найдены")
            print("\n❌ Теннисные матчи не найдены на странице")
        
        return matches
    
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