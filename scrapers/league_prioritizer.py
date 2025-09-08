"""
Система приоритизации лиг и матчей
Определяет важность матчей для телеграм каналов российских пользователей
"""

import re
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from enum import Enum

class LeaguePriority(Enum):
    """Приоритеты лиг"""
    TOP = 1        # Топ-лиги (РПЛ, АПЛ, Ла Лига, etc)
    EUROPEAN = 2   # Европейские лиги 
    MAJOR = 3      # Крупные турниры
    REGIONAL = 4   # Региональные лиги
    MINOR = 5      # Малоизвестные лиги

@dataclass
class LeagueInfo:
    """Информация о лиге"""
    name: str
    priority: LeaguePriority
    country: str
    keywords: List[str]
    min_coefficient: float = 1.05
    max_matches: int = 20

class LeaguePrioritizer:
    """
    Система приоритизации лиг для российских пользователей
    """
    
    def __init__(self):
        self.league_patterns = self._initialize_league_patterns()
        self.priority_limits = {
            LeaguePriority.TOP: 25,       # До 25 матчей из топ-лиг
            LeaguePriority.EUROPEAN: 15,  # До 15 из европейских
            LeaguePriority.MAJOR: 10,     # До 10 из крупных турниров
            LeaguePriority.REGIONAL: 5,   # До 5 из региональных
            LeaguePriority.MINOR: 3       # До 3 из малоизвестных
        }
    
    def _initialize_league_patterns(self) -> Dict[LeaguePriority, List[LeagueInfo]]:
        """Инициализация паттернов лиг с приоритетами"""
        
        patterns = {
            LeaguePriority.TOP: [
                # Российские лиги (высший приоритет)
                LeagueInfo("РПЛ", LeaguePriority.TOP, "Россия", 
                          ["рпл", "российская премьер", "премьер лига", "россии"]),
                LeagueInfo("ФНЛ", LeaguePriority.TOP, "Россия",
                          ["фнл", "национальная лига", "первая лига"]),
                
                # Топ-5 европейских лиг
                LeagueInfo("АПЛ", LeaguePriority.TOP, "Англия",
                          ["премьер лига", "англи", "premier league", "epl"]),
                LeagueInfo("Ла Лига", LeaguePriority.TOP, "Испания", 
                          ["ла лига", "laliga", "испан", "primera"]),
                LeagueInfo("Бундеслига", LeaguePriority.TOP, "Германия",
                          ["бундеслига", "bundesliga", "герман", "1. liga"]),
                LeagueInfo("Серия А", LeaguePriority.TOP, "Италия",
                          ["серия а", "serie a", "итали", "seria"]),
                LeagueInfo("Лига 1", LeaguePriority.TOP, "Франция",
                          ["лига 1", "ligue 1", "франц", "l1"]),
                
                # СНГ лиги (важны для российских пользователей)
                LeagueInfo("УПЛ", LeaguePriority.TOP, "Украина",
                          ["упл", "украин", "премьер лига украины"]),
                LeagueInfo("Беларусь", LeaguePriority.TOP, "Беларусь",
                          ["беларус", "высшая лига", "belarus"]),
            ],
            
            LeaguePriority.EUROPEAN: [
                # Вторые дивизионы топ-стран
                LeagueInfo("Чемпионшип", LeaguePriority.EUROPEAN, "Англия",
                          ["чемпионшип", "championship", "англия 2"]),
                LeagueInfo("Сегунда", LeaguePriority.EUROPEAN, "Испания",
                          ["сегунда", "segunda", "испания 2", "2 дивизион"]),
                LeagueInfo("2.Бундеслига", LeaguePriority.EUROPEAN, "Германия",
                          ["2 бундеслига", "2.bundesliga", "германия 2"]),
                LeagueInfo("Серия Б", LeaguePriority.EUROPEAN, "Италия",
                          ["серия б", "serie b", "италия 2"]),
                LeagueInfo("Лига 2", LeaguePriority.EUROPEAN, "Франция",
                          ["лига 2", "ligue 2", "франция 2"]),
                
                # Другие европейские топ-лиги
                LeagueInfo("Эредивизи", LeaguePriority.EUROPEAN, "Нидерланды",
                          ["эредивизи", "eredivisie", "нидерланд", "голланд"]),
                LeagueInfo("Примейра", LeaguePriority.EUROPEAN, "Португалия",
                          ["примейра", "primeira", "португал"]),
                LeagueInfo("Жюпиле", LeaguePriority.EUROPEAN, "Бельгия",
                          ["жюпиле", "jupiler", "бельги"]),
                LeagueInfo("Суперлига", LeaguePriority.EUROPEAN, "Турция",
                          ["суперлига", "super lig", "турци"]),
            ],
            
            LeaguePriority.MAJOR: [
                # Международные турниры
                LeagueInfo("Лига Чемпионов", LeaguePriority.MAJOR, "UEFA",
                          ["лига чемпионов", "champions league", "ucl", "лч"]),
                LeagueInfo("Лига Европы", LeaguePriority.MAJOR, "UEFA", 
                          ["лига европы", "europa league", "uel", "ле"]),
                LeagueInfo("Лига Конференций", LeaguePriority.MAJOR, "UEFA",
                          ["лига конференций", "conference league", "uecl"]),
                
                # Чемпионаты мира и Европы
                LeagueInfo("ЧМ", LeaguePriority.MAJOR, "FIFA",
                          ["чм", "чемпионат мира", "world cup", "fifa"]),
                LeagueInfo("Евро", LeaguePriority.MAJOR, "UEFA",
                          ["евро", "чемпионат европы", "euro", "european"]),
                LeagueInfo("Лига Наций", LeaguePriority.MAJOR, "UEFA",
                          ["лига наций", "nations league", "уефа"]),
            ],
            
            LeaguePriority.REGIONAL: [
                # Скандинавские лиги
                LeagueInfo("Аллсвенскан", LeaguePriority.REGIONAL, "Швеция",
                          ["аллсвенскан", "allsvenskan", "швеци"]),
                LeagueInfo("Элитесериен", LeaguePriority.REGIONAL, "Норвегия",
                          ["элитесериен", "eliteserien", "норвеги"]),
                
                # Восточная Европа
                LeagueInfo("Экстракласа", LeaguePriority.REGIONAL, "Польша",
                          ["экстракласа", "ekstraklasa", "польш"]),
                LeagueInfo("Фортуна Лига", LeaguePriority.REGIONAL, "Чехия",
                          ["фортуна", "fortuna liga", "чехи"]),
                
                # Америки  
                LeagueInfo("MLS", LeaguePriority.REGIONAL, "США",
                          ["mls", "мажор лиг", "сша", "америк"]),
                LeagueInfo("Бразилейрао", LeaguePriority.REGIONAL, "Бразилия",
                          ["бразилейрао", "brasileirao", "бразили", "серия а"]),
            ],
            
            LeaguePriority.MINOR: [
                # Азиатские лиги
                LeagueInfo("Азия", LeaguePriority.MINOR, "Азия",
                          ["азиат", "asia", "япони", "корея", "китай", "индонези", "малайзи"]),
                
                # Африканские лиги
                LeagueInfo("Африка", LeaguePriority.MINOR, "Африка", 
                          ["африк", "africa", "египет", "марокко", "нигери", "гана"]),
                
                # Океания и прочие
                LeagueInfo("Прочие", LeaguePriority.MINOR, "Прочие",
                          ["океани", "oceania", "австрали", "новая зеландия"])
            ]
        }
        
        return patterns
    
    def determine_league_priority(self, match_info: Dict[str, Any]) -> Tuple[LeaguePriority, str]:
        """
        Определяет приоритет матча на основе информации о лиге
        
        Args:
            match_info: Информация о матче (должна содержать league, team1, team2)
            
        Returns:
            Tuple[LeaguePriority, str]: Приоритет и название лиги
        """
        league_text = str(match_info.get('league', '')).lower()
        team1 = str(match_info.get('team1', '')).lower()
        team2 = str(match_info.get('team2', '')).lower()
        
        # Объединяем весь текст для анализа
        full_text = f"{league_text} {team1} {team2}".lower()
        
        # Проверяем по приоритетам (от высокого к низкому)
        for priority in [LeaguePriority.TOP, LeaguePriority.EUROPEAN, 
                        LeaguePriority.MAJOR, LeaguePriority.REGIONAL, 
                        LeaguePriority.MINOR]:
            
            for league_info in self.league_patterns.get(priority, []):
                for keyword in league_info.keywords:
                    if keyword.lower() in full_text:
                        return priority, league_info.name
        
        # Если не найдено - минимальный приоритет
        return LeaguePriority.MINOR, "Неизвестная лига"
    
    def should_include_match(self, match_info: Dict[str, Any], 
                           priority_counts: Dict[LeaguePriority, int]) -> Tuple[bool, str]:
        """
        Определяет, стоит ли включать матч в выборку
        
        Args:
            match_info: Информация о матче
            priority_counts: Текущие счетчики по приоритетам
            
        Returns:
            Tuple[bool, str]: (включать ли матч, причина решения)
        """
        priority, league_name = self.determine_league_priority(match_info)
        current_count = priority_counts.get(priority, 0)
        max_count = self.priority_limits.get(priority, 0)
        
        # Проверяем лимит для данного приоритета
        if current_count >= max_count:
            return False, f"Превышен лимит для {priority.name} ({current_count}/{max_count})"
        
        # Проверяем коэффициенты (если есть)
        odds = match_info.get('odds', {})
        if odds:
            try:
                # Ищем минимальный коэффициент
                min_odd = float('inf')
                for key in ['П1', 'X', 'П2', '1', 'X', '2']:
                    if key in odds:
                        try:
                            odd_value = float(str(odds[key]).replace(',', '.'))
                            min_odd = min(min_odd, odd_value)
                        except (ValueError, TypeError):
                            continue
                
                # Слишком низкий коэффициент = неинтересный матч
                if min_odd < 1.08:
                    return False, f"Слишком низкий коэффициент: {min_odd}"
                    
            except Exception:
                pass  # Игнорируем ошибки парсинга коэффициентов
        
        return True, f"Включен как {priority.name}: {league_name}"
    
    def prioritize_matches(self, matches: List[Dict[str, Any]], 
                          max_total: int = 58) -> List[Dict[str, Any]]:
        """
        Приоритизирует матчи по важности лиг
        
        Args:
            matches: Список матчей для приоритизации
            max_total: Максимальное общее количество матчей
            
        Returns:
            List[Dict[str, Any]]: Приоритизированный список матчей
        """
        prioritized_matches = []
        priority_counts = {priority: 0 for priority in LeaguePriority}
        
        # Группируем матчи по приоритетам
        matches_by_priority = {priority: [] for priority in LeaguePriority}
        
        for match in matches:
            priority, league_name = self.determine_league_priority(match)
            match['_priority'] = priority
            match['_league_detected'] = league_name
            matches_by_priority[priority].append(match)
        
        # Добавляем матчи по приоритетам
        for priority in [LeaguePriority.TOP, LeaguePriority.EUROPEAN,
                        LeaguePriority.MAJOR, LeaguePriority.REGIONAL, 
                        LeaguePriority.MINOR]:
            
            priority_matches = matches_by_priority[priority]
            max_for_priority = self.priority_limits[priority]
            
            added_count = 0
            for match in priority_matches:
                if len(prioritized_matches) >= max_total:
                    break
                    
                should_include, reason = self.should_include_match(match, priority_counts)
                
                if should_include and added_count < max_for_priority:
                    match['_inclusion_reason'] = reason
                    prioritized_matches.append(match)
                    priority_counts[priority] += 1
                    added_count += 1
                else:
                    match['_exclusion_reason'] = reason
        
        return prioritized_matches
    
    def get_priority_stats(self, matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Получает статистику по приоритетам матчей
        
        Args:
            matches: Список матчей
            
        Returns:
            Dict[str, Any]: Статистика приоритизации
        """
        stats = {
            'total_matches': len(matches),
            'by_priority': {},
            'by_league': {},
            'inclusion_reasons': {},
            'exclusion_reasons': {}
        }
        
        for match in matches:
            # Статистика по приоритетам
            priority = match.get('_priority', LeaguePriority.MINOR)
            priority_name = priority.name if hasattr(priority, 'name') else str(priority)
            stats['by_priority'][priority_name] = stats['by_priority'].get(priority_name, 0) + 1
            
            # Статистика по лигам
            league = match.get('_league_detected', 'Неизвестная')
            stats['by_league'][league] = stats['by_league'].get(league, 0) + 1
            
            # Причины включения/исключения
            if '_inclusion_reason' in match:
                reason = match['_inclusion_reason']
                stats['inclusion_reasons'][reason] = stats['inclusion_reasons'].get(reason, 0) + 1
            
            if '_exclusion_reason' in match:
                reason = match['_exclusion_reason'] 
                stats['exclusion_reasons'][reason] = stats['exclusion_reasons'].get(reason, 0) + 1
        
        return stats