"""
Скрапер для теннисных матчей
"""
from typing import List, Dict, Any
import re
import time
from selenium.webdriver.common.by import By
from scrapers.base_scraper import BaseScraper
from scrapers.sofascore_simple_quality import SofaScoreSimpleQuality
from config import TENNIS_FILTER, TOP_LEAGUES

class TennisScraper(BaseScraper):
    """
    Скрапер для сбора данных теннисных матчей с scores24.live
    """
    
    def __init__(self, logger):
        super().__init__(logger)
        self.sofascore_scraper = SofaScoreSimpleQuality(logger)
    
    def get_live_matches(self, url: str) -> List[Dict[str, Any]]:
        """
        Получение списка live теннисных матчей
        """
        self.logger.info(f"Сбор live теннисных матчей (SofaScore)")
        
        # Используем исправленный скрапер
        try:
            matches = self.sofascore_scraper.get_live_matches('tennis')
            self.logger.info(f"SofaScore: найдено {len(matches)} теннисных матчей")
            return matches
        except Exception as e:
            self.logger.error(f"Ошибка получения теннисных матчей: {e}")
            return []
    
    def _extract_basic_match_info(self, match_elem) -> Dict[str, Any]:
        """
        Извлечение базовой информации о теннисном матче
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
        
        # Турнир
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
            'sport': 'tennis'
        }
    
    def filter_matches(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Фильтрация теннисных матчей по критериям
        """
        filtered = []
        
        for match in matches:
            if self._should_analyze_match(match):
                # Добавляем приоритет для топ-турниров
                match['priority'] = self._get_tournament_priority(match.get('tournament', ''))
                filtered.append(match)
        
        # Сортируем по приоритету турнира
        filtered.sort(key=lambda x: x.get('priority', 999))
        
        self.logger.info(f"Отфильтровано {len(filtered)} теннисных матчей из {len(matches)}")
        return filtered
    
    def _should_analyze_match(self, match: Dict[str, Any]) -> bool:
        """
        Проверка, подходит ли теннисный матч для анализа
        """
        sets_score = match.get('sets_score', '')
        current_set = match.get('current_set', '')
        
        # Проверяем, что ведущий выиграл первый сет или ведет с разрывом >= 4 гейма
        if self._leading_won_first_set(sets_score):
            return True
        
        if self._has_significant_game_lead(current_set):
            return True
        
        # Исключаем матчи с ничейным счетом по сетам
        if TENNIS_FILTER['exclude_even_sets'] and self._is_even_sets(sets_score):
            return False
        
        return False
    
    def _leading_won_first_set(self, sets_score: str) -> bool:
        """
        Проверка, выиграл ли ведущий первый сет
        """
        try:
            # Парсим счет по сетам (например, "1-0", "2-1")
            parts = re.split(r'[-:]', sets_score)
            if len(parts) == 2:
                set1, set2 = int(parts[0]), int(parts[1])
                return set1 > set2  # Первый игрок ведет по сетам
        except:
            pass
        return False
    
    def _has_significant_game_lead(self, current_set: str) -> bool:
        """
        Проверка на значительное преимущество в геймах текущего сета
        """
        try:
            # Парсим счет в текущем сете (например, "6-2", "5-1")
            parts = re.split(r'[-:]', current_set)
            if len(parts) == 2:
                games1, games2 = int(parts[0]), int(parts[1])
                return abs(games1 - games2) >= TENNIS_FILTER['min_games_lead']
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
    
    def _get_tournament_priority(self, tournament: str) -> int:
        """
        Получение приоритета турнира
        """
        for i, top_tournament in enumerate(TOP_LEAGUES.get('tennis', [])):
            if top_tournament.lower() in tournament.lower():
                return i
        return 999
    
    def collect_match_data(self, match_url: str) -> Dict[str, Any]:
        """
        Сбор подробных данных по теннисному матчу
        """
        self.logger.info(f"Сбор подробных данных теннисного матча: {match_url}")
        
        try:
            self.setup_driver()
            full_url = f"https://scores24.live{match_url}" if not match_url.startswith('http') else match_url
            self.driver.get(full_url)
            time.sleep(3)
            
            match_data = {
                'url': match_url,
                'sport': 'tennis'
            }
            
            # Основная информация
            match_data.update(self._collect_main_info())
            
            # Статистика
            match_data.update(self._collect_statistics())
            
            # История встреч
            match_data.update(self._collect_h2h())
            
            # Коэффициенты
            match_data.update(self._collect_odds())
            
            # Рейтинги
            match_data.update(self._collect_rankings())
            
            # Результаты игроков
            match_data.update(self._collect_results())
            
            return match_data
            
        except Exception as e:
            self.logger.error(f"Ошибка сбора данных теннисного матча {match_url}: {e}")
            return {'url': match_url, 'sport': 'tennis', 'error': str(e)}
        finally:
            self.close_driver()
    
    def _collect_main_info(self) -> Dict[str, Any]:
        """
        Сбор основной информации о теннисном матче
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
    
    def _collect_statistics(self) -> Dict[str, Any]:
        """
        Сбор статистики теннисного матча
        """
        stats_tab = self.safe_find_element(By.CSS_SELECTOR, "[data-tab='stats']")
        if stats_tab:
            self.safe_click(stats_tab)
            time.sleep(2)
            
            stats = {}
            stat_elements = self.safe_find_elements(By.CSS_SELECTOR, "[data-testid='tennis-stat']")
            
            for stat_elem in stat_elements:
                stat_name = self.safe_get_text(self.safe_find_element(stat_elem, By.CSS_SELECTOR, ".stat-name"))
                stat_values = self.safe_find_elements(stat_elem, By.CSS_SELECTOR, ".stat-value")
                
                if len(stat_values) >= 2:
                    stats[stat_name] = {
                        'player1': self.safe_get_text(stat_values[0]),
                        'player2': self.safe_get_text(stat_values[1])
                    }
            
            return {'statistics': stats}
        
        return {'statistics': {}}
    
    def _collect_h2h(self) -> Dict[str, Any]:
        """
        Сбор истории личных встреч в теннисе
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
                    'tournament': self.safe_get_text(self.safe_find_element(match_elem, By.CSS_SELECTOR, ".match-tournament")),
                    'surface': self.safe_get_text(self.safe_find_element(match_elem, By.CSS_SELECTOR, ".match-surface"))
                }
                h2h_matches.append(match_info)
            
            return {'h2h': h2h_matches}
        
        return {'h2h': []}
    
    def _collect_odds(self) -> Dict[str, Any]:
        """
        Сбор коэффициентов на теннисный матч
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
    
    def _collect_rankings(self) -> Dict[str, Any]:
        """
        Сбор рейтингов игроков
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
    
    def _collect_results(self) -> Dict[str, Any]:
        """
        Сбор результатов игроков
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
        Сбор результатов конкретного игрока
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
            
            # Подсчитываем сеты (примерно)
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