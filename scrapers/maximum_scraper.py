"""
Максимальный скрапер для извлечения ВСЕХ live матчей с scores24.live
"""
import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Any
from scrapers.simple_tt_parser import parse_table_tennis_simple

class MaximumScraper:
    """
    Скрапер для извлечения максимального количества live матчей
    """
    
    def __init__(self, logger):
        self.logger = logger
        
        # Простой парсер для настольного тенниса
        self.simple_tt_parser = parse_table_tennis_simple
        
        # Словари для улучшенного разделения команд
        self.country_endings = [
            'ия', 'ан', 'ка', 'да', 'ль', 'на', 'ра', 'ин', 'ен', 'он', 'ус', 'ор', 'ал', 'ел'
        ]
        
        self.common_team_words = [
            'Юнайтед', 'Сити', 'Таун', 'Роверс', 'Альбион', 'Рейнджерс', 'Атлетико',
            'Депортиво', 'Реал', 'Барселона', 'Милан', 'Интер', 'Арсенал', 'Челси'
        ]
    
    def get_live_matches(self, url: str, sport: str) -> List[Dict[str, Any]]:
        """
        Максимальное извлечение live матчей
        """
        self.logger.info(f"МАКСИМАЛЬНЫЙ сбор {sport} данных с {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.7339.80 Safari/537.36'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            all_matches = []
            
            # Метод 1: Улучшенный парсинг leagueWrapper
            league_matches = self._extract_from_league_wrappers(soup, sport)
            all_matches.extend(league_matches)
            
            # Метод 2: Извлечение из MatchGenericInfo
            info_matches = self._extract_from_match_info(soup, sport)
            all_matches.extend(info_matches)
            
            # Метод 3: Поиск дополнительных источников
            additional_matches = self._extract_additional_sources(soup, sport)
            all_matches.extend(additional_matches)
            
            # Очистка и валидация
            clean_matches = self._advanced_cleaning(all_matches, sport)
            
            self.logger.info(f"МАКСИМУМ извлечено {len(clean_matches)} {sport} матчей")
            
            return clean_matches
            
        except Exception as e:
            self.logger.error(f"Максимальный скрапер ошибка: {e}")
            return []
    
    def _extract_from_league_wrappers(self, soup, sport: str) -> List[Dict[str, Any]]:
        """
        Улучшенное извлечение из leagueWrapper
        """
        matches = []
        league_wrappers = soup.find_all(attrs={'data-testid': 'leagueWrapper'})
        
        for wrapper in league_wrappers:
            text = wrapper.get_text(strip=True)
            
            # Извлекаем название лиги
            league_match = re.search(r'^([^(]+)', text)
            league_name = league_match.group(1).strip() if league_match else "Неизвестная лига"
            
            # Специальная обработка для настольного тенниса
            if sport == 'table_tennis':
                tt_matches = parse_table_tennis_simple(text, league_name)
                matches.extend(tt_matches)
                continue  # Пропускаем стандартную обработку для настольного тенниса
            
            # Улучшенные паттерны для разных видов спорта
            if sport == 'football':
                patterns = [
                    # Основной паттерн: время+минута+команды+счет
                    r'(\d{2}:\d{2})(\d{1,3})[\'"мин]?([А-Яа-яA-Za-z\s\-\'\(\)]{6,60}?)(\d{1,2})(\d{1,2})(\d{1,2})(\d{1,2})',
                    # Альтернативный: команды со счетом
                    r'([А-Я][а-я]+)([А-Я][а-я]+)(\d{1,2})(\d{1,2})(\d{1,2})(\d{1,2})'
                ]
            elif sport == 'tennis':
                patterns = [
                    # Теннисный паттерн: сет+игроки+счет
                    r'(\d{1,2}-й сет)([А-Яа-яA-Za-z\s\.\-\']{6,60}?)(\d{1,2})(\d{1,2})',
                    r'(\d{2}:\d{2})(\d{1,2}-й сет)([А-Яа-яA-Za-z\s\.\-\']{6,60}?)(\d{1,2})(\d{1,2})'
                ]
            elif sport == 'table_tennis':
                patterns = [
                    # Настольный теннис: время+партия+игроки+счет
                    r'(\d{2}:\d{2})(\d{1,2}-я партия)([А-Яа-яA-Za-z\s\.\-\',]{6,60}?)(\d{1,2})(\d{1,2})',
                    # Только партия+игроки+счет
                    r'(\d{1,2}-я партия)([А-Яа-яA-Za-z\s\.\-\',]{6,60}?)(\d{1,2})(\d{1,2})',
                    # Простой паттерн: игрок1+игрок2+счет
                    r'([А-Я][а-яё\s]{3,25})([А-Я][а-яё\s]{3,25})(\d{1,2})(\d{1,2})'
                ]
            else:  # handball
                patterns = [
                    r'(\d{2}:\d{2})(\d{1,2}-й т\.)([А-Яа-яA-Za-z\s\-\']{6,40}?)(\d{1,2})(\d{1,2})'
                ]
            
            # Применяем паттерны
            for pattern in patterns:
                matches_found = re.findall(pattern, text, re.IGNORECASE)
                
                for match_data in matches_found:
                    try:
                        parsed_match = self._parse_match_tuple(match_data, league_name, sport)
                        if parsed_match:
                            matches.append(parsed_match)
                    except Exception:
                        continue
        
        return matches
    
    def _parse_match_tuple(self, match_tuple: tuple, league_name: str, sport: str) -> Dict[str, Any]:
        """
        Парсинг кортежа данных матча
        """
        try:
            if sport == 'football':
                if len(match_tuple) >= 7:
                    start_time, minute, teams_text, s1, s2, s3, s4 = match_tuple[:7]
                    
                    # Улучшенное разделение команд
                    team1, team2 = self._smart_split_teams(teams_text)
                    
                    if team1 and team2:
                        # Определяем правильный счет
                        score = self._determine_score([s1, s2, s3, s4])
                        
                        return {
                            'team1': team1,
                            'team2': team2,
                            'score': score,
                            'time': f"{minute}'",
                            'start_time': start_time,
                            'league': league_name,
                            'url': '',
                            'sport': sport,
                            'source': 'maximum_scraper'
                        }
                        
            elif sport in ['tennis', 'table_tennis']:
                if len(match_tuple) >= 4:
                    # Для настольного тенниса может быть разная структура
                    if len(match_tuple) == 5:  # время+партия+игроки+счет
                        start_time, set_info, players_text, s1, s2 = match_tuple
                    elif len(match_tuple) == 4:  # партия+игроки+счет ИЛИ игрок1+игрок2+счет
                        if 'партия' in str(match_tuple[0]):
                            set_info, players_text, s1, s2 = match_tuple
                            start_time = '20:00'  # Fallback
                        else:
                            # Простой паттерн: игрок1+игрок2+счет
                            player1, player2, s1, s2 = match_tuple
                            start_time = '20:00'
                            set_info = '1-я партия'
                            
                            if player1 and player2:
                                return {
                                    'player1': player1,
                                    'player2': player2,
                                    'sets_score': f"{s1}:{s2}",
                                    'current_set': set_info,
                                    'tournament': league_name,
                                    'url': '',
                                    'sport': sport,
                                    'source': 'maximum_scraper'
                                }
                    else:
                        return None
                    
                    # Разделяем игроков (если есть players_text)
                    if 'players_text' in locals():
                        player1, player2 = self._smart_split_teams(players_text)
                        
                        if player1 and player2:
                            score = f"{s1}:{s2}"
                            
                            return {
                                'player1': player1,
                                'player2': player2,
                                'sets_score': score,
                                'current_set': set_info,
                                'tournament': league_name,
                                'url': '',
                                'sport': sport,
                                'source': 'maximum_scraper'
                            }
                        
            elif sport == 'handball':
                if len(match_tuple) >= 5:
                    start_time, period, teams_text, s1, s2 = match_tuple[:5]
                    
                    team1, team2 = self._smart_split_teams(teams_text)
                    
                    if team1 and team2:
                        return {
                            'team1': team1,
                            'team2': team2,
                            'score': f"{s1}:{s2}",
                            'time': period,
                            'start_time': start_time,
                            'league': league_name,
                            'url': '',
                            'sport': sport,
                            'source': 'maximum_scraper'
                        }
            
            return None
            
        except Exception:
            return None
    
    def _smart_split_teams(self, teams_text: str) -> tuple:
        """
        Умное разделение склеенных названий команд/игроков
        """
        if not teams_text:
            return None, None
        
        # Убираем лишние символы
        clean_text = teams_text.strip("'\"()").replace('  ', ' ')
        
        # Метод 1: Разделение по заглавным буквам
        # Ищем место, где заглавная буква следует за строчной
        capital_positions = []
        for i, char in enumerate(clean_text[1:], 1):  # Начинаем с 1, т.к. первая буква может быть заглавной
            if char.isupper() and i > 0 and clean_text[i-1].islower():
                capital_positions.append(i)
        
        # Пробуем разделить по найденным позициям
        for pos in capital_positions:
            team1 = clean_text[:pos].strip()
            team2 = clean_text[pos:].strip()
            
            if (len(team1) >= 3 and len(team2) >= 3 and 
                self._is_valid_team_name(team1) and 
                self._is_valid_team_name(team2)):
                return team1, team2
        
        # Метод 2: Разделение по известным окончаниям
        for ending in self.country_endings:
            if ending in clean_text:
                # Ищем все вхождения
                matches = list(re.finditer(ending, clean_text))
                for match in matches:
                    end_pos = match.end()
                    if end_pos < len(clean_text) - 3:  # Есть место для второй команды
                        team1 = clean_text[:end_pos].strip()
                        team2 = clean_text[end_pos:].strip()
                        
                        if (len(team1) >= 3 and len(team2) >= 3 and
                            self._is_valid_team_name(team1) and 
                            self._is_valid_team_name(team2)):
                            return team1, team2
        
        # Метод 3: Разделение по известным словам команд
        for word in self.common_team_words:
            if word in clean_text:
                word_pos = clean_text.find(word)
                word_end = word_pos + len(word)
                
                # Если слово в середине, пробуем разделить
                if 3 <= word_pos <= len(clean_text) - 6:
                    team1 = clean_text[:word_end].strip()
                    team2 = clean_text[word_end:].strip()
                    
                    if (len(team1) >= 3 and len(team2) >= 3 and
                        self._is_valid_team_name(team1) and 
                        self._is_valid_team_name(team2)):
                        return team1, team2
        
        # Метод 4: Разделение пополам с поиском хорошей позиции
        if len(clean_text) >= 8:
            mid = len(clean_text) // 2
            
            # Ищем хорошую позицию разделения в окрестности середины
            for offset in range(-3, 4):
                split_pos = mid + offset
                if 3 <= split_pos <= len(clean_text) - 3:
                    team1 = clean_text[:split_pos].strip()
                    team2 = clean_text[split_pos:].strip()
                    
                    if (len(team1) >= 3 and len(team2) >= 3 and
                        self._is_valid_team_name(team1) and 
                        self._is_valid_team_name(team2) and
                        team1.lower() != team2.lower()):
                        return team1, team2
        
        return None, None
    
    def _determine_score(self, score_parts: List[str]) -> str:
        """
        Определение правильного счета из массива цифр
        """
        try:
            # Конвертируем в числа
            nums = [int(part) for part in score_parts if part.isdigit()]
            
            if len(nums) >= 2:
                # Для футбола обычно счет не превышает 10:10
                if len(nums) >= 2:
                    s1, s2 = nums[0], nums[1]
                    
                    # Проверяем разумность счета
                    if s1 <= 15 and s2 <= 15:  # Разумные пределы
                        return f"{s1}:{s2}"
                
                # Если первые два числа слишком большие, пробуем другие комбинации
                if len(nums) >= 4:
                    # Возможно счет в других позициях
                    for i in range(len(nums) - 1):
                        s1, s2 = nums[i], nums[i + 1]
                        if s1 <= 10 and s2 <= 10:
                            return f"{s1}:{s2}"
            
            return "0:0"  # Fallback
            
        except Exception:
            return "0:0"
    
    def _extract_from_match_info(self, soup, sport: str) -> List[Dict[str, Any]]:
        """
        Извлечение из MatchGenericInfo
        """
        matches = []
        match_infos = soup.find_all(attrs={'data-testid': 'MatchGenericInfo'})
        
        # MatchGenericInfo содержит время матчей
        for info in match_infos:
            text = info.get_text(strip=True)
            
            # Извлекаем время матча
            time_match = re.search(r'(\d{2}:\d{2})(\d{1,3})[\'"мин]?', text)
            if time_match:
                start_time, minute = time_match.groups()
                
                # Пытаемся найти соответствующие команды в соседних элементах
                # (это более сложная логика для случаев, когда основной метод не сработал)
                
                match_data = {
                    'start_time': start_time,
                    'time': f"{minute}'",
                    'sport': sport,
                    'source': 'match_info'
                }
                
                # Ищем команды в родительском или соседних элементах
                parent = info.parent
                if parent:
                    parent_text = parent.get_text(strip=True)
                    team1, team2 = self._extract_teams_from_context(parent_text)
                    
                    if team1 and team2:
                        if sport == 'tennis':
                            match_data.update({
                                'player1': team1,
                                'player2': team2,
                                'sets_score': '0:0',
                                'current_set': '0:0',
                                'tournament': 'Live турнир'
                            })
                        else:
                            match_data.update({
                                'team1': team1,
                                'team2': team2,
                                'score': '0:0',
                                'league': 'Live лига'
                            })
                        
                        matches.append(match_data)
        
        return matches
    
    def _extract_additional_sources(self, soup, sport: str) -> List[Dict[str, Any]]:
        """
        Извлечение из дополнительных источников
        """
        matches = []
        
        # Ищем в других data-testid элементах
        additional_testids = [
            'MatchGenericSubscribe',
            'MatchGenericActions', 
            'MatchCard'
        ]
        
        for testid in additional_testids:
            elements = soup.find_all(attrs={'data-testid': testid})
            
            for elem in elements:
                text = elem.get_text(strip=True)
                
                # Ищем признаки матча в тексте
                if self._has_match_indicators(text):
                    match_data = self._extract_match_from_text(text, sport)
                    if match_data:
                        matches.append(match_data)
        
        return matches
    
    def _extract_teams_from_context(self, context_text: str) -> tuple:
        """
        Извлечение команд из контекста
        """
        # Ищем паттерны команд в контексте
        team_patterns = [
            r'([А-Я][а-я]{2,20})\\s+([А-Я][а-я]{2,20})',
            r'([А-Яа-я]{3,20})\\s*[-–vs]\\s*([А-Яа-я]{3,20})',
            r'([А-Яа-я]{3,20})\\s+([А-Яа-я]{3,20})'
        ]
        
        for pattern in team_patterns:
            match = re.search(pattern, context_text)
            if match:
                team1, team2 = match.group(1).strip(), match.group(2).strip()
                if (self._is_valid_team_name(team1) and 
                    self._is_valid_team_name(team2)):
                    return team1, team2
        
        return None, None
    
    def _has_match_indicators(self, text: str) -> bool:
        """
        Проверка наличия индикаторов матча
        """
        if not text or len(text) < 5:
            return False
        
        indicators = [
            bool(re.search(r'\d+[:\-]\d+', text)),  # Счет
            bool(re.search(r'\d+[\'"мин]', text)),     # Время
            bool(re.search(r'[А-Я][а-я]+.*[А-Я][а-я]+', text)),  # Команды
            'vs' in text.lower(),
            '-' in text and len(text) > 10
        ]
        
        return sum(indicators) >= 2
    
    def _extract_match_from_text(self, text: str, sport: str) -> Dict[str, Any]:
        """
        Извлечение матча из произвольного текста
        """
        # Ищем команды
        team1, team2 = self._smart_split_teams(text)
        
        if not team1 or not team2:
            return None
        
        # Ищем счет
        score_match = re.search(r'(\d{1,2}[:\-]\d{1,2})', text)
        score = score_match.group(1) if score_match else '0:0'
        
        # Ищем время
        time_match = re.search(r'(\d{1,3})[\'"мин]', text)
        match_time = f"{time_match.group(1)}'" if time_match else "0'"
        
        if sport == 'tennis':
            return {
                'player1': team1,
                'player2': team2,
                'sets_score': score,
                'current_set': '0:0',
                'tournament': 'Live турнир',
                'url': '',
                'sport': sport,
                'source': 'text_extraction'
            }
        else:
            return {
                'team1': team1,
                'team2': team2,
                'score': score,
                'time': match_time,
                'league': 'Live лига',
                'url': '',
                'sport': sport,
                'source': 'text_extraction'
            }
    
    def _is_valid_team_name(self, name: str) -> bool:
        """
        Улучшенная валидация названий команд
        """
        if not name or len(name) < 2 or len(name) > 40:
            return False
        
        # Должно содержать буквы
        if not re.search(r'[А-Яа-яA-Za-z]', name):
            return False
        
        # Исключаем служебные слова
        invalid_words = [
            'матч', 'матча', 'матчей', 'сет', 'партия', 'тайм', 'время', 
            'счет', 'live', 'лига', 'турнир', 'чемпионат'
        ]
        
        name_lower = name.lower().strip()
        if name_lower in invalid_words or name_lower.isdigit():
            return False
        
        # Не должно быть только символов
        if not re.search(r'[а-яёА-ЯЁa-zA-Z]', name):
            return False
        
        return True
    
    def _advanced_cleaning(self, matches: List[Dict[str, Any]], sport: str) -> List[Dict[str, Any]]:
        """
        Продвинутая очистка и дедупликация
        """
        # Убираем дубликаты
        seen_keys = set()
        unique_matches = []
        
        for match in matches:
            # Создаем более умный ключ для дедупликации
            if sport == 'tennis':
                key_parts = [
                    match.get('player1', '').lower().strip(),
                    match.get('player2', '').lower().strip()
                ]
            else:
                key_parts = [
                    match.get('team1', '').lower().strip(),
                    match.get('team2', '').lower().strip()
                ]
            
            # Сортируем части для учета порядка команд
            key_parts.sort()
            key = '|'.join(key_parts)
            
            if key not in seen_keys and len(key) > 6:
                seen_keys.add(key)
                unique_matches.append(match)
        
        # Дополнительная валидация
        validated_matches = []
        for match in unique_matches:
            if self._final_validation(match, sport):
                validated_matches.append(match)
        
        return validated_matches
    
    def _final_validation(self, match: Dict[str, Any], sport: str) -> bool:
        """
        Финальная валидация матча
        """
        if sport == 'tennis':
            p1 = match.get('player1', '').strip()
            p2 = match.get('player2', '').strip()
            return (len(p1) >= 3 and len(p2) >= 3 and 
                   p1.lower() != p2.lower() and
                   self._is_valid_team_name(p1) and 
                   self._is_valid_team_name(p2))
        else:
            t1 = match.get('team1', '').strip()
            t2 = match.get('team2', '').strip()
            return (len(t1) >= 3 and len(t2) >= 3 and 
                   t1.lower() != t2.lower() and
                   self._is_valid_team_name(t1) and 
                   self._is_valid_team_name(t2))