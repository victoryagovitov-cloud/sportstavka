"""
Скрапер теннисных матчей с BetBoom через MCP Browser
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
logger = logging.getLogger('betboom_tennis_scraper')

class BetBoomTennisScraper:
    """Скрапер теннисных матчей с BetBoom через MCP Browser"""
    
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
            self.logger.info("🔌 Подключение к MCP серверу browser-use...")
            read, write = await stdio_client(self.server_params).__aenter__()
            self.session = ClientSession(read, write)
            await self.session.initialize()
            self.logger.info("✅ MCP сервер подключен успешно")
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
    
    async def navigate_to_tennis(self) -> bool:
        """Переход на страницу тенниса"""
        if not self.session:
            self.logger.error("MCP сессия не инициализирована")
            return False
        
        try:
            url = "https://betboom.ru/sport/tennis?type=live"
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
    
    async def get_page_content(self) -> Optional[str]:
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
    
    async def find_tennis_matches(self) -> List[str]:
        """Поиск теннисных матчей на странице"""
        if not self.session:
            self.logger.error("MCP сессия не инициализирована")
            return []
        
        try:
            # Пробуем разные селекторы для поиска матчей
            selectors = [
                ".match-item",
                ".game-item", 
                ".event-item",
                "[class*='match']",
                "[class*='game']",
                "[class*='event']",
                "[class*='live']",
                ".sport-event",
                ".bet-item"
            ]
            
            all_matches = []
            
            for selector in selectors:
                try:
                    self.logger.info(f"🔍 Поиск элементов: {selector}")
                    result = await self.session.call_tool("browser_find_elements", arguments={"selector": selector})
                    
                    if result.content:
                        for item in result.content:
                            if hasattr(item, 'text') and item.text:
                                all_matches.append(item.text)
                            elif isinstance(item, str) and item:
                                all_matches.append(item)
                    
                    if all_matches:
                        self.logger.info(f"✅ Найдено {len(all_matches)} элементов по селектору: {selector}")
                        break
                        
                except Exception as e:
                    self.logger.warning(f"Ошибка поиска по селектору {selector}: {e}")
                    continue
            
            return all_matches
            
        except Exception as e:
            self.logger.error(f"Ошибка поиска матчей: {e}")
            return []
    
    def parse_tennis_matches(self, matches: List[str]) -> List[Dict[str, Any]]:
        """Парсинг теннисных матчей с неничейным счетом по сетам"""
        tennis_matches = []
        
        for match_text in matches:
            try:
                # Ищем паттерны теннисных матчей
                # Формат: "Игрок1 vs Игрок2 - 6-4 6-2 (LIVE)" или "Игрок1 - Игрок2 6-4 6-2"
                
                # Различные паттерны для поиска теннисных матчей
                patterns = [
                    r'([A-Za-zА-Яа-я\s]+)\s+vs\s+([A-Za-zА-Яа-я\s]+)\s*[-–]\s*(\d+-\d+(?:\s+\d+-\d+)*)',
                    r'([A-Za-zА-Яа-я\s]+)\s*[-–]\s*([A-Za-zА-Яа-я\s]+)\s+(\d+-\d+(?:\s+\d+-\d+)*)',
                    r'([A-Za-zА-Яа-я\s]+)\s+([A-Za-zА-Яа-я\s]+)\s+(\d+-\d+(?:\s+\d+-\d+)*)'
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, match_text, re.IGNORECASE)
                    if match:
                        player1 = match.group(1).strip()
                        player2 = match.group(2).strip()
                        score = match.group(3).strip()
                        
                        # Проверяем, что это неничейный счет по сетам
                        if self.is_non_tie_score(score):
                            tennis_matches.append({
                                'player1': player1,
                                'player2': player2,
                                'score': score,
                                'status': 'LIVE',
                                'sport': 'tennis',
                                'source': 'betboom_mcp'
                            })
                            self.logger.info(f"🎾 Найден матч: {player1} vs {player2} - {score}")
                        break
                
                # Дополнительный поиск по ключевым словам
                if any(word in match_text.lower() for word in ['tennis', 'теннис', 'set', 'сет']):
                    # Пытаемся извлечь данные из текста
                    parts = match_text.split(' - ')
                    if len(parts) >= 2:
                        players_part = parts[0]
                        score_part = parts[1]
                        
                        # Ищем игроков
                        if ' vs ' in players_part:
                            players = players_part.split(' vs ')
                        elif ' - ' in players_part:
                            players = players_part.split(' - ')
                        else:
                            continue
                        
                        if len(players) == 2:
                            player1 = players[0].strip()
                            player2 = players[1].strip()
                            
                            # Ищем счет в формате 6-4 6-2
                            score_match = re.search(r'(\d+-\d+(?:\s+\d+-\d+)*)', score_part)
                            if score_match:
                                score = score_match.group(1)
                                if self.is_non_tie_score(score):
                                    tennis_matches.append({
                                        'player1': player1,
                                        'player2': player2,
                                        'score': score,
                                        'status': 'LIVE',
                                        'sport': 'tennis',
                                        'source': 'betboom_mcp'
                                    })
                                    self.logger.info(f"🎾 Найден матч: {player1} vs {player2} - {score}")
            
            except Exception as e:
                self.logger.warning(f"Ошибка парсинга матча '{match_text}': {e}")
                continue
        
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
    
    scraper = BetBoomTennisScraper(logger)
    
    try:
        # Подключаемся к MCP серверу
        if not await scraper.connect():
            logger.error("❌ Не удалось подключиться к MCP серверу")
            return []
        
        logger.info("✅ MCP сервер подключен успешно")
        
        # Переходим на страницу тенниса
        if not await scraper.navigate_to_tennis():
            logger.error("❌ Не удалось перейти на страницу тенниса")
            return []
        
        logger.info("✅ Успешно перешли на страницу тенниса")
        
        # Ждем загрузки страницы
        await asyncio.sleep(5)
        
        # Получаем содержимое страницы
        content = await scraper.get_page_content()
        if not content:
            logger.error("❌ Не удалось получить содержимое страницы")
            return []
        
        logger.info("✅ Содержимое страницы получено")
        
        # Ищем матчи
        matches = await scraper.find_tennis_matches()
        if not matches:
            logger.warning("❌ Матчи не найдены")
            return []
        
        logger.info(f"✅ Найдено {len(matches)} элементов на странице")
        
        # Парсим теннисные матчи
        tennis_matches = scraper.parse_tennis_matches(matches)
        
        if tennis_matches:
            logger.info(f"🎾 Найдено {len(tennis_matches)} теннисных матчей с неничейным счетом")
            
            # Выводим результаты
            for i, match in enumerate(tennis_matches, 1):
                logger.info(f"  {i}. {match['player1']} vs {match['player2']} - {match['score']} ({match['status']})")
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