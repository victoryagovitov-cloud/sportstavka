"""
Специальный парсер для настольного тенниса
"""
import re
from typing import List, Dict, Any, Tuple

class TableTennisParser:
    """
    Специализированный парсер для настольного тенниса
    """
    
    def __init__(self):
        # Известные имена и фамилии для лучшего разделения
        self.known_names = [
            'Габор', 'Дохнал', 'Лукаш', 'Вич', 'Рэйдк', 'Славик', 'Петр', 'Моравец',
            'Мартин', 'Стехлик', 'Виктор', 'Кукала', 'Спартак', 'Абалмаз', 'Олександр', 'Наида',
            'Ондрей', 'Фиклик', 'Михал', 'Брожек', 'Орест', 'Хура', 'Ruslan', 'Haiseniuk',
            'Strowski', 'Karol', 'Сзимон', 'Коласа', 'Мичал', 'Скорски', 'Ковалцзик', 'Марцин',
            'Henryk', 'Tkaczyk', 'Дариусз', 'Сцигани', 'Крзисзтоф', 'Жусзцзик', 'Щаниел'
        ]
    
    def parse_table_tennis_text(self, text: str, league_name: str) -> List[Dict[str, Any]]:
        """
        Специальный парсинг текста настольного тенниса
        """
        matches = []
        
        # Метод 1: Поиск по известным именам
        matches.extend(self._parse_by_known_names(text, league_name))
        
        # Метод 2: Поиск по паттернам партий
        matches.extend(self._parse_by_party_patterns(text, league_name))
        
        # Метод 3: Поиск по структуре времени
        matches.extend(self._parse_by_time_structure(text, league_name))
        
        return self._remove_duplicates(matches)
    
    def _parse_by_known_names(self, text: str, league_name: str) -> List[Dict[str, Any]]:
        """
        Парсинг по известным именам игроков
        """
        matches = []
        
        # Ищем склеенные имена из известных
        for i, name1 in enumerate(self.known_names):
            for name2 in self.known_names[i+1:]:
                # Ищем склеенные имена: "ГабораДохналЛукашВич"
                pattern1 = f"{name1}{name2}"
                pattern2 = f"{name2}{name1}"
                
                if pattern1 in text:
                    # Ищем счет рядом с этими именами
                    name_pos = text.find(pattern1)
                    surrounding = text[max(0, name_pos-20):name_pos+len(pattern1)+20]
                    
                    score_match = re.search(r'(\\d{1,2})(\\d{1,2})', surrounding)
                    if score_match:
                        score = f"{score_match.group(1)}:{score_match.group(2)}"
                        
                        matches.append({
                            'player1': name1,
                            'player2': name2,
                            'sets_score': score,
                            'current_set': '1-я партия',
                            'tournament': league_name,
                            'url': '',
                            'sport': 'table_tennis',
                            'source': 'known_names'
                        })
                
                elif pattern2 in text:
                    name_pos = text.find(pattern2)
                    surrounding = text[max(0, name_pos-20):name_pos+len(pattern2)+20]
                    
                    score_match = re.search(r'(\\d{1,2})(\\d{1,2})', surrounding)
                    if score_match:
                        score = f"{score_match.group(1)}:{score_match.group(2)}"
                        
                        matches.append({
                            'player1': name2,
                            'player2': name1,
                            'sets_score': score,
                            'current_set': '1-я партия',
                            'tournament': league_name,
                            'url': '',
                            'sport': 'table_tennis',
                            'source': 'known_names'
                        })
        
        return matches
    
    def _parse_by_party_patterns(self, text: str, league_name: str) -> List[Dict[str, Any]]:
        """
        Парсинг по паттернам партий
        """
        matches = []
        
        # Ищем блоки: партия + имена + счет
        party_pattern = r'(\\d{1,2}-я партия)([А-Яа-яA-Za-z\\s,\\.]{10,60}?)(\\d{2})(\\d{2})'
        
        party_matches = re.findall(party_pattern, text)
        
        for party_info, players_text, s1, s2 in party_matches:
            # Пробуем разделить игроков
            player1, player2 = self._split_table_tennis_players(players_text)
            
            if player1 and player2:
                matches.append({
                    'player1': player1,
                    'player2': player2,
                    'sets_score': f"{s1}:{s2}",
                    'current_set': party_info,
                    'tournament': league_name,
                    'url': '',
                    'sport': 'table_tennis',
                    'source': 'party_pattern'
                })
        
        return matches
    
    def _parse_by_time_structure(self, text: str, league_name: str) -> List[Dict[str, Any]]:
        """
        Парсинг по структуре времени
        """
        matches = []
        
        # Ищем блоки: время + партия + игроки + счет
        time_pattern = r'(\\d{2}:\\d{2})(\\d{1,2}-я партия)([А-Яа-яA-Za-z\\s,\\.]{8,50}?)(\\d{2})(\\d{2})'
        
        time_matches = re.findall(time_pattern, text)
        
        for start_time, party_info, players_text, s1, s2 in time_matches:
            player1, player2 = self._split_table_tennis_players(players_text)
            
            if player1 and player2:
                matches.append({
                    'player1': player1,
                    'player2': player2,
                    'sets_score': f"{s1}:{s2}",
                    'current_set': party_info,
                    'tournament': league_name,
                    'start_time': start_time,
                    'url': '',
                    'sport': 'table_tennis',
                    'source': 'time_structure'
                })
        
        return matches
    
    def _split_table_tennis_players(self, players_text: str) -> Tuple[str, str]:
        """
        Специальное разделение игроков настольного тенниса
        """
        if not players_text:
            return None, None
        
        clean_text = players_text.strip()
        
        # Метод 1: По известным именам
        for name in self.known_names:
            if name in clean_text:
                name_pos = clean_text.find(name)
                name_end = name_pos + len(name)
                
                # Ищем следующее имя после этого
                remaining = clean_text[name_end:]
                for next_name in self.known_names:
                    if next_name in remaining and next_name != name:
                        next_pos = remaining.find(next_name)
                        
                        # Формируем полные имена
                        player1_end = name_end + next_pos
                        player1 = clean_text[:player1_end].strip()
                        player2 = clean_text[player1_end:].strip()
                        
                        if len(player1) >= 3 and len(player2) >= 3:
                            return player1, player2
        
        # Метод 2: По заглавным буквам
        # Ищем позиции заглавных букв
        capital_positions = [i for i, char in enumerate(clean_text) if char.isupper()]
        
        if len(capital_positions) >= 4:  # Минимум 2 имени + 2 фамилии
            # Пробуем разделить в середине между заглавными буквами
            mid_caps = capital_positions[len(capital_positions)//2:]
            
            for pos in mid_caps:
                if 3 <= pos <= len(clean_text) - 3:
                    player1 = clean_text[:pos].strip()
                    player2 = clean_text[pos:].strip()
                    
                    if (len(player1) >= 3 and len(player2) >= 3 and
                        player1[0].isupper() and player2[0].isupper()):
                        return player1, player2
        
        # Метод 3: По средней точке
        if len(clean_text) >= 8:
            mid = len(clean_text) // 2
            
            # Ищем хорошую точку разделения рядом с серединой
            for offset in range(-2, 3):
                split_pos = mid + offset
                if 3 <= split_pos <= len(clean_text) - 3:
                    player1 = clean_text[:split_pos].strip()
                    player2 = clean_text[split_pos:].strip()
                    
                    # Проверяем, что оба начинаются с заглавной буквы
                    if (len(player1) >= 3 and len(player2) >= 3 and
                        player1[0].isupper() and player2[0].isupper() and
                        player1 != player2):
                        return player1, player2
        
        return None, None
    
    def _remove_duplicates(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Удаление дубликатов
        """
        seen = set()
        unique = []
        
        for match in matches:
            key = f"{match.get('player1', '')}-{match.get('player2', '')}".lower()
            if key not in seen and len(key) > 6:
                seen.add(key)
                unique.append(match)
        
        return unique