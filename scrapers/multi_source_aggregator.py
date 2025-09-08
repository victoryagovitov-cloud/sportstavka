"""
Агрегатор данных из множественных источников
Объединяет данные от SofaScore, FlashScore, Scores24 и MarathonBet (расширенная версия)
"""
import asyncio
import time
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

from scrapers.sofascore_simple_quality import SofaScoreSimpleQuality
from scrapers.flashscore_scraper import FlashScoreScraper
from scrapers.scores24_scraper import Scores24Scraper
from scrapers.marathonbet_scraper import MarathonBetScraper
from scrapers.team_stats_collector import TeamStatsCollector
from scrapers.understat_scraper import UnderstatScraper
from scrapers.fotmob_scraper import FotMobScraper
from scrapers.parallel_aggregator import SafeParallelAggregator

class MultiSourceAggregator:
    """
    Агрегатор данных из множественных источников спортивных данных
    """
    
    def __init__(self, logger):
        self.logger = logger
        
        # Инициализируем эффективные + новые перспективные скраперы
        self.scrapers = {
            'sofascore': SofaScoreSimpleQuality(logger),
            'flashscore': FlashScoreScraper(logger),
            'scores24': Scores24Scraper(logger),
            'marathonbet': MarathonBetScraper(logger)
        }
        
        # Специализированные сборщики статистики
        self.stats_collectors = {
            'team_stats': TeamStatsCollector(logger),
            'understat': UnderstatScraper(logger),
            'fotmob': FotMobScraper(logger)
        }
        
        # Безопасный параллельный агрегатор
        self.parallel_aggregator = SafeParallelAggregator(self.scrapers, logger)
        
        # Комплексный пайплайн статистики для MarathonBet
        from utils.comprehensive_stats_pipeline import create_comprehensive_stats_pipeline
        self.stats_pipeline = create_comprehensive_stats_pipeline(self, logger)
        
        # Режим работы (можно переключать)
        self.use_parallel_mode = True
        self.enable_comprehensive_stats = True  # Флаг для полной статистики
        
        # Приоритеты источников для разных типов данных (расширенные)
        self.source_priorities = {
            'live_scores': ['sofascore', 'flashscore', 'scores24', 'marathonbet'],  # Быстрые обновления
            'detailed_stats': ['sofascore', 'flashscore'],  # Детальная статистика
            'player_ratings': ['sofascore'],  # Рейтинги игроков
            'basic_info': ['sofascore', 'flashscore', 'scores24', 'marathonbet'],  # Базовая информация
            'betting_odds': ['marathonbet', 'sofascore']  # Коэффициенты от MarathonBet
        }
        
        # Кэш для избежания дублированных запросов
        self.cache = {}
        self.cache_ttl = 30  # 30 секунд для live данных
    
    def get_aggregated_matches(self, sport: str, data_type: str = 'basic_info') -> List[Dict[str, Any]]:
        """
        Получение агрегированных данных матчей из всех источников
        """
        try:
            self.logger.info(f"Агрегатор: сбор {data_type} для {sport}")
            
            # Проверяем кэш
            cache_key = f"{sport}_{data_type}"
            if self._is_cache_valid(cache_key):
                self.logger.info(f"Агрегатор: используем кэш для {cache_key}")
                return self.cache[cache_key]['data']
            
            # Получаем данные из всех источников параллельно
            all_matches = self._fetch_from_all_sources(sport, data_type)
            
            # Объединяем и дедуплицируем данные
            aggregated_matches = self._merge_and_deduplicate(all_matches, data_type)
            
            # Кэшируем результат
            self._cache_data(cache_key, aggregated_matches)
            
            self.logger.info(f"Агрегатор: получено {len(aggregated_matches)} агрегированных матчей {sport}")
            return aggregated_matches
            
        except Exception as e:
            self.logger.error(f"Агрегатор ошибка для {sport}: {e}")
            return []
    
    def _fetch_from_all_sources(self, sport: str, data_type: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Параллельное получение данных из всех источников
        """
        all_matches = {}
        source_list = self.source_priorities.get(data_type, ['sofascore', 'livescore', 'flashscore'])
        
        # Проверяем доступность источников
        available_sources = []
        for source_name in source_list:
            scraper = self.scrapers[source_name]
            if hasattr(scraper, 'verify_connection') and scraper.verify_connection():
                available_sources.append(source_name)
                self.logger.info(f"Агрегатор: {source_name} доступен")
            else:
                self.logger.warning(f"Агрегатор: {source_name} недоступен")
        
        # Параллельно получаем данные
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_source = {}
            
            for source_name in available_sources:
                scraper = self.scrapers[source_name]
                future = executor.submit(self._safe_get_matches, scraper, sport, source_name)
                future_to_source[future] = source_name
            
            # Собираем результаты
            for future in as_completed(future_to_source, timeout=30):
                source_name = future_to_source[future]
                try:
                    matches = future.result(timeout=10)
                    all_matches[source_name] = matches
                    self.logger.info(f"Агрегатор: {source_name} вернул {len(matches)} матчей")
                except Exception as e:
                    self.logger.warning(f"Агрегатор: ошибка {source_name}: {e}")
                    all_matches[source_name] = []
        
        return all_matches
    
    def _safe_get_matches(self, scraper, sport: str, source_name: str) -> List[Dict[str, Any]]:
        """
        Безопасное получение матчей от скрапера
        """
        try:
            matches = scraper.get_live_matches(sport)
            
            # Добавляем метаданные источника
            for match in matches:
                match['source'] = source_name
                match['fetched_at'] = datetime.now().isoformat()
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Агрегатор: ошибка получения от {source_name}: {e}")
            return []
    
    def _merge_and_deduplicate(self, all_matches: Dict[str, List[Dict[str, Any]]], data_type: str) -> List[Dict[str, Any]]:
        """
        Объединение и дедупликация данных из разных источников
        """
        try:
            merged_matches = []
            match_signatures = {}  # Для дедупликации
            
            # Приоритет источников для данного типа данных
            source_priority = self.source_priorities.get(data_type, ['sofascore', 'livescore', 'flashscore'])
            
            # Обрабатываем источники в порядке приоритета
            for source_name in source_priority:
                matches = all_matches.get(source_name, [])
                
                for match in matches:
                    # Создаем сигнатуру матча для дедупликации
                    signature = self._create_match_signature(match)
                    
                    if signature not in match_signatures:
                        # Новый матч
                        enhanced_match = self._enhance_match_data(match, all_matches, signature)
                        merged_matches.append(enhanced_match)
                        match_signatures[signature] = enhanced_match
                    else:
                        # Матч уже есть, обогащаем данными из других источников
                        existing_match = match_signatures[signature]
                        self._merge_match_data(existing_match, match, source_name)
            
            # Сортируем по качеству данных
            merged_matches.sort(key=self._calculate_match_quality, reverse=True)
            
            self.logger.info(f"Агрегатор: объединено {len(merged_matches)} уникальных матчей")
            return merged_matches
            
        except Exception as e:
            self.logger.error(f"Агрегатор ошибка объединения: {e}")
            return []
    
    def _create_match_signature(self, match: Dict[str, Any]) -> str:
        """
        Создание уникальной сигнатуры матча для дедупликации
        """
        try:
            team1 = match.get('team1', '').lower().strip()
            team2 = match.get('team2', '').lower().strip()
            
            # Нормализуем названия команд
            team1 = self._normalize_team_name(team1)
            team2 = self._normalize_team_name(team2)
            
            # Создаем сигнатуру (порядок команд не важен)
            if team1 < team2:
                signature = f"{team1}_vs_{team2}"
            else:
                signature = f"{team2}_vs_{team1}"
            
            # Добавляем дату для уникальности
            today = datetime.now().strftime('%Y-%m-%d')
            return f"{signature}_{today}"
            
        except Exception as e:
            self.logger.warning(f"Агрегатор ошибка создания сигнатуры: {e}")
            return f"unknown_{time.time()}"
    
    def _normalize_team_name(self, team_name: str) -> str:
        """
        Нормализация названий команд для лучшего сопоставления
        """
        # Убираем общие сокращения и префиксы
        team_name = re.sub(r'\b(fc|cf|sc|ac|bk|hc)\b', '', team_name)
        team_name = re.sub(r'\s+', ' ', team_name).strip()
        
        # Убираем специальные символы
        team_name = re.sub(r'[^\w\s]', '', team_name)
        
        return team_name
    
    def _enhance_match_data(self, match: Dict[str, Any], all_matches: Dict, signature: str) -> Dict[str, Any]:
        """
        Обогащение данных матча информацией из других источников
        """
        enhanced_match = match.copy()
        enhanced_match['sources'] = [match.get('source', 'unknown')]
        enhanced_match['data_quality'] = self._calculate_data_quality(match)
        
        # Ищем этот же матч в других источниках
        for source_name, matches in all_matches.items():
            if source_name == match.get('source'):
                continue
                
            for other_match in matches:
                other_signature = self._create_match_signature(other_match)
                if other_signature == signature:
                    self._merge_match_data(enhanced_match, other_match, source_name)
                    break
        
        return enhanced_match
    
    def _merge_match_data(self, main_match: Dict[str, Any], additional_match: Dict[str, Any], source_name: str):
        """
        Слияние данных матча из дополнительного источника
        """
        try:
            # Добавляем источник
            if source_name not in main_match.get('sources', []):
                main_match.setdefault('sources', []).append(source_name)
            
            # Обновляем данные если они лучше или отсутствуют
            self._merge_field(main_match, additional_match, 'score', source_name)
            self._merge_field(main_match, additional_match, 'time', source_name)
            self._merge_field(main_match, additional_match, 'league', source_name)
            self._merge_field(main_match, additional_match, 'url', source_name)
            
            # Объединяем статистику
            if 'statistics' in additional_match:
                main_stats = main_match.setdefault('statistics', {})
                for stat_name, stat_value in additional_match['statistics'].items():
                    if stat_name not in main_stats:
                        main_stats[stat_name] = stat_value
            
            # Добавляем специфичные данные источника
            source_data_key = f"{source_name}_data"
            main_match[source_data_key] = {
                'score': additional_match.get('score'),
                'time': additional_match.get('time'),
                'updated': additional_match.get('fetched_at')
            }
            
            # Пересчитываем качество данных
            main_match['data_quality'] = self._calculate_data_quality(main_match)
            
        except Exception as e:
            self.logger.warning(f"Агрегатор ошибка слияния данных: {e}")
    
    def _merge_field(self, main_match: Dict, additional_match: Dict, field_name: str, source_name: str):
        """
        Слияние конкретного поля с учетом приоритета источника
        """
        try:
            main_value = main_match.get(field_name, '')
            additional_value = additional_match.get(field_name, '')
            
            # Если основное значение пустое, используем дополнительное
            if not main_value and additional_value:
                main_match[field_name] = additional_value
                return
            
            # Если дополнительное значение из приоритетного источника
            if source_name in ['livescore', 'sofascore'] and additional_value:
                if field_name in ['score', 'time']:  # Для live данных приоритет LiveScore
                    main_match[field_name] = additional_value
                    
        except Exception as e:
            self.logger.warning(f"Агрегатор ошибка слияния поля {field_name}: {e}")
    
    def _calculate_data_quality(self, match: Dict[str, Any]) -> float:
        """
        Расчет качества данных матча (0.0 - 1.0)
        """
        try:
            quality = 0.0
            
            # Базовые поля (40%)
            if match.get('team1') and match.get('team2'):
                quality += 0.2
            if match.get('score') and match.get('score') != '0:0':
                quality += 0.1
            if match.get('time'):
                quality += 0.1
            
            # Дополнительные поля (30%)
            if match.get('league'):
                quality += 0.1
            if match.get('url'):
                quality += 0.1
            if match.get('statistics'):
                quality += 0.1
            
            # Количество источников (30%)
            sources_count = len(match.get('sources', []))
            quality += min(sources_count * 0.1, 0.3)
            
            return min(quality, 1.0)
            
        except Exception as e:
            self.logger.warning(f"Агрегатор ошибка расчета качества: {e}")
            return 0.5
    
    def _calculate_match_quality(self, match: Dict[str, Any]) -> float:
        """
        Расчет общего качества матча для сортировки
        """
        return match.get('data_quality', 0.0)
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """
        Проверка валидности кэша
        """
        if cache_key not in self.cache:
            return False
        
        cached_time = self.cache[cache_key]['timestamp']
        return (datetime.now() - cached_time).seconds < self.cache_ttl
    
    def _cache_data(self, cache_key: str, data: List[Dict[str, Any]]):
        """
        Кэширование данных
        """
        self.cache[cache_key] = {
            'data': data,
            'timestamp': datetime.now()
        }
    
    def get_quick_score_updates(self, sport: str) -> Dict[str, Any]:
        """
        Быстрое обновление только счетов (для real-time мониторинга)
        """
        try:
            # Используем только быстрые источники
            quick_sources = ['livescore', 'flashscore']
            score_updates = {}
            
            for source_name in quick_sources:
                if source_name in self.scrapers:
                    scraper = self.scrapers[source_name]
                    if hasattr(scraper, 'get_quick_scores'):
                        updates = scraper.get_quick_scores(sport)
                        score_updates[source_name] = updates
            
            return score_updates
            
        except Exception as e:
            self.logger.error(f"Агрегатор быстрые обновления ошибка: {e}")
            return {}
    
    def get_source_health(self) -> Dict[str, bool]:
        """
        Проверка здоровья всех источников данных
        """
        health_status = {}
        
        for source_name, scraper in self.scrapers.items():
            try:
                if hasattr(scraper, 'verify_connection'):
                    health_status[source_name] = scraper.verify_connection()
                else:
                    health_status[source_name] = True  # Предполагаем что работает
            except:
                health_status[source_name] = False
        
        return health_status
    
    def get_matches_with_odds(self, sport: str) -> List[Dict[str, Any]]:
        """
        Получение матчей с коэффициентами (ограниченная функциональность)
        """
        try:
            self.logger.info(f"Получение {sport} с коэффициентами (ограниченно)")
            
            # Используем источники с коэффициентами
            odds_sources = self.source_priorities.get('betting_odds', ['marathonbet', 'sofascore'])
            
            for source_name in odds_sources:
                if source_name in self.scrapers:
                    try:
                        scraper = self.scrapers[source_name]
                        
                        # MarathonBet имеет специальный метод для коэффициентов
                        if source_name == 'marathonbet' and hasattr(scraper, 'get_live_matches_with_odds'):
                            matches = scraper.get_live_matches_with_odds()
                        else:
                            matches = scraper.get_live_matches(sport)
                        
                        if matches:
                            self.logger.info(f"{source_name}: получено {len(matches)} матчей с коэффициентами")
                            return matches
                                
                    except Exception as e:
                        self.logger.warning(f"Ошибка получения от {source_name}: {e}")
                        continue
            
            return []
            
        except Exception as e:
            self.logger.error(f"Ошибка получения матчей с коэффициентами: {e}")
            return []
    
    def get_comprehensive_team_stats(self, team1: str, team2: str, sport: str = 'football') -> Dict[str, Any]:
        """
        Получение комплексной статистики команд из всех источников
        """
        try:
            self.logger.info(f"Сбор комплексной статистики: {team1} vs {team2}")
            
            comprehensive_stats = {
                'match_info': {
                    'team1': team1,
                    'team2': team2,
                    'sport': sport,
                    'analysis_time': datetime.now().isoformat()
                },
                'live_data': {},
                'betting_data': {},
                'xg_analytics': {},
                'team_ratings': {},
                'player_stats': {}
            }
            
            # 1. Live данные из основных источников
            live_matches = self.get_aggregated_matches(sport, 'live_scores')
            target_match = self._find_target_match(live_matches, team1, team2)
            if target_match:
                comprehensive_stats['live_data'] = target_match
            
            # 2. Букмекерские данные
            betting_matches = self.get_matches_with_odds(sport)
            target_betting = self._find_target_match(betting_matches, team1, team2)
            if target_betting:
                comprehensive_stats['betting_data'] = target_betting
            
            # 3. Статистика команд
            if 'team_stats' in self.stats_collectors:
                team_stats = self.stats_collectors['team_stats'].get_team_statistics(team1, team2, sport)
                comprehensive_stats['team_statistics'] = team_stats
            
            # 4. xG аналитика
            if 'understat' in self.stats_collectors:
                understat_data = self.stats_collectors['understat'].get_match_xg_data(team1, team2)
                comprehensive_stats['xg_analytics'] = understat_data
            
            # 5. Рейтинги FotMob
            if 'fotmob' in self.stats_collectors:
                fotmob_data = self.stats_collectors['fotmob'].get_match_analytics(team1, team2)
                comprehensive_stats['team_ratings'] = fotmob_data
            
            return comprehensive_stats
            
        except Exception as e:
            self.logger.error(f"Ошибка сбора комплексной статистики: {e}")
            return {}
    
    def get_player_comprehensive_stats(self, player_name: str, team: str, sport: str = 'football') -> Dict[str, Any]:
        """
        Получение комплексной статистики игрока
        """
        try:
            self.logger.info(f"Сбор статистики игрока: {player_name}")
            
            player_stats = {
                'player_info': {
                    'name': player_name,
                    'team': team,
                    'sport': sport,
                    'analysis_time': datetime.now().isoformat()
                },
                'understat_stats': {},
                'fotmob_ratings': {},
                'season_performance': {},
                'match_history': []
            }
            
            # Статистика с Understat
            if 'understat' in self.stats_collectors:
                understat_stats = self.stats_collectors['understat'].get_player_xg_stats(player_name, team)
                player_stats['understat_stats'] = understat_stats
            
            # Рейтинги с FotMob
            if 'fotmob' in self.stats_collectors:
                fotmob_stats = self.stats_collectors['fotmob'].get_player_ratings(player_name, team)
                player_stats['fotmob_ratings'] = fotmob_stats
            
            return player_stats
            
        except Exception as e:
            self.logger.error(f"Ошибка сбора статистики игрока: {e}")
            return {}
    
    def _find_target_match(self, matches: List[Dict[str, Any]], team1: str, team2: str) -> Optional[Dict[str, Any]]:
        """
        Поиск целевого матча в списке
        """
        try:
            for match in matches:
                match_team1 = match.get('team1', '').lower()
                match_team2 = match.get('team2', '').lower()
                
                if ((team1.lower() in match_team1 or team1.lower() in match_team2) and
                    (team2.lower() in match_team1 or team2.lower() in match_team2)):
                    return match
            
            return None
            
        except Exception as e:
            return None
    
    def get_stats_sources_health(self) -> Dict[str, bool]:
        """
        Проверка здоровья источников статистики
        """
        stats_health = {}
        
        for source_name, collector in self.stats_collectors.items():
            try:
                if hasattr(collector, 'verify_connection'):
                    stats_health[source_name] = collector.verify_connection()
                else:
                    stats_health[source_name] = True
            except:
                stats_health[source_name] = False
        
        return stats_health
    
    async def get_aggregated_matches_parallel(self, sport: str, data_type: str = 'basic_info') -> List[Dict[str, Any]]:
        """
        НОВЫЙ: Параллельное получение агрегированных данных матчей
        """
        try:
            if not self.use_parallel_mode:
                # Fallback на последовательный режим
                return self.get_aggregated_matches(sport, data_type)
            
            self.logger.info(f"Параллельный агрегатор: сбор {data_type} для {sport}")
            
            # Используем параллельный агрегатор
            sport_results = await self.parallel_aggregator.collect_sport_parallel(sport)
            
            if sport_results:
                self.logger.info(f"Параллельный агрегатор: получено {len(sport_results)} матчей {sport}")
                return sport_results
            else:
                # Fallback на обычный режим при проблемах
                self.logger.warning(f"Параллельный режим не дал результата, переключаемся на обычный")
                return self.get_aggregated_matches(sport, data_type)
            
        except Exception as e:
            self.logger.error(f"Ошибка параллельного агрегатора для {sport}: {e}")
            # Fallback на обычный режим
            return self.get_aggregated_matches(sport, data_type)
    
    def set_parallel_mode(self, enabled: bool):
        """
        Переключение между параллельным и последовательным режимами
        """
        self.use_parallel_mode = enabled
        mode_name = "параллельный" if enabled else "последовательный"
        self.logger.info(f"Переключен на {mode_name} режим")
    
    def get_parallel_performance_stats(self) -> Dict[str, Any]:
        """
        Получение статистики производительности параллельной системы
        """
        if hasattr(self.parallel_aggregator, 'get_performance_report'):
            return self.parallel_aggregator.get_performance_report()
        return {}