"""
Словарь сокращений и альтернативных названий команд
Для улучшения поиска матчей в разных источниках
"""

import re
from typing import Dict, List, Set
from difflib import SequenceMatcher

class TeamAbbreviations:
    """Словарь сокращений команд для улучшения поиска"""
    
    def __init__(self):
        self.team_mappings = self._initialize_team_mappings()
        self.compiled_patterns = self._compile_search_patterns()
    
    def _initialize_team_mappings(self) -> Dict[str, List[str]]:
        """Инициализация словаря команд и их сокращений"""
        return {
            # НАЦИОНАЛЬНЫЕ СБОРНЫЕ (КРИТИЧНО ДЛЯ MARATHONBET)
            'беларусь': ['belarus', 'белоруссия', 'bel', 'blr'],
            'шотландия': ['scotland', 'sco', 'scot'],
            'гибралтар': ['gibraltar', 'gib'],
            'фарерские острова': ['faroe islands', 'far', 'фареры', 'faroe'],
            'греция': ['greece', 'gre', 'эллада', 'hellas'],
            'дания': ['denmark', 'den', 'дан', 'danish'],
            'израиль': ['israel', 'isr', 'израиль'],
            'италия': ['italy', 'ita', 'итальянская', 'azzurri'],
            'косово': ['kosovo', 'kos', 'xk'],
            'швеция': ['sweden', 'swe', 'swedish'],
            'хорватия': ['croatia', 'cro', 'hrvatska'],
            'черногория': ['montenegro', 'mne', 'crna gora'],
            'швейцария': ['switzerland', 'sui', 'свисс', 'swiss'],
            'словения': ['slovenia', 'svn', 'slo'],
            'гана': ['ghana', 'gha'],
            'мали': ['mali', 'mli'],
            'ливия': ['libya', 'lib', 'lby'],
            'эсватини': ['eswatini', 'esw', 'свазиленд', 'swaziland'],
            'андорра': ['andorra', 'and', 'fc andorra'],
            'эйбар': ['eibar', 'sd eibar', 'sociedad deportiva eibar'],
            'россия': ['russia', 'rus', 'российская'],
            'украина': ['ukraine', 'ukr', 'українська'],
            'казахстан': ['kazakhstan', 'kaz'],
            'узбекистан': ['uzbekistan', 'uzb'],
            'грузия': ['georgia', 'geo'],
            'армения': ['armenia', 'arm'],
            'азербайджан': ['azerbaijan', 'aze'],
            'молдова': ['moldova', 'mda'],
            'латвия': ['latvia', 'lva', 'lat'],
            'литва': ['lithuania', 'ltu', 'lit'],
            'эстония': ['estonia', 'est'],
            'финляндия': ['finland', 'fin'],
            'норвегия': ['norway', 'nor'],
            'исландия': ['iceland', 'isl'],
            'ирландия': ['ireland', 'irl'],
            'уэльс': ['wales', 'wal'],
            'англия': ['england', 'eng'],
            'франция': ['france', 'fra', 'французская'],
            'германия': ['germany', 'ger', 'deutsche'],
            'испания': ['spain', 'esp', 'española'],
            'португалия': ['portugal', 'por'],
            'нидерланды': ['netherlands', 'ned', 'holland', 'голландия'],
            'бельгия': ['belgium', 'bel'],
            'австрия': ['austria', 'aut'],
            'чехия': ['czech republic', 'cze', 'czechia'],
            'польша': ['poland', 'pol'],
            'венгрия': ['hungary', 'hun'],
            'румыния': ['romania', 'rou'],
            'болгария': ['bulgaria', 'bul'],
            'сербия': ['serbia', 'srb'],
            'босния': ['bosnia', 'bih', 'bosnia and herzegovina'],
            'македония': ['macedonia', 'mkd', 'north macedonia'],
            'албания': ['albania', 'alb'],
            'турция': ['turkey', 'tur'],
            
            # РОССИЙСКИЕ КОМАНДЫ
            'зенит': ['zenit', 'fc zenit', 'зенит спб', 'zenith', 'зенит санкт-петербург'],
            'спартак': ['spartak', 'fc spartak', 'спартак москва', 'спартак м'],
            'цска': ['cska', 'fc cska', 'цска москва', 'cska moscow'],
            'динамо': ['dinamo', 'dynamo', 'fc dinamo', 'динамо москва'],
            'локомотив': ['lokomotiv', 'fc lokomotiv', 'локо', 'локомотив москва'],
            'краснодар': ['krasnodar', 'fc krasnodar', 'краснодар фк'],
            'рубин': ['rubin', 'fc rubin', 'рубин казань'],
            'ростов': ['rostov', 'fc rostov', 'ростов фк'],
            'сочи': ['sochi', 'fc sochi', 'сочи фк'],
            'урал': ['ural', 'fc ural', 'урал екатеринбург'],
            
            # ИСПАНСКИЕ КОМАНДЫ
            'реал мадрид': ['real madrid', 'real', 'реал', 'rm', 'madrid', 'real m'],
            'барселона': ['barcelona', 'barca', 'барса', 'fcb', 'fc barcelona', 'barca fc'],
            'атлетико мадрид': ['atletico madrid', 'atletico', 'атлетико', 'atm', 'atletico m'],
            'севилья': ['sevilla', 'fc sevilla', 'севилья фк'],
            'валенсия': ['valencia', 'fc valencia', 'valencia cf'],
            'вильярреал': ['villarreal', 'fc villarreal', 'villareal'],
            'реал сосьедад': ['real sociedad', 'sociedad', 'real s'],
            'атлетик бильбао': ['athletic bilbao', 'athletic', 'bilbao'],
            
            # АНГЛИЙСКИЕ КОМАНДЫ
            'манчестер юнайтед': ['manchester united', 'man utd', 'manchester utd', 'mufc', 'united', 'ман юнайтед', 'мю'],
            'манчестер сити': ['manchester city', 'man city', 'city', 'mcfc', 'ман сити'],
            'ливерпуль': ['liverpool', 'lfc', 'liverpool fc'],
            'челси': ['chelsea', 'fc chelsea', 'cfc'],
            'арсенал': ['arsenal', 'fc arsenal', 'afc', 'арсенал лондон'],
            'тоттенхэм': ['tottenham', 'spurs', 'tottenham hotspur', 'thfc'],
            'ньюкасл': ['newcastle', 'newcastle united', 'nufc', 'ньюкасл юнайтед'],
            'вест хэм': ['west ham', 'west ham united', 'whufc', 'hammers'],
            'эвертон': ['everton', 'efc', 'everton fc'],
            'лестер': ['leicester', 'leicester city', 'lcfc', 'foxes'],
            
            # ИТАЛЬЯНСКИЕ КОМАНДЫ
            'ювентус': ['juventus', 'juve', 'fc juventus', 'juventus fc'],
            'милан': ['milan', 'ac milan', 'ак милан', 'acm'],
            'интер': ['inter', 'inter milan', 'fc inter', 'internazionale'],
            'наполи': ['napoli', 'ssc napoli', 'наполи сск'],
            'рома': ['roma', 'as roma', 'ас рома'],
            'лацио': ['lazio', 'ss lazio', 'лацио сс'],
            'аталанта': ['atalanta', 'atalanta bc'],
            'фиорентина': ['fiorentina', 'acf fiorentina'],
            
            # НЕМЕЦКИЕ КОМАНДЫ
            'бавария': ['bayern', 'bayern munich', 'fc bayern', 'bayern munchen', 'fcb'],
            'боруссия дортмунд': ['borussia dortmund', 'bvb', 'дортмунд', 'borussia d'],
            'лейпциг': ['leipzig', 'rb leipzig', 'red bull leipzig'],
            'байер леверкузен': ['bayer leverkusen', 'leverkusen', 'bayer 04'],
            'боруссия менхенгладбах': ['borussia monchengladbach', 'gladbach', 'bmg'],
            'вольфсбург': ['wolfsburg', 'vfl wolfsburg'],
            'айнтрахт франкфурт': ['eintracht frankfurt', 'frankfurt', 'sge'],
            'шальке': ['schalke', 'fc schalke 04', 'schalke 04'],
            
            # ФРАНЦУЗСКИЕ КОМАНДЫ
            'псж': ['psg', 'paris saint-germain', 'paris sg', 'пари сен жермен'],
            'марсель': ['marseille', 'olympique marseille', 'om'],
            'лион': ['lyon', 'olympique lyon', 'ol'],
            'монако': ['monaco', 'as monaco', 'asm'],
            'лилль': ['lille', 'losc lille'],
            'ницца': ['nice', 'ogc nice'],
            'ренн': ['rennes', 'stade rennes'],
            
            # ТЕННИСНЫЕ ИГРОКИ (примеры)
            'новак джокович': ['djokovic', 'novak djokovic', 'nole', 'djoko'],
            'рафаэль надаль': ['nadal', 'rafael nadal', 'rafa', 'rafa nadal'],
            'роджер федерер': ['federer', 'roger federer', 'fed', 'rf'],
            'энди маррей': ['murray', 'andy murray', 'andy m'],
            'серена уильямс': ['serena williams', 'serena', 'williams'],
            'мария шарапова': ['sharapova', 'maria sharapova', 'masha'],
            
            # ОБЩИЕ СОКРАЩЕНИЯ
            'фк': ['fc', 'football club'],
            'спортинг': ['sporting', 'sc'],
            'олимпиакос': ['olympiacos', 'olympiakos'],
            'реал': ['real'],
            'атлетико': ['atletico', 'atm']
        }
    
    def _compile_search_patterns(self) -> Dict[str, re.Pattern]:
        """Предкомпилированные regex паттерны для быстрого поиска"""
        return {
            'vs_pattern': re.compile(r'(\w+.*?)\s+vs\s+(\w+.*?)', re.IGNORECASE),
            'dash_pattern': re.compile(r'(\w+.*?)\s+[-–—]\s+(\w+.*?)', re.IGNORECASE),
            'score_pattern': re.compile(r'(\w+.*?)\s+(\d+:\d+)\s+(\w+.*?)', re.IGNORECASE),
            'team_cleanup': re.compile(r'\b(fc|фк|football club)\b', re.IGNORECASE)
        }
    
    def generate_team_variants(self, team_name: str) -> List[str]:
        """
        Генерирует все возможные варианты названия команды
        """
        if not team_name:
            return []
        
        variants = set()
        team_lower = team_name.lower().strip()
        
        # Добавляем исходное название
        variants.add(team_lower)
        variants.add(team_name.strip())
        
        # Ищем в словаре сокращений
        for full_name, abbreviations in self.team_mappings.items():
            if (team_lower == full_name or 
                team_lower in abbreviations or 
                any(abbr in team_lower for abbr in abbreviations if len(abbr) > 3)):
                
                variants.add(full_name)
                variants.update(abbreviations)
        
        # Автоматические варианты
        # Убираем "ФК"/"FC"
        cleaned = self.compiled_patterns['team_cleanup'].sub('', team_name).strip()
        if cleaned and cleaned != team_name:
            variants.add(cleaned.lower())
        
        # Первое слово (для составных названий)
        first_word = team_name.split()[0].lower()
        if len(first_word) > 2:
            variants.add(first_word)
        
        # Без пробелов
        no_spaces = team_name.replace(' ', '').lower()
        if no_spaces != team_lower:
            variants.add(no_spaces)
        
        # Убираем пустые и слишком короткие
        return [v for v in variants if v and len(v) >= 2]
    
    def calculate_match_confidence(self, text: str, team1_variants: List[str], 
                                  team2_variants: List[str]) -> float:
        """
        Вычисляет уверенность в том, что текст содержит матч команд
        """
        text_lower = text.lower()
        
        # Проверяем наличие обеих команд
        team1_matches = [v for v in team1_variants if v in text_lower]
        team2_matches = [v for v in team2_variants if v in text_lower]
        
        if not (team1_matches and team2_matches):
            return 0.0
        
        # Базовая уверенность
        confidence = 0.6
        
        # Бонусы за качество совпадений
        # Точное совпадение полного названия
        if any(len(match) > 10 for match in team1_matches + team2_matches):
            confidence += 0.2
        
        # Четкие разделители
        if any(sep in text_lower for sep in ['vs', ' - ', ' v ', 'против']):
            confidence += 0.15
        
        # Live индикаторы
        if any(indicator in text_lower for indicator in ['live', 'мин', "'", 'ht', 'ft']):
            confidence += 0.05
        
        # Счет в тексте
        if re.search(r'\d+[:-]\d+', text):
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def find_best_team_match(self, search_text: str, target_team: str) -> tuple:
        """
        Находит лучшее совпадение для команды в тексте
        Возвращает (найденный_текст, уверенность)
        """
        variants = self.generate_team_variants(target_team)
        best_match = ""
        best_confidence = 0.0
        
        search_lower = search_text.lower()
        
        for variant in variants:
            if variant in search_lower:
                # Точное совпадение
                confidence = len(variant) / len(target_team)  # Чем длиннее совпадение, тем лучше
                if confidence > best_confidence:
                    best_match = variant
                    best_confidence = confidence
            else:
                # Нечеткое совпадение
                fuzzy_confidence = SequenceMatcher(None, variant, search_lower).ratio()
                if fuzzy_confidence > 0.8 and fuzzy_confidence > best_confidence:
                    best_match = variant
                    best_confidence = fuzzy_confidence * 0.8  # Штраф за нечеткость
        
        return best_match, best_confidence
    
    def get_team_mapping_stats(self) -> Dict[str, int]:
        """Получение статистики словаря команд"""
        total_teams = len(self.team_mappings)
        total_variants = sum(len(variants) for variants in self.team_mappings.values())
        
        by_league = {}
        for team, variants in self.team_mappings.items():
            # Определяем лигу по названию команды
            if any(ru_word in team for ru_word in ['зенит', 'спартак', 'цска', 'динамо']):
                league = 'РПЛ'
            elif any(en_word in team for en_word in ['real', 'barcelona', 'atletico', 'sevilla']):
                league = 'Ла Лига'
            elif any(en_word in team for en_word in ['manchester', 'liverpool', 'chelsea', 'arsenal']):
                league = 'АПЛ'
            elif any(en_word in team for en_word in ['bayern', 'dortmund', 'leipzig']):
                league = 'Бундеслига'
            elif any(en_word in team for en_word in ['juventus', 'milan', 'inter', 'napoli']):
                league = 'Серия А'
            elif any(en_word in team for en_word in ['psg', 'marseille', 'lyon', 'monaco']):
                league = 'Лига 1'
            elif any(tennis_word in team for tennis_word in ['джокович', 'надаль', 'федерер']):
                league = 'Теннис'
            else:
                league = 'Другие'
            
            by_league[league] = by_league.get(league, 0) + 1
        
        return {
            'total_teams': total_teams,
            'total_variants': total_variants,
            'average_variants_per_team': round(total_variants / total_teams, 2),
            'by_league': by_league
        }

# Глобальный экземпляр
TEAM_ABBREVIATIONS = TeamAbbreviations()

def get_team_variants(team_name: str) -> List[str]:
    """Быстрый доступ к вариантам команды"""
    return TEAM_ABBREVIATIONS.generate_team_variants(team_name)

def calculate_team_match_confidence(text: str, team1: str, team2: str) -> float:
    """Быстрый расчет уверенности в совпадении"""
    team1_variants = get_team_variants(team1)
    team2_variants = get_team_variants(team2)
    return TEAM_ABBREVIATIONS.calculate_match_confidence(text, team1_variants, team2_variants)