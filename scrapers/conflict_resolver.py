"""
Система разрешения конфликтов данных при параллельном сборе
Обрабатывает ситуации когда разные источники дают разные данные
"""
import time
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

class DataConflictResolver:
    """
    Интеллектуальная система разрешения конфликтов данных
    """
    
    def __init__(self, logger):
        self.logger = logger
        
        # Приоритеты источников (чем выше число, тем больше доверие)
        self.source_priorities = {
            'sofascore': 10,      # Самый надежный для детальной статистики
            'flashscore': 8,      # Хорош для live данных
            'marathonbet': 9,     # Лучший для коэффициентов
            'scores24': 6,        # Дополнительный источник
            'understat': 9,       # Отличный для xG
            'fotmob': 8,          # Хорош для рейтингов
            'manual_verified': 7  # Ручные данные
        }
        
        # Специализация источников
        self.source_specialization = {
            'live_scores': ['sofascore', 'flashscore', 'scores24'],
            'betting_odds': ['marathonbet'],
            'detailed_stats': ['sofascore', 'understat'],
            'player_ratings': ['fotmob', 'sofascore'],
            'xg_data': ['understat']
        }
    
    def resolve_match_conflicts(self, conflicting_matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Разрешение конфликтов для одного матча из разных источников
        """
        try:
            if not conflicting_matches:
                return {}
            
            if len(conflicting_matches) == 1:
                return conflicting_matches[0]
            
            self.logger.info(f"Разрешение конфликта для {len(conflicting_matches)} версий матча")
            
            # Создаем итоговый матч
            resolved_match = self._create_base_match(conflicting_matches)
            
            # Разрешаем конфликты по каждому полю
            resolved_match['score'] = self._resolve_score_conflict(conflicting_matches)
            resolved_match['time'] = self._resolve_time_conflict(conflicting_matches)
            resolved_match['odds'] = self._resolve_odds_conflict(conflicting_matches)
            resolved_match['statistics'] = self._resolve_statistics_conflict(conflicting_matches)
            
            # Добавляем метаданные о разрешении конфликта
            resolved_match['conflict_resolution'] = {
                'sources_count': len(conflicting_matches),
                'sources': [m.get('source', 'unknown') for m in conflicting_matches],
                'resolution_time': datetime.now().isoformat(),
                'conflicts_found': self._detect_conflicts(conflicting_matches)
            }
            
            return resolved_match
            
        except Exception as e:
            self.logger.error(f"Ошибка разрешения конфликта: {e}")
            # Возвращаем первый доступный матч как fallback
            return conflicting_matches[0] if conflicting_matches else {}
    
    def _create_base_match(self, matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Создание базовой структуры матча
        """
        # Берем базовую информацию от самого приоритетного источника
        prioritized_matches = sorted(matches, 
                                   key=lambda m: self.source_priorities.get(m.get('source', ''), 0), 
                                   reverse=True)
        
        base_match = prioritized_matches[0].copy()
        base_match['sources'] = [m.get('source', 'unknown') for m in matches]
        
        return base_match
    
    def _resolve_score_conflict(self, matches: List[Dict[str, Any]]) -> str:
        """
        Разрешение конфликта счетов
        """
        try:
            scores = []
            
            for match in matches:
                score = match.get('score', '')
                source = match.get('source', '')
                timestamp = match.get('timestamp', '')
                
                if score and score != 'LIVE':
                    scores.append({
                        'score': score,
                        'source': source,
                        'timestamp': timestamp,
                        'priority': self.source_priorities.get(source, 0)
                    })
            
            if not scores:
                return 'LIVE'
            
            # Стратегия 1: Самые свежие данные
            latest_scores = self._get_latest_scores(scores)
            if len(latest_scores) == 1:
                self.logger.info(f"Выбран счет по времени: {latest_scores[0]['score']}")
                return latest_scores[0]['score']
            
            # Стратегия 2: Приоритет источника
            prioritized_score = max(latest_scores, key=lambda x: x['priority'])
            self.logger.info(f"Выбран счет по приоритету источника: {prioritized_score['score']} от {prioritized_score['source']}")
            return prioritized_score['score']
            
        except Exception as e:
            self.logger.warning(f"Ошибка разрешения конфликта счетов: {e}")
            return matches[0].get('score', 'LIVE')
    
    def _resolve_time_conflict(self, matches: List[Dict[str, Any]]) -> str:
        """
        Разрешение конфликта времени матча
        """
        try:
            times = []
            
            for match in matches:
                time_info = match.get('time', '')
                source = match.get('source', '')
                
                if time_info and time_info != 'LIVE':
                    # Конвертируем время в числовое значение для сравнения
                    numeric_time = self._convert_time_to_numeric(time_info)
                    
                    times.append({
                        'time': time_info,
                        'numeric': numeric_time,
                        'source': source,
                        'priority': self.source_priorities.get(source, 0)
                    })
            
            if not times:
                return 'LIVE'
            
            # Выбираем максимальное время (самое актуальное)
            latest_time = max(times, key=lambda x: (x['numeric'], x['priority']))
            
            self.logger.info(f"Выбрано время: {latest_time['time']} от {latest_time['source']}")
            return latest_time['time']
            
        except Exception as e:
            self.logger.warning(f"Ошибка разрешения конфликта времени: {e}")
            return matches[0].get('time', 'LIVE')
    
    def _resolve_odds_conflict(self, matches: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Разрешение конфликта коэффициентов
        """
        try:
            odds_data = []
            
            for match in matches:
                odds = match.get('odds', {})
                source = match.get('source', '')
                
                if odds:
                    odds_data.append({
                        'odds': odds,
                        'source': source,
                        'priority': self.source_priorities.get(source, 0),
                        'completeness': len(odds)  # Количество коэффициентов
                    })
            
            if not odds_data:
                return {}
            
            # Приоритет для коэффициентов: полнота данных + приоритет источника
            best_odds = max(odds_data, 
                          key=lambda x: (x['completeness'], x['priority']))
            
            self.logger.info(f"Выбраны коэффициенты от {best_odds['source']}: {best_odds['odds']}")
            return best_odds['odds']
            
        except Exception as e:
            self.logger.warning(f"Ошибка разрешения конфликта коэффициентов: {e}")
            return matches[0].get('odds', {})
    
    def _resolve_statistics_conflict(self, matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Разрешение конфликта статистики
        """
        try:
            combined_stats = {}
            
            for match in matches:
                stats = match.get('statistics', {})
                source = match.get('source', '')
                
                if stats:
                    for stat_name, stat_value in stats.items():
                        if stat_name not in combined_stats:
                            # Первое значение статистики
                            combined_stats[stat_name] = {
                                'value': stat_value,
                                'source': source,
                                'priority': self.source_priorities.get(source, 0)
                            }
                        else:
                            # Конфликт статистики - выбираем по приоритету
                            existing = combined_stats[stat_name]
                            current_priority = self.source_priorities.get(source, 0)
                            
                            if current_priority > existing['priority']:
                                combined_stats[stat_name] = {
                                    'value': stat_value,
                                    'source': source,
                                    'priority': current_priority
                                }
            
            # Возвращаем только значения (без метаданных)
            final_stats = {}
            for stat_name, stat_info in combined_stats.items():
                final_stats[stat_name] = stat_info['value']
            
            return final_stats
            
        except Exception as e:
            self.logger.warning(f"Ошибка разрешения конфликта статистики: {e}")
            return matches[0].get('statistics', {})
    
    def _get_latest_scores(self, scores: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Получение самых свежих счетов
        """
        try:
            if not scores:
                return []
            
            # Сортируем по времени (самые свежие первыми)
            sorted_scores = sorted(scores, 
                                 key=lambda x: self._parse_timestamp(x.get('timestamp', '')), 
                                 reverse=True)
            
            # Берем счета не старше 2 минут от самого свежего
            latest_time = self._parse_timestamp(sorted_scores[0].get('timestamp', ''))
            
            latest_scores = []
            for score in sorted_scores:
                score_time = self._parse_timestamp(score.get('timestamp', ''))
                if latest_time - score_time <= 120:  # 2 минуты
                    latest_scores.append(score)
            
            return latest_scores
            
        except Exception as e:
            return scores
    
    def _convert_time_to_numeric(self, time_str: str) -> int:
        """
        Конвертация времени матча в числовое значение для сравнения
        """
        try:
            time_str = time_str.strip().lower()
            
            # FT (Full Time) = 90+ минут
            if time_str in ['ft', 'full time']:
                return 95
            
            # HT (Half Time) = 45+ минут  
            if time_str in ['ht', 'half time']:
                return 48
            
            # Обычные минуты: "67'", "45+2'"
            minute_match = re.search(r'(\d+)', time_str)
            if minute_match:
                minutes = int(minute_match.group(1))
                
                # Добавляем дополнительное время
                extra_match = re.search(r'\+(\d+)', time_str)
                if extra_match:
                    minutes += int(extra_match.group(1))
                
                return minutes
            
            # LIVE = текущее время (предполагаем среднее)
            if time_str == 'live':
                return 50
            
            return 0
            
        except Exception as e:
            return 0
    
    def _parse_timestamp(self, timestamp_str: str) -> float:
        """
        Парсинг timestamp в unix время
        """
        try:
            if not timestamp_str:
                return 0
            
            # Пробуем разные форматы
            if 'T' in timestamp_str:
                # ISO формат
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                return dt.timestamp()
            else:
                # Unix timestamp
                return float(timestamp_str)
                
        except Exception as e:
            return time.time()
    
    def _detect_conflicts(self, matches: List[Dict[str, Any]]) -> List[str]:
        """
        Обнаружение типов конфликтов в данных
        """
        conflicts = []
        
        try:
            # Проверяем конфликты счетов
            scores = [m.get('score', '') for m in matches if m.get('score', '') != 'LIVE']
            unique_scores = set(scores)
            if len(unique_scores) > 1:
                conflicts.append(f"score_conflict: {list(unique_scores)}")
            
            # Проверяем конфликты времени
            times = [m.get('time', '') for m in matches if m.get('time', '') != 'LIVE']
            if times:
                numeric_times = [self._convert_time_to_numeric(t) for t in times]
                time_diff = max(numeric_times) - min(numeric_times)
                if time_diff > 5:  # Разница больше 5 минут
                    conflicts.append(f"time_conflict: {times} (разница {time_diff} мин)")
            
            # Проверяем конфликты коэффициентов
            odds_list = [m.get('odds', {}) for m in matches if m.get('odds', {})]
            if len(odds_list) > 1:
                # Сравниваем основные коэффициенты П1
                p1_odds = [float(odds.get('П1', 0)) for odds in odds_list if odds.get('П1')]
                if p1_odds:
                    p1_diff = max(p1_odds) - min(p1_odds)
                    if p1_diff > 0.5:  # Разница больше 0.5
                        conflicts.append(f"odds_conflict: П1 разница {p1_diff:.2f}")
            
            return conflicts
            
        except Exception as e:
            return [f"detection_error: {e}"]
    
    def validate_resolved_data(self, resolved_match: Dict[str, Any]) -> Dict[str, Any]:
        """
        Валидация разрешенных данных
        """
        try:
            validation_report = {
                'is_valid': True,
                'warnings': [],
                'errors': []
            }
            
            # Проверяем обязательные поля
            required_fields = ['team1', 'team2', 'sport']
            for field in required_fields:
                if not resolved_match.get(field):
                    validation_report['errors'].append(f"Отсутствует обязательное поле: {field}")
                    validation_report['is_valid'] = False
            
            # Проверяем разумность счета
            score = resolved_match.get('score', '')
            if score and score != 'LIVE':
                if not self._is_reasonable_score(score):
                    validation_report['warnings'].append(f"Подозрительный счет: {score}")
            
            # Проверяем разумность времени
            time_info = resolved_match.get('time', '')
            if time_info and time_info != 'LIVE':
                numeric_time = self._convert_time_to_numeric(time_info)
                if numeric_time > 120:  # Больше 120 минут
                    validation_report['warnings'].append(f"Подозрительное время: {time_info}")
            
            # Проверяем разумность коэффициентов
            odds = resolved_match.get('odds', {})
            if odds:
                for bet_type, odd_value in odds.items():
                    try:
                        odd_float = float(odd_value)
                        if odd_float < 1.01 or odd_float > 100:
                            validation_report['warnings'].append(f"Подозрительный коэффициент {bet_type}: {odd_value}")
                    except:
                        validation_report['warnings'].append(f"Некорректный коэффициент {bet_type}: {odd_value}")
            
            resolved_match['validation'] = validation_report
            
            return resolved_match
            
        except Exception as e:
            self.logger.error(f"Ошибка валидации: {e}")
            return resolved_match
    
    def _is_reasonable_score(self, score: str) -> bool:
        """
        Проверка разумности счета
        """
        try:
            # Извлекаем числа из счета
            numbers = re.findall(r'\d+', score)
            if len(numbers) >= 2:
                goals1, goals2 = int(numbers[0]), int(numbers[1])
                
                # Разумные ограничения
                if 0 <= goals1 <= 20 and 0 <= goals2 <= 20:
                    return True
            
            return False
            
        except Exception as e:
            return True  # В случае ошибки считаем разумным
    
    def create_conflict_resolution_report(self, all_conflicts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Создание отчета о разрешенных конфликтах
        """
        try:
            report = {
                'total_conflicts': len(all_conflicts),
                'conflict_types': {},
                'source_reliability': {},
                'resolution_success_rate': 0,
                'recommendations': []
            }
            
            # Анализируем типы конфликтов
            for conflict in all_conflicts:
                conflict_info = conflict.get('conflict_resolution', {})
                conflicts_found = conflict_info.get('conflicts_found', [])
                
                for conflict_type in conflicts_found:
                    conflict_category = conflict_type.split(':')[0]
                    if conflict_category not in report['conflict_types']:
                        report['conflict_types'][conflict_category] = 0
                    report['conflict_types'][conflict_category] += 1
            
            # Анализируем надежность источников
            for conflict in all_conflicts:
                sources = conflict.get('sources', [])
                for source in sources:
                    if source not in report['source_reliability']:
                        report['source_reliability'][source] = {'total': 0, 'conflicts': 0}
                    
                    report['source_reliability'][source]['total'] += 1
                    
                    # Если есть конфликты, увеличиваем счетчик
                    conflict_info = conflict.get('conflict_resolution', {})
                    if conflict_info.get('conflicts_found'):
                        report['source_reliability'][source]['conflicts'] += 1
            
            # Рассчитываем надежность в процентах
            for source, stats in report['source_reliability'].items():
                if stats['total'] > 0:
                    reliability = (stats['total'] - stats['conflicts']) / stats['total'] * 100
                    stats['reliability_percent'] = round(reliability, 1)
            
            # Генерируем рекомендации
            if report['total_conflicts'] > 0:
                report['recommendations'].append("Обнаружены конфликты данных - система автоматически разрешила их")
            
            most_unreliable = min(report['source_reliability'].items(), 
                                key=lambda x: x[1].get('reliability_percent', 100))
            
            if most_unreliable[1].get('reliability_percent', 100) < 80:
                report['recommendations'].append(f"Источник {most_unreliable[0]} показывает низкую надежность ({most_unreliable[1]['reliability_percent']}%)")
            
            return report
            
        except Exception as e:
            self.logger.error(f"Ошибка создания отчета о конфликтах: {e}")
            return {'total_conflicts': 0, 'error': str(e)}
    
    def get_conflict_resolution_stats(self) -> Dict[str, Any]:
        """
        Получение статистики разрешения конфликтов
        """
        return {
            'source_priorities': self.source_priorities,
            'specialization': self.source_specialization,
            'resolution_strategies': [
                'Приоритет по времени обновления',
                'Приоритет по надежности источника',
                'Приоритет по полноте данных',
                'Валидация разумности данных'
            ]
        }