"""
Реальный скрапер теннисных матчей с BetBoom через MCP Browser
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
logger = logging.getLogger('real_betboom_tennis')

class RealBetBoomTennisScraper:
    """Реальный скрапер теннисных матчей с BetBoom через MCP Browser"""
    
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
    
    async def take_screenshot(self, path: str = "betboom_tennis_screenshot.png") -> bool:
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
    
    def parse_tennis_matches(self, html_content: str) -> List[Dict[str, Any]]:
        """Парсинг теннисных матчей из HTML"""
        matches = []
        
        try:
            from bs4 import BeautifulSoup
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
            
            found_matches = []
            
            for selector in match_selectors:
                elements = soup.select(selector)
                if elements:
                    self.logger.info(f"Найдено {len(elements)} элементов по селектору: {selector}")
                    found_matches.extend(elements)
                    break
            
            # Если не нашли по селекторам, ищем по тексту
            if not found_matches:
                self.logger.info("Поиск матчей по тексту...")
                # Ищем все элементы с текстом, содержащим теннисные термины
                all_elements = soup.find_all(text=re.compile(r'(WTA|ATP|ITF|теннис|tennis|сет|set)', re.IGNORECASE))
                for element in all_elements:
                    parent = element.parent
                    if parent and parent not in found_matches:
                        found_matches.append(parent)
            
            # Парсим найденные элементы
            for element in found_matches[:50]:  # Ограничиваем количество
                try:
                    match_data = self.extract_match_data(element)
                    if match_data:
                        matches.append(match_data)
                except Exception as e:
                    self.logger.warning(f"Ошибка парсинга элемента: {e}")
                    continue
            
            # Дополнительный поиск по всему тексту страницы
            if not matches:
                self.logger.info("Поиск матчей по всему тексту страницы...")
                text_matches = self.find_matches_in_text(html_content)
                matches.extend(text_matches)
            
        except Exception as e:
            self.logger.error(f"Ошибка парсинга HTML: {e}")
        
        return matches
    
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
                                'source': 'betboom_mcp',
                                'raw_text': text[:100] + "..." if len(text) > 100 else text
                            }
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения данных матча: {e}")
            return None
    
    def find_matches_in_text(self, html_content: str) -> List[Dict[str, Any]]:
        """Поиск матчей в тексте страницы"""
        matches = []
        
        try:
            # Ищем паттерны в тексте
            lines = html_content.split('\n')
            
            for line in lines:
                line = line.strip()
                if len(line) < 20 or len(line) > 200:
                    continue
                
                # Ищем строки с теннисными терминами
                if any(term in line.lower() for term in ['wta', 'atp', 'itf', 'теннис', 'tennis']):
                    # Пытаемся извлечь данные матча
                    match_data = self.extract_match_from_text(line)
                    if match_data:
                        matches.append(match_data)
            
        except Exception as e:
            self.logger.error(f"Ошибка поиска в тексте: {e}")
        
        return matches
    
    def extract_match_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Извлечение данных матча из текста"""
        try:
            # Различные паттерны для поиска матчей
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
                                'source': 'betboom_mcp',
                                'raw_text': text[:100] + "..." if len(text) > 100 else text
                            }
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения из текста: {e}")
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

async def scrape_real_tennis_matches():
    """Основная функция скрапинга реальных теннисных матчей"""
    logger.info("🎾 Начинаем реальный скрапинг теннисных матчей с BetBoom")
    
    scraper = RealBetBoomTennisScraper(logger)
    
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
        await asyncio.sleep(8)
        
        # Создаем скриншот для проверки
        await scraper.take_screenshot("betboom_tennis_real.png")
        
        # Получаем содержимое страницы
        content = await scraper.get_page_content()
        if not content:
            logger.error("❌ Не удалось получить содержимое страницы")
            return []
        
        logger.info("✅ Содержимое страницы получено")
        
        # Сохраняем HTML для анализа
        with open("betboom_tennis_content.html", "w", encoding="utf-8") as f:
            f.write(content)
        logger.info("💾 HTML сохранен в betboom_tennis_content.html")
        
        # Парсим матчи
        matches = scraper.parse_tennis_matches(content)
        
        if matches:
            logger.info(f"🎾 Найдено {len(matches)} теннисных матчей")
            
            # Выводим результаты
            print("\n" + "="*100)
            print("🎾 РЕАЛЬНЫЕ ТЕННИСНЫЕ МАТЧИ С BETBOOM (MCP Browser)")
            print("="*100)
            print(f"📅 Время получения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"🌐 Источник: https://betboom.ru/sport/tennis?type=live")
            print(f"🔧 Метод: MCP Browser Python SDK")
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
        # Отключаемся
        await scraper.disconnect()
        logger.info("🔌 Отключение завершено")

if __name__ == "__main__":
    asyncio.run(scrape_real_tennis_matches())