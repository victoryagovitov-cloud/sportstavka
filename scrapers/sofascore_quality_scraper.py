"""
Качественный скрапер SofaScore.com с извлечением всех данных
"""
import requests
from bs4 import BeautifulSoup
import re
import json
from typing import List, Dict, Any
from urllib.parse import urljoin

class SofaScoreQualityScraper:
    """
    Качественный скрапер SofaScore для извлечения максимума данных
    """
    
    def __init__(self, logger):
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.7339.80 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.sofascore.com/',
            'Cache-Control': 'no-cache'
        })
        
        self.base_url = 'https://www.sofascore.com'
    
    def get_all_live_matches(self) -> List[Dict[str, Any]]:
        """
        Получение ВСЕХ live матчей со всех видов спорта
        """
        self.logger.info("SofaScore: качественный сбор ВСЕХ live матчей")
        
        all_matches = []
        
        sports = {
            'football': 'https://www.sofascore.com/football/livescore',
            'tennis': 'https://www.sofascore.com/tennis/livescore',
            'handball': 'https://www.sofascore.com/handball/livescore',
            'table_tennis': 'https://www.sofascore.com/table-tennis/livescore',
            'basketball': 'https://www.sofascore.com/basketball/livescore'
        }
        
        for sport, url in sports.items():
            try:
                sport_matches = self._get_sport_live_matches(url, sport)
                all_matches.extend(sport_matches)
                self.logger.info(f"SofaScore {sport}: {len(sport_matches)} матчей")
            except Exception as e:
                self.logger.warning(f"SofaScore {sport} ошибка: {e}")
        
        return all_matches
    
    def _get_sport_live_matches(self, url: str, sport: str) -> List[Dict[str, Any]]:
        """
        Получение live матчей конкретного вида спорта
        """
        try:
            response = self.session.get(url, timeout=15)
            
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Извлекаем ссылки на live матчи
            match_links = self._extract_match_links(soup)
            
            matches = []
            
            # Для каждой ссылки получаем базовые данные
            for link in match_links:
                try:
                    match_data = self._extract_match_basic_data(link, sport)
                    if match_data:
                        matches.append(match_data)
                except Exception as e:
                    self.logger.warning(f"Ошибка парсинга ссылки {link}: {e}")
                    continue
            
            return matches
            
        except Exception as e:
            self.logger.error(f"Ошибка {sport}: {e}")
            return []
    
    def _extract_match_links(self, soup: BeautifulSoup) -> List[str]:
        """
        Извлечение ссылок на матчи
        """
        links = []
        
        # Ищем все ссылки на матчи
        match_links = soup.find_all('a', href=re.compile(r'/match/|/event/'))
        
        for link in match_links:
            href = link.get('href')
            if href:
                # Проверяем, что это live матч
                link_text = link.get_text(strip=True)
                
                # Если в тексте ссылки есть команды, это вероятно live матч
                if self._looks_like_live_match_link(link_text):
                    links.append(href)
        
        return list(set(links))  # Убираем дубликаты
    
    def _looks_like_live_match_link(self, text: str) -> bool:
        """
        Проверка, похожа ли ссылка на live матч
        """
        if not text or len(text) < 8:
            return False
        
        # Исключаем навигационные ссылки
        exclude_words = ['home', 'livescore', 'standings', 'fixtures', 'results', 'news']
        text_lower = text.lower()
        
        if any(word in text_lower for word in exclude_words):
            return False
        
        # Ищем признаки команд
        # SofaScore обычно показывает: \"Team1 - Team2\"
        has_teams = bool(re.search(r'[A-Za-z]{3,}.*[-–vs].*[A-Za-z]{3,}', text, re.IGNORECASE))
        has_separator = ' - ' in text or ' vs ' in text.lower()
        
        return has_teams or has_separator
    
    def _extract_match_basic_data(self, match_url: str, sport: str) -> Dict[str, Any]:
        """
        Извлечение базовых данных матча из URL и текста ссылки
        """
        try:
            # Парсим URL для получения ID и команд
            # Пример: /football/match/chile-brazil/YUbseVb#id:14169219
            
            url_match = re.search(r'/([^/]+)/match/([^/]+)/([^#]+)#id:(\d+)', match_url)
            if url_match:
                sport_from_url, teams_slug, match_code, match_id = url_match.groups()
                
                # Парсим команды из slug
                teams = teams_slug.split('-')
                if len(teams) >= 2:
                    # Объединяем части команд (может быть \"real-madrid-barcelona\")
                    mid = len(teams) // 2
                    team1_parts = teams[:mid]
                    team2_parts = teams[mid:]
                    
                    team1 = ' '.join(word.capitalize() for word in team1_parts)
                    team2 = ' '.join(word.capitalize() for word in team2_parts)
                    
                    # Получаем детальные данные матча
                    match_details = self._get_match_details(match_url)
                    
                    # Формируем базовые данные
                    base_data = {
                        'url': match_url,
                        'sport': sport,
                        'source': 'sofascore_quality',
                        'match_id': match_id,
                        'match_code': match_code
                    }
                    
                    if sport == 'tennis':
                        base_data.update({
                            'player1': team1,
                            'player2': team2,
                            'sets_score': match_details.get('score', '0:0'),
                            'current_set': match_details.get('current_set', '0:0'),
                            'tournament': match_details.get('tournament', 'SofaScore Live')
                        })
                    else:
                        base_data.update({
                            'team1': team1,
                            'team2': team2,
                            'score': match_details.get('score', '0:0'),
                            'time': match_details.get('time', "0'"),
                            'league': match_details.get('league', 'SofaScore Live')
                        })
                    
                    # Добавляем детальные данные
                    if match_details:
                        base_data.update(match_details)
                    
                    return base_data
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Ошибка парсинга URL {match_url}: {e}")
            return None
    
    def _get_match_details(self, match_url: str) -> Dict[str, Any]:
        \"\"\"
        Получение детальных данных матча
        \"\"\"
        if not match_url.startswith('http'):
            full_url = urljoin(self.base_url, match_url)
        else:
            full_url = match_url
        
        try:
            response = self.session.get(full_url, timeout=10)
            
            if response.status_code != 200:
                return {}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = response.text
            
            details = {}
            
            # 1. Извлекаем счет и время
            details.update(self._extract_score_and_time(page_text))
            
            # 2. Извлекаем статистику
            details.update(self._extract_match_statistics(page_text))
            
            # 3. Извлекаем информацию о турнире
            details.update(self._extract_tournament_info(page_text))
            
            # 4. Извлекаем H2H данные
            details.update(self._extract_h2h_info(page_text))
            
            # 5. Извлекаем форму команд
            details.update(self._extract_team_form(page_text))
            
            return details
            
        except Exception as e:
            self.logger.warning(f"Ошибка получения деталей матча: {e}")
            return {}
    
    def _extract_score_and_time(self, page_text: str) -> Dict[str, Any]:
        \"\"\"
        Извлечение счета и времени матча
        \"\"\"
        data = {}
        
        # Ищем live счет
        live_score_pattern = r'\"homeScore\"\\s*:\\s*(\\d+).*?\"awayScore\"\\s*:\\s*(\\d+)'
        score_match = re.search(live_score_pattern, page_text)
        
        if score_match:
            home_score, away_score = score_match.groups()
            data['score'] = f"{home_score}:{away_score}"
        else:
            # Альтернативный поиск счета
            simple_score = re.search(r'(\\d{1,2}[:-]\\d{1,2})', page_text)
            if simple_score:
                data['score'] = simple_score.group(1)
        
        # Ищем время матча
        time_patterns = [
            r'\"minute\"\\s*:\\s*(\\d+)',
            r'\"time\"\\s*:\\s*\"(\\d+\\')\",
            r'(\\d{1,3})\\'(?!\\d)'  # Минуты с апострофом, не время
        ]
        
        for pattern in time_patterns:
            time_match = re.search(pattern, page_text)
            if time_match:
                minute = time_match.group(1)
                data['time'] = f"{minute}'"
                break
        
        return data
    
    def _extract_match_statistics(self, page_text: str) -> Dict[str, Any]:
        \"\"\"
        Извлечение статистики матча
        \"\"\"
        stats = {}
        
        # 1. Владение мячом
        possession_matches = re.findall(r'(\\d{1,2})%', page_text)
        if len(possession_matches) >= 2:
            # Берем первые два процента как владение
            stats['possession'] = {
                'team1': f"{possession_matches[0]}%",
                'team2': f"{possession_matches[1]}%"
            }
        
        # 2. xG (ожидаемые голы)
        xg_pattern = r'\"expectedGoals\"\\s*:\\s*(\\d+\\.\\d+)'
        xg_matches = re.findall(xg_pattern, page_text)
        
        if len(xg_matches) >= 2:
            stats['xG'] = {
                'team1': xg_matches[0],
                'team2': xg_matches[1]
            }
        else:
            # Альтернативный поиск xG
            xg_alt = re.findall(r'(\\d+\\.\\d+)', page_text)
            if len(xg_alt) >= 2:
                # Фильтруем разумные значения xG (0.0-10.0)
                valid_xg = [x for x in xg_alt if 0.0 <= float(x) <= 10.0]
                if len(valid_xg) >= 2:
                    stats['xG'] = {
                        'team1': valid_xg[0],
                        'team2': valid_xg[1]
                    }
        
        # 3. Удары
        shots_pattern = r'\"shots\"\\s*:\\s*\\[(\\d+),\\s*(\\d+)\\]'
        shots_match = re.search(shots_pattern, page_text)
        
        if shots_match:
            stats['shots'] = {
                'team1': shots_match.group(1),
                'team2': shots_match.group(2)
            }
        else:
            # Ищем удары в тексте
            shot_numbers = [int(x) for x in re.findall(r'\\b(\\d{1,2})\\b', page_text) 
                           if 1 <= int(x) <= 30]  # Разумные пределы для ударов
            if len(shot_numbers) >= 4:
                stats['shots'] = {
                    'team1_total': str(shot_numbers[0]),
                    'team1_on_target': str(shot_numbers[1]),
                    'team2_total': str(shot_numbers[2]),
                    'team2_on_target': str(shot_numbers[3])
                }
        
        # 4. Угловые
        corners_pattern = r'\"corners\"\\s*:\\s*\\[(\\d+),\\s*(\\d+)\\]'
        corners_match = re.search(corners_pattern, page_text)
        
        if corners_match:
            stats['corners'] = {
                'team1': corners_match.group(1),
                'team2': corners_match.group(2)
            }
        
        # 5. Фолы
        fouls_pattern = r'\"fouls\"\\s*:\\s*\\[(\\d+),\\s*(\\d+)\\]'
        fouls_match = re.search(fouls_pattern, page_text)
        
        if fouls_match:
            stats['fouls'] = {
                'team1': fouls_match.group(1),
                'team2': fouls_match.group(2)
            }
        
        # 6. Карточки
        cards_yellow = re.findall(r'\"yellowCards\"\\s*:\\s*(\\d+)', page_text)
        cards_red = re.findall(r'\"redCards\"\\s*:\\s*(\\d+)', page_text)
        
        if cards_yellow or cards_red:
            stats['cards'] = {}
            if len(cards_yellow) >= 2:
                stats['cards']['yellow'] = {
                    'team1': cards_yellow[0],
                    'team2': cards_yellow[1]
                }
            if len(cards_red) >= 2:
                stats['cards']['red'] = {
                    'team1': cards_red[0],
                    'team2': cards_red[1]
                }
        
        return {'statistics': stats} if stats else {}
    
    def _extract_tournament_info(self, page_text: str) -> Dict[str, Any]:
        \"\"\"
        Извлечение информации о турнире/лиге
        \"\"\"
        info = {}
        
        # Ищем название турнира
        tournament_patterns = [
            r'\"tournament\"\\s*:\\s*{[^}]*\"name\"\\s*:\\s*\"([^\"]+)\"',
            r'\"league\"\\s*:\\s*\"([^\"]+)\"',
            r'\"competition\"\\s*:\\s*\"([^\"]+)\"'
        ]
        
        for pattern in tournament_patterns:
            match = re.search(pattern, page_text)
            if match:
                info['league'] = match.group(1)
                break
        
        # Ищем страну/регион
        country_pattern = r'\"country\"\\s*:\\s*{[^}]*\"name\"\\s*:\\s*\"([^\"]+)\"'
        country_match = re.search(country_pattern, page_text)
        
        if country_match:
            country = country_match.group(1)
            if 'league' in info:
                info['league'] = f\"{country} {info['league']}\"
            else:
                info['league'] = country
        
        return info
    
    def _extract_h2h_info(self, page_text: str) -> Dict[str, Any]:
        \"\"\"
        Извлечение H2H данных
        \"\"\"
        h2h_data = {}
        
        # Ищем H2H упоминания
        h2h_count = page_text.lower().count('h2h') + page_text.lower().count('head to head')
        
        if h2h_count > 5:
            # Ищем результаты предыдущих встреч
            h2h_pattern = r'\"h2h\"\\s*:\\s*\\[([^\\]]+)\\]'
            h2h_match = re.search(h2h_pattern, page_text)
            
            if h2h_match:
                h2h_data['h2h'] = 'H2H данные найдены'
            else:
                h2h_data['h2h'] = f'H2H упоминаний: {h2h_count}'
        
        return h2h_data
    
    def _extract_team_form(self, page_text: str) -> Dict[str, Any]:
        \"\"\"
        Извлечение формы команд
        \"\"\"
        form_data = {}
        
        form_count = page_text.lower().count('form')
        
        if form_count > 10:
            form_data['team_form'] = f'Форма команд: {form_count} упоминаний'
        
        return form_data
    
    def get_enhanced_match_data(self, match_url: str) -> Dict[str, Any]:
        \"\"\"
        Получение расширенных данных конкретного матча
        \"\"\"
        if not match_url.startswith('http'):
            full_url = urljoin(self.base_url, match_url)
        else:
            full_url = match_url
        
        try:
            response = self.session.get(full_url, timeout=12)
            
            if response.status_code != 200:
                return {}
            
            page_text = response.text
            soup = BeautifulSoup(page_text, 'html.parser')
            
            enhanced_data = {}
            
            # Извлекаем ВСЮ доступную статистику
            enhanced_data.update(self._extract_score_and_time(page_text))
            enhanced_data.update(self._extract_match_statistics(page_text))
            enhanced_data.update(self._extract_tournament_info(page_text))
            enhanced_data.update(self._extract_h2h_info(page_text))
            enhanced_data.update(self._extract_team_form(page_text))
            
            # Дополнительные данные
            enhanced_data.update(self._extract_additional_stats(page_text))
            
            return enhanced_data
            
        except Exception as e:
            self.logger.warning(f\"Ошибка получения расширенных данных: {e}\")
            return {}
    
    def _extract_additional_stats(self, page_text: str) -> Dict[str, Any]:
        \"\"\"
        Извлечение дополнительной статистики
        \"\"\"
        additional = {}
        
        # Точность передач
        pass_accuracy = re.findall(r'(\\d{1,2})%', page_text)
        if len(pass_accuracy) >= 4:  # Владение + точность передач для обеих команд
            additional['pass_accuracy'] = {
                'team1': f"{pass_accuracy[2]}%",  # 3-й и 4-й проценты
                'team2': f"{pass_accuracy[3]}%"
            }
        
        # Офсайды
        offsides = re.findall(r'\"offsides\"\\s*:\\s*(\\d+)', page_text)
        if len(offsides) >= 2:
            additional['offsides'] = {
                'team1': offsides[0],
                'team2': offsides[1]
            }
        
        # Сейвы вратарей
        saves = re.findall(r'\"saves\"\\s*:\\s*(\\d+)', page_text)
        if len(saves) >= 2:
            additional['saves'] = {
                'team1': saves[0],
                'team2': saves[1]
            }
        
        return {'additional_statistics': additional} if additional else {}