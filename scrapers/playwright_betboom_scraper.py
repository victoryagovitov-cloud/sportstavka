"""
Продвинутый BetBoom парсер с использованием Playwright
Автоматически извлекает live данные точно как видит пользователь
"""
import asyncio
import time
import re
from typing import List, Dict, Any
from playwright.async_api import async_playwright
from datetime import datetime

class PlaywrightBetBoomScraper:
    """
    Современный парсер BetBoom с Playwright
    """
    
    def __init__(self, logger):
        self.logger = logger
    
    async def auto_scrape_football_live(self) -> List[Dict[str, Any]]:
        """
        АВТОМАТИЧЕСКОЕ извлечение live футбольных данных
        """
        try:
            self.logger.info("Playwright: автоматическое извлечение BetBoom футбол")
            
            async with async_playwright() as p:
                # Запускаем браузер с антидетекцией
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-blink-features=AutomationControlled',
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor'
                    ]
                )
                
                # Создаем контекст с реалистичными настройками
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080},
                    locale='ru-RU'
                )
                
                page = await context.new_page()
                
                # Маскируем автоматизацию
                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    Object.defineProperty(navigator, 'languages', {get: () => ['ru-RU', 'ru', 'en-US', 'en']});
                """)
                
                # Переходим на страницу
                await page.goto('https://betboom.ru/sport/football?type=live')
                
                self.logger.info("Playwright: страница загружена")
                
                # Ждем загрузки контента
                await page.wait_for_timeout(10000)  # 10 секунд
                
                # Имитируем действия пользователя
                await self._simulate_user_actions(page)
                
                # Извлекаем данные
                matches = await self._extract_football_matches(page)
                
                await browser.close()
                
                self.logger.info(f"Playwright: извлечено {len(matches)} футбольных матчей")
                return matches
                
        except Exception as e:
            self.logger.error(f"Playwright ошибка: {e}")
            return []
    
    async def _simulate_user_actions(self, page):
        """
        Имитация действий реального пользователя
        """
        try:
            # Прокрутка страницы
            await page.evaluate("window.scrollTo(0, 500)")
            await page.wait_for_timeout(2000)
            
            # Движение мыши
            await page.mouse.move(100, 100)
            await page.wait_for_timeout(1000)
            
            # Клик (если нужно)
            await page.mouse.click(500, 300)
            await page.wait_for_timeout(1000)
            
            # Возврат наверх
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(2000)
            
        except Exception as e:
            self.logger.warning(f"Ошибка имитации пользователя: {e}")
    
    async def _extract_football_matches(self, page) -> List[Dict[str, Any]]:
        """
        Извлечение футбольных матчей с Playwright
        """
        matches = []
        
        try:
            # Метод 1: Получение всего текста страницы
            page_text = await page.inner_text('body')
            
            self.logger.info(f"Playwright: получен текст {len(page_text)} символов")
            
            # Автоматический парсинг структурированных данных
            structured_matches = await self._parse_structured_football_data(page_text)
            matches.extend(structured_matches)
            
            # Метод 2: Поиск через селекторы
            if not matches:
                selector_matches = await self._extract_via_selectors(page)
                matches.extend(selector_matches)
            
            # Метод 3: JavaScript извлечение
            if not matches:
                js_matches = await self._extract_via_javascript(page)
                matches.extend(js_matches)
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения футбольных матчей: {e}")
            return []
    
    async def _parse_structured_football_data(self, page_text: str) -> List[Dict[str, Any]]:
        """
        Парсинг структурированных футбольных данных
        """
        matches = []
        
        try:
            lines = page_text.split('\\n')
            
            # Автоматический анализатор структуры
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                # Ищем блоки турниров
                if self._is_tournament_line(line):
                    tournament_name = line
                    
                    # Ищем матчи в этом турнире
                    j = i + 1
                    while j < len(lines) and j < i + 50:  # Ограничиваем поиск
                        match_data = await self._try_extract_match_at_position(lines, j, tournament_name)
                        
                        if match_data:
                            matches.append(match_data)
                            j += 10  # Пропускаем обработанные строки
                        else:
                            j += 1
                    
                    i = j
                else:
                    i += 1
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка парсинга структурированных данных: {e}")
            return []
    
    def _is_tournament_line(self, line: str) -> bool:
        """
        Определение строки с названием турнира
        """
        tournament_indicators = [
            'ЧМ.', 'Лига', 'Кубок', 'Чемпионат', 'Примера', 'Серия',
            'League', 'Cup', 'Championship', 'Premier', 'Division'
        ]
        
        return any(indicator in line for indicator in tournament_indicators)
    
    async def _try_extract_match_at_position(self, lines: List[str], start_pos: int, tournament: str) -> Dict[str, Any]:
        """
        Попытка извлечения матча начиная с позиции
        """
        try:
            # Ищем команды (обычно 2 строки подряд)
            team1_line = lines[start_pos].strip() if start_pos < len(lines) else ''
            team2_line = lines[start_pos + 1].strip() if start_pos + 1 < len(lines) else ''
            
            # Проверяем что это команды
            if (self._looks_like_team_name(team1_line) and 
                self._looks_like_team_name(team2_line) and
                team1_line != team2_line):
                
                # Ищем счет (следующие 4 числа)
                scores = []
                for offset in range(2, 10):
                    if start_pos + offset < len(lines):
                        line = lines[start_pos + offset].strip()
                        if re.match(r'^\d+$', line):
                            scores.append(int(line))
                        if len(scores) >= 4:
                            break
                
                # Ищем время/статус
                time_status = ''
                for offset in range(6, 15):
                    if start_pos + offset < len(lines):
                        line = lines[start_pos + offset].strip()
                        if self._looks_like_time_status(line):
                            time_status = line
                            break
                
                # Ищем коэффициенты
                odds = {}
                for offset in range(10, 20):
                    if start_pos + offset < len(lines):
                        line = lines[start_pos + offset].strip()
                        if re.match(r'^\d+\.\d+$', line):
                            if not odds.get('П1'):
                                odds['П1'] = line
                            elif not odds.get('X'):
                                odds['X'] = line
                            elif not odds.get('П2'):
                                odds['П2'] = line
                                break
                
                # Создаем матч если есть минимальные данные
                if len(scores) >= 2:
                    match_data = {
                        'source': 'playwright_betboom',
                        'sport': 'football',
                        'team1': team1_line,
                        'team2': team2_line,
                        'score': f"{scores[0]}:{scores[1]}",
                        'detailed_score': {
                            'team1_goals': scores[0],
                            'team2_goals': scores[1],
                            'team1_shots': scores[2] if len(scores) > 2 else 0,
                            'team2_shots': scores[3] if len(scores) > 3 else 0
                        },
                        'time': time_status or 'LIVE',
                        'league': tournament,
                        'odds': odds,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Определяем важность и регион
                    match_data.update(self._classify_match(tournament))
                    
                    return match_data
            
            return None
            
        except Exception as e:
            return None
    
    def _looks_like_team_name(self, line: str) -> bool:
        """
        Проверка похоже ли на название команды
        """
        if not line or len(line) < 3 or len(line) > 30:
            return False
        
        # Исключаем служебные строки
        exclude_words = ['исход', 'тотал', 'фора', 'ещё', 'мин', 'сет', 'п1', 'п2']
        if any(word in line.lower() for word in exclude_words):
            return False
        
        # Проверяем что начинается с заглавной буквы
        return re.match(r'^[А-ЯA-Z][а-яa-zA-Z\s\-\.]+$', line) is not None
    
    def _looks_like_time_status(self, line: str) -> bool:
        """
        Проверка похоже ли на время/статус матча
        """
        time_patterns = [
            r'\d+Т,\s\d+\sмин',  # 2Т, 90 мин
            r'Перерыв',
            r'Не начался',
            r'\d+\sмин',
            r'Начало через',
            r'LIVE',
            r'HT',
            r'FT'
        ]
        
        return any(re.search(pattern, line) for pattern in time_patterns)
    
    def _classify_match(self, tournament: str) -> Dict[str, Any]:
        """
        Классификация матча по турниру
        """
        classification = {}
        
        # Важность
        if 'ЧМ' in tournament or 'World Cup' in tournament:
            classification['importance'] = 'HIGH'
            classification['tournament_type'] = 'World Cup Qualification'
        elif any(word in tournament for word in ['Серия', 'Примера', 'Лига', 'Premier']):
            classification['importance'] = 'MEDIUM'
            classification['tournament_type'] = 'Professional League'
        else:
            classification['importance'] = 'LOW'
            classification['tournament_type'] = 'Regional League'
        
        # Регион
        if any(word in tournament for word in ['Бразилия', 'Аргентина', 'Колумбия', 'Уругвай']):
            classification['region'] = 'South America'
        elif any(word in tournament for word in ['США', 'Канада', 'Мексика']):
            classification['region'] = 'North America'
        elif 'CONCACAF' in tournament:
            classification['region'] = 'CONCACAF'
        elif any(word in tournament for word in ['Новая Зеландия']):
            classification['region'] = 'Oceania'
        else:
            classification['region'] = 'Unknown'
        
        return classification
    
    async def _extract_via_selectors(self, page) -> List[Dict[str, Any]]:
        """
        Извлечение через CSS селекторы
        """
        matches = []
        
        try:
            # Современные селекторы для букмекерских сайтов
            selectors = [
                '[data-testid*="match"]',
                '[data-testid*="event"]',
                '[data-testid*="fixture"]',
                '.match-row',
                '.event-row',
                '.fixture',
                '.match',
                '.event',
                'tr',
                'div[class*="sport"]'
            ]
            
            for selector in selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    
                    if elements:
                        self.logger.info(f"Playwright селектор {selector}: {len(elements)} элементов")
                        
                        for element in elements[:20]:
                            text = await element.inner_text()
                            match_data = self._parse_element_text_for_match(text)
                            if match_data:
                                matches.append(match_data)
                        
                        if matches:
                            break
                            
                except Exception as e:
                    continue
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения через селекторы: {e}")
            return []
    
    async def _extract_via_javascript(self, page) -> List[Dict[str, Any]]:
        """
        Извлечение через выполнение JavaScript
        """
        matches = []
        
        try:
            # JavaScript для поиска live данных
            js_result = await page.evaluate("""
                () => {
                    const liveData = [];
                    
                    // Поиск всех элементов с текстом
                    const allElements = document.querySelectorAll('*');
                    
                    for (let elem of allElements) {
                        const text = elem.textContent || '';
                        
                        // Ищем элементы с командами и счетами
                        if (text.length > 10 && text.length < 200) {
                            if (text.includes('vs') || text.includes('-') || /\\d+:\\d+/.test(text)) {
                                liveData.push({
                                    text: text,
                                    tagName: elem.tagName,
                                    className: elem.className
                                });
                            }
                        }
                    }
                    
                    return liveData.slice(0, 50);
                }
            """)
            
            if js_result:
                self.logger.info(f"Playwright JavaScript: получено {len(js_result)} элементов")
                
                for item in js_result:
                    text = item.get('text', '')
                    match_data = self._parse_element_text_for_match(text)
                    if match_data:
                        matches.append(match_data)
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка JavaScript извлечения: {e}")
            return []
    
    def _parse_element_text_for_match(self, text: str) -> Dict[str, Any]:
        """
        Парсинг текста элемента для извлечения матча
        """
        try:
            # Паттерны для автоматического извлечения
            patterns = [
                # Команда1 Команда2 Счет1 Счет2
                r'([А-ЯA-Z][а-яa-zA-Z\s]{3,25})\s+([А-ЯA-Z][а-яa-zA-Z\s]{3,25})\s+(\d+)\s+(\d+)',
                
                # Команда1 - Команда2
                r'([А-ЯA-Z][а-яa-zA-Z\s]{3,25})\s*-\s*([А-ЯA-Z][а-яa-zA-Z\s]{3,25})',
                
                # Команда1 vs Команда2
                r'([А-ЯA-Z][а-яa-zA-Z\s]{3,25})\s+vs\s+([А-ЯA-Z][а-яa-zA-Z\s]{3,25})',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    groups = match.groups()
                    
                    if len(groups) >= 2:
                        team1, team2 = groups[0].strip(), groups[1].strip()
                        
                        # Проверяем валидность
                        if self._is_valid_team_pair(team1, team2):
                            match_data = {
                                'source': 'playwright_auto',
                                'sport': 'football',
                                'team1': team1,
                                'team2': team2,
                                'raw_text': text[:100]
                            }
                            
                            # Добавляем счет если есть
                            if len(groups) >= 4:
                                match_data['score'] = f"{groups[2]}:{groups[3]}"
                            else:
                                match_data['score'] = 'LIVE'
                            
                            return match_data
            
            return None
            
        except Exception as e:
            return None
    
    def _is_valid_team_pair(self, team1: str, team2: str) -> bool:
        """
        Проверка валидности пары команд
        """
        try:
            # Базовые проверки
            if not team1 or not team2:
                return False
            
            if len(team1) < 3 or len(team2) < 3:
                return False
            
            if team1.lower() == team2.lower():
                return False
            
            # Исключаем служебные строки
            exclude_words = ['исход', 'тотал', 'фора', 'ещё', 'п1', 'п2', 'коэф']
            
            for word in exclude_words:
                if word in team1.lower() or word in team2.lower():
                    return False
            
            return True
            
        except Exception as e:
            return False
    
    def run_football_scraping(self) -> List[Dict[str, Any]]:
        """
        Синхронный запуск футбольного парсинга
        """
        try:
            return asyncio.run(self.auto_scrape_football_live())
        except Exception as e:
            self.logger.error(f"Ошибка синхронного запуска: {e}")
            return []
    
    def run_tennis_scraping(self) -> List[Dict[str, Any]]:
        """
        Синхронный запуск теннисного парсинга
        """
        try:
            return asyncio.run(self.auto_scrape_tennis_live())
        except Exception as e:
            self.logger.error(f"Ошибка синхронного запуска тенниса: {e}")
            return []
    
    async def auto_scrape_tennis_live(self) -> List[Dict[str, Any]]:
        """
        АВТОМАТИЧЕСКОЕ извлечение live теннисных данных
        """
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = await context.new_page()
                
                await page.goto('https://betboom.ru/sport/tennis?type=live')
                await page.wait_for_timeout(10000)
                
                page_text = await page.inner_text('body')
                tennis_matches = self._parse_tennis_structure(page_text)
                
                await browser.close()
                
                return tennis_matches
                
        except Exception as e:
            self.logger.error(f"Ошибка автоматического извлечения тенниса: {e}")
            return []
    
    def _parse_tennis_structure(self, page_text: str) -> List[Dict[str, Any]]:
        """
        Парсинг структуры теннисных данных
        """
        matches = []
        
        try:
            lines = page_text.split('\\n')
            
            # Автоматический поиск теннисных матчей
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                # Ищем игроков (имена с точками)
                if re.match(r'^[А-ЯA-Z][а-яa-z]+\s[А-ЯA-Z]\.?$', line):
                    player1 = line
                    
                    # Ищем второго игрока
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if re.match(r'^[А-ЯA-Z][а-яa-z]+\s[А-ЯA-Z]\.?$', next_line):
                            player2 = next_line
                            
                            # Ищем данные матча
                            match_data = self._extract_tennis_match_data(lines, i + 2, player1, player2)
                            if match_data:
                                matches.append(match_data)
                            
                            i += 10  # Пропускаем обработанные строки
                        else:
                            i += 1
                    else:
                        i += 1
                else:
                    i += 1
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка парсинга теннисной структуры: {e}")
            return []
    
    def _extract_tennis_match_data(self, lines: List[str], start_pos: int, player1: str, player2: str) -> Dict[str, Any]:
        """
        Извлечение данных теннисного матча
        """
        try:
            # Ищем счет по сетам и геймам (следующие числа)
            scores = []
            for offset in range(0, 10):
                if start_pos + offset < len(lines):
                    line = lines[start_pos + offset].strip()
                    if re.match(r'^\d+$', line):
                        scores.append(int(line))
                    if len(scores) >= 6:  # Достаточно для теннисного счета
                        break
            
            if len(scores) >= 4:
                match_data = {
                    'source': 'playwright_auto_tennis',
                    'sport': 'tennis',
                    'team1': player1,
                    'team2': player2,
                    'score': f"{scores[0]}:{scores[1]}, {scores[2]}:{scores[3]}",
                    'sets_score': f"{scores[0]}:{scores[1]}",
                    'games_score': f"{scores[2]}:{scores[3]}",
                    'timestamp': datetime.now().isoformat()
                }
                
                # Ищем текущий счет в гейме
                if len(scores) >= 6:
                    match_data['current_game'] = f"{scores[4]}:{scores[5]}"
                
                return match_data
            
            return None
            
        except Exception as e:
            return None