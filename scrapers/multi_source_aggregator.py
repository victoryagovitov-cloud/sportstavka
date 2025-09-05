"""
Агрегатор данных из множественных источников
Объединяет данные от SofaScore, LiveScore, FlashScore и WhoScored
"""
import asyncio
import time
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

from scrapers.sofascore_simple_quality import SofaScoreSimpleQuality
from scrapers.livescore_scraper import LiveScoreScraper
from scrapers.flashscore_scraper import FlashScoreScraper
from scrapers.whoscored_scraper import WhoScoredScraper

class MultiSourceAggregator:
    """
    Агрегатор данных из множественных источников спортивных данных
    """
    
    def __init__(self, logger):
        self.logger = logger
        
        # Инициализируем все скраперы
        self.scrapers = {
            'sofascore': SofaScoreSimpleQuality(logger),
            'livescore': LiveScoreScraper(logger),
            'flashscore': FlashScoreScraper(logger),
            'whoscored': WhoScoredScraper(logger)
        }
        
        # Приоритеты источников для разных типов данных
        self.source_priorities = {
            'live_scores': ['livescore', 'sofascore', 'flashscore'],  # Быстрые обновления
            'detailed_stats': ['sofascore', 'whoscored', 'flashscore'],  # Детальная статистика
            'player_ratings': ['whoscored', 'sofascore'],  # Рейтинги игроков
            'basic_info': ['sofascore', 'flashscore', 'livescore']  # Базовая информация
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