"""
Улучшенная система рейтингов команд и игроков
Собирает данные из множественных источников с валидацией и взвешенным расчетом
"""

import re
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging

@dataclass
class RatingSource:
    """Конфигурация источника рейтингов"""
    name: str
    weight: float
    max_rating: float
    min_rating: float = 0.0
    timeout: int = 10
    enabled: bool = True

@dataclass 
class TeamRating:
    """Рейтинг команды"""
    team_name: str
    rating: float
    confidence: float
    sources_used: List[str]
    factors: Dict[str, float]
    last_updated: datetime
    sport: str

class ImprovedRatingSystem:
    """
    Улучшенная система рейтингов с множественными источниками
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Конфигурация источников рейтингов
        self.rating_sources = {
            'sofascore': RatingSource('sofascore', 0.4, 10.0, 0.0, 10, True),
            'fotmob': RatingSource('fotmob', 0.3, 10.0, 0.0, 10, True),
            'flashscore_form': RatingSource('flashscore_form', 0.2, 5.0, 0.0, 10, True),
            'league_position': RatingSource('league_position', 0.1, 20.0, 1.0, 5, True)
        }
        
        # Факторы для взвешенного расчета
        self.weight_factors = {
            'recent_form': 0.4,        # 40% - форма в последних 5 матчах
            'head_to_head': 0.3,       # 30% - личные встречи
            'league_position': 0.2,    # 20% - позиция в лиге/турнире
            'player_ratings': 0.1      # 10% - рейтинги ключевых игроков
        }
        
        # Базовые рейтинги известных команд
        self.base_team_ratings = {
            # Топ-команды мира (футбол)
            'реал мадрид': 9.2, 'барселона': 9.0, 'манчестер сити': 8.8,
            'ливерпуль': 8.5, 'челси': 8.3, 'арсенал': 8.0, 'бавария': 8.9,
            'боруссия дортмунд': 8.1, 'ювентус': 8.2, 'милан': 7.8, 'интер': 7.9,
            'псж': 8.4, 'атлетико мадрид': 8.0, 'севилья': 7.5,
            
            # Российские команды
            'зенит': 7.5, 'спартак': 7.2, 'цска': 7.0, 'динамо': 6.8,
            'локомотив': 6.9, 'краснодар': 7.1, 'рубин': 6.5, 'ростов': 6.3,
            
            # Топ теннисисты
            'новак джокович': 9.5, 'рафаэль надаль': 9.3, 'роджер федерер': 9.1,
            'энди маррей': 8.5, 'серена уильямс': 9.4, 'мария шарапова': 8.2
        }
        
        # Кэш рейтингов (для избежания повторных запросов)
        self._ratings_cache = {}
        self._cache_ttl = 3600  # 1 час
    
    def get_comprehensive_rating(self, team1: str, team2: str, sport: str = 'football') -> Dict[str, Any]:
        """
        Получение комплексного рейтинга для пары команд/игроков
        """
        try:
            self.logger.info(f"Расчет рейтинга: {team1} vs {team2} ({sport})")
            
            # Получаем рейтинги для каждой команды
            team1_rating = self._calculate_team_rating(team1, sport)
            team2_rating = self._calculate_team_rating(team2, sport)
            
            # Рассчитываем дополнительные факторы
            h2h_factor = self._calculate_h2h_factor(team1, team2, sport)
            form_factor = self._calculate_form_factor(team1, team2, sport)
            
            # Итоговый расчет
            result = {
                'team1': {
                    'name': team1,
                    'rating': team1_rating.rating,
                    'confidence': team1_rating.confidence,
                    'sources': team1_rating.sources_used
                },
                'team2': {
                    'name': team2,
                    'rating': team2_rating.rating,
                    'confidence': team2_rating.confidence,
                    'sources': team2_rating.sources_used
                },
                'comparison': {
                    'rating_difference': abs(team1_rating.rating - team2_rating.rating),
                    'favorite': team1 if team1_rating.rating > team2_rating.rating else team2,
                    'h2h_advantage': h2h_factor,
                    'form_advantage': form_factor
                },
                'metadata': {
                    'sport': sport,
                    'calculation_time': datetime.now().isoformat(),
                    'total_confidence': (team1_rating.confidence + team2_rating.confidence) / 2
                }
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка расчета рейтинга: {e}")
            return self._get_fallback_rating(team1, team2, sport)
    
    def _calculate_team_rating(self, team_name: str, sport: str) -> TeamRating:
        """
        Расчет рейтинга одной команды/игрока
        """
        # Проверяем кэш
        cache_key = f"{team_name.lower()}:{sport}"
        if cache_key in self._ratings_cache:
            cached_data = self._ratings_cache[cache_key]
            if time.time() - cached_data['timestamp'] < self._cache_ttl:
                return cached_data['rating']
        
        # Собираем рейтинги из всех источников
        source_ratings = self._collect_multi_source_ratings(team_name, sport)
        
        # Валидация и нормализация
        normalized_ratings = self._normalize_ratings(source_ratings)
        
        # Взвешенный расчет
        final_rating = self._calculate_weighted_rating(normalized_ratings, team_name)
        
        # Применяем факторы формы
        adjusted_rating = self._apply_form_factors(final_rating, team_name, sport)
        
        # Создаем объект рейтинга
        team_rating = TeamRating(
            team_name=team_name,
            rating=adjusted_rating,
            confidence=self._calculate_confidence(source_ratings),
            sources_used=list(source_ratings.keys()),
            factors=self._get_applied_factors(team_name, sport),
            last_updated=datetime.now(),
            sport=sport
        )
        
        # Кэшируем результат
        self._ratings_cache[cache_key] = {
            'rating': team_rating,
            'timestamp': time.time()
        }
        
        return team_rating
    
    def _collect_multi_source_ratings(self, team_name: str, sport: str) -> Dict[str, float]:
        """
        Сбор рейтингов из множественных источников
        """
        ratings = {}
        
        for source_name, source_config in self.rating_sources.items():
            if not source_config.enabled:
                continue
                
            try:
                rating = self._get_rating_from_source(source_name, team_name, sport)
                if rating is not None and self._validate_rating(rating, source_config):
                    ratings[source_name] = rating
                    self.logger.debug(f"Рейтинг {team_name} из {source_name}: {rating}")
                    
            except Exception as e:
                self.logger.debug(f"Источник {source_name} недоступен для {team_name}: {e}")
        
        # Fallback к базовому рейтингу
        if not ratings:
            base_rating = self._get_base_rating(team_name)
            if base_rating:
                ratings['base'] = base_rating
        
        return ratings
    
    def _get_rating_from_source(self, source_name: str, team_name: str, sport: str) -> Optional[float]:
        """
        Получение рейтинга из конкретного источника
        """
        team_lower = team_name.lower()
        
        if source_name == 'sofascore':
            # Симуляция получения рейтинга из SofaScore
            # TODO: Интеграция с реальным API SofaScore
            if 'реал' in team_lower or 'real' in team_lower:
                return 9.2
            elif 'барс' in team_lower or 'barca' in team_lower:
                return 9.0
            elif 'зенит' in team_lower or 'zenit' in team_lower:
                return 7.5
            
        elif source_name == 'fotmob':
            # Симуляция FotMob рейтингов
            if any(top_team in team_lower for top_team in ['реал', 'барс', 'челси', 'арсенал']):
                return 8.5 + (hash(team_name) % 10) / 10  # Псевдо-случайный рейтинг
                
        elif source_name == 'flashscore_form':
            # Форма команды из FlashScore (1-5 шкала)
            return 3.0 + (hash(team_name) % 20) / 10  # Псевдо-форма
            
        elif source_name == 'league_position':
            # Позиция в лиге (1-20)
            return max(1, 15 - (hash(team_name) % 15))  # Псевдо-позиция
        
        return None
    
    def _validate_rating(self, rating: Any, source_config: RatingSource) -> bool:
        """
        Валидация рейтинга от источника
        """
        return (isinstance(rating, (int, float)) and 
                source_config.min_rating <= rating <= source_config.max_rating and
                rating > 0)  # 0 обычно означает отсутствие данных
    
    def _normalize_ratings(self, source_ratings: Dict[str, float]) -> Dict[str, float]:
        """
        Нормализация рейтингов к единой шкале 0-10
        """
        normalized = {}
        
        for source_name, rating in source_ratings.items():
            source_config = self.rating_sources.get(source_name)
            if source_config:
                # Нормализуем к шкале 0-10
                normalized_rating = ((rating - source_config.min_rating) / 
                                   (source_config.max_rating - source_config.min_rating)) * 10
                normalized[source_name] = max(0.0, min(10.0, normalized_rating))
            else:
                # Для неизвестных источников предполагаем шкалу 0-10
                normalized[source_name] = max(0.0, min(10.0, rating))
        
        return normalized
    
    def _calculate_weighted_rating(self, normalized_ratings: Dict[str, float], team_name: str) -> float:
        """
        Взвешенный расчет итогового рейтинга
        """
        if not normalized_ratings:
            return self._get_base_rating(team_name) or 5.0
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for source_name, rating in normalized_ratings.items():
            source_config = self.rating_sources.get(source_name)
            weight = source_config.weight if source_config else 0.1
            
            weighted_sum += rating * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 5.0
    
    def _apply_form_factors(self, base_rating: float, team_name: str, sport: str) -> float:
        """
        Применение факторов текущей формы
        """
        # Факторы формы команды (можно расширить интеграцией с реальными данными)
        form_adjustments = {
            'recent_wins_bonus': 0.0,      # +0.1 за каждую победу в последних 5 матчах
            'home_advantage': 0.0,         # +0.3 за домашнюю игру
            'key_players_available': 0.0,  # +0.2 если ключевые игроки здоровы
            'motivation_factor': 0.0,      # +0.4 за важность матча (дерби, плей-офф)
            'recent_form_trend': 0.0       # +/-0.5 за тренд последних результатов
        }
        
        # TODO: Интеграция с реальными источниками данных о форме
        # Пока используем базовые эвристики
        team_lower = team_name.lower()
        
        # Бонус для топ-команд (они обычно в хорошей форме)
        if any(top in team_lower for top in ['реал', 'барс', 'челси', 'бавария', 'зенит']):
            form_adjustments['recent_wins_bonus'] = 0.3
            form_adjustments['key_players_available'] = 0.2
        
        # Применяем все корректировки
        total_adjustment = sum(form_adjustments.values())
        adjusted_rating = base_rating + total_adjustment
        
        # Ограничиваем диапазон 1-10
        return max(1.0, min(10.0, adjusted_rating))
    
    def _calculate_confidence(self, source_ratings: Dict[str, float]) -> float:
        """
        Расчет уверенности в рейтинге на основе количества и качества источников
        """
        if not source_ratings:
            return 0.1  # Очень низкая уверенность
        
        # Базовая уверенность зависит от количества источников
        base_confidence = min(0.8, len(source_ratings) * 0.2)
        
        # Бонус за качественные источники
        quality_bonus = 0.0
        for source_name in source_ratings.keys():
            if source_name in ['sofascore', 'fotmob']:
                quality_bonus += 0.1
            elif source_name in ['flashscore_form', 'league_position']:
                quality_bonus += 0.05
        
        total_confidence = base_confidence + quality_bonus
        return min(1.0, total_confidence)
    
    def _get_base_rating(self, team_name: str) -> Optional[float]:
        """
        Получение базового рейтинга для известных команд
        """
        team_lower = team_name.lower()
        
        # Прямое совпадение
        if team_lower in self.base_team_ratings:
            return self.base_team_ratings[team_lower]
        
        # Поиск по частичному совпадению
        for known_team, rating in self.base_team_ratings.items():
            if known_team in team_lower or team_lower in known_team:
                return rating
        
        # Поиск по ключевым словам
        for known_team, rating in self.base_team_ratings.items():
            team_words = known_team.split()
            if any(word in team_lower for word in team_words if len(word) > 3):
                return rating * 0.9  # Небольшой штраф за неточное совпадение
        
        return None
    
    def _calculate_h2h_factor(self, team1: str, team2: str, sport: str) -> Dict[str, Any]:
        """
        Расчет фактора личных встреч
        """
        # TODO: Интеграция с реальными H2H данными
        # Пока возвращаем нейтральные значения
        return {
            'team1_wins': 0,
            'team2_wins': 0,
            'draws': 0,
            'last_meetings': [],
            'advantage': 'neutral'
        }
    
    def _calculate_form_factor(self, team1: str, team2: str, sport: str) -> Dict[str, Any]:
        """
        Расчет фактора текущей формы
        """
        # TODO: Интеграция с данными о последних результатах
        return {
            'team1_form': 'unknown',
            'team2_form': 'unknown',
            'form_trend': 'neutral'
        }
    
    def _get_applied_factors(self, team_name: str, sport: str) -> Dict[str, float]:
        """
        Получение примененных факторов для команды
        """
        return {
            'base_rating_factor': 1.0,
            'form_factor': 0.0,
            'league_factor': 0.0,
            'h2h_factor': 0.0
        }
    
    def _get_fallback_rating(self, team1: str, team2: str, sport: str) -> Dict[str, Any]:
        """
        Fallback рейтинг при ошибках
        """
        base1 = self._get_base_rating(team1) or 5.0
        base2 = self._get_base_rating(team2) or 5.0
        
        return {
            'team1': {
                'name': team1,
                'rating': base1,
                'confidence': 0.3,
                'sources': ['fallback']
            },
            'team2': {
                'name': team2,
                'rating': base2,
                'confidence': 0.3,
                'sources': ['fallback']
            },
            'comparison': {
                'rating_difference': abs(base1 - base2),
                'favorite': team1 if base1 > base2 else team2,
                'h2h_advantage': 'unknown',
                'form_advantage': 'unknown'
            },
            'metadata': {
                'sport': sport,
                'calculation_time': datetime.now().isoformat(),
                'total_confidence': 0.3,
                'fallback_used': True
            }
        }
    
    def get_rating_stats(self) -> Dict[str, Any]:
        """
        Получение статистики системы рейтингов
        """
        return {
            'cache_size': len(self._ratings_cache),
            'enabled_sources': sum(1 for source in self.rating_sources.values() if source.enabled),
            'total_sources': len(self.rating_sources),
            'base_teams_count': len(self.base_team_ratings),
            'cache_ttl_minutes': self._cache_ttl // 60
        }
    
    def clear_cache(self):
        """Очистка кэша рейтингов"""
        self._ratings_cache.clear()
        self.logger.info("Кэш рейтингов очищен")

# Глобальный экземпляр
IMPROVED_RATING_SYSTEM = ImprovedRatingSystem()

def get_improved_team_rating(team1: str, team2: str, sport: str = 'football') -> Dict[str, Any]:
    """Быстрый доступ к улучшенным рейтингам"""
    return IMPROVED_RATING_SYSTEM.get_comprehensive_rating(team1, team2, sport)