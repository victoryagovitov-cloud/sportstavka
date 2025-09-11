"""
Простой тест MCP Browser системы
"""
import asyncio
import logging
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('simple_test')

async def test_mcp_connection():
    """Простой тест подключения к MCP серверу"""
    logger.info("🚀 Тестирование MCP подключения")
    
    server_params = StdioServerParameters(
        command="python",
        args=["simple_mcp_server.py"]
    )
    
    try:
        logger.info("🔌 Подключение к MCP серверу...")
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                logger.info("✅ MCP сервер подключен успешно")
                
                # Тестируем навигацию
                logger.info("🌐 Тестирование навигации...")
                result = await session.call_tool("browser_navigate", arguments={"url": "https://betboom.ru/sport/football?type=live"})
                logger.info(f"Результат навигации: {result}")
                
                # Тестируем получение контента
                logger.info("📄 Тестирование получения контента...")
                result = await session.call_tool("browser_get_content", arguments={})
                logger.info(f"Результат получения контента: {result}")
                
                # Тестируем поиск элементов
                logger.info("🔍 Тестирование поиска элементов...")
                result = await session.call_tool("browser_find_elements", arguments={"selector": ".match-item"})
                logger.info(f"Результат поиска элементов: {result}")
                
                logger.info("✅ Все тесты прошли успешно!")
                
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp_connection())