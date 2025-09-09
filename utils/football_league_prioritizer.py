"""
Система приоритетности футбольных лиг
Исключает киберфутбол, понижает приоритет ACL и 5x5
"""

import re
import logging
from typing import List, Dict, Any
from enum import Enum


class LeaguePriority(Enum):
    """Уровни приоритета лиг"""
    HIGHEST = 1      # Топ-лиги (Премьер-лига, Чемпионат мира)
    HIGH = 2         # Национальные лиги
    MEDIUM = 3       # Региональные лиги
    LOW = 4          # Молодежные лиги
    VERY_LOW = 5     # ACL, 5x5 - самый низкий приоритет
    EXCLUDED = 999   # Киберфутбол - полностью исключен


class FootballLeaguePrioritizer:
    """
    Приоритизация футбольных лиг согласно требованиям:
    
    ИСКЛЮЧАЕМ ПОЛНОСТЬЮ:
    - Киберфутбол (FIFA, eSports)
    
    НИЗКИЙ ПРИОРИТЕТ (последние):
    - ACL лиги
    - 5x5 турниры
    
    ВЫСОКИЙ ПРИОРИТЕТ (первые):
    - Национальные сборные
    - Премьер-лиги
    - Чемпионаты мира/Европы
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        
        # ИСКЛЮЧАЕМЫЕ ЛИГИ (киберфутбол)
        self.excluded_patterns = [
            r'\b(киберфутбол|cyber|fifa|esports|e-sports)\b',
            r'\b(bomb1to|arcos|wboy|kraftvk|lowheels)\b',  # Никнеймы игроков
            r'\b(guardian|lava|kalibrikon|lx7ss)\b',
        ]
        
        # ОЧЕНЬ НИЗКИЙ ПРИОРИТЕТ (ACL, 5x5)
        self.very_low_priority_patterns = [
            r'\b(acl|5x5|5х5|3x3|3х3)\b',
            r'\b(круговой турнир)\b'
        ]
        
        # НИЗКИЙ ПРИОРИТЕТ (молодежь)
        self.low_priority_patterns = [
            r'\b(до \d+|under \d+|u\d+)\b',
            r'\b(молодежь|юниор|junior)\b'
        ]
        
        # СРЕДНИЙ ПРИОРИТЕТ (региональные)
        self.medium_priority_patterns = [
            r'\b(дивизион|division|серия|serie)\b',
            r'\b(региональ|local|областн)\b'
        ]
        
        # ВЫСОКИЙ ПРИОРИТЕТ (национальные лиги)
        self.high_priority_patterns = [
            r'\b(премьер|premier|лига|liga|чемпионат|championship)\b',
            r'\b(бундеслига|ла лига|серия а|лига 1)\b'
        ]
        
        # МАКСИМАЛЬНЫЙ ПРИОРИТЕТ (топ-турниры)
        self.highest_priority_patterns = [
            r'\b(чемпионат мира|world cup|евро|euro|кубок|cup)\b',
            r'\b(лига чемпионов|champions league|uefa)\b',
            r'\b(отборочные|qualifier|playoff)\b'
        ]
    
    def get_league_priority(self, league_name: str) -> LeaguePriority:
        """
        Определяет приоритет лиги
        
        Args:
            league_name: Название лиги
            
        Returns:
            LeaguePriority: Уровень приоритета
        """
        
        if not league_name:
            return LeaguePriority.MEDIUM
        
        league_lower = league_name.lower()
        
        # ИСКЛЮЧАЕМ киберфутбол
        for pattern in self.excluded_patterns:
            if re.search(pattern, league_lower, re.IGNORECASE):
                self.logger.info(f"❌ ИСКЛЮЧЕН киберфутбол: {league_name}")
                return LeaguePriority.EXCLUDED
        
        # ОЧЕНЬ НИЗКИЙ приоритет (ACL, 5x5)
        for pattern in self.very_low_priority_patterns:
            if re.search(pattern, league_lower, re.IGNORECASE):
                self.logger.debug(f"⬇️ Очень низкий приоритет: {league_name}")
                return LeaguePriority.VERY_LOW
        
        # МАКСИМАЛЬНЫЙ приоритет
        for pattern in self.highest_priority_patterns:
            if re.search(pattern, league_lower, re.IGNORECASE):
                self.logger.debug(f"⬆️ Максимальный приоритет: {league_name}")
                return LeaguePriority.HIGHEST
        
        # ВЫСОКИЙ приоритет
        for pattern in self.high_priority_patterns:
            if re.search(pattern, league_lower, re.IGNORECASE):
                self.logger.debug(f"⬆️ Высокий приоритет: {league_name}")
                return LeaguePriority.HIGH
        
        # НИЗКИЙ приоритет (молодежь)
        for pattern in self.low_priority_patterns:
            if re.search(pattern, league_lower, re.IGNORECASE):
                self.logger.debug(f"⬇️ Низкий приоритет: {league_name}")
                return LeaguePriority.LOW
        
        # СРЕДНИЙ приоритет (региональные)
        for pattern in self.medium_priority_patterns:
            if re.search(pattern, league_lower, re.IGNORECASE):
                self.logger.debug(f"➡️ Средний приоритет: {league_name}")
                return LeaguePriority.MEDIUM
        
        # По умолчанию средний приоритет
        return LeaguePriority.MEDIUM
    
    def prioritize_football_matches(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Приоритизирует футбольные матчи по лигам
        
        Args:
            matches: Список футбольных матчей
            
        Returns:
            List[Dict]: Отсортированные матчи (лучшие первые)
        """
        
        if not matches:
            return []
        
        prioritized_matches = []
        excluded_count = 0
        
        # Добавляем приоритет каждому матчу
        for match in matches:
            league = match.get('league', match.get('tournament', 'Неизвестная лига'))
            priority = self.get_league_priority(league)
            
            if priority == LeaguePriority.EXCLUDED:
                excluded_count += 1
                continue  # Полностью исключаем киберфутбол
            
            match_copy = match.copy()
            match_copy['league_priority'] = priority.value
            match_copy['league_priority_name'] = priority.name
            prioritized_matches.append(match_copy)
        
        # Сортируем по приоритету (меньшее число = выше приоритет)
        prioritized_matches.sort(key=lambda m: m['league_priority'])
        
        self.logger.info(f"⚽ Футбольная приоритизация:")
        self.logger.info(f"   Исходных матчей: {len(matches)}")
        self.logger.info(f"   Исключено киберфутбола: {excluded_count}")
        self.logger.info(f"   Приоритизировано: {len(prioritized_matches)}")
        
        return prioritized_matches
    
    def get_priority_statistics(self, prioritized_matches: List[Dict[str, Any]]) -> Dict[str, int]:
        """Возвращает статистику по приоритетам"""
        
        stats = {}
        
        for match in prioritized_matches:
            priority_name = match.get('league_priority_name', 'UNKNOWN')
            stats[priority_name] = stats.get(priority_name, 0) + 1
        
        return stats
    
    def filter_top_priority_matches(self, prioritized_matches: List[Dict[str, Any]], max_matches: int = 10) -> List[Dict[str, Any]]:
        """
        Выбирает топ матчи с учетом приоритета
        
        Args:
            prioritized_matches: Приоритизированные матчи
            max_matches: Максимальное количество матчей
            
        Returns:
            List[Dict]: Топ матчи для анализа
        """
        
        if len(prioritized_matches) <= max_matches:
            return prioritized_matches
        
        # Берем лучшие матчи по приоритету
        top_matches = prioritized_matches[:max_matches]
        
        self.logger.info(f"🎯 Отобрано {len(top_matches)} топ футбольных матчей из {len(prioritized_matches)}")
        
        # Показываем статистику отобранных
        selected_stats = self.get_priority_statistics(top_matches)
        for priority, count in selected_stats.items():
            self.logger.info(f"   {priority}: {count} матчей")
        
        return top_matches


# Функция для тестирования
def test_football_prioritizer():
    """Тестирование приоритизации футбольных лиг"""
    
    import logging
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    prioritizer = FootballLeaguePrioritizer(logger)
    
    # Тестовые матчи
    test_matches = [
        {'team1': 'Реал', 'team2': 'Барса', 'league': 'Испания. Ла Лига', 'score': '1:0'},
        {'team1': 'Команда А', 'team2': 'Команда Б', 'league': '5x5. ACL. Круговой турнир', 'score': '2:1'},
        {'team1': 'Реал (Bomb1to)', 'team2': 'Барса (Arcos)', 'league': 'Киберфутбол. FIFA', 'score': '1:2'},
        {'team1': 'Бразилия до 23', 'team2': 'Аргентина до 23', 'league': 'Чемпионат мира. Отборочные', 'score': '0:1'},
        {'team1': 'Локальная А', 'team2': 'Локальная Б', 'league': 'Региональный дивизион', 'score': '1:1'},
    ]
    
    print("\\n🧪 ТЕСТ ПРИОРИТИЗАЦИИ:")
    print("="*30)
    
    # Приоритизируем
    prioritized = prioritizer.prioritize_football_matches(test_matches)
    
    print(f"\\nРезультат приоритизации:")
    for i, match in enumerate(prioritized, 1):
        priority = match['league_priority_name']
        print(f"  {i}. {match['team1']} vs {match['team2']}")
        print(f"     Лига: {match['league']}")
        print(f"     Приоритет: {priority}")
    
    # Статистика
    stats = prioritizer.get_priority_statistics(prioritized)
    print(f"\\nСтатистика приоритетов:")
    for priority, count in stats.items():
        print(f"  {priority}: {count} матчей")


if __name__ == "__main__":
    test_football_prioritizer()