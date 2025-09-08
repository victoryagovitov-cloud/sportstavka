"""
Умное сопоставление команд между разными источниками
Решает проблему случайного присвоения счетов командам
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from difflib import SequenceMatcher
import requests
from bs4 import BeautifulSoup


class SmartTeamMatcher:
    """
    Умное сопоставление команд между MarathonBet и SofaScore
    
    ПРОБЛЕМА:
    - MarathonBet: команды + коэффициенты + LIVE счета
    - SofaScore: только счета без точных названий команд
    
    РЕШЕНИЕ:
    - Извлекаем команды из SofaScore тоже
    - Сопоставляем по fuzzy matching
    - Присваиваем правильные счета правильным командам
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3'
        }
        
        # Кэш для сопоставлений
        self._team_matches_cache = {}
        
    def get_sofascore_matches_with_teams(self) -> List[Dict[str, Any]]:
        """
        Получает матчи из SofaScore с названиями команд И счетами
        
        Returns:
            List[Dict]: [{'team1': 'Команда А', 'team2': 'Команда Б', 'score': '1:0'}, ...]
        """
        
        try:
            url = 'https://www.sofascore.com/football/livescore'
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                self.logger.error(f"SofaScore HTTP {response.status_code}")
                return []
                
            soup = BeautifulSoup(response.text, 'html.parser')
            matches = []
            
            # Ищем блоки матчей в SofaScore
            match_elements = soup.find_all(['div', 'tr', 'li'], class_=re.compile(r'match|game|event', re.I))
            
            for element in match_elements:
                match_data = self._extract_match_from_sofascore_element(element)
                if match_data:
                    matches.append(match_data)
            
            # Дедуплицируем
            unique_matches = self._deduplicate_sofascore_matches(matches)
            
            self.logger.info(f"SofaScore: извлечено {len(unique_matches)} матчей с командами и счетами")
            return unique_matches
            
        except Exception as e:
            self.logger.error(f"Ошибка получения матчей SofaScore: {e}")
            return []
    
    def _extract_match_from_sofascore_element(self, element) -> Optional[Dict[str, Any]]:
        """
        Извлекает данные матча из элемента SofaScore
        """
        
        try:
            text = element.get_text(strip=True)
            
            # Ищем паттерны: "Команда А vs Команда Б 1:0"
            patterns = [
                r'([A-Za-zА-Яа-я\s]+?)\s+vs?\s+([A-Za-zА-Яа-я\s]+?)\s+(\d+[:-]\d+)',
                r'([A-Za-zА-Яа-я\s]+?)\s*-\s*([A-Za-zА-Яа-я\s]+?)\s+(\d+[:-]\d+)',
                r'([A-Za-zА-Яа-я\s]{3,})\s+(\d+[:-]\d+)\s+([A-Za-zА-Яа-я\s]{3,})',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    if len(match.groups()) == 3:
                        team1, team2, score = match.groups()
                        
                        # Очищаем названия команд
                        team1 = self._clean_team_name(team1)
                        team2 = self._clean_team_name(team2)
                        score = score.replace('-', ':')
                        
                        # Проверяем валидность
                        if (len(team1) >= 3 and len(team2) >= 3 and 
                            team1.lower() != team2.lower() and
                            ':' in score):
                            
                            return {
                                'team1': team1,
                                'team2': team2,
                                'score': score,
                                'source': 'sofascore_smart'
                            }
            
            return None
            
        except Exception as e:
            return None
    
    def _clean_team_name(self, name: str) -> str:
        """Очищает название команды"""
        
        # Убираем лишние символы
        name = re.sub(r'[^\w\s]', '', name).strip()
        
        # Убираем множественные пробелы
        name = re.sub(r'\s+', ' ', name)
        
        return name
    
    def _deduplicate_sofascore_matches(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Убирает дубликаты матчей"""
        
        seen = set()
        unique = []
        
        for match in matches:
            key = f"{match['team1'].lower()}_{match['team2'].lower()}_{match['score']}"
            if key not in seen:
                seen.add(key)
                unique.append(match)
        
        return unique
    
    def match_marathonbet_with_sofascore(self, 
                                       marathonbet_matches: List[Dict[str, Any]], 
                                       sofascore_matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        КЛЮЧЕВОЙ МЕТОД: Сопоставляет матчи MarathonBet с матчами SofaScore
        
        Args:
            marathonbet_matches: Матчи от MarathonBet (команды + коэффициенты + LIVE счета)
            sofascore_matches: Матчи от SofaScore (команды + реальные счета)
            
        Returns:
            List[Dict]: Матчи MarathonBet с правильными счетами от SofaScore
        """
        
        matched_matches = []
        sofascore_used = set()
        
        self.logger.info(f"Сопоставляем {len(marathonbet_matches)} матчей MarathonBet с {len(sofascore_matches)} матчами SofaScore")
        
        for mb_match in marathonbet_matches:
            mb_team1 = mb_match.get('team1', '').strip()
            mb_team2 = mb_match.get('team2', '').strip()
            
            if not mb_team1 or not mb_team2:
                continue
            
            # Ищем лучшее сопоставление в SofaScore
            best_match = None
            best_score = 0
            best_index = -1
            
            for i, ss_match in enumerate(sofascore_matches):
                if i in sofascore_used:
                    continue
                    
                ss_team1 = ss_match.get('team1', '').strip()
                ss_team2 = ss_match.get('team2', '').strip()
                
                # Вычисляем similarity score
                similarity = self._calculate_team_similarity(mb_team1, mb_team2, ss_team1, ss_team2)
                
                if similarity > best_score and similarity > 0.6:  # Минимальный порог
                    best_score = similarity
                    best_match = ss_match
                    best_index = i
            
            if best_match:
                # Создаем обогащенный матч
                enriched_match = mb_match.copy()
                enriched_match['score'] = best_match['score']
                enriched_match['score_source'] = 'sofascore_matched'
                enriched_match['original_score'] = mb_match.get('score', 'LIVE')
                enriched_match['match_confidence'] = best_score
                enriched_match['matched_with'] = f"{best_match['team1']} vs {best_match['team2']}"
                
                matched_matches.append(enriched_match)
                sofascore_used.add(best_index)
                
                self.logger.debug(f"✅ Сопоставлено: '{mb_team1} vs {mb_team2}' → '{best_match['team1']} vs {best_match['team2']}' ({best_score:.2f})")
            else:
                # Не нашли сопоставление - оставляем оригинальный матч
                mb_match['score_source'] = 'marathonbet_original'
                matched_matches.append(mb_match)
                
                self.logger.debug(f"❌ Не сопоставлено: '{mb_team1} vs {mb_team2}'")
        
        match_rate = len([m for m in matched_matches if m.get('score_source') == 'sofascore_matched']) / len(marathonbet_matches) * 100
        
        self.logger.info(f"✅ Сопоставлено {match_rate:.1f}% матчей MarathonBet с SofaScore")
        
        return matched_matches
    
    def _calculate_team_similarity(self, mb_team1: str, mb_team2: str, ss_team1: str, ss_team2: str) -> float:
        """
        Вычисляет similarity между командами из разных источников
        
        Returns:
            float: 0.0-1.0, где 1.0 = идеальное совпадение
        """
        
        # Нормализуем названия
        mb_team1_norm = self._normalize_team_name(mb_team1)
        mb_team2_norm = self._normalize_team_name(mb_team2)
        ss_team1_norm = self._normalize_team_name(ss_team1)
        ss_team2_norm = self._normalize_team_name(ss_team2)
        
        # Проверяем прямое и обратное сопоставление
        direct_sim = (self._string_similarity(mb_team1_norm, ss_team1_norm) + 
                     self._string_similarity(mb_team2_norm, ss_team2_norm)) / 2
        
        reverse_sim = (self._string_similarity(mb_team1_norm, ss_team2_norm) + 
                      self._string_similarity(mb_team2_norm, ss_team1_norm)) / 2
        
        return max(direct_sim, reverse_sim)
    
    def _normalize_team_name(self, name: str) -> str:
        """Нормализует название команды для сравнения"""
        
        # Приводим к нижнему регистру
        name = name.lower()
        
        # Убираем общие слова
        common_words = ['fc', 'фк', 'club', 'клуб', 'team', 'команда', 'united', 'юнайтед']
        for word in common_words:
            name = re.sub(rf'\b{word}\b', '', name)
        
        # Убираем лишние символы и пробелы
        name = re.sub(r'[^\w\s]', '', name)
        name = re.sub(r'\s+', ' ', name).strip()
        
        return name
    
    def _string_similarity(self, s1: str, s2: str) -> float:
        """Вычисляет similarity между строками"""
        
        if not s1 or not s2:
            return 0.0
            
        return SequenceMatcher(None, s1, s2).ratio()
    
    def get_matching_statistics(self, matched_matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Возвращает статистику сопоставления"""
        
        total = len(matched_matches)
        matched = len([m for m in matched_matches if m.get('score_source') == 'sofascore_matched'])
        
        if matched > 0:
            avg_confidence = sum(m.get('match_confidence', 0) for m in matched_matches if m.get('match_confidence')) / matched
        else:
            avg_confidence = 0
        
        return {
            'total_matches': total,
            'successfully_matched': matched,
            'match_rate_percent': (matched / total * 100) if total > 0 else 0,
            'average_confidence': avg_confidence,
            'unmatched': total - matched
        }


# Функция для тестирования
def test_smart_matcher():
    """Тестирование умного сопоставления"""
    
    import logging
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    matcher = SmartTeamMatcher(logger)
    
    # Получаем матчи из SofaScore
    sofascore_matches = matcher.get_sofascore_matches_with_teams()
    
    print(f"SofaScore матчи: {len(sofascore_matches)}")
    for match in sofascore_matches[:5]:
        print(f"  {match['team1']} vs {match['team2']}: {match['score']}")


if __name__ == "__main__":
    test_smart_matcher()