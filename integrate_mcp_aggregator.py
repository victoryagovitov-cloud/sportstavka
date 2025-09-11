"""
Интеграция MCP Browser в существующий мульти-источник агрегатор
"""
import asyncio
import logging
from typing import List, Dict, Any
from mcp_browser_client import MCPBetBoomScraper

class MCPMultiSourceAggregator:
    """
    Расширенный мульти-источник агрегатор с поддержкой MCP Browser
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        
        # Инициализируем MCP скраперы
        self.mcp_scrapers = {
            'mcp_betboom': MCPBetBoomScraper(logger),
            # Можно добавить другие MCP скраперы
        }
        
        # Статус подключений
        self.connections_status = {}
    
    async def initialize_mcp_connections(self):
        """Инициализация всех MCP подключений"""
        self.logger.info("MCP Агрегатор: инициализация подключений")
        
        for name, scraper in self.mcp_scrapers.items():
            try:
                connected = await scraper.connect()
                self.connections_status[name] = connected
                
                if connected:
                    self.logger.info(f"MCP Агрегатор: {name} подключен")
                else:
                    self.logger.warning(f"MCP Агрегатор: {name} не подключен")
                    
            except Exception as e:
                self.logger.error(f"MCP Агрегатор: ошибка подключения {name} - {e}")
                self.connections_status[name] = False
    
    async def close_mcp_connections(self):
        """Закрытие всех MCP подключений"""
        self.logger.info("MCP Агрегатор: закрытие подключений")
        
        for name, scraper in self.mcp_scrapers.items():
            try:
                await scraper.disconnect()
                self.logger.info(f"MCP Агрегатор: {name} отключен")
            except Exception as e:
                self.logger.error(f"MCP Агрегатор: ошибка отключения {name} - {e}")
    
    async def get_mcp_matches(self, sport: str = 'football') -> Dict[str, List[Dict[str, Any]]]:
        """
        Получение матчей от всех MCP источников
        """
        all_matches = {}
        
        for name, scraper in self.mcp_scrapers.items():
            if self.connections_status.get(name, False):
                try:
                    self.logger.info(f"MCP Агрегатор: получение данных от {name}")
                    matches = await scraper.get_live_matches(sport)
                    all_matches[name] = matches
                    self.logger.info(f"MCP Агрегатор: {name} вернул {len(matches)} матчей")
                    
                except Exception as e:
                    self.logger.error(f"MCP Агрегатор: ошибка получения от {name} - {e}")
                    all_matches[name] = []
            else:
                self.logger.warning(f"MCP Агрегатор: {name} недоступен")
                all_matches[name] = []
        
        return all_matches
    
    async def get_aggregated_matches(self, sport: str = 'football') -> List[Dict[str, Any]]:
        """
        Получение агрегированных матчей от всех источников включая MCP
        """
        try:
            self.logger.info(f"MCP Агрегатор: сбор данных для {sport}")
            
            # Получаем данные от MCP источников
            mcp_matches = await self.get_mcp_matches(sport)
            
            # Объединяем все матчи
            all_matches = []
            for source, matches in mcp_matches.items():
                all_matches.extend(matches)
            
            # Дедуплицируем матчи
            unique_matches = self.deduplicate_matches(all_matches)
            
            self.logger.info(f"MCP Агрегатор: получено {len(unique_matches)} уникальных матчей")
            return unique_matches
            
        except Exception as e:
            self.logger.error(f"MCP Агрегатор: ошибка получения матчей - {e}")
            return []
    
    def deduplicate_matches(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Дедупликация матчей по командам и времени
        """
        seen = set()
        unique_matches = []
        
        for match in matches:
            # Создаем ключ для дедупликации
            key = (
                match.get('team1', '').lower(),
                match.get('team2', '').lower(),
                match.get('time', '')
            )
            
            if key not in seen:
                seen.add(key)
                unique_matches.append(match)
        
        return unique_matches

# Пример использования
async def test_mcp_aggregator():
    """Тестовая функция для проверки MCP агрегатора"""
    import logging
    
    # Настройка логирования
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('test')
    
    # Создаем агрегатор
    aggregator = MCPMultiSourceAggregator(logger)
    
    try:
        # Инициализируем подключения
        await aggregator.initialize_mcp_connections()
        
        # Получаем матчи
        matches = await aggregator.get_aggregated_matches('football')
        
        print(f"Получено {len(matches)} матчей:")
        for match in matches:
            print(f"  {match['team1']} vs {match['team2']} - {match['score']} ({match['source']})")
    
    finally:
        # Закрываем подключения
        await aggregator.close_mcp_connections()

if __name__ == "__main__":
    # Запуск теста
    asyncio.run(test_mcp_aggregator())