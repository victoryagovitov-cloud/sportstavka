"""
Простой MCP сервер для browser-use
"""
import asyncio
import json
import sys
from typing import Any, Dict, List
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('simple_mcp_server')

# Создаем MCP сервер
server = Server("simple-browser-server")

@server.list_tools()
async def list_tools() -> List[Tool]:
    """Список доступных инструментов"""
    return [
        Tool(
            name="browser_navigate",
            description="Навигация на URL",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL для навигации"
                    }
                },
                "required": ["url"]
            }
        ),
        Tool(
            name="browser_get_content",
            description="Получение содержимого страницы",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="browser_take_screenshot",
            description="Создание скриншота",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Путь для сохранения скриншота"
                    }
                }
            }
        ),
        Tool(
            name="browser_find_elements",
            description="Поиск элементов на странице",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "CSS селектор для поиска"
                    }
                },
                "required": ["selector"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Обработка вызовов инструментов"""
    logger.info(f"Вызов инструмента: {name} с аргументами: {arguments}")
    
    if name == "browser_navigate":
        url = arguments.get("url", "")
        logger.info(f"Навигация на {url}")
        return [TextContent(type="text", text="success")]
    
    elif name == "browser_get_content":
        logger.info("Получение содержимого страницы")
        # Возвращаем пример HTML
        html_content = """
        <html>
        <body>
            <div class="match-item">
                <span class="team-name">Real Madrid</span>
                <span class="vs">vs</span>
                <span class="team-name">Barcelona</span>
                <span class="score">2-1</span>
                <span class="time">LIVE</span>
            </div>
            <div class="match-item">
                <span class="team-name">Manchester United</span>
                <span class="vs">vs</span>
                <span class="team-name">Liverpool</span>
                <span class="score">1-0</span>
                <span class="time">LIVE</span>
            </div>
        </body>
        </html>
        """
        return [TextContent(type="text", text=html_content)]
    
    elif name == "browser_take_screenshot":
        path = arguments.get("path", "screenshot.png")
        logger.info(f"Создание скриншота: {path}")
        return [TextContent(type="text", text="success")]
    
    elif name == "browser_find_elements":
        selector = arguments.get("selector", "")
        logger.info(f"Поиск элементов: {selector}")
        # Возвращаем пример найденных элементов
        elements = [
            "Real Madrid vs Barcelona - 2-1 (LIVE)",
            "Manchester United vs Liverpool - 1-0 (LIVE)"
        ]
        return [TextContent(type="text", text=json.dumps(elements))]
    
    else:
        logger.warning(f"Неизвестный инструмент: {name}")
        return [TextContent(type="text", text="error: unknown tool")]

async def main():
    """Главная функция сервера"""
    logger.info("🚀 Запуск простого MCP сервера...")
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())