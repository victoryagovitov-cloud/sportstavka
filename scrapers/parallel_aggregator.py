"""
Безопасный параллельный агрегатор данных
Собирает данные от всех источников одновременно с защитой от конфликтов
"""
import asyncio
import aiohttp
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from scrapers.conflict_resolver import DataConflictResolver

class SafeParallelAggregator:
    """
    Безопасный параллельный сборщик данных с разрешением конфликтов
    """
    
    def __init__(self, scrapers: Dict[str, Any], logger):
        self.scrapers = scrapers
        self.logger = logger
        self.conflict_resolver = DataConflictResolver(logger)
        
        # Настройки безопасности
        self.source_timeouts = {
            'sofascore': 10,      # Быстрый источник
            'flashscore': 20,     # Средний источник  
            'scores24': 15,       # Средний с CAPTCHA
            'marathonbet': 35     # Медленный источник
        }
        
        # Ограничения запросов к доменам
        self.domain_limits = {
            'sofascore.com': 1,
            'flashscore.com': 2,
            'scores24.live': 1,
            'marathonbet.ru': 1
        }
        
        # Статистика работы
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'conflicts_resolved': 0,
            'average_time': 0
        }
    
    async def collect_all_sports_parallel(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Параллельный сбор данных по всем видам спорта
        """
        try:
            self.logger.info("Начинаем безопасный параллельный сбор данных")
            start_time = time.time()
            
            # Собираем все виды спорта параллельно
            sports = ['football', 'tennis', 'table_tennis', 'handball']
            
            tasks = []
            for sport in sports:
                task = self.collect_sport_parallel(sport)
                tasks.append((sport, task))
            
            # Ждем завершения всех задач
            results = {}
            
            for sport, task in tasks:
                try:
                    sport_matches = await asyncio.wait_for(task, timeout=60)
                    results[sport] = sport_matches
                    self.logger.info(f"Параллельный сбор {sport}: {len(sport_matches)} матчей")
                except asyncio.TimeoutError:
                    self.logger.warning(f"Таймаут для {sport}")
                    results[sport] = []
                except Exception as e:
                    self.logger.error(f"Ошибка сбора {sport}: {e}")
                    results[sport] = []
            
            total_time = time.time() - start_time
            self._update_stats(total_time, results)
            
            self.logger.info(f"Параллельный сбор завершен за {total_time:.2f} сек")
            return results
            
        except Exception as e:
            self.logger.error(f"Критическая ошибка параллельного сбора: {e}")
            return {}
    
    async def collect_sport_parallel(self, sport: str) -> List[Dict[str, Any]]:
        """
        Параллельный сбор данных для одного вида спорта
        """
        try:
            self.logger.info(f"Параллельный сбор {sport}")
            
            # Создаем задачи для каждого источника
            tasks = {}
            
            for source_name, scraper in self.scrapers.items():
                if hasattr(scraper, 'get_live_matches'):
                    task = self._safe_source_request(source_name, scraper, sport)
                    tasks[source_name] = task
            
            # Запускаем все задачи параллельно
            results = {}
            
            for source_name, task in tasks.items():
                try:
                    timeout = self.source_timeouts.get(source_name, 30)
                    result = await asyncio.wait_for(task, timeout=timeout)
                    results[source_name] = result
                    self.stats['successful_requests'] += 1
                    
                except asyncio.TimeoutError:
                    self.logger.warning(f"{source_name} превысил таймаут {timeout} сек")
                    results[source_name] = []
                    self.stats['failed_requests'] += 1
                    
                except Exception as e:
                    self.logger.warning(f"{source_name} ошибка: {e}")
                    results[source_name] = []
                    self.stats['failed_requests'] += 1
            
            # Безопасно объединяем результаты
            merged_matches = self._merge_results_safely(results, sport)
            
            return merged_matches
            
        except Exception as e:
            self.logger.error(f"Ошибка параллельного сбора {sport}: {e}")
            return []
    
    async def _safe_source_request(self, source_name: str, scraper: Any, sport: str) -> List[Dict[str, Any]]:
        """
        Безопасный запрос к источнику
        """
        try:
            self.logger.debug(f"Запрос к {source_name} для {sport}")
            
            # Имитируем async через ThreadPoolExecutor для синхронных скраперов
            loop = asyncio.get_event_loop()
            
            def sync_request():
                try:
                    matches = scraper.get_live_matches(sport)
                    
                    # Добавляем метаданные
                    for match in matches:
                        match['source'] = source_name
                        match['fetch_time'] = time.time()
                        match['timestamp'] = datetime.now().isoformat()
                    
                    return matches
                    
                except Exception as e:
                    self.logger.warning(f"Синхронная ошибка {source_name}: {e}")
                    return []
            
            # Выполняем в отдельном потоке
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = loop.run_in_executor(executor, sync_request)
                result = await future
            
            self.logger.debug(f"{source_name} вернул {len(result)} матчей для {sport}")
            return result
            
        except Exception as e:
            self.logger.warning(f"Ошибка безопасного запроса {source_name}: {e}")
            return []
    
    def _merge_results_safely(self, results: Dict[str, List[Dict[str, Any]]], sport: str) -> List[Dict[str, Any]]:
        """
        Безопасное объединение результатов с разрешением конфликтов
        """
        try:
            all_matches = []
            
            # Собираем все матчи от всех источников
            for source_name, matches in results.items():
                if matches:
                    self.logger.info(f"Получено от {source_name}: {len(matches)} матчей")
                    all_matches.extend(matches)
            
            if not all_matches:
                self.logger.warning("Нет данных от источников")
                return []
            
            # Группируем матчи по командам для обнаружения дублей
            match_groups = self._group_matches_by_teams(all_matches)
            
            # Разрешаем конфликты для каждой группы
            final_matches = []
            
            for team_pair, match_list in match_groups.items():
                if len(match_list) == 1:
                    # Нет конфликта
                    final_matches.append(match_list[0])
                else:
                    # Есть конфликт - разрешаем
                    self.logger.info(f"Разрешение конфликта для {team_pair}: {len(match_list)} версий")
                    resolved_match = self.conflict_resolver.resolve_match_conflicts(match_list)
                    
                    if resolved_match:
                        # Валидируем разрешенные данные
                        validated_match = self.conflict_resolver.validate_resolved_data(resolved_match)
                        final_matches.append(validated_match)
                        self.stats['conflicts_resolved'] += 1
            
            self.logger.info(f"Объединение завершено: {len(final_matches)} финальных матчей")
            return final_matches
            
        except Exception as e:
            self.logger.error(f"Ошибка безопасного объединения: {e}")
            # Fallback: возвращаем все матчи без разрешения конфликтов
            return all_matches
    
    def _group_matches_by_teams(self, matches: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Группировка матчей по командам для обнаружения дублей
        """
        try:
            groups = {}
            
            for match in matches:
                team1 = match.get('team1', '').lower().strip()
                team2 = match.get('team2', '').lower().strip()
                
                if team1 and team2:
                    # Создаем уникальный ключ (порядок команд не важен)
                    key = tuple(sorted([team1, team2]))
                    
                    if key not in groups:
                        groups[key] = []
                    
                    groups[key].append(match)
            
            return groups
            
        except Exception as e:
            self.logger.error(f"Ошибка группировки матчей: {e}")
            return {}
    
    def _update_stats(self, execution_time: float, results: Dict[str, List[Dict[str, Any]]]):
        """
        Обновление статистики работы
        """
        try:
            self.stats['total_requests'] += 1
            
            # Обновляем среднее время
            if self.stats['total_requests'] == 1:
                self.stats['average_time'] = execution_time
            else:
                self.stats['average_time'] = (
                    self.stats['average_time'] * (self.stats['total_requests'] - 1) + execution_time
                ) / self.stats['total_requests']
            
            # Подсчитываем успешные результаты
            total_matches = sum(len(matches) for matches in results.values())
            if total_matches > 0:
                self.stats['successful_requests'] += 1
            
        except Exception as e:
            self.logger.warning(f"Ошибка обновления статистики: {e}")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """
        Отчет о производительности параллельной системы
        """
        return {
            'statistics': self.stats,
            'source_timeouts': self.source_timeouts,
            'domain_limits': self.domain_limits,
            'conflict_resolution_stats': self.conflict_resolver.get_conflict_resolution_stats()
        }
    
    def enable_debug_mode(self):
        """
        Включение режима отладки для диагностики конфликтов
        """
        self.logger.setLevel(logging.DEBUG)
        self.logger.info("Включен режим отладки параллельной системы")
    
    def disable_parallel_mode(self):
        """
        Отключение параллельного режима (возврат к последовательному)
        """
        self.logger.info("Параллельный режим отключен, возврат к последовательному")
        # Здесь можно добавить логику переключения на старый агрегатор