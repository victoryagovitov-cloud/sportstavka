"""
Скрапер для гандбольных матчей
"""
from typing import List, Dict, Any, Tuple
import re
import time
from selenium.webdriver.common.by import By
from scrapers.base_scraper import BaseScraper
from scrapers.sofascore_scraper_v2 import SofaScoreScraperV2
from config import HANDBALL_FILTER
import math

class HandballScraper(BaseScraper):
    """
    Скрапер для сбора данных гандбольных матчей с scores24.live
    """
    
    def __init__(self, logger):
        super().__init__(logger)
        self.sofascore_scraper = SofaScoreScraperV2(logger)
    
    def get_live_matches(self, url: str) -> List[Dict[str, Any]]:
        """
        Получение списка live гандбольных матчей
        """
        self.logger.info(f"Сбор live гандбольных матчей с {url}")
        
        # Используем исправленный скрапер
        try:
            matches = self.sofascore_scraper.get_live_matches('handball')
            self.logger.info(f"Найдено {len(matches)} гандбольных матчей")
            return matches
        except Exception as e:
            self.logger.error(f"Ошибка получения гандбольных матчей: {e}")
            return []
    
    def _extract_basic_match_info(self, match_elem) -> Dict[str, Any]:
        """
        Извлечение базовой информации о гандбольном матче
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
            'sport': 'handball'
        }
    
    def filter_matches(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Фильтрация гандбольных матчей по критериям
        """
        filtered = []
        
        for match in matches:
            if self._should_analyze_match(match):
                # Добавляем расчеты тоталов для подходящих матчей
                match.update(self._calculate_totals(match))
                filtered.append(match)
        
        self.logger.info(f"Отфильтровано {len(filtered)} гандбольных матчей из {len(matches)}")
        return filtered
    
    def _should_analyze_match(self, match: Dict[str, Any]) -> bool:
        """
        Проверка, подходит ли гандбольный матч для анализа
        """
        score = match.get('score', '')
        match_time = match.get('time', '')
        
        # Проверяем разность голов
        goal_difference = self._get_goal_difference(score)
        if goal_difference < HANDBALL_FILTER['min_goal_difference']:
            return False
        
        # Исключаем ничейные матчи
        if HANDBALL_FILTER['exclude_draw'] and goal_difference == 0:
            return False
        
        # Проверяем время для расчета тоталов (2-й тайм, 10-45 минута)
        if self._is_suitable_for_totals(match_time):
            return True
        
        return goal_difference >= HANDBALL_FILTER['min_goal_difference']
    
    def _get_goal_difference(self, score: str) -> int:
        """
        Получение разности голов
        """
        try:
            parts = re.split(r'[:-]', score)
            if len(parts) == 2:
                goals1, goals2 = int(parts[0]), int(parts[1])
                return abs(goals1 - goals2)
        except:
            pass
        return 0
    
    def _is_suitable_for_totals(self, match_time: str) -> bool:
        """
        Проверка, подходит ли матч для расчета тоталов
        """
        try:
            # Ищем время вида "2T 25'" (второй тайм, 25 минута)
            second_half_match = re.search(r'2T?\s*(\d+)', match_time)
            if second_half_match:
                minute = int(second_half_match.group(1))
                return (HANDBALL_FILTER['min_minute_second_half'] <= 
                       minute <= HANDBALL_FILTER['max_minute_second_half'])
        except:
            pass
        return False
    
    def _calculate_totals(self, match: Dict[str, Any]) -> Dict[str, Any]:
        """
        Расчет тоталов для гандбольного матча
        """
        score = match.get('score', '')
        match_time = match.get('time', '')
        
        try:
            # Парсим счет
            parts = re.split(r'[:-]', score)
            if len(parts) != 2:
                return {}
            
            goals1, goals2 = int(parts[0]), int(parts[1])
            total_goals = goals1 + goals2
            
            # Парсим время
            played_minutes = self._extract_played_minutes(match_time)
            if played_minutes == 0:
                return {}
            
            # Расчет прогнозного тотала
            predicted_total_raw = (total_goals / played_minutes) * 60
            predicted_total = math.ceil(predicted_total_raw)  # Округляем в большую сторону
            
            # Построение интервала
            total_over = predicted_total - 4  # ТБ
            total_under = predicted_total + 4  # ТМ
            
            # Определение темпа игры
            if total_goals > played_minutes:
                tempo = "БЫСТРЫЙ"
                recommendation = f"ТБ {total_over}"
                recommendation_type = "over"
            elif total_goals < played_minutes:
                tempo = "МЕДЛЕННЫЙ" 
                recommendation = f"ТМ {total_under}"
                recommendation_type = "under"
            else:
                tempo = "НЕЙТРАЛЬНЫЙ"
                recommendation = f"ТМ {total_under} или ТБ {total_over}"
                recommendation_type = "both"
            
            return {
                'totals_calculation': {
                    'total_goals': total_goals,
                    'played_minutes': played_minutes,
                    'predicted_total': predicted_total,
                    'total_over': total_over,
                    'total_under': total_under,
                    'tempo': tempo,
                    'recommendation': recommendation,
                    'recommendation_type': recommendation_type,
                    'reasoning': f"{tempo} темп игры ({total_goals} голов за {played_minutes} минут)"
                }
            }
            
        except Exception as e:
            self.logger.warning(f"Ошибка расчета тоталов: {e}")
            return {}
    
    def _extract_played_minutes(self, match_time: str) -> int:
        """
        Извлечение количества сыгранных минут
        """
        try:
            # Для второго тайма: "2T 25'" -> 30 + 25 = 55 минут
            second_half_match = re.search(r'2T?\s*(\d+)', match_time)
            if second_half_match:
                return 30 + int(second_half_match.group(1))
            
            # Для первого тайма: "1T 20'" -> 20 минут
            first_half_match = re.search(r'1T?\s*(\d+)', match_time)
            if first_half_match:
                return int(first_half_match.group(1))
            
            # Общий формат: "45'" -> 45 минут
            general_match = re.search(r'(\d+)', match_time)
            if general_match:
                return int(general_match.group(1))
                
        except:
            pass
        return 0
    
    def collect_match_data(self, match_url: str) -> Dict[str, Any]:
        """
        Сбор подробных данных по гандбольному матчу
        """
        self.logger.info(f"Сбор подробных данных гандбольного матча: {match_url}")
        
        try:
            self.setup_driver()
            full_url = f"https://scores24.live{match_url}" if not match_url.startswith('http') else match_url
            self.driver.get(full_url)
            time.sleep(3)
            
            match_data = {
                'url': match_url,
                'sport': 'handball'
            }
            
            # Основная информация
            match_data.update(self._collect_main_info())
            
            # Коэффициенты
            match_data.update(self._collect_odds())
            
            # Результаты команд
            match_data.update(self._collect_results())
            
            # Турнирная таблица
            match_data.update(self._collect_table())
            
            return match_data
            
        except Exception as e:
            self.logger.error(f"Ошибка сбора данных гандбольного матча {match_url}: {e}")
            return {'url': match_url, 'sport': 'handball', 'error': str(e)}
        finally:
            self.close_driver()
    
    def _collect_main_info(self) -> Dict[str, Any]:
        """
        Сбор основной информации о гандбольном матче
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
    
    def _collect_odds(self) -> Dict[str, Any]:
        """
        Сбор коэффициентов на гандбольный матч
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
    
    def _collect_results(self) -> Dict[str, Any]:
        """
        Сбор результатов команд в гандболе
        """
        results_tab = self.safe_find_element(By.CSS_SELECTOR, "[data-tab='results']")
        if results_tab:
            self.safe_click(results_tab)
            time.sleep(2)
            
            # Загружаем все результаты
            self.load_more_results("[data-testid='load-more-results']")
            
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
        Сбор результатов конкретной команды в гандболе
        """
        results = []
        match_elements = self.safe_find_elements(By.CSS_SELECTOR, "[data-testid='team-match']")
        
        wins = draws = losses = 0
        total_goals_scored = total_goals_conceded = 0
        
        for match_elem in match_elements:
            result = self.safe_get_text(self.safe_find_element(match_elem, By.CSS_SELECTOR, ".match-result"))
            score = self.safe_get_text(self.safe_find_element(match_elem, By.CSS_SELECTOR, ".match-score"))
            date = self.safe_get_text(self.safe_find_element(match_elem, By.CSS_SELECTOR, ".match-date"))
            opponent = self.safe_get_text(self.safe_find_element(match_elem, By.CSS_SELECTOR, ".opponent"))
            
            results.append({
                'result': result,
                'score': score,
                'date': date,
                'opponent': opponent
            })
            
            # Подсчитываем статистику
            if result == 'W':
                wins += 1
            elif result == 'D':
                draws += 1
            elif result == 'L':
                losses += 1
            
            # Подсчитываем голы
            try:
                goals = re.findall(r'(\d+)', score)
                if len(goals) >= 2:
                    total_goals_scored += int(goals[0])
                    total_goals_conceded += int(goals[1])
            except:
                pass
        
        total_matches = len(results)
        win_percentage = (wins / total_matches * 100) if total_matches > 0 else 0
        avg_goals_scored = total_goals_scored / total_matches if total_matches > 0 else 0
        avg_goals_conceded = total_goals_conceded / total_matches if total_matches > 0 else 0
        
        return {
            'matches': results,
            'statistics': {
                'wins': wins,
                'draws': draws,
                'losses': losses,
                'win_percentage': round(win_percentage, 1),
                'avg_goals_scored': round(avg_goals_scored, 1),
                'avg_goals_conceded': round(avg_goals_conceded, 1),
                'avg_total_goals': round(avg_goals_scored + avg_goals_conceded, 1)
            }
        }
    
    def _collect_table(self) -> Dict[str, Any]:
        """
        Сбор турнирной таблицы для гандбола
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