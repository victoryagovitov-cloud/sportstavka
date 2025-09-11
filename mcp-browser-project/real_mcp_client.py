"""
Реальный MCP клиент для browser-use
"""
import asyncio
import logging
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
from typing import List, Dict, Any, Optional
import json
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('real_mcp_client')

class RealMCPBrowserClient:
    """Реальный MCP клиент для browser-use"""
    
    def __init__(self, logger):
        self.logger = logger
        self.session: Optional[ClientSession] = None
        self.server_params = StdioServerParameters(
            command="python",
            args=["-c", "from browser_use.cli import main; main()", "--mcp"]
        )
    
    async def connect(self):
        """Подключение к MCP серверу"""
        try:
            self.logger.info("🔌 Подключение к реальному MCP серверу browser-use...")
            read, write = await stdio_client(self.server_params).__aenter__()
            self.session = ClientSession(read, write)
            await self.session.initialize()
            self.logger.info("✅ MCP сервер browser-use подключен успешно")
            return True
        except Exception as e:
            self.logger.error(f"❌ Ошибка подключения к MCP серверу: {e}")
            return False
    
    async def disconnect(self):
        """Отключение от MCP сервера"""
        if self.session:
            try:
                await self.session.__aexit__(None, None, None)
                self.session = None
                self.logger.info("🔌 MCP сервер отключен")
            except Exception as e:
                self.logger.error(f"Ошибка отключения: {e}")
    
    async def navigate(self, url: str) -> bool:
        """Навигация на URL"""
        if not self.session:
            self.logger.error("MCP сессия не инициализирована")
            return False
        
        try:
            self.logger.info(f"🌐 Переход на {url}")
            result = await self.session.call_tool("browser_navigate", arguments={"url": url})
            
            if result.content and len(result.content) > 0:
                content = result.content[0]
                if hasattr(content, 'text'):
                    self.logger.info(f"Результат навигации: {content.text}")
                    return "success" in content.text.lower()
                elif isinstance(content, str):
                    self.logger.info(f"Результат навигации: {content}")
                    return "success" in content.lower()
            
            return False
        except Exception as e:
            self.logger.error(f"Ошибка навигации: {e}")
            return False
    
    async def get_content(self) -> Optional[str]:
        """Получение содержимого страницы"""
        if not self.session:
            self.logger.error("MCP сессия не инициализирована")
            return None
        
        try:
            self.logger.info("📄 Получение содержимого страницы...")
            result = await self.session.call_tool("browser_get_content", arguments={})
            
            if result.content and len(result.content) > 0:
                content = result.content[0]
                if hasattr(content, 'text'):
                    self.logger.info(f"Получено {len(content.text)} символов")
                    return content.text
                elif isinstance(content, str):
                    self.logger.info(f"Получено {len(content)} символов")
                    return content
            
            return None
        except Exception as e:
            self.logger.error(f"Ошибка получения контента: {e}")
            return None
    
    async def take_screenshot(self, path: str = "screenshot.png") -> bool:
        """Создание скриншота"""
        if not self.session:
            self.logger.error("MCP сессия не инициализирована")
            return False
        
        try:
            self.logger.info(f"📸 Создание скриншота: {path}")
            result = await self.session.call_tool("browser_take_screenshot", arguments={"path": path})
            
            if result.content and len(result.content) > 0:
                content = result.content[0]
                if hasattr(content, 'text'):
                    return "success" in content.text.lower()
                elif isinstance(content, str):
                    return "success" in content.lower()
            
            return False
        except Exception as e:
            self.logger.error(f"Ошибка создания скриншота: {e}")
            return False
    
    async def find_elements(self, selector: str) -> List[str]:
        """Поиск элементов на странице"""
        if not self.session:
            self.logger.error("MCP сессия не инициализирована")
            return []
        
        try:
            self.logger.info(f"🔍 Поиск элементов: {selector}")
            result = await self.session.call_tool("browser_find_elements", arguments={"selector": selector})
            
            elements = []
            if result.content:
                for item in result.content:
                    if hasattr(item, 'text'):
                        elements.append(item.text)
                    elif isinstance(item, str):
                        elements.append(item)
            
            return elements
        except Exception as e:
            self.logger.error(f"Ошибка поиска элементов: {e}")
            return []

class RealBetBoomScraper:
    """Реальный скрапер BetBoom через MCP Browser"""
    
    def __init__(self, logger):
        self.logger = logger
        self.mcp_client = RealMCPBrowserClient(logger)
    
    async def connect(self):
        """Подключение к MCP серверу"""
        return await self.mcp_client.connect()
    
    async def disconnect(self):
        """Отключение от MCP сервера"""
        await self.mcp_client.disconnect()
    
    async def get_live_matches(self, sport: str = 'football') -> List[Dict[str, Any]]:
        """Получение live матчей"""
        self.logger.info(f"⚽ Получение live матчей для {sport}")
        
        # Формируем URL в зависимости от спорта
        if sport == 'football':
            url = "https://betboom.ru/sport/football?type=live"
        elif sport == 'tennis':
            url = "https://betboom.ru/sport/tennis?type=live"
        else:
            url = f"https://betboom.ru/sport/{sport}?type=live"
        
        try:
            # Переходим на страницу
            if not await self.mcp_client.navigate(url):
                self.logger.error(f"❌ Ошибка навигации на {url}")
                return []
            
            # Ждем загрузки
            await asyncio.sleep(5)
            
            # Получаем содержимое
            content = await self.mcp_client.get_content()
            if not content:
                self.logger.error("❌ Не удалось получить содержимое страницы")
                return []
            
            # Парсим матчи
            matches = self.parse_betboom_content(content, sport)
            
            self.logger.info(f"✅ Найдено {len(matches)} матчей для {sport}")
            return matches
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения матчей: {e}")
            return []
    
    def parse_betboom_content(self, html: str, sport: str) -> List[Dict[str, Any]]:
        """Парсинг содержимого BetBoom"""
        matches = []
        
        try:
            from bs4 import BeautifulSoup
            import re
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Ищем элементы с матчами
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
                    'source': 'real_mcp_browser_use'
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
            lines = text.split('\n')
            
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
                                'source': 'real_mcp_browser_use_text'
                            })
        
        except Exception as e:
            self.logger.error(f"Ошибка поиска по тексту: {e}")
        
        return matches

async def test_real_mcp_browser():
    """Тестирование реального MCP Browser для BetBoom"""
    logger.info("🚀 Тестирование реального MCP Browser для BetBoom")
    
    urls_to_test = [
        ('https://betboom.ru/sport/football?type=live', 'football'),
        ('https://betboom.ru/sport/tennis?type=live', 'tennis')
    ]
    
    scraper = RealBetBoomScraper(logger)
    
    try:
        # Подключаемся к MCP серверу
        if not await scraper.connect():
            logger.error("❌ Не удалось подключиться к MCP серверу")
            return
        
        logger.info("✅ MCP сервер подключен успешно")
        
        # Тестируем каждый URL
        for url, sport in urls_to_test:
            logger.info(f"\n🌐 Тестирование: {url} ({sport})")
            
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
        
        # Создаем скриншот для проверки
        logger.info("\n📸 Создание скриншота...")
        if await scraper.mcp_client.take_screenshot("betboom_real_screenshot.png"):
            logger.info("✅ Скриншот создан: betboom_real_screenshot.png")
        else:
            logger.warning("❌ Не удалось создать скриншот")
    
    except Exception as e:
        logger.error(f"❌ Общая ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Отключаемся
        await scraper.disconnect()
        logger.info("\n🔌 Отключение завершено")

if __name__ == "__main__":
    asyncio.run(test_real_mcp_browser())