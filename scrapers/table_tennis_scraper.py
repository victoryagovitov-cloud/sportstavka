"""
Скрапер для матчей настольного тенниса
"""
from typing import List, Dict, Any
import re
import time
from selenium.webdriver.common.by import By
from scrapers.base_scraper import BaseScraper
from scrapers.sofascore_scraper_v2 import SofaScoreScraperV2
from config import TABLE_TENNIS_FILTER

class TableTennisScraper(BaseScraper):
    """
    Скрапер для сбора данных матчей настольного тенниса с scores24.live
    """
    
    def __init__(self, logger):
        super().__init__(logger)
        self.sofascore_scraper = SofaScoreScraperV2(logger)
    
    def get_live_matches(self, url: str) -> List[Dict[str, Any]]:
        """
        Получение списка live матчей настольного тенниса
        """
        self.logger.info(f"Сбор live матчей настольного тенниса с {url}")
        
        # Используем исправленный скрапер
        try:
            matches = self.sofascore_scraper.get_live_matches('table_tennis')
            self.logger.info(f"Найдено {len(matches)} матчей настольного тенниса")
            return matches
        except Exception as e:
            self.logger.error(f"Ошибка получения матчей настольного тенниса: {e}")
            return []
    
    def _extract_basic_match_info(self, match_elem) -> Dict[str, Any]:
        """
        Извлечение базовой информации о матче настольного тенниса
        """
        # Игроки
        players = self.safe_find_elements(match_elem, By.CSS_SELECTOR, "[data-testid='player-name']")
        if len(players) < 2:
            return None
        
        player1 = self.safe_get_text(players[0])
        player2 = self.safe_get_text(players[1])
        
        # Счет по сетам
        sets_score_elem = self.safe_find_element(match_elem, By.CSS_SELECTOR, "[data-testid='sets-score']")
        sets_score = self.safe_get_text(sets_score_elem)
        
        # Текущий сет
        current_set_elem = self.safe_find_element(match_elem, By.CSS_SELECTOR, "[data-testid='current-set']")
        current_set = self.safe_get_text(current_set_elem)
        
        # Турнир/лига
        tournament_elem = self.safe_find_element(match_elem, By.CSS_SELECTOR, "[data-testid='tournament-name']")
        tournament = self.safe_get_text(tournament_elem)
        
        # URL матча
        match_link = self.safe_find_element(match_elem, By.CSS_SELECTOR, "a")
        match_url = self.safe_get_attribute(match_link, "href") if match_link else ""
        
        return {
            'player1': player1,
            'player2': player2,
            'sets_score': sets_score,
            'current_set': current_set,
            'tournament': tournament,
            'url': match_url,
            'sport': 'table_tennis'
        }
    
    def filter_matches(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Фильтрация матчей настольного тенниса по критериям
        """
        filtered = []
        
        for match in matches:
            if self._should_analyze_match(match):
                filtered.append(match)
        
        self.logger.info(f"Отфильтровано {len(filtered)} матчей настольного тенниса из {len(matches)}")
        return filtered
    
    def _should_analyze_match(self, match: Dict[str, Any]) -> bool:
        """
        Проверка, подходит ли матч настольного тенниса для анализа
        """
        sets_score = match.get('sets_score', '')
        
        # Проверяем, что ведущий имеет преимущество 1:0 или 2:0
        if self._has_required_set_lead(sets_score):
            return True
        
        # Исключаем матчи с ничейным счетом по сетам
        if TABLE_TENNIS_FILTER['exclude_even_sets'] and self._is_even_sets(sets_score):
            return False
        
        return False
    
    def _has_required_set_lead(self, sets_score: str) -> bool:
        """
        Проверка на требуемое преимущество в сетах (1:0 или 2:0)
        """
        try:
            # Парсим счет по сетам (например, "1-0", "2-0")
            parts = re.split(r'[-:]', sets_score)
            if len(parts) == 2:
                sets1, sets2 = int(parts[0]), int(parts[1])
                lead = sets1 - sets2
                return lead in TABLE_TENNIS_FILTER['required_set_leads']
        except:
            pass
        return False
    
    def _is_even_sets(self, sets_score: str) -> bool:
        """
        Проверка на ничейный счет по сетам
        """
        try:
            parts = re.split(r'[-:]', sets_score)
            if len(parts) == 2:
                return parts[0] == parts[1]
        except:
            pass
        return False
    
    def collect_match_data(self, match_url: str) -> Dict[str, Any]:
        """
        Сбор подробных данных по матчу настольного тенниса
        """
        self.logger.info(f"Сбор подробных данных матча настольного тенниса: {match_url}")
        
        try:
            self.setup_driver()
            full_url = f"https://scores24.live{match_url}" if not match_url.startswith('http') else match_url
            self.driver.get(full_url)
            time.sleep(3)
            
            match_data = {
                'url': match_url,
                'sport': 'table_tennis'
            }
            
            # Основная информация
            match_data.update(self._collect_main_info())
            
            # Тренды
            match_data.update(self._collect_trends())
            
            # Коэффициенты
            match_data.update(self._collect_odds())
            
            # Результаты игроков
            match_data.update(self._collect_results())
            
            # Рейтинги (если доступны)
            match_data.update(self._collect_rankings())
            
            return match_data
            
        except Exception as e:
            self.logger.error(f"Ошибка сбора данных матча настольного тенниса {match_url}: {e}")
            return {'url': match_url, 'sport': 'table_tennis', 'error': str(e)}
        finally:
            self.close_driver()
    
    def _collect_main_info(self) -> Dict[str, Any]:
        """
        Сбор основной информации о матче настольного тенниса
        """
        data = {}
        
        # Игроки
        players = self.safe_find_elements(By.CSS_SELECTOR, "[data-testid='player-name']")
        if len(players) >= 2:
            data['player1'] = self.safe_get_text(players[0])
            data['player2'] = self.safe_get_text(players[1])
        
        # Счет по сетам
        sets_elem = self.safe_find_element(By.CSS_SELECTOR, "[data-testid='sets-score']")
        data['sets_score'] = self.safe_get_text(sets_elem)
        
        # Текущий сет
        current_set_elem = self.safe_find_element(By.CSS_SELECTOR, "[data-testid='current-set']")
        data['current_set'] = self.safe_get_text(current_set_elem)
        
        # Турнир
        tournament_elem = self.safe_find_element(By.CSS_SELECTOR, "[data-testid='tournament-name']")
        data['tournament'] = self.safe_get_text(tournament_elem)
        
        return data
    
    def _collect_trends(self) -> Dict[str, Any]:
        """
        Сбор трендов матча настольного тенниса
        """
        trends_tab = self.safe_find_element(By.CSS_SELECTOR, "[data-tab='trends']")
        if trends_tab:
            self.safe_click(trends_tab)
            time.sleep(2)
            
            trends = {}
            trend_elements = self.safe_find_elements(By.CSS_SELECTOR, "[data-testid='trend-item']")
            
            for trend_elem in trend_elements:
                trend_name = self.safe_get_text(self.safe_find_element(trend_elem, By.CSS_SELECTOR, ".trend-name"))
                trend_value = self.safe_get_text(self.safe_find_element(trend_elem, By.CSS_SELECTOR, ".trend-value"))
                trends[trend_name] = trend_value
            
            return {'trends': trends}
        
        return {'trends': {}}
    
    def _collect_odds(self) -> Dict[str, Any]:
        """
        Сбор коэффициентов на матч настольного тенниса
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
        Сбор результатов игроков в настольном теннисе
        """
        results_tab = self.safe_find_element(By.CSS_SELECTOR, "[data-tab='results']")
        if results_tab:
            self.safe_click(results_tab)
            time.sleep(2)
            
            # Загружаем все результаты
            self.load_more_results("[data-testid='load-more-results']")
            
            player_results = {}
            
            # Результаты первого игрока
            player1_tab = self.safe_find_element(By.CSS_SELECTOR, "[data-tab='player1-results']")
            if player1_tab:
                self.safe_click(player1_tab)
                time.sleep(1)
                player_results['player1'] = self._collect_player_results()
            
            # Результаты второго игрока
            player2_tab = self.safe_find_element(By.CSS_SELECTOR, "[data-tab='player2-results']")
            if player2_tab:
                self.safe_click(player2_tab)
                time.sleep(1)
                player_results['player2'] = self._collect_player_results()
            
            return {'results': player_results}
        
        return {'results': {}}
    
    def _collect_player_results(self) -> Dict[str, Any]:
        """
        Сбор результатов конкретного игрока в настольном теннисе
        """
        results = []
        match_elements = self.safe_find_elements(By.CSS_SELECTOR, "[data-testid='player-match']")
        
        wins = losses = 0
        sets_won = sets_lost = 0
        
        for match_elem in match_elements:
            result = self.safe_get_text(self.safe_find_element(match_elem, By.CSS_SELECTOR, ".match-result"))
            score = self.safe_get_text(self.safe_find_element(match_elem, By.CSS_SELECTOR, ".match-score"))
            date = self.safe_get_text(self.safe_find_element(match_elem, By.CSS_SELECTOR, ".match-date"))
            tournament = self.safe_get_text(self.safe_find_element(match_elem, By.CSS_SELECTOR, ".match-tournament"))
            
            results.append({
                'result': result,
                'score': score,
                'date': date,
                'tournament': tournament
            })
            
            # Подсчитываем статистику
            if result == 'W':
                wins += 1
            elif result == 'L':
                losses += 1
            
            # Подсчитываем сеты
            try:
                sets = re.findall(r'(\d+)-(\d+)', score)
                for set_score in sets:
                    sets_won += int(set_score[0])
                    sets_lost += int(set_score[1])
            except:
                pass
        
        total_matches = len(results)
        win_percentage = (wins / total_matches * 100) if total_matches > 0 else 0
        
        return {
            'matches': results,
            'statistics': {
                'wins': wins,
                'losses': losses,
                'win_percentage': round(win_percentage, 1),
                'sets_won': sets_won,
                'sets_lost': sets_lost
            }
        }
    
    def _collect_rankings(self) -> Dict[str, Any]:
        """
        Сбор рейтингов игроков (если доступны)
        """
        ranking_tab = self.safe_find_element(By.CSS_SELECTOR, "[data-tab='ranking']")
        if ranking_tab:
            self.safe_click(ranking_tab)
            time.sleep(2)
            
            rankings = {}
            
            # Рейтинг первого игрока
            player1_ranking = self.safe_find_element(By.CSS_SELECTOR, "[data-testid='player1-ranking']")
            if player1_ranking:
                rankings['player1'] = self.safe_get_text(player1_ranking)
            
            # Рейтинг второго игрока
            player2_ranking = self.safe_find_element(By.CSS_SELECTOR, "[data-testid='player2-ranking']")
            if player2_ranking:
                rankings['player2'] = self.safe_get_text(player2_ranking)
            
            return {'rankings': rankings}
        
        return {'rankings': {}}