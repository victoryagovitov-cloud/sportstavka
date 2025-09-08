"""
Комплексный пайплайн сбора статистики для матчей MarathonBet
Обеспечивает максимальное покрытие статистикой для анализа Claude AI
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import logging
from datetime import datetime

@dataclass
class StatsCollectionResult:
    """Результат сбора статистики для матча"""
    match_id: str
    team1: str
    team2: str
    sport: str
    
    # Основные данные (из MarathonBet)
    basic_data: Dict[str, Any] = field(default_factory=dict)
    
    # Детальная статистика (из SofaScore)
    detailed_stats: Optional[Dict[str, Any]] = None
    detailed_stats_source: Optional[str] = None
    
    # Дополнительная статистика (из других источников)
    additional_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Метаданные
    collection_time: float = 0.0
    success_rate: float = 0.0
    sources_attempted: List[str] = field(default_factory=list)
    sources_successful: List[str] = field(default_factory=list)
    
    # Готовность для Claude AI
    claude_ready: bool = False
    total_parameters: int = 0

class ComprehensiveStatsPipeline:
    """
    Комплексный пайплайн сбора статистики для максимального покрытия
    """
    
    def __init__(self, aggregator, logger: Optional[logging.Logger] = None):
        self.aggregator = aggregator
        self.logger = logger or logging.getLogger(__name__)
        
        # Приоритизированные источники статистики
        self.stats_sources = [
            ('sofascore_detailed', self._get_sofascore_detailed_stats),
            ('sofascore_basic', self._get_sofascore_basic_stats),
            ('team_stats_collector', self._get_team_stats_collector_stats),
            ('understat_xg', self._get_understat_stats),
            ('fotmob_ratings', self._get_fotmob_stats),
            ('flashscore_form', self._get_flashscore_form_stats),
            ('scores24_additional', self._get_scores24_additional_stats)
        ]
        
        # Улучшенное сопоставление названий команд
        self.team_name_mappings = self._init_team_name_mappings()
        
        # Статистика пайплайна
        self.pipeline_stats = {
            'total_matches_processed': 0,
            'successful_enrichments': 0,
            'failed_enrichments': 0,
            'average_collection_time': 0.0,
            'sources_success_rate': {}
        }
    
    def _init_team_name_mappings(self) -> Dict[str, List[str]]:
        """
        Расширенные сопоставления названий команд MarathonBet ↔ другие источники
        """
        return {
            # Национальные сборные
            'беларусь': ['belarus', 'белоруссия', 'bel'],
            'шотландия': ['scotland', 'sco'],
            'гибралтар': ['gibraltar', 'gib'],
            'фарерские острова': ['faroe islands', 'far', 'фареры'],
            'греция': ['greece', 'gre', 'эллада'],
            'дания': ['denmark', 'den', 'дан'],
            'израиль': ['israel', 'isr'],
            'италия': ['italy', 'ita'],
            'косово': ['kosovo', 'kos'],
            'швеция': ['sweden', 'swe'],
            'хорватия': ['croatia', 'cro'],
            'черногория': ['montenegro', 'mne'],
            'швейцария': ['switzerland', 'sui', 'свисс'],
            'словения': ['slovenia', 'svn'],
            'гана': ['ghana', 'gha'],
            'мали': ['mali', 'mli'],
            'ливия': ['libya', 'lib'],
            'эсватини': ['eswatini', 'esw', 'свазиленд'],
            
            # Клубные команды
            'эйбар': ['eibar', 'sd eibar'],
            'андорра': ['andorra', 'fc andorra'],
            'реал мадрид': ['real madrid', 'real', 'madrid'],
            'барселона': ['barcelona', 'barca', 'fcb'],
            'зенит': ['zenit', 'fc zenit'],
            'спартак': ['spartak', 'fc spartak'],
            
            # Общие сопоставления
            'фк': ['fc', 'football club'],
            'спортинг': ['sporting', 'sc']
        }
    
    async def enrich_all_marathonbet_matches(self, marathonbet_matches: List[Dict[str, Any]], 
                                           sport: str = 'football') -> List[StatsCollectionResult]:
        """
        Обогащение ВСЕХ матчей MarathonBet подробной статистикой
        """
        self.logger.info(f"Начинаем обогащение {len(marathonbet_matches)} матчей MarathonBet статистикой")
        
        enriched_results = []
        start_time = time.time()
        
        # Обрабатываем матчи пакетами для эффективности
        batch_size = 5
        for i in range(0, len(marathonbet_matches), batch_size):
            batch = marathonbet_matches[i:i + batch_size]
            
            self.logger.info(f"Обрабатываем пакет {i//batch_size + 1}/{(len(marathonbet_matches)-1)//batch_size + 1} "
                           f"({len(batch)} матчей)")
            
            batch_results = await self._process_matches_batch(batch, sport)
            enriched_results.extend(batch_results)
            
            # Пауза между пакетами для избежания блокировок
            if i + batch_size < len(marathonbet_matches):
                await asyncio.sleep(0.5)
        
        total_time = time.time() - start_time
        
        # Обновляем статистику пайплайна
        self._update_pipeline_stats(enriched_results, total_time)
        
        self.logger.info(f"Обогащение завершено: {len(enriched_results)} матчей за {total_time:.2f}с")
        
        return enriched_results
    
    async def _process_matches_batch(self, matches: List[Dict[str, Any]], sport: str) -> List[StatsCollectionResult]:
        """
        Обработка пакета матчей параллельно
        """
        tasks = []
        for match in matches:
            task = self._enrich_single_match(match, sport)
            tasks.append(task)
        
        # Выполняем параллельно с таймаутом
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Фильтруем успешные результаты
            successful_results = []
            for result in results:
                if isinstance(result, StatsCollectionResult):
                    successful_results.append(result)
                elif isinstance(result, Exception):
                    self.logger.warning(f"Ошибка обогащения матча: {result}")
            
            return successful_results
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки пакета: {e}")
            return []
    
    async def _enrich_single_match(self, match: Dict[str, Any], sport: str) -> StatsCollectionResult:
        """
        Обогащение одного матча всей доступной статистикой
        """
        team1 = match.get('team1', '')
        team2 = match.get('team2', '')
        match_id = f"{team1}:{team2}:{sport}"
        
        start_time = time.time()
        
        result = StatsCollectionResult(
            match_id=match_id,
            team1=team1,
            team2=team2,
            sport=sport,
            basic_data=match.copy()  # Копируем все данные из MarathonBet
        )
        
        # Пробуем все источники статистики по приоритету
        for source_name, source_func in self.stats_sources:
            try:
                result.sources_attempted.append(source_name)
                
                stats_data = await source_func(team1, team2, sport)
                
                if stats_data:
                    if source_name.startswith('sofascore') and not result.detailed_stats:
                        result.detailed_stats = stats_data
                        result.detailed_stats_source = source_name
                    else:
                        result.additional_stats[source_name] = stats_data
                    
                    result.sources_successful.append(source_name)
                    
            except Exception as e:
                self.logger.debug(f"Источник {source_name} не сработал для {team1} vs {team2}: {e}")
                continue
        
        # Финализируем результат
        result.collection_time = time.time() - start_time
        result.success_rate = len(result.sources_successful) / len(result.sources_attempted) if result.sources_attempted else 0
        
        # Подсчитываем общее количество параметров
        total_params = len(result.basic_data)
        if result.detailed_stats:
            total_params += len(result.detailed_stats)
        for stats in result.additional_stats.values():
            if isinstance(stats, dict):
                total_params += len(stats)
        
        result.total_parameters = total_params
        result.claude_ready = total_params >= 10  # Минимум 10 параметров для качественного анализа
        
        return result
    
    async def _get_sofascore_detailed_stats(self, team1: str, team2: str, sport: str) -> Optional[Dict[str, Any]]:
        """Получение детальной статистики из SofaScore"""
        try:
            # Пробуем разные варианты названий команд
            team1_variants = self._get_team_variants(team1)
            team2_variants = self._get_team_variants(team2)
            
            for t1 in team1_variants[:3]:  # Ограничиваем попытки
                for t2 in team2_variants[:3]:
                    try:
                        stats = self.aggregator.scrapers['sofascore'].get_detailed_match_data(t1, t2)
                        if stats and len(stats) > 5:
                            self.logger.debug(f"SofaScore статистика найдена: {t1} vs {t2}")
                            return stats
                    except:
                        continue
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Ошибка SofaScore детальной статистики: {e}")
            return None
    
    async def _get_sofascore_basic_stats(self, team1: str, team2: str, sport: str) -> Optional[Dict[str, Any]]:
        """Получение базовой статистики из SofaScore"""
        try:
            matches = self.aggregator.scrapers['sofascore'].get_live_matches(sport)
            
            # Ищем наш матч среди live матчей SofaScore
            for sofascore_match in matches:
                sf_team1 = sofascore_match.get('team1', '').lower()
                sf_team2 = sofascore_match.get('team2', '').lower()
                
                if (self._teams_match(team1, sf_team1) and self._teams_match(team2, sf_team2)) or \
                   (self._teams_match(team1, sf_team2) and self._teams_match(team2, sf_team1)):
                    return {
                        'sofascore_match_found': True,
                        'sofascore_data': sofascore_match,
                        'match_confidence': 0.8
                    }
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Ошибка SofaScore базовой статистики: {e}")
            return None
    
    async def _get_team_stats_collector_stats(self, team1: str, team2: str, sport: str) -> Optional[Dict[str, Any]]:
        """Получение статистики из TeamStatsCollector"""
        try:
            if 'team_stats' in self.aggregator.stats_collectors:
                collector = self.aggregator.stats_collectors['team_stats']
                
                if hasattr(collector, 'get_comprehensive_match_analysis'):
                    stats = collector.get_comprehensive_match_analysis(team1, team2, sport)
                    return stats if stats else None
                    
        except Exception as e:
            self.logger.debug(f"Ошибка TeamStatsCollector: {e}")
        
        return None
    
    async def _get_understat_stats(self, team1: str, team2: str, sport: str) -> Optional[Dict[str, Any]]:
        """Получение xG статистики из Understat"""
        try:
            if sport == 'football' and 'understat' in self.aggregator.stats_collectors:
                collector = self.aggregator.stats_collectors['understat']
                
                if hasattr(collector, 'get_match_xg_data'):
                    stats = collector.get_match_xg_data(team1, team2)
                    return stats if stats else None
                    
        except Exception as e:
            self.logger.debug(f"Ошибка Understat: {e}")
        
        return None
    
    async def _get_fotmob_stats(self, team1: str, team2: str, sport: str) -> Optional[Dict[str, Any]]:
        """Получение рейтингов из FotMob"""
        try:
            if 'fotmob' in self.aggregator.stats_collectors:
                collector = self.aggregator.stats_collectors['fotmob']
                
                if hasattr(collector, 'get_match_analytics'):
                    stats = collector.get_match_analytics(team1, team2)
                    return stats if stats else None
                    
        except Exception as e:
            self.logger.debug(f"Ошибка FotMob: {e}")
        
        return None
    
    async def _get_flashscore_form_stats(self, team1: str, team2: str, sport: str) -> Optional[Dict[str, Any]]:
        """Получение данных о форме из FlashScore"""
        try:
            # Ищем матч в FlashScore данных
            flashscore_matches = self.aggregator.scrapers['flashscore'].get_live_matches(sport)
            
            for fs_match in flashscore_matches:
                if self._match_teams_found(team1, team2, fs_match):
                    return {
                        'flashscore_match_found': True,
                        'flashscore_data': fs_match,
                        'form_indicators': self._extract_form_indicators(fs_match)
                    }
                    
        except Exception as e:
            self.logger.debug(f"Ошибка FlashScore формы: {e}")
        
        return None
    
    async def _get_scores24_additional_stats(self, team1: str, team2: str, sport: str) -> Optional[Dict[str, Any]]:
        """Получение дополнительных данных из Scores24"""
        try:
            scores24_matches = self.aggregator.scrapers['scores24'].get_live_matches(sport)
            
            for s24_match in scores24_matches:
                if self._match_teams_found(team1, team2, s24_match):
                    return {
                        'scores24_match_found': True,
                        'scores24_data': s24_match,
                        'additional_indicators': self._extract_additional_indicators(s24_match)
                    }
                    
        except Exception as e:
            self.logger.debug(f"Ошибка Scores24 дополнительных данных: {e}")
        
        return None
    
    def _get_team_variants(self, team_name: str) -> List[str]:
        """Получение вариантов названия команды"""
        variants = [team_name, team_name.lower(), team_name.upper()]
        
        team_lower = team_name.lower()
        
        # Добавляем известные сопоставления
        if team_lower in self.team_name_mappings:
            variants.extend(self.team_name_mappings[team_lower])
        
        # Ищем частичные совпадения
        for known_team, alternatives in self.team_name_mappings.items():
            if known_team in team_lower or team_lower in known_team:
                variants.extend(alternatives)
        
        # Автоматические варианты
        if ' ' in team_name:
            variants.append(team_name.split()[0])  # Первое слово
            variants.append(team_name.replace(' ', ''))  # Без пробелов
        
        return list(set(variants))  # Убираем дубли
    
    def _teams_match(self, marathonbet_team: str, other_team: str) -> bool:
        """Проверка совпадения названий команд"""
        mb_variants = self._get_team_variants(marathonbet_team)
        
        other_lower = other_team.lower()
        
        return any(variant.lower() in other_lower or other_lower in variant.lower() 
                  for variant in mb_variants)
    
    def _match_teams_found(self, team1: str, team2: str, match: Dict[str, Any]) -> bool:
        """Проверка, найден ли матч команд в данных другого источника"""
        match_team1 = match.get('team1', '')
        match_team2 = match.get('team2', '')
        
        # Прямое совпадение
        if ((self._teams_match(team1, match_team1) and self._teams_match(team2, match_team2)) or
            (self._teams_match(team1, match_team2) and self._teams_match(team2, match_team1))):
            return True
        
        return False
    
    def _extract_form_indicators(self, match: Dict[str, Any]) -> Dict[str, Any]:
        """Извлечение индикаторов формы из данных матча"""
        return {
            'recent_form': 'unknown',
            'home_away': match.get('venue', 'unknown'),
            'league_importance': self._assess_league_importance(match.get('league', '')),
            'time_context': match.get('time', 'unknown')
        }
    
    def _extract_additional_indicators(self, match: Dict[str, Any]) -> Dict[str, Any]:
        """Извлечение дополнительных индикаторов"""
        return {
            'live_status': match.get('time', 'unknown'),
            'score_trend': self._analyze_score_trend(match.get('score', '')),
            'match_intensity': self._assess_match_intensity(match)
        }
    
    def _assess_league_importance(self, league: str) -> str:
        """Оценка важности лиги"""
        league_lower = league.lower()
        
        if any(top in league_lower for top in ['лига чемпионов', 'чемпионат мира', 'евро']):
            return 'very_high'
        elif any(major in league_lower for top in ['рпл', 'премьер', 'ла лига', 'серия а']):
            return 'high'
        elif any(euro in league_lower for euro in ['лига европы', 'чемпионат', 'кубок']):
            return 'medium'
        else:
            return 'low'
    
    def _analyze_score_trend(self, score: str) -> str:
        """Анализ тренда счета"""
        if not score or score == 'LIVE':
            return 'unknown'
        
        try:
            if ':' in score:
                home, away = map(int, score.split(':'))
                if home > away:
                    return 'home_leading'
                elif away > home:
                    return 'away_leading'
                else:
                    return 'draw'
        except:
            pass
        
        return 'unknown'
    
    def _assess_match_intensity(self, match: Dict[str, Any]) -> str:
        """Оценка интенсивности матча"""
        score = match.get('score', '')
        time_info = match.get('time', '')
        
        if 'live' in time_info.lower():
            return 'high'
        elif any(indicator in score for indicator in [':', '-']):
            return 'medium'
        else:
            return 'low'
    
    def _update_pipeline_stats(self, results: List[StatsCollectionResult], total_time: float):
        """Обновление статистики пайплайна"""
        self.pipeline_stats['total_matches_processed'] += len(results)
        
        successful = sum(1 for r in results if r.claude_ready)
        self.pipeline_stats['successful_enrichments'] += successful
        self.pipeline_stats['failed_enrichments'] += len(results) - successful
        
        # Обновляем среднее время
        if self.pipeline_stats['total_matches_processed'] > 0:
            self.pipeline_stats['average_collection_time'] = total_time / len(results) if results else 0
        
        # Статистика по источникам
        for result in results:
            for source in result.sources_successful:
                if source not in self.pipeline_stats['sources_success_rate']:
                    self.pipeline_stats['sources_success_rate'][source] = {'attempts': 0, 'successes': 0}
                self.pipeline_stats['sources_success_rate'][source]['successes'] += 1
            
            for source in result.sources_attempted:
                if source not in self.pipeline_stats['sources_success_rate']:
                    self.pipeline_stats['sources_success_rate'][source] = {'attempts': 0, 'successes': 0}
                self.pipeline_stats['sources_success_rate'][source]['attempts'] += 1
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Получение статистики работы пайплайна"""
        success_rate = 0.0
        if self.pipeline_stats['total_matches_processed'] > 0:
            success_rate = (self.pipeline_stats['successful_enrichments'] / 
                          self.pipeline_stats['total_matches_processed']) * 100
        
        # Статистика по источникам
        sources_stats = {}
        for source, data in self.pipeline_stats['sources_success_rate'].items():
            if data['attempts'] > 0:
                source_success_rate = (data['successes'] / data['attempts']) * 100
                sources_stats[source] = {
                    'attempts': data['attempts'],
                    'successes': data['successes'],
                    'success_rate': round(source_success_rate, 2)
                }
        
        return {
            'total_matches_processed': self.pipeline_stats['total_matches_processed'],
            'successful_enrichments': self.pipeline_stats['successful_enrichments'],
            'failed_enrichments': self.pipeline_stats['failed_enrichments'],
            'success_rate': round(success_rate, 2),
            'average_collection_time': round(self.pipeline_stats['average_collection_time'], 3),
            'sources_performance': sources_stats
        }
    
    def prepare_for_claude_ai(self, enriched_results: List[StatsCollectionResult]) -> List[Dict[str, Any]]:
        """
        Подготовка обогащенных данных для анализа Claude AI
        """
        claude_ready_matches = []
        
        for result in enriched_results:
            # Структурируем данные для Claude AI
            claude_match = {
                # Основные данные из MarathonBet
                'source': 'marathonbet_comprehensive',
                'sport': result.sport,
                'team1': result.team1,
                'team2': result.team2,
                'score': result.basic_data.get('score', 'LIVE'),
                'time': result.basic_data.get('time', 'LIVE'),
                'league': result.basic_data.get('league', 'Unknown'),
                
                # Коэффициенты (главное преимущество MarathonBet)
                'odds': result.basic_data.get('odds', {}),
                
                # Детальная статистика (если доступна)
                'detailed_statistics': result.detailed_stats,
                'detailed_stats_source': result.detailed_stats_source,
                
                # Дополнительная статистика
                'additional_statistics': result.additional_stats,
                
                # Метаданные для Claude AI
                'data_quality': {
                    'total_parameters': result.total_parameters,
                    'sources_used': result.sources_successful,
                    'collection_success_rate': result.success_rate,
                    'claude_ready': result.claude_ready,
                    'enrichment_time': result.collection_time
                },
                
                # Временные метки
                'collected_at': datetime.now().isoformat(),
                'match_id': result.match_id
            }
            
            claude_ready_matches.append(claude_match)
        
        return claude_ready_matches

# Фабричная функция
def create_comprehensive_stats_pipeline(aggregator, logger: Optional[logging.Logger] = None) -> ComprehensiveStatsPipeline:
    """Создание комплексного пайплайна статистики"""
    return ComprehensiveStatsPipeline(aggregator, logger)