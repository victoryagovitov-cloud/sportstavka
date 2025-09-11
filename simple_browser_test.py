"""
Простой тест получения данных с BetBoom через обычный браузер
Без MCP - используем Selenium для тестирования
"""
import asyncio
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('browser_test')

class SimpleBetBoomScraper:
    """Простой скрапер для BetBoom через Selenium"""
    
    def __init__(self, logger):
        self.logger = logger
        self.driver = None
    
    def setup_driver(self):
        """Настройка Chrome драйвера"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.logger.info("Chrome драйвер настроен")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка настройки драйвера: {e}")
            return False
    
    def close_driver(self):
        """Закрытие драйвера"""
        if self.driver:
            self.driver.quit()
            self.logger.info("Chrome драйвер закрыт")
    
    def scrape_url(self, url):
        """Скрапинг указанного URL"""
        try:
            self.logger.info(f"Переход на {url}")
            self.driver.get(url)
            
            # Ждем загрузки страницы
            time.sleep(5)
            
            # Получаем HTML
            html = self.driver.page_source
            self.logger.info(f"Получен HTML ({len(html)} символов)")
            
            # Парсим данные
            matches = self.parse_html(html, url)
            
            return {
                "success": True,
                "url": url,
                "matches": matches,
                "html_length": len(html)
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка скрапинга {url}: {e}")
            return {
                "success": False,
                "url": url,
                "error": str(e)
            }
    
    def parse_html(self, html, url):
        """Парсинг HTML для извлечения матчей"""
        matches = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Определяем тип спорта по URL
            sport = "football" if "football" in url else "tennis"
            
            # Ищем элементы с матчами
            # Это примерные селекторы - нужно адаптировать под реальную структуру BetBoom
            match_selectors = [
                '.match-item',
                '.game-item', 
                '.event-item',
                '[data-testid*="match"]',
                '[class*="match"]',
                '[class*="game"]',
                '[class*="event"]'
            ]
            
            for selector in match_selectors:
                elements = soup.select(selector)
                if elements:
                    self.logger.info(f"Найдено {len(elements)} элементов по селектору: {selector}")
                    
                    for element in elements[:10]:  # Берем первые 10
                        try:
                            match_data = self.extract_match_data(element, sport)
                            if match_data:
                                matches.append(match_data)
                        except Exception as e:
                            self.logger.warning(f"Ошибка парсинга элемента: {e}")
                            continue
                    break
            
            # Если не нашли по селекторам, попробуем найти по тексту
            if not matches:
                self.logger.info("Поиск матчей по тексту...")
                matches = self.find_matches_by_text(soup, sport)
            
        except Exception as e:
            self.logger.error(f"Ошибка парсинга HTML: {e}")
        
        return matches
    
    def extract_match_data(self, element, sport):
        """Извлечение данных матча из элемента"""
        try:
            # Ищем команды/игроков
            team_elements = element.find_all(['span', 'div', 'a'], class_=lambda x: x and any(
                word in x.lower() for word in ['team', 'player', 'name', 'title']
            ))
            
            if len(team_elements) >= 2:
                team1 = team_elements[0].get_text(strip=True)
                team2 = team_elements[1].get_text(strip=True)
                
                # Ищем счет
                score_elements = element.find_all(['span', 'div'], class_=lambda x: x and any(
                    word in x.lower() for word in ['score', 'result', 'count']
                ))
                score = score_elements[0].get_text(strip=True) if score_elements else "LIVE"
                
                # Ищем время
                time_elements = element.find_all(['span', 'div'], class_=lambda x: x and any(
                    word in x.lower() for word in ['time', 'minute', 'clock']
                ))
                time_str = time_elements[0].get_text(strip=True) if time_elements else "LIVE"
                
                return {
                    'team1': team1,
                    'team2': team2,
                    'score': score,
                    'time': time_str,
                    'sport': sport,
                    'source': 'selenium_betboom'
                }
        
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения данных матча: {e}")
        
        return None
    
    def find_matches_by_text(self, soup, sport):
        """Поиск матчей по тексту (fallback метод)"""
        matches = []
        
        try:
            # Ищем паттерны типа "Команда1 vs Команда2" или "Игрок1 vs Игрок2"
            text = soup.get_text()
            lines = text.split('\\n')
            
            for line in lines:
                line = line.strip()
                if len(line) > 10 and len(line) < 200:  # Разумная длина строки
                    # Проверяем, содержит ли строка паттерн матча
                    if any(word in line.lower() for word in ['vs', 'v', 'против', '-']):
                        # Пытаемся извлечь команды
                        parts = line.split(' vs ')
                        if len(parts) == 2:
                            team1 = parts[0].strip()
                            team2 = parts[1].strip()
                            
                            matches.append({
                                'team1': team1,
                                'team2': team2,
                                'score': 'LIVE',
                                'time': 'LIVE',
                                'sport': sport,
                                'source': 'selenium_betboom_text'
                            })
        
        except Exception as e:
            self.logger.error(f"Ошибка поиска по тексту: {e}")
        
        return matches

def test_betboom_urls():
    """Тестирование URL BetBoom"""
    logger.info("🚀 Начало тестирования BetBoom URLs")
    
    urls_to_test = [
        'https://betboom.ru/sport/football?type=live',
        'https://betboom.ru/sport/tennis?type=live'
    ]
    
    scraper = SimpleBetBoomScraper(logger)
    
    try:
        # Настраиваем драйвер
        if not scraper.setup_driver():
            logger.error("❌ Не удалось настроить Chrome драйвер")
            return
        
        logger.info("✅ Chrome драйвер настроен")
        
        # Тестируем каждый URL
        for url in urls_to_test:
            logger.info(f"\\n🌐 Тестирование: {url}")
            
            result = scraper.scrape_url(url)
            
            if result["success"]:
                matches = result["matches"]
                logger.info(f"✅ Успешно получено {len(matches)} матчей")
                
                # Показываем первые несколько матчей
                for i, match in enumerate(matches[:5]):
                    logger.info(f"  {i+1}. {match['team1']} vs {match['team2']} - {match['score']} ({match['sport']})")
                
                if len(matches) > 5:
                    logger.info(f"  ... и еще {len(matches) - 5} матчей")
            else:
                logger.error(f"❌ Ошибка: {result['error']}")
    
    except Exception as e:
        logger.error(f"❌ Общая ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Закрываем драйвер
        scraper.close_driver()
        logger.info("\\n🔌 Chrome драйвер закрыт")

if __name__ == "__main__":
    test_betboom_urls()