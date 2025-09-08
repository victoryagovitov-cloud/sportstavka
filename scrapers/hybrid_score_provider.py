"""
Гибридный провайдер счетов для системы спортивного анализа
Комбинирует MarathonBet (коэффициенты) + SofaScore (реальные счета)
"""

import requests
import re
import logging
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from scrapers.smart_team_matcher import SmartTeamMatcher


class HybridScoreProvider:
    """
    Гибридный провайдер для получения реальных счетов live матчей
    
    ФИЛОСОФИЯ:
    - MarathonBet: коэффициенты, команды, время
    - SofaScore: реальные счета live матчей
    - Результат: полные данные для фильтрации неничейного счета
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        
        # Источники счетов по приоритету
        self.score_sources = [
            {
                'name': 'SofaScore',
                'url': 'https://www.sofascore.com/football/livescore',
                'patterns': [r'\b(\d+)\s*-\s*(\d+)\b', r'\b(\d+):(\d+)\b']
            },
            {
                'name': 'FlashScore',
                'url': 'https://www.flashscore.com/football/',
                'patterns': [r'\b(\d+)\s*-\s*(\d+)\b', r'\b(\d+):(\d+)\b']
            },
            {
                'name': 'Scores24',
                'url': 'https://scores24.live/ru/soccer?matchesFilter=live',
                'patterns': [r'\b(\d+)\s*-\s*(\d+)\b', r'\b(\d+):(\d+)\b']
            }
        ]
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3'
        }
        
        # Кэш счетов для избежания повторных запросов
        self._scores_cache = {}
        
        # Умное сопоставление команд
        self.smart_matcher = SmartTeamMatcher(logger)
        
    def get_live_scores_from_best_source(self) -> Dict[str, str]:
        """
        Получает все live счета из лучшего доступного источника
        
        Returns:
            Dict[str, str]: Словарь {команды: счет}
        """
        
        for source in self.score_sources:
            try:
                self.logger.info(f"Пробуем получить счета из {source['name']}")
                
                response = requests.get(source['url'], headers=self.headers, timeout=10)
                
                if response.status_code == 200:
                    html_content = response.text
                    scores = self._extract_scores_from_html(html_content, source['patterns'])
                    
                    if scores:
                        self.logger.info(f"✅ {source['name']}: найдено {len(scores)} счетов")
                        self._scores_cache = scores
                        return scores
                    else:
                        self.logger.warning(f"❌ {source['name']}: счета не найдены")
                else:
                    self.logger.warning(f"❌ {source['name']}: HTTP {response.status_code}")
                    
            except Exception as e:
                self.logger.error(f"❌ {source['name']}: ошибка {e}")
                continue
        
        self.logger.error("❌ Ни один источник счетов не работает")
        return {}
    
    def _extract_scores_from_html(self, html_content: str, patterns: List[str]) -> Dict[str, str]:
        """
        Извлекает счета из HTML используя паттерны
        
        Args:
            html_content: HTML контент
            patterns: Список регулярных выражений для поиска счетов
            
        Returns:
            Dict[str, str]: Словарь {уникальный_ключ: счет}
        """
        
        all_scores = set()
        
        for pattern in patterns:
            matches = re.findall(pattern, html_content)
            for match in matches:
                if len(match) == 2:
                    try:
                        home, away = int(match[0]), int(match[1])
                        # Фильтруем разумные футбольные счета
                        if 0 <= home <= 15 and 0 <= away <= 15:
                            score = f"{home}:{away}"
                            all_scores.add(score)
                    except ValueError:
                        continue
        
        # Преобразуем в словарь с уникальными ключами
        scores_dict = {}
        for i, score in enumerate(sorted(all_scores)):
            scores_dict[f"match_{i}"] = score
            
        return scores_dict
    
    def enrich_marathonbet_matches_with_real_scores(self, marathonbet_matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        БЕЗОПАСНЫЙ МЕТОД: Консервативный подход к обогащению матчей
        
        ФИЛОСОФИЯ: Лучше меньше матчей, но точных!
        
        Args:
            marathonbet_matches: Матчи от MarathonBet с коэффициентами но LIVE счетами
            
        Returns:
            List[Dict[str, Any]]: Только матчи с проверенными реальными счетами
        """
        
        self.logger.info("🛡️ КОНСЕРВАТИВНЫЙ ПОДХОД: Только проверенные данные")
        
        # Сначала пытаемся умное сопоставление
        try:
            sofascore_matches = self.smart_matcher.get_sofascore_matches_with_teams()
            
            if sofascore_matches:
                self.logger.info(f"✅ SofaScore: получено {len(sofascore_matches)} матчей")
                
                matched_matches = self.smart_matcher.match_marathonbet_with_sofascore(
                    marathonbet_matches, sofascore_matches
                )
                
                # Фильтруем только высокоуверенные сопоставления
                high_confidence_matches = []
                for match in matched_matches:
                    confidence = match.get('match_confidence', 0)
                    if confidence >= 0.7:  # Высокий порог безопасности
                        high_confidence_matches.append(match)
                
                if high_confidence_matches:
                    self.logger.info(f"✅ Принято {len(high_confidence_matches)} матчей с высокой уверенностью")
                    return high_confidence_matches
                else:
                    self.logger.warning("⚠️ Нет высокоуверенных сопоставлений")
            else:
                self.logger.warning("❌ SofaScore недоступен для сопоставления")
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка умного сопоставления: {e}")
        
        # КОНСЕРВАТИВНЫЙ FALLBACK: только матчи с реальными счетами от MarathonBet
        self.logger.info("🛡️ Переключаемся на консервативный режим")
        
        real_score_matches = []
        for match in marathonbet_matches:
            score = match.get('score', 'LIVE')
            
            # Принимаем только матчи с реальными (не LIVE) счетами
            if score != 'LIVE' and ':' in score and score != '0:0':
                try:
                    home, away = map(int, score.split(':'))
                    if 0 <= home <= 10 and 0 <= away <= 10:  # Разумные счета
                        match['score_source'] = 'marathonbet_verified'
                        match['quality_level'] = 'high'
                        real_score_matches.append(match)
                except ValueError:
                    continue
        
        self.logger.info(f"✅ Консервативный режим: {len(real_score_matches)} проверенных матчей")
        
        if real_score_matches:
            self.logger.info("🎯 Используем только проверенные счета от MarathonBet")
        else:
            self.logger.warning("⚠️ Нет матчей с проверенными счетами")
            self.logger.info("💡 Рекомендация: дождаться матчей с реальными счетами")
        
        return real_score_matches
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Возвращает статистику работы гибридного провайдера
        """
        
        cached_scores = len(self._scores_cache)
        
        if cached_scores > 0:
            # Анализируем кэшированные счета
            non_draw_count = 0
            draw_count = 0
            
            for score in self._scores_cache.values():
                try:
                    home, away = map(int, score.split(':'))
                    if home == away:
                        draw_count += 1
                    else:
                        non_draw_count += 1
                except:
                    continue
            
            return {
                'total_scores': cached_scores,
                'non_draw_scores': non_draw_count,
                'draw_scores': draw_count,
                'non_draw_percentage': (non_draw_count / cached_scores * 100) if cached_scores > 0 else 0,
                'cache_status': 'active',
                'best_source': self.score_sources[0]['name'] if self.score_sources else 'unknown'
            }
        else:
            return {
                'total_scores': 0,
                'non_draw_scores': 0,
                'draw_scores': 0,
                'non_draw_percentage': 0,
                'cache_status': 'empty',
                'best_source': 'none'
            }


# Функция для быстрого тестирования
def test_hybrid_provider():
    """Тестирование гибридного провайдера"""
    
    import logging
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    provider = HybridScoreProvider(logger)
    
    # Тестируем получение счетов
    scores = provider.get_live_scores_from_best_source()
    
    print(f"Получено счетов: {len(scores)}")
    
    if scores:
        print("Примеры счетов:")
        for key, score in list(scores.items())[:5]:
            print(f"  {key}: {score}")
    
    # Статистика
    stats = provider.get_statistics()
    print(f"\nСтатистика:")
    print(f"  Всего: {stats['total_scores']}")
    print(f"  Неничейных: {stats['non_draw_scores']}")
    print(f"  Процент неничейных: {stats['non_draw_percentage']:.1f}%")


if __name__ == "__main__":
    test_hybrid_provider()