"""
Скрапер для футбольных матчей
"""
from typing import List, Dict, Any
import re
import time
from selenium.webdriver.common.by import By
from scrapers.base_scraper import BaseScraper
from config import FOOTBALL_FILTER, TOP_LEAGUES

class FootballScraper(BaseScraper):
    """
    Скрапер для сбора данных футбольных матчей с scores24.live
    """
    
    def get_live_matches(self, url: str) -> List[Dict[str, Any]]:
        """
        Получение списка live футбольных матчей
        """
        self.logger.info(f"Сбор live футбольных матчей с {url}")
        
        try:
            self.setup_driver()
            self.driver.get(url)
            time.sleep(5)
            
            matches = []
            
            # Ищем все live матчи
            match_elements = self.safe_find_elements(By.CSS_SELECTOR, "[data-testid='match']")
            
            for match_elem in match_elements:
                try:
                    match_data = self._extract_basic_match_info(match_elem)
                    if match_data:
                        matches.append(match_data)
                except Exception as e:
                    self.logger.warning(f"Ошибка извлечения данных матча: {e}")
                    continue
            
            self.logger.info(f"Найдено {len(matches)} футбольных матчей")
            return matches
            
        except Exception as e:
            self.logger.error(f"Ошибка получения футбольных матчей: {e}")
            return []
        finally:
            self.close_driver()
    
    def _extract_basic_match_info(self, match_elem) -> Dict[str, Any]:
        """
        Извлечение базовой информации о матче
        """
        # Команды
        teams = self.safe_find_elements(match_elem, By.CSS_SELECTOR, "[data-testid='team-name']")
        if len(teams) < 2:
            return None
        
        team1 = self.safe_get_text(teams[0])
        team2 = self.safe_get_text(teams[1])
        
        # Счет
        score_elem = self.safe_find_element(match_elem, By.CSS_SELECTOR, "[data-testid='match-score']")
        score = self.safe_get_text(score_elem)
        
        # Время
        time_elem = self.safe_find_element(match_elem, By.CSS_SELECTOR, "[data-testid='match-time']")
        match_time = self.safe_get_text(time_elem)
        
        # Лига
        league_elem = self.safe_find_element(match_elem, By.CSS_SELECTOR, "[data-testid='league-name']")
        league = self.safe_get_text(league_elem)
        
        # URL матча
        match_link = self.safe_find_element(match_elem, By.CSS_SELECTOR, "a")
        match_url = self.safe_get_attribute(match_link, "href") if match_link else ""
        
        return {
            'team1': team1,
            'team2': team2,
            'score': score,
            'time': match_time,
            'league': league,
            'url': match_url,
            'sport': 'football'
        }
    
    def filter_matches(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Фильтрация футбольных матчей по критериям
        """
        filtered = []
        
        for match in matches:
            if self._should_analyze_match(match):
                # Добавляем приоритет для топ-лиг
                match['priority'] = self._get_league_priority(match.get('league', ''))
                filtered.append(match)
        
        # Сортируем по приоритету лиги
        filtered.sort(key=lambda x: x.get('priority', 999))
        
        self.logger.info(f"Отфильтровано {len(filtered)} футбольных матчей из {len(matches)}")
        return filtered
    
    def _should_analyze_match(self, match: Dict[str, Any]) -> bool:
        """
        Проверка, подходит ли матч для анализа
        """
        # Извлекаем минуту из времени матча
        time_str = match.get('time', '')
        minute = self._extract_minute(time_str)
        
        # Проверяем временные рамки
        if minute < FOOTBALL_FILTER['min_minute'] or minute > FOOTBALL_FILTER['max_minute']:
            return False
        
        # Проверяем, что счет не ничейный
        if FOOTBALL_FILTER['exclude_draw']:
            score = match.get('score', '')
            if self._is_draw_score(score):
                return False
        
        return True
    
    def _extract_minute(self, time_str: str) -> int:
        """
        Извлечение минуты из строки времени
        """
        try:
            # Ищем число перед апострофом (например, "67'")
            match = re.search(r'(\d+)', time_str)
            if match:
                return int(match.group(1))
        except:
            pass
        return 0
    
    def _is_draw_score(self, score: str) -> bool:
        """
        Проверка, является ли счет ничейным
        """
        try:
            # Парсим счет вида "1:1" или "0-0"
            parts = re.split(r'[:-]', score)
            if len(parts) == 2:
                return parts[0].strip() == parts[1].strip()
        except:
            pass
        return False
    
    def _get_league_priority(self, league: str) -> int:
        """
        Получение приоритета лиги (чем меньше число, тем выше приоритет)
        """
        for i, top_league in enumerate(TOP_LEAGUES.get('football', [])):
            if top_league.lower() in league.lower():
                return i
        return 999
    
    def collect_match_data(self, match_url: str) -> Dict[str, Any]:
        """
        Сбор подробных данных по футбольному матчу
        """
        self.logger.info(f"Сбор подробных данных матча: {match_url}")
        
        try:
            self.setup_driver()
            full_url = f"https://scores24.live{match_url}" if not match_url.startswith('http') else match_url
            self.driver.get(full_url)
            time.sleep(3)
            
            match_data = {
                'url': match_url,
                'sport': 'football'
            }
            
            # Основная информация
            match_data.update(self._collect_main_info())
            
            # Статистика
            match_data.update(self._collect_statistics())
            
            # Прогноз
            match_data.update(self._collect_prediction())
            
            # Тренды
            match_data.update(self._collect_trends())
            
            # История встреч
            match_data.update(self._collect_h2h())
            
            # Коэффициенты
            match_data.update(self._collect_odds())
            
            # Турнирная таблица
            match_data.update(self._collect_table())
            
            # Результаты команд
            match_data.update(self._collect_results())
            
            return match_data
            
        except Exception as e:
            self.logger.error(f"Ошибка сбора данных матча {match_url}: {e}")
            return {'url': match_url, 'sport': 'football', 'error': str(e)}
        finally:
            self.close_driver()
    
    def _collect_main_info(self) -> Dict[str, Any]:
        """
        Сбор основной информации о матче
        """
        data = {}
        
        # Команды
        teams = self.safe_find_elements(By.CSS_SELECTOR, "[data-testid='team-name']")
        if len(teams) >= 2:
            data['team1'] = self.safe_get_text(teams[0])
            data['team2'] = self.safe_get_text(teams[1])
        
        # Счет
        score_elem = self.safe_find_element(By.CSS_SELECTOR, "[data-testid='match-score']")
        data['score'] = self.safe_get_text(score_elem)
        
        # Время
        time_elem = self.safe_find_element(By.CSS_SELECTOR, "[data-testid='match-time']")
        data['time'] = self.safe_get_text(time_elem)
        
        # Лига
        league_elem = self.safe_find_element(By.CSS_SELECTOR, "[data-testid='league-name']")
        data['league'] = self.safe_get_text(league_elem)
        
        return data
    
    def _collect_statistics(self) -> Dict[str, Any]:
        """
        Сбор статистики матча
        """
        stats = {}
        
        # Ищем статистику на главной странице
        stat_elements = self.safe_find_elements(By.CSS_SELECTOR, "[data-testid='match-stat']")
        
        for stat_elem in stat_elements:
            stat_name = self.safe_get_text(self.safe_find_element(stat_elem, By.CSS_SELECTOR, ".stat-name"))
            stat_values = self.safe_find_elements(stat_elem, By.CSS_SELECTOR, ".stat-value")
            
            if len(stat_values) >= 2:
                stats[stat_name] = {
                    'team1': self.safe_get_text(stat_values[0]),
                    'team2': self.safe_get_text(stat_values[1])
                }
        
        return {'statistics': stats}
    
    def _collect_prediction(self) -> Dict[str, Any]:
        """
        Сбор прогноза матча
        """
        # Переходим на вкладку прогноза
        prediction_tab = self.safe_find_element(By.CSS_SELECTOR, "[data-tab='prediction']")
        if prediction_tab:
            self.safe_click(prediction_tab)
            time.sleep(2)
            
            prediction_elem = self.safe_find_element(By.CSS_SELECTOR, "[data-testid='match-prediction']")
            prediction = self.safe_get_text(prediction_elem)
            
            return {'prediction': prediction}
        
        return {'prediction': 'Недоступно'}
    
    def _collect_trends(self) -> Dict[str, Any]:
        """
        Сбор трендов матча
        """
        trends_tab = self.safe_find_element(By.CSS_SELECTOR, "[data-tab='trends']")
        if trends_tab:
            self.safe_click(trends_tab)
            time.sleep(2)
            
            # Собираем данные трендов
            trends = {}
            trend_elements = self.safe_find_elements(By.CSS_SELECTOR, "[data-testid='trend-item']")
            
            for trend_elem in trend_elements:
                trend_name = self.safe_get_text(self.safe_find_element(trend_elem, By.CSS_SELECTOR, ".trend-name"))
                trend_value = self.safe_get_text(self.safe_find_element(trend_elem, By.CSS_SELECTOR, ".trend-value"))
                trends[trend_name] = trend_value
            
            return {'trends': trends}
        
        return {'trends': {}}
    
    def _collect_h2h(self) -> Dict[str, Any]:
        """
        Сбор истории личных встреч
        """
        h2h_tab = self.safe_find_element(By.CSS_SELECTOR, "[data-tab='h2h']")
        if h2h_tab:
            self.safe_click(h2h_tab)
            time.sleep(2)
            
            h2h_matches = []
            match_elements = self.safe_find_elements(By.CSS_SELECTOR, "[data-testid='h2h-match']")
            
            for match_elem in match_elements:
                match_info = {
                    'date': self.safe_get_text(self.safe_find_element(match_elem, By.CSS_SELECTOR, ".match-date")),
                    'score': self.safe_get_text(self.safe_find_element(match_elem, By.CSS_SELECTOR, ".match-score")),
                    'league': self.safe_get_text(self.safe_find_element(match_elem, By.CSS_SELECTOR, ".match-league"))
                }
                h2h_matches.append(match_info)
            
            return {'h2h': h2h_matches}
        
        return {'h2h': []}
    
    def _collect_odds(self) -> Dict[str, Any]:
        """
        Сбор коэффициентов
        """
        odds_tab = self.safe_find_element(By.CSS_SELECTOR, "[data-tab='odds']")
        if odds_tab:
            self.safe_click(odds_tab)
            time.sleep(2)
            
            odds = {}
            odds_elements = self.safe_find_elements(By.CSS_SELECTOR, "[data-testid='odds-item']")
            
            for odds_elem in odds_elements:
                market = self.safe_get_text(self.safe_find_element(odds_elem, By.CSS_SELECTOR, ".odds-market"))
                values = self.safe_find_elements(odds_elem, By.CSS_SELECTOR, ".odds-value")
                
                if values:
                    odds[market] = [self.safe_get_text(val) for val in values]
            
            return {'odds': odds}
        
        return {'odds': {}}
    
    def _collect_table(self) -> Dict[str, Any]:
        """
        Сбор турнирной таблицы
        """
        table_tab = self.safe_find_element(By.CSS_SELECTOR, "[data-tab='table']")
        if table_tab:
            self.safe_click(table_tab)
            time.sleep(2)
            
            table_data = {}
            table_rows = self.safe_find_elements(By.CSS_SELECTOR, "[data-testid='table-row']")
            
            for row in table_rows:
                team_name = self.safe_get_text(self.safe_find_element(row, By.CSS_SELECTOR, ".team-name"))
                position = self.safe_get_text(self.safe_find_element(row, By.CSS_SELECTOR, ".position"))
                points = self.safe_get_text(self.safe_find_element(row, By.CSS_SELECTOR, ".points"))
                
                table_data[team_name] = {
                    'position': position,
                    'points': points
                }
            
            return {'table': table_data}
        
        return {'table': {}}
    
    def _collect_results(self) -> Dict[str, Any]:
        """
        Сбор результатов команд
        """
        results_tab = self.safe_find_element(By.CSS_SELECTOR, "[data-tab='results']")
        if results_tab:
            self.safe_click(results_tab)
            time.sleep(2)
            
            # Загружаем все результаты
            self.load_more_results("[data-testid='load-more-results']")
            
            # Собираем результаты для каждой команды
            team_results = {}
            
            # Результаты первой команды
            team1_tab = self.safe_find_element(By.CSS_SELECTOR, "[data-tab='team1-results']")
            if team1_tab:
                self.safe_click(team1_tab)
                time.sleep(1)
                team_results['team1'] = self._collect_team_results()
            
            # Результаты второй команды
            team2_tab = self.safe_find_element(By.CSS_SELECTOR, "[data-tab='team2-results']")
            if team2_tab:
                self.safe_click(team2_tab)
                time.sleep(1)
                team_results['team2'] = self._collect_team_results()
            
            return {'results': team_results}
        
        return {'results': {}}
    
    def _collect_team_results(self) -> Dict[str, Any]:
        """
        Сбор результатов конкретной команды
        """
        results = []
        match_elements = self.safe_find_elements(By.CSS_SELECTOR, "[data-testid='team-match']")
        
        wins = draws = losses = 0
        
        for match_elem in match_elements:
            result = self.safe_get_text(self.safe_find_element(match_elem, By.CSS_SELECTOR, ".match-result"))
            score = self.safe_get_text(self.safe_find_element(match_elem, By.CSS_SELECTOR, ".match-score"))
            date = self.safe_get_text(self.safe_find_element(match_elem, By.CSS_SELECTOR, ".match-date"))
            
            results.append({
                'result': result,
                'score': score,
                'date': date
            })
            
            # Подсчитываем статистику
            if result == 'W':
                wins += 1
            elif result == 'D':
                draws += 1
            elif result == 'L':
                losses += 1
        
        total_matches = len(results)
        win_percentage = (wins / total_matches * 100) if total_matches > 0 else 0
        
        return {
            'matches': results,
            'statistics': {
                'wins': wins,
                'draws': draws,
                'losses': losses,
                'win_percentage': round(win_percentage, 1)
            }
        }