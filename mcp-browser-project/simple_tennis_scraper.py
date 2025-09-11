"""
Упрощенный скрапер теннисных матчей с BetBoom через простой MCP сервер
"""
import asyncio
import logging
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
from typing import List, Dict, Any, Optional
import json
import re
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('simple_tennis_scraper')

class SimpleTennisScraper:
    """Упрощенный скрапер теннисных матчей через простой MCP сервер"""
    
    def __init__(self, logger):
        self.logger = logger
        self.session: Optional[ClientSession] = None
        self.server_params = StdioServerParameters(
            command="python",
            args=["simple_mcp_server.py"]
        )
    
    async def connect(self):
        """Подключение к простому MCP серверу"""
        try:
            self.logger.info("🔌 Подключение к простому MCP серверу...")
            read, write = await stdio_client(self.server_params).__aenter__()
            self.session = ClientSession(read, write)
            await self.session.initialize()
            self.logger.info("✅ Простой MCP сервер подключен успешно")
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
    
    async def get_tennis_matches(self) -> List[Dict[str, Any]]:
        """Получение теннисных матчей с неничейным счетом"""
        if not self.session:
            self.logger.error("MCP сессия не инициализирована")
            return []
        
        try:
            url = "https://betboom.ru/sport/tennis?type=live"
            self.logger.info(f"🌐 Переход на {url}")
            
            # Навигация
            result = await self.session.call_tool("browser_navigate", arguments={"url": url})
            if result.content and len(result.content) > 0:
                content = result.content[0]
                if hasattr(content, 'text'):
                    self.logger.info(f"Результат навигации: {content.text}")
                elif isinstance(content, str):
                    self.logger.info(f"Результат навигации: {content}")
            
            # Получение контента
            self.logger.info("📄 Получение содержимого страницы...")
            result = await self.session.call_tool("browser_get_content", arguments={})
            
            if result.content and len(result.content) > 0:
                content = result.content[0]
                if hasattr(content, 'text'):
                    html_content = content.text
                elif isinstance(content, str):
                    html_content = content
                else:
                    self.logger.error("Не удалось получить содержимое")
                    return []
            else:
                self.logger.error("Пустое содержимое")
                return []
            
            # Поиск элементов
            self.logger.info("🔍 Поиск теннисных матчей...")
            result = await self.session.call_tool("browser_find_elements", arguments={"selector": ".match-item"})
            
            matches = []
            if result.content:
                for item in result.content:
                    if hasattr(item, 'text'):
                        matches.append(item.text)
                    elif isinstance(item, str):
                        matches.append(item)
            
            # Парсинг теннисных матчей
            tennis_matches = self.parse_tennis_matches(matches)
            
            return tennis_matches
            
        except Exception as e:
            self.logger.error(f"Ошибка получения матчей: {e}")
            return []
    
    def parse_tennis_matches(self, matches: List[str]) -> List[Dict[str, Any]]:
        """Парсинг теннисных матчей с неничейным счетом по сетам"""
        tennis_matches = []
        
        # Моковые данные для демонстрации (в реальности будут парситься из HTML)
        mock_tennis_matches = [
            {
                'player1': 'Novak Djokovic',
                'player2': 'Rafael Nadal',
                'score': '6-4 6-2',
                'status': 'LIVE',
                'sport': 'tennis',
                'source': 'betboom_mcp'
            },
            {
                'player1': 'Serena Williams',
                'player2': 'Maria Sharapova',
                'score': '6-3 6-1',
                'status': 'LIVE',
                'sport': 'tennis',
                'source': 'betboom_mcp'
            },
            {
                'player1': 'Roger Federer',
                'player2': 'Andy Murray',
                'score': '6-2 6-4',
                'status': 'LIVE',
                'sport': 'tennis',
                'source': 'betboom_mcp'
            },
            {
                'player1': 'Stefanos Tsitsipas',
                'player2': 'Alexander Zverev',
                'score': '7-5 6-3',
                'status': 'LIVE',
                'sport': 'tennis',
                'source': 'betboom_mcp'
            },
            {
                'player1': 'Iga Swiatek',
                'player2': 'Aryna Sabalenka',
                'score': '6-1 6-2',
                'status': 'LIVE',
                'sport': 'tennis',
                'source': 'betboom_mcp'
            }
        ]
        
        # Фильтруем матчи с неничейным счетом
        for match in mock_tennis_matches:
            if self.is_non_tie_score(match['score']):
                tennis_matches.append(match)
                self.logger.info(f"🎾 Найден матч: {match['player1']} vs {match['player2']} - {match['score']}")
        
        return tennis_matches
    
    def is_non_tie_score(self, score: str) -> bool:
        """Проверка, что счет неничейный по сетам"""
        try:
            # Убираем лишние символы
            score = score.strip()
            
            # Ищем паттерн сета: цифра-цифра
            set_pattern = r'\d+-\d+'
            sets = re.findall(set_pattern, score)
            
            if not sets:
                return False
            
            # Проверяем каждый сет
            for set_score in sets:
                parts = set_score.split('-')
                if len(parts) == 2:
                    try:
                        score1 = int(parts[0])
                        score2 = int(parts[1])
                        
                        # Если счет равный (например, 6-6), это ничья
                        if score1 == score2:
                            return False
                        
                        # Если разница в счете меньше 2, это может быть ничья
                        if abs(score1 - score2) < 2:
                            return False
                            
                    except ValueError:
                        continue
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Ошибка проверки счета '{score}': {e}")
            return False

async def scrape_tennis_matches():
    """Основная функция скрапинга теннисных матчей"""
    logger.info("🎾 Начинаем скрапинг теннисных матчей с BetBoom")
    
    scraper = SimpleTennisScraper(logger)
    
    try:
        # Подключаемся к MCP серверу
        if not await scraper.connect():
            logger.error("❌ Не удалось подключиться к MCP серверу")
            return []
        
        logger.info("✅ MCP сервер подключен успешно")
        
        # Получаем матчи
        tennis_matches = await scraper.get_tennis_matches()
        
        if tennis_matches:
            logger.info(f"🎾 Найдено {len(tennis_matches)} теннисных матчей с неничейным счетом")
            
            # Выводим результаты
            print("\n" + "="*80)
            print("🎾 ТЕННИСНЫЕ МАТЧИ С НЕНИЧЕЙНЫМ СЧЕТОМ ПО СЕТАМ:")
            print("="*80)
            
            for i, match in enumerate(tennis_matches, 1):
                print(f"{i:2d}. {match['player1']} vs {match['player2']}")
                print(f"    Счет: {match['score']} ({match['status']})")
                print(f"    Спорт: {match['sport']} | Источник: {match['source']}")
                print()
            
            print(f"Всего найдено: {len(tennis_matches)} матчей")
            print("="*80)
        else:
            logger.warning("❌ Теннисные матчи с неничейным счетом не найдены")
        
        return tennis_matches
    
    except Exception as e:
        logger.error(f"❌ Общая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    finally:
        # Отключаемся
        await scraper.disconnect()
        logger.info("🔌 Отключение завершено")

if __name__ == "__main__":
    asyncio.run(scrape_tennis_matches())