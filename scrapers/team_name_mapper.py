"""
Система сопоставления названий команд между источниками
Обеспечивает единообразие названий команд из MarathonBet
"""

import re
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
import difflib

@dataclass
class TeamMapping:
    """Информация о сопоставлении команды"""
    marathonbet_name: str
    alternative_names: List[str]
    country: str
    league: str
    confidence: float = 1.0

class TeamNameMapper:
    """
    Система сопоставления названий команд
    MarathonBet - основной источник названий
    """
    
    def __init__(self):
        self.team_mappings: Dict[str, TeamMapping] = {}
        self.reverse_mappings: Dict[str, str] = {}  # альтернативное -> основное
        self.common_abbreviations = self._initialize_abbreviations()
        self.name_normalizers = self._initialize_normalizers()
        
    def _initialize_abbreviations(self) -> Dict[str, List[str]]:
        """Инициализация общих сокращений команд"""
        return {
            # Российские клубы
            'зенит': ['zenit', 'fc zenit', 'зенит спб'],
            'спартак': ['spartak', 'fc spartak', 'спартак москва'],
            'цска': ['cska', 'fc cska', 'цска москва'],
            'динамо': ['dinamo', 'fc dinamo', 'динамо москва'],
            'локомотив': ['lokomotiv', 'fc lokomotiv', 'локо'],
            'краснодар': ['krasnodar', 'fc krasnodar', 'краснодар фк'],
            'рубин': ['rubin', 'fc rubin', 'рубин казань'],
            'ростов': ['rostov', 'fc rostov', 'ростов фк'],
            
            # Европейские топ-клубы
            'реал мадрид': ['real madrid', 'real', 'реал'],
            'барселона': ['barcelona', 'barca', 'барса'],
            'манчестер юнайтед': ['manchester united', 'man utd', 'man united', 'юнайтед'],
            'манчестер сити': ['manchester city', 'man city', 'сити'],
            'ливерпуль': ['liverpool', 'lfc'],
            'челси': ['chelsea', 'fc chelsea'],
            'арсенал': ['arsenal', 'fc arsenal'],
            'бавария': ['bayern', 'bayern munich', 'fc bayern'],
            'боруссия дортмунд': ['borussia dortmund', 'bvb', 'дортмунд'],
            'ювентус': ['juventus', 'juve', 'fc juventus'],
            'милан': ['milan', 'ac milan', 'ак милан'],
            'интер': ['inter', 'inter milan', 'fc inter'],
            'пsg': ['paris saint-germain', 'пари сен жермен', 'псж'],
            
            # Общие сокращения
            'фк': ['fc', 'football club'],
            'спортинг': ['sporting', 'sc'],
            'атлетико': ['atletico', 'atm'],
            'олимпиакос': ['olympiacos', 'olympiakos'],
        }
    
    def _initialize_normalizers(self) -> List[callable]:
        """Инициализация нормализаторов названий"""
        return [
            lambda x: x.lower().strip(),
            lambda x: re.sub(r'\s+', ' ', x),  # Множественные пробелы
            lambda x: re.sub(r'[^\w\s]', '', x),  # Убираем пунктуацию
            lambda x: re.sub(r'\b(фк|fc|football club)\b', '', x).strip(),  # Убираем FC/ФК
            lambda x: re.sub(r'\b\d+\b', '', x).strip(),  # Убираем цифры
        ]
    
    def normalize_team_name(self, name: str) -> str:
        """
        Нормализует название команды для сравнения
        
        Args:
            name: Исходное название команды
            
        Returns:
            str: Нормализованное название
        """
        if not name:
            return ""
            
        normalized = name
        for normalizer in self.name_normalizers:
            normalized = normalizer(normalized)
            
        return normalized.strip()
    
    def add_team_mapping(self, marathonbet_name: str, alternative_names: List[str], 
                        country: str = "", league: str = "", confidence: float = 1.0):
        """
        Добавляет сопоставление команды
        
        Args:
            marathonbet_name: Название в MarathonBet (основное)
            alternative_names: Альтернативные названия в других источниках
            country: Страна команды
            league: Лига команды
            confidence: Уверенность в сопоставлении (0.0-1.0)
        """
        mapping = TeamMapping(
            marathonbet_name=marathonbet_name,
            alternative_names=alternative_names,
            country=country,
            league=league,
            confidence=confidence
        )
        
        # Основное сопоставление
        normalized_main = self.normalize_team_name(marathonbet_name)
        self.team_mappings[normalized_main] = mapping
        
        # Обратные сопоставления
        for alt_name in alternative_names:
            normalized_alt = self.normalize_team_name(alt_name)
            self.reverse_mappings[normalized_alt] = marathonbet_name
    
    def find_marathonbet_name(self, external_name: str, 
                             confidence_threshold: float = 0.7) -> Tuple[Optional[str], float]:
        """
        Находит название команды в формате MarathonBet по внешнему названию
        
        Args:
            external_name: Название команды из внешнего источника
            confidence_threshold: Минимальный порог уверенности
            
        Returns:
            Tuple[Optional[str], float]: (название MarathonBet, уверенность)
        """
        if not external_name:
            return None, 0.0
            
        normalized_external = self.normalize_team_name(external_name)
        
        # Точное совпадение в обратных сопоставлениях
        if normalized_external in self.reverse_mappings:
            return self.reverse_mappings[normalized_external], 1.0
        
        # Точное совпадение в основных сопоставлениях
        if normalized_external in self.team_mappings:
            return self.team_mappings[normalized_external].marathonbet_name, 1.0
        
        # Поиск по сокращениям
        for main_name, abbreviations in self.common_abbreviations.items():
            if normalized_external in [self.normalize_team_name(abbr) for abbr in abbreviations]:
                return main_name, 0.9
        
        # Нечеткий поиск
        best_match = None
        best_confidence = 0.0
        
        # Поиск среди основных названий
        for normalized_main, mapping in self.team_mappings.items():
            confidence = difflib.SequenceMatcher(None, normalized_external, normalized_main).ratio()
            if confidence > best_confidence and confidence >= confidence_threshold:
                best_match = mapping.marathonbet_name
                best_confidence = confidence
        
        # Поиск среди альтернативных названий
        for alt_name, main_name in self.reverse_mappings.items():
            confidence = difflib.SequenceMatcher(None, normalized_external, alt_name).ratio()
            if confidence > best_confidence and confidence >= confidence_threshold:
                best_match = main_name
                best_confidence = confidence
        
        return best_match, best_confidence
    
    def auto_learn_from_marathonbet_matches(self, marathonbet_matches: List[Dict[str, any]]):
        """
        Автоматически изучает названия команд из MarathonBet матчей
        
        Args:
            marathonbet_matches: Список матчей из MarathonBet
        """
        for match in marathonbet_matches:
            team1 = match.get('team1', '')
            team2 = match.get('team2', '')
            league = match.get('league', '')
            
            if team1:
                self.add_team_mapping(
                    marathonbet_name=team1,
                    alternative_names=[team1],  # Пока только само название
                    league=league,
                    confidence=1.0
                )
            
            if team2:
                self.add_team_mapping(
                    marathonbet_name=team2,
                    alternative_names=[team2],
                    league=league,
                    confidence=1.0
                )
    
    def enrich_external_match_with_marathonbet_names(self, external_match: Dict[str, any], 
                                                   confidence_threshold: float = 0.7) -> Dict[str, any]:
        """
        Обогащает внешний матч названиями команд из MarathonBet
        
        Args:
            external_match: Матч из внешнего источника
            confidence_threshold: Минимальный порог уверенности
            
        Returns:
            Dict[str, any]: Обогащенный матч с MarathonBet названиями
        """
        enriched_match = external_match.copy()
        
        # Исходные названия
        original_team1 = external_match.get('team1', '')
        original_team2 = external_match.get('team2', '')
        
        # Поиск MarathonBet названий
        mb_team1, confidence1 = self.find_marathonbet_name(original_team1, confidence_threshold)
        mb_team2, confidence2 = self.find_marathonbet_name(original_team2, confidence_threshold)
        
        # Обновляем названия команд
        if mb_team1:
            enriched_match['team1'] = mb_team1
            enriched_match['team1_confidence'] = confidence1
            enriched_match['team1_original'] = original_team1
        
        if mb_team2:
            enriched_match['team2'] = mb_team2
            enriched_match['team2_confidence'] = confidence2
            enriched_match['team2_original'] = original_team2
        
        # Добавляем метаинформацию
        enriched_match['names_mapped'] = bool(mb_team1 and mb_team2)
        enriched_match['mapping_quality'] = (confidence1 + confidence2) / 2 if mb_team1 and mb_team2 else 0.0
        
        return enriched_match
    
    def get_mapping_stats(self) -> Dict[str, any]:
        """
        Получает статистику сопоставлений
        
        Returns:
            Dict[str, any]: Статистика системы сопоставлений
        """
        return {
            'total_teams': len(self.team_mappings),
            'reverse_mappings': len(self.reverse_mappings),
            'common_abbreviations': len(self.common_abbreviations),
            'countries': len(set(mapping.country for mapping in self.team_mappings.values() if mapping.country)),
            'leagues': len(set(mapping.league for mapping in self.team_mappings.values() if mapping.league)),
            'high_confidence': len([m for m in self.team_mappings.values() if m.confidence >= 0.9]),
            'medium_confidence': len([m for m in self.team_mappings.values() if 0.7 <= m.confidence < 0.9]),
            'low_confidence': len([m for m in self.team_mappings.values() if m.confidence < 0.7])
        }
    
    def export_mappings_for_telegram(self) -> Dict[str, str]:
        """
        Экспортирует сопоставления для использования в телеграм каналах
        
        Returns:
            Dict[str, str]: Словарь {внешнее_название: marathonbet_название}
        """
        telegram_mappings = {}
        
        for alt_name, main_name in self.reverse_mappings.items():
            telegram_mappings[alt_name] = main_name
            
        # Добавляем основные названия
        for mapping in self.team_mappings.values():
            telegram_mappings[mapping.marathonbet_name] = mapping.marathonbet_name
            
        return telegram_mappings