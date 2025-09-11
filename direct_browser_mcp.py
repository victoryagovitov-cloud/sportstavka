"""
Прямой MCP клиент для работы с browser-use
Без использования CLI - напрямую через Python API
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
import json
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('direct_mcp')

class DirectBrowserMCP:
    """Прямой MCP клиент для browser-use"""
    
    def __init__(self, logger):
        self.logger = logger
        self.browser = None
    
    async def connect(self):
        """Подключение к browser-use"""
        try:
            # Импортируем browser-use напрямую
            from browser_use import Browser
            
            self.logger.info("Инициализация browser-use...")
            
            # Создаем экземпляр браузера
            self.browser = Browser()
            await self.browser.start()
            
            self.logger.info("✅ Browser-use подключен успешно")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка подключения к browser-use: {e}")
            return False
    
    async def disconnect(self):
        """Отключение от browser-use"""
        if self.browser:
            try:
                await self.browser.close()
                self.logger.info("Browser-use отключен")
            except Exception as e:
                self.logger.error(f"Ошибка отключения: {e}")
    
    async def navigate_to_url(self, url: str) -> Dict[str, Any]:
        """Навигация на URL"""
        try:
            self.logger.info(f"Переход на {url}")
            
            # Используем browser-use для навигации
            result = await self.browser.navigate(url)
            
            return {
                "success": True,
                "url": url,
                "result": str(result)
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка навигации на {url}: {e}")
            return {
                "success": False,
                "url": url,
                "error": str(e)
            }
    
    async def get_page_content(self) -> Dict[str, Any]:
        """Получение содержимого страницы"""
        try:
            self.logger.info("Получение содержимого страницы...")
            
            # Получаем HTML страницы
            html = await self.browser.get_page_content()
            
            return {
                "success": True,
                "content": html,
                "length": len(html) if html else 0
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка получения контента: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def take_screenshot(self, path: str = "screenshot.png") -> Dict[str, Any]:
        """Создание скриншота"""
        try:
            self.logger.info(f"Создание скриншота: {path}")
            
            # Создаем скриншот
            screenshot_path = await self.browser.take_screenshot(path)
            
            return {
                "success": True,
                "path": screenshot_path
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка создания скриншота: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def find_elements(self, selector: str) -> List[str]:
        """Поиск элементов на странице"""
        try:
            self.logger.info(f"Поиск элементов: {selector}")
            
            # Ищем элементы
            elements = await self.browser.find_elements(selector)
            
            return elements
            
        except Exception as e:
            self.logger.error(f"Ошибка поиска элементов: {e}")
            return []

class DirectBetBoomScraper:
    """Скрапер BetBoom через прямой browser-use"""
    
    def __init__(self, logger):
        self.logger = logger
        self.browser_mcp = DirectBrowserMCP(logger)
        self.base_url = "https://betboom.ru/sport/football?type=live"
    
    async def connect(self):
        """Подключение к browser-use"""
        return await self.browser_mcp.connect()
    
    async def disconnect(self):
        """Отключение от browser-use"""
        await self.browser_mcp.disconnect()
    
    async def get_live_matches(self, sport: str = 'football') -> List[Dict[str, Any]]:
        """Получение live матчей"""
        self.logger.info(f"Получение live матчей для {sport}")
        
        # Формируем URL в зависимости от спорта
        if sport == 'football':
            url = "https://betboom.ru/sport/football?type=live"
        elif sport == 'tennis':
            url = "https://betboom.ru/sport/tennis?type=live"
        else:
            url = f"https://betboom.ru/sport/{sport}?type=live"
        
        try:
            # Переходим на страницу
            nav_result = await self.browser_mcp.navigate_to_url(url)
            if not nav_result["success"]:
                self.logger.error(f"Ошибка навигации: {nav_result['error']}")
                return []
            
            # Ждем загрузки
            await asyncio.sleep(3)
            
            # Получаем содержимое
            content_result = await self.browser_mcp.get_page_content()
            if not content_result["success"]:
                self.logger.error(f"Ошибка получения контента: {content_result['error']}")
                return []
            
            # Парсим матчи
            matches = self.parse_betboom_content(content_result["content"], sport)
            
            self.logger.info(f"Найдено {len(matches)} матчей для {sport}")
            return matches
            
        except Exception as e:
            self.logger.error(f"Ошибка получения матчей: {e}")
            return []
    
    def parse_betboom_content(self, html: str, sport: str) -> List[Dict[str, Any]]:
        """Парсинг содержимого BetBoom"""
        matches = []
        
        try:
            from bs4 import BeautifulSoup
            import re
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Ищем элементы с матчами
            # Это примерные селекторы - нужно адаптировать под реальную структуру
            match_selectors = [
                '.match-item',
                '.game-item',
                '.event-item',
                '[class*="match"]',
                '[class*="game"]',
                '[class*="event"]',
                '[class*="live"]'
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
    
    def extract_match_data(self, element, sport: str) -> Optional[Dict[str, Any]]:
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
                    'source': 'direct_browser_use'
                }
        
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения данных матча: {e}")
        
        return None
    
    def find_matches_by_text(self, soup, sport: str) -> List[Dict[str, Any]]:
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
                                'source': 'direct_browser_use_text'
                            })
        
        except Exception as e:
            self.logger.error(f"Ошибка поиска по тексту: {e}")
        
        return matches

async def test_direct_browser_mcp():
    """Тестирование прямого browser-use MCP"""
    logger.info("🚀 Тестирование прямого browser-use MCP")
    
    urls_to_test = [
        'https://betboom.ru/sport/football?type=live',
        'https://betboom.ru/sport/tennis?type=live'
    ]
    
    scraper = DirectBetBoomScraper(logger)
    
    try:
        # Подключаемся
        if not await scraper.connect():
            logger.error("❌ Не удалось подключиться к browser-use")
            return
        
        logger.info("✅ Подключение успешно")
        
        # Тестируем каждый URL
        for url in urls_to_test:
            logger.info(f"\\n🌐 Тестирование: {url}")
            
            # Определяем спорт по URL
            sport = 'football' if 'football' in url else 'tennis'
            
            matches = await scraper.get_live_matches(sport)
            
            if matches:
                logger.info(f"✅ Найдено {len(matches)} матчей")
                
                # Показываем первые несколько матчей
                for i, match in enumerate(matches[:5]):
                    logger.info(f"  {i+1}. {match['team1']} vs {match['team2']} - {match['score']} ({match['sport']})")
                
                if len(matches) > 5:
                    logger.info(f"  ... и еще {len(matches) - 5} матчей")
            else:
                logger.warning("❌ Матчи не найдены")
    
    except Exception as e:
        logger.error(f"❌ Общая ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Отключаемся
        await scraper.disconnect()
        logger.info("\\n🔌 Отключение завершено")

if __name__ == "__main__":
    asyncio.run(test_direct_browser_mcp())