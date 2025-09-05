"""
РАБОЧИЙ скрапер для реальных данных scores24.live
"""
import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Any

class RealScores24Scraper:
    """
    Рабочий скрапер для извлечения реальных live матчей
    """
    
    def __init__(self, logger):
        self.logger = logger
    
    def get_live_matches(self, url: str, sport: str) -> List[Dict[str, Any]]:
        """
        Получение реальных live матчей с scores24.live
        """
        self.logger.info(f"РЕАЛЬНЫЙ сбор {sport} данных с {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.7339.80 Safari/537.36'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                self.logger.error(f"HTTP ошибка: {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            matches = []
            
            # Метод 1: Извлечение из leagueWrapper (основной источник данных)
            league_wrappers = soup.find_all(attrs={'data-testid': 'leagueWrapper'})
            
            for wrapper in league_wrappers:
                wrapper_matches = self._parse_league_wrapper(wrapper, sport)
                matches.extend(wrapper_matches)
            
            # Метод 2: Извлечение из MatchGenericInfo (дополнительные данные)
            match_infos = soup.find_all(attrs={'data-testid': 'MatchGenericInfo'})
            
            if match_infos and not matches:
                # Если основной метод не сработал, пробуем альтернативный
                info_matches = self._parse_match_infos(match_infos, sport)
                matches.extend(info_matches)
            
            # Убираем дубликаты и валидируем
            unique_matches = self._clean_and_validate(matches, sport)
            
            self.logger.info(f"Найдено {len(unique_matches)} реальных {sport} матчей")
            
            # Показываем найденные матчи для отладки
            for i, match in enumerate(unique_matches[:3]):
                teams = f"{match.get('team1', match.get('player1', '?'))} - {match.get('team2', match.get('player2', '?'))}"
                score = match.get('score', match.get('sets_score', '?'))
                time = match.get('time', '?')
                self.logger.info(f"  {i+1}. {teams} {score} ({time})")
            
            return unique_matches
            
        except Exception as e:
            self.logger.error(f"Ошибка парсинга {sport}: {e}")
            return []
    
    def _parse_league_wrapper(self, wrapper, sport: str) -> List[Dict[str, Any]]:
        """
        Парсинг данных из leagueWrapper
        """
        text = wrapper.get_text(strip=True)
        matches = []
        
        # Извлекаем название лиги
        league_match = re.search(r'^([^(]+)', text)
        league_name = league_match.group(1).strip() if league_match else "Неизвестная лига"
        
        # Основной паттерн для live матчей:
        # Время(минуты')Команда1Команда2Счет1Счет2Дополнительные_цифры
        # Пример: 18:4574'ИталияЭстония300030
        
        # Ищем все блоки времени + матчи
        time_match_pattern = r'(\d{2}:\d{2})(\d{1,3})[\'"мин]?([А-Яа-яA-Za-z\s\-\']{6,}?)(\d{1,2})(\d{1,2})(\d{1,2})(\d{1,2})'
        
        time_matches = re.findall(time_match_pattern, text)
        
        for match_data in time_matches:
            try:
                start_time, minute, teams_text, score1, score2, extra1, extra2 = match_data
                
                # Разделяем команды
                team1, team2 = self._split_team_names(teams_text)
                
                if team1 and team2:
                    # Определяем реальный счет (берем первые две цифры как основной счет)
                    final_score = f"{score1}:{score2}"
                    match_time = f"{minute}'"
                    
                    match_info = {
                        'team1' if sport != 'tennis' else 'player1': team1,
                        'team2' if sport != 'tennis' else 'player2': team2,
                        'score': final_score,
                        'time': match_time,
                        'start_time': start_time,
                        'league': league_name,
                        'url': '',
                        'sport': sport,
                        'source': 'real_scores24'
                    }
                    
                    # Для тенниса добавляем специфичные поля
                    if sport == 'tennis':
                        match_info['sets_score'] = final_score
                        match_info['current_set'] = '0:0'
                        match_info['tournament'] = league_name
                    
                    matches.append(match_info)
                    
            except Exception as e:
                self.logger.warning(f"Ошибка парсинга матча: {e}")
                continue
        
        return matches
    
    def _split_team_names(self, teams_text: str) -> tuple:
        """
        Разделение склеенных названий команд
        """
        # Убираем лишние символы
        clean_text = teams_text.strip("'\"")
        
        # Пробуем различные способы разделения
        
        # Способ 1: По заглавным буквам в середине
        # Пример: "ИталияЭстония" -> "Италия" + "Эстония"
        capital_split = re.search(r'^([А-Яа-я\-\']+?)([А-Я][а-я\-\']+)$', clean_text)
        if capital_split:
            return capital_split.group(1), capital_split.group(2)
        
        # Способ 2: По известным окончаниям стран/команд
        country_endings = ['ия', 'ан', 'ия', 'ка', 'да', 'ль', 'на', 'ра', 'ин', 'ен']
        
        for ending in country_endings:
            if ending in clean_text:
                parts = clean_text.split(ending, 1)
                if len(parts) == 2:
                    team1 = parts[0] + ending
                    team2 = parts[1]
                    if len(team1) >= 3 and len(team2) >= 3:
                        return team1, team2
        
        # Способ 3: Разделение пополам (если другие способы не сработали)
        if len(clean_text) >= 6:
            mid = len(clean_text) // 2
            # Ищем хорошую точку разделения рядом с серединой
            for offset in range(0, min(3, mid)):
                split_pos = mid + offset
                if split_pos < len(clean_text):
                    char = clean_text[split_pos]
                    if char.isupper():  # Разделяем по заглавной букве
                        team1 = clean_text[:split_pos]
                        team2 = clean_text[split_pos:]
                        if len(team1) >= 3 and len(team2) >= 3:
                            return team1, team2
        
        return None, None
    
    def _parse_match_infos(self, match_infos, sport: str) -> List[Dict[str, Any]]:
        """
        Альтернативный парсинг через MatchGenericInfo
        """
        matches = []
        
        # MatchGenericInfo содержит время матчей: "18:4574'"
        times_data = []
        
        for info in match_infos:
            text = info.get_text(strip=True)
            
            # Извлекаем время и минуту
            time_match = re.search(r'(\d{2}:\d{2})(\d{1,3})[\'"мин]?', text)
            if time_match:
                start_time, minute = time_match.groups()
                times_data.append({
                    'start_time': start_time,
                    'minute': f"{minute}'",
                    'element': info
                })
        
        # Если есть времена, пробуем найти соответствующие команды
        # (это более сложный метод, используется как fallback)
        
        return matches
    
    def _clean_and_validate(self, matches: List[Dict[str, Any]], sport: str) -> List[Dict[str, Any]]:
        """
        Очистка и валидация найденных матчей
        """
        validated_matches = []
        seen_keys = set()
        
        for match in matches:
            # Проверяем валидность
            if sport == 'tennis':
                team1 = match.get('player1', '').strip()
                team2 = match.get('player2', '').strip()
            else:
                team1 = match.get('team1', '').strip()
                team2 = match.get('team2', '').strip()
            
            # Базовая валидация
            if (len(team1) >= 3 and len(team2) >= 3 and 
                team1 != team2 and
                team1.lower() != team2.lower() and
                not team1.isdigit() and not team2.isdigit()):
                
                # Создаем уникальный ключ
                key = f"{team1}-{team2}-{match.get('score', match.get('sets_score', ''))}"
                key = key.lower()
                
                if key not in seen_keys:
                    seen_keys.add(key)
                    validated_matches.append(match)
        
        return validated_matches