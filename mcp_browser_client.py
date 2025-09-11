"""
MCP Browser Client для автоматизации вызовов Browser MCP из Python
Использует официальный MCP Python SDK для подключения к browser-use MCP серверу
"""
import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters

class MCPBrowserClient:
    """
    Клиент для работы с Browser MCP через официальный Python SDK
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.session: Optional[ClientSession] = None
        self.read = None
        self.write = None
        
    async def connect(self):
        """Подключение к MCP серверу browser-use"""
        try:
            self.logger.info("MCP Browser: подключение к серверу")
            
            # Параметры для подключения к browser-use MCP серверу
            server_params = StdioServerParameters(
                command="uvx",
                args=["browser-use", "--mcp"]
            )
            
            # Устанавливаем соединение
            self.read, self.write = await stdio_client(server_params)
            self.session = ClientSession(self.read, self.write)
            
            # Инициализируем сессию
            await self.session.initialize()
            
            self.logger.info("MCP Browser: успешно подключен")
            return True
            
        except Exception as e:
            self.logger.error(f"MCP Browser: ошибка подключения - {e}")
            return False
    
    async def disconnect(self):
        """Отключение от MCP сервера"""
        try:
            if self.session:
                await self.session.close()
            if self.read:
                self.read.close()
            if self.write:
                self.write.close()
            self.logger.info("MCP Browser: отключен")
        except Exception as e:
            self.logger.error(f"MCP Browser: ошибка отключения - {e}")
    
    async def navigate_to_url(self, url: str) -> Dict[str, Any]:
        """Переход на указанный URL"""
        try:
            self.logger.info(f"MCP Browser: переход на {url}")
            
            result = await self.session.call_tool(
                "browser_navigate", 
                arguments={"url": url}
            )
            
            return {
                "success": True,
                "url": url,
                "content": result.content[0].text if result.content else "",
                "metadata": result.metadata
            }
            
        except Exception as e:
            self.logger.error(f"MCP Browser: ошибка навигации - {e}")
            return {"success": False, "error": str(e)}
    
    async def take_screenshot(self) -> Dict[str, Any]:
        """Создание скриншота текущей страницы"""
        try:
            self.logger.info("MCP Browser: создание скриншота")
            
            result = await self.session.call_tool(
                "browser_take_screenshot", 
                arguments={}
            )
            
            return {
                "success": True,
                "screenshot": result.content[0].text if result.content else "",
                "metadata": result.metadata
            }
            
        except Exception as e:
            self.logger.error(f"MCP Browser: ошибка скриншота - {e}")
            return {"success": False, "error": str(e)}
    
    async def get_page_content(self) -> Dict[str, Any]:
        """Получение содержимого текущей страницы"""
        try:
            self.logger.info("MCP Browser: получение содержимого страницы")
            
            result = await self.session.call_tool(
                "browser_get_content", 
                arguments={}
            )
            
            return {
                "success": True,
                "content": result.content[0].text if result.content else "",
                "metadata": result.metadata
            }
            
        except Exception as e:
            self.logger.error(f"MCP Browser: ошибка получения контента - {e}")
            return {"success": False, "error": str(e)}
    
    async def find_elements(self, selector: str) -> Dict[str, Any]:
        """Поиск элементов на странице по селектору"""
        try:
            self.logger.info(f"MCP Browser: поиск элементов по селектору {selector}")
            
            result = await self.session.call_tool(
                "browser_find_elements", 
                arguments={"selector": selector}
            )
            
            return {
                "success": True,
                "elements": result.content[0].text if result.content else "",
                "count": len(result.content) if result.content else 0,
                "metadata": result.metadata
            }
            
        except Exception as e:
            self.logger.error(f"MCP Browser: ошибка поиска элементов - {e}")
            return {"success": False, "error": str(e)}
    
    async def click_element(self, selector: str) -> Dict[str, Any]:
        """Клик по элементу"""
        try:
            self.logger.info(f"MCP Browser: клик по элементу {selector}")
            
            result = await self.session.call_tool(
                "browser_click", 
                arguments={"selector": selector}
            )
            
            return {
                "success": True,
                "result": result.content[0].text if result.content else "",
                "metadata": result.metadata
            }
            
        except Exception as e:
            self.logger.error(f"MCP Browser: ошибка клика - {e}")
            return {"success": False, "error": str(e)}
    
    async def type_text(self, selector: str, text: str) -> Dict[str, Any]:
        """Ввод текста в поле"""
        try:
            self.logger.info(f"MCP Browser: ввод текста в {selector}")
            
            result = await self.session.call_tool(
                "browser_type", 
                arguments={"selector": selector, "text": text}
            )
            
            return {
                "success": True,
                "result": result.content[0].text if result.content else "",
                "metadata": result.metadata
            }
            
        except Exception as e:
            self.logger.error(f"MCP Browser: ошибка ввода текста - {e}")
            return {"success": False, "error": str(e)}

class MCPBetBoomScraper:
    """
    Специализированный скрапер для BetBoom.ru через MCP Browser
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.mcp_client = MCPBrowserClient(logger)
        self.connected = False
    
    async def connect(self):
        """Подключение к MCP серверу"""
        self.connected = await self.mcp_client.connect()
        return self.connected
    
    async def disconnect(self):
        """Отключение от MCP сервера"""
        await self.mcp_client.disconnect()
        self.connected = False
    
    async def get_live_matches(self, sport: str = 'football') -> List[Dict[str, Any]]:
        """
        Получение live матчей с BetBoom.ru через MCP Browser
        """
        if not self.connected:
            if not await self.connect():
                self.logger.error("MCP BetBoom: не удалось подключиться")
                return []
        
        try:
            self.logger.info(f"MCP BetBoom: получение live {sport}")
            
            # URL для live матчей BetBoom
            url = "https://betboom.ru/live"
            
            # Переходим на страницу
            nav_result = await self.mcp_client.navigate_to_url(url)
            if not nav_result["success"]:
                self.logger.error(f"MCP BetBoom: ошибка навигации - {nav_result['error']}")
                return []
            
            # Ждем загрузки страницы
            await asyncio.sleep(3)
            
            # Получаем содержимое страницы
            content_result = await self.mcp_client.get_page_content()
            if not content_result["success"]:
                self.logger.error(f"MCP BetBoom: ошибка получения контента - {content_result['error']}")
                return []
            
            # Парсим данные матчей
            matches = self.parse_betboom_content(content_result["content"])
            
            self.logger.info(f"MCP BetBoom: получено {len(matches)} матчей")
            return matches
            
        except Exception as e:
            self.logger.error(f"MCP BetBoom: ошибка получения матчей - {e}")
            return []
    
    def parse_betboom_content(self, content: str) -> List[Dict[str, Any]]:
        """
        Парсинг содержимого страницы BetBoom для извлечения матчей
        """
        matches = []
        
        try:
            # Здесь нужно реализовать парсинг HTML контента
            # Это зависит от структуры страницы BetBoom
            
            # Пример базового парсинга (нужно адаптировать под реальную структуру)
            import re
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Ищем элементы с матчами (нужно адаптировать селекторы)
            match_elements = soup.find_all(['div', 'tr'], class_=re.compile(r'match|game|event'))
            
            for element in match_elements:
                try:
                    # Извлекаем данные матча
                    team1_elem = element.find(['span', 'div'], class_=re.compile(r'team1|home'))
                    team2_elem = element.find(['span', 'div'], class_=re.compile(r'team2|away'))
                    score_elem = element.find(['span', 'div'], class_=re.compile(r'score|result'))
                    time_elem = element.find(['span', 'div'], class_=re.compile(r'time|minute'))
                    
                    if team1_elem and team2_elem:
                        match_data = {
                            'team1': team1_elem.get_text(strip=True),
                            'team2': team2_elem.get_text(strip=True),
                            'score': score_elem.get_text(strip=True) if score_elem else 'LIVE',
                            'time': time_elem.get_text(strip=True) if time_elem else 'LIVE',
                            'source': 'mcp_betboom',
                            'sport': 'football'
                        }
                        matches.append(match_data)
                        
                except Exception as e:
                    self.logger.warning(f"MCP BetBoom: ошибка парсинга элемента - {e}")
                    continue
            
        except Exception as e:
            self.logger.error(f"MCP BetBoom: ошибка парсинга контента - {e}")
        
        return matches

# Пример использования
async def test_mcp_browser():
    """Тестовая функция для проверки работы MCP Browser"""
    import logging
    
    # Настройка логирования
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('test')
    
    # Создаем скрапер
    scraper = MCPBetBoomScraper(logger)
    
    try:
        # Подключаемся
        if await scraper.connect():
            # Получаем матчи
            matches = await scraper.get_live_matches()
            print(f"Получено {len(matches)} матчей:")
            for match in matches:
                print(f"  {match['team1']} vs {match['team2']} - {match['score']}")
        else:
            print("Не удалось подключиться к MCP серверу")
    
    finally:
        # Отключаемся
        await scraper.disconnect()

if __name__ == "__main__":
    # Запуск теста
    asyncio.run(test_mcp_browser())