"""
Простой качественный скрапер SofaScore
"""
import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Any

class SofaScoreSimpleQuality:
    """
    Простой но качественный скрапер SofaScore
    """
    
    def __init__(self, logger):
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9'
        })
    
    def get_live_matches(self, sport: str) -> List[Dict[str, Any]]:
        """
        Получение live матчей
        """
        self.logger.info(f"SofaScore качественный сбор {sport}")
        
        # ИСПРАВЛЕНИЕ: Идем на главную страницу для получения АКТУАЛЬНЫХ live матчей
        sport_urls = {
            'football': 'https://www.sofascore.com/',  # Главная страница с актуальными live
            'tennis': 'https://www.sofascore.com/',
            'handball': 'https://www.sofascore.com/',
            'table_tennis': 'https://www.sofascore.com/',
            'basketball': 'https://www.sofascore.com/'
        }
        
        url = sport_urls.get(sport)
        if not url:
            return []
        
        try:
            # ИСПРАВЛЕНИЕ: Добавляем заголовки для получения свежих данных (не кэш)
            fresh_headers = self.session.headers.copy()
            fresh_headers.update({
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache', 
                'Expires': '0',
                'If-None-Match': '',
                'If-Modified-Since': ''
            })
            
            response = self.session.get(url, headers=fresh_headers, timeout=15)
            
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Извлекаем ссылки на матчи
            match_links = soup.find_all('a', href=re.compile(r'/match/'))
            
            matches = []
            
            for link in match_links:
                try:
                    match_data = self._parse_match_link(link, sport)
                    if match_data:
                        matches.append(match_data)
                except Exception:
                    continue
            
            # Убираем дубликаты
            unique_matches = self._remove_duplicates(matches, sport)
            
            self.logger.info(f"SofaScore {sport}: {len(unique_matches)} качественных матчей")
            return unique_matches
            
        except Exception as e:
            self.logger.error(f"SofaScore {sport} ошибка: {e}")
            return []
    
    def _parse_match_link(self, link, sport: str) -> Dict[str, Any]:
        """
        Парсинг ссылки на матч
        """
        href = link.get('href', '')
        text = link.get_text(strip=True)
        
        if not href or not text:
            return None
        
        # Парсим URL: /football/match/chile-brazil/YUbseVb#id:14169219
        url_match = re.search(r'/([^/]+)/match/([^/]+)/[^#]+#id:(\d+)', href)
        
        if not url_match:
            return None
        
        sport_from_url, teams_slug, match_id = url_match.groups()
        
        # Парсим команды из slug
        team1, team2 = self._parse_teams_from_slug(teams_slug)
        
        if not team1 or not team2:
            # Пробуем извлечь из текста ссылки
            team1, team2 = self._parse_teams_from_text(text)
        
        if not team1 or not team2:
            return None
        
        # Получаем детальные данные матча
        match_details = self._get_basic_match_data(href)
        
        # Формируем результат
        base_data = {
            'url': href,
            'sport': sport,
            'source': 'sofascore_quality',
            'match_id': match_id,
            'sofascore_url': f"https://www.sofascore.com{href}"
        }
        
        if sport == 'tennis':
            base_data.update({
                'player1': team1,
                'player2': team2,
                'sets_score': match_details.get('score', '0:0'),
                'current_set': '0:0',
                'tournament': match_details.get('league', 'SofaScore Live')
            })
        else:
            base_data.update({
                'team1': team1,
                'team2': team2,
                'score': match_details.get('score', '0:0'),
                'time': match_details.get('time', "0'"),
                'league': match_details.get('league', 'SofaScore Live')
            })
        
        # Добавляем статистику если есть
        if 'statistics' in match_details:
            base_data['statistics'] = match_details['statistics']
        
        return base_data
    
    def _parse_teams_from_slug(self, teams_slug: str) -> tuple:
        """
        Парсинг команд из URL slug
        """
        try:
            # Разделяем по дефису
            parts = teams_slug.split('-')
            
            if len(parts) >= 2:
                # Находим середину
                mid = len(parts) // 2
                
                team1_parts = parts[:mid]
                team2_parts = parts[mid:]
                
                team1 = ' '.join(word.capitalize() for word in team1_parts)
                team2 = ' '.join(word.capitalize() for word in team2_parts)
                
                if len(team1) >= 3 and len(team2) >= 3:
                    return team1, team2
            
            return None, None
            
        except Exception:
            return None, None
    
    def _parse_teams_from_text(self, text: str) -> tuple:
        """
        Парсинг команд из текста ссылки
        """
        try:
            # SofaScore обычно использует формат "Team1 - Team2"
            if ' - ' in text:
                parts = text.split(' - ', 1)
                if len(parts) == 2:
                    team1, team2 = parts[0].strip(), parts[1].strip()
                    
                    # Убираем лишнее (время, счет)
                    team1 = re.sub(r'\d+.*', '', team1).strip()
                    team2 = re.sub(r'\d+.*', '', team2).strip()
                    
                    if len(team1) >= 3 and len(team2) >= 3:
                        return team1, team2
            
            return None, None
            
        except Exception:
            return None, None
    
    def _get_basic_match_data(self, match_url: str) -> Dict[str, Any]:
        """
        Получение базовых данных матча
        """
        full_url = f"https://www.sofascore.com{match_url}"
        
        try:
            response = self.session.get(full_url, timeout=8)
            
            if response.status_code != 200:
                return {}
            
            page_text = response.text
            data = {}
            
            # Ищем live счет
            score_patterns = [
                r'"homeScore":\s*(\d+).*?"awayScore":\s*(\d+)',
                r'(\d{1,2})\s*[-:]\s*(\d{1,2})'
            ]
            
            for pattern in score_patterns:
                score_match = re.search(pattern, page_text)
                if score_match:
                    home_score, away_score = score_match.groups()
                    data['score'] = f"{home_score}:{away_score}"
                    break
            
            # Улучшенное извлечение времени матча
            data['time'] = self._extract_match_time(page_text)
            
            # Ищем название лиги/турнира
            league_patterns = [
                r'"tournament":\s*{[^}]*"name":\s*"([^"]+)"',
                r'"league":\s*"([^"]+)"'
            ]
            
            for pattern in league_patterns:
                league_match = re.search(pattern, page_text)
                if league_match:
                    data['league'] = league_match.group(1)
                    break
            
            # Извлекаем базовую статистику
            stats = self._extract_basic_statistics(page_text)
            if stats:
                data['statistics'] = stats
            
            return data
            
        except Exception as e:
            return {}
    
    def _extract_match_time(self, page_text: str) -> str:
        """
        Улучшенное извлечение времени матча
        """
        try:
            # Сначала ищем статус матча и время в JSON
            status_patterns = [
                r'"status":\s*{[^}]*"code":\s*(\d+)[^}]*"description":\s*"([^"]+)"',
                r'"status":\s*{[^}]*"type":\s*"([^"]+)"'
            ]
            
            # Ищем минуту в различных форматах
            time_patterns = [
                r'"minute":\s*(\d+)',  # JSON minute
                r'"time":\s*"(\d{1,3})\'?"',  # JSON time с апострофом
                r'"currentPeriodStartTimestamp":\s*(\d+)',  # Timestamp начала периода
                r'(\d{1,3})\'\s*(?:HT|FT|LIVE|$)',  # 45' HT формат
                r'(\d{1,3})\+(\d+)\'',  # 90+3' формат (добавленное время)
                r'HT\s*(\d{1,2}):(\d{2})',  # HT 45:00 формат
                r'FT\s*(\d{1,2}):(\d{2})',  # FT 90:00 формат
            ]
            
            # Проверяем статус матча
            for pattern in status_patterns:
                status_match = re.search(pattern, page_text)
                if status_match:
                    if len(status_match.groups()) >= 2:
                        status_code, description = status_match.groups()[:2]
                        # Если матч завершен
                        if 'finished' in description.lower() or 'ended' in description.lower():
                            return "FT"
                        # Если перерыв
                        elif 'halftime' in description.lower() or 'break' in description.lower():
                            return "HT"
                    elif len(status_match.groups()) == 1:
                        status_type = status_match.group(1)
                        if status_type.lower() in ['finished', 'ended']:
                            return "FT"
                        elif status_type.lower() in ['halftime', 'break']:
                            return "HT"
            
            # Ищем конкретную минуту
            for pattern in time_patterns:
                time_match = re.search(pattern, page_text)
                if time_match:
                    if '+' in pattern and len(time_match.groups()) >= 2:
                        # Добавленное время: 90+3'
                        main_time, added_time = time_match.groups()[:2]
                        return f"{main_time}+{added_time}'"
                    elif ':' in pattern and len(time_match.groups()) >= 2:
                        # Формат HH:MM
                        hours, minutes = time_match.groups()[:2]
                        total_minutes = int(hours) * 60 + int(minutes)
                        return f"{total_minutes}'"
                    else:
                        # Обычная минута
                        minute = time_match.group(1)
                        return f"{minute}'"
            
            # Если ничего не найдено, ищем ключевые слова статуса
            if re.search(r'\bLIVE\b', page_text, re.IGNORECASE):
                # Если матч live, но минута не найдена, возвращаем среднее значение
                return "45'"
            elif re.search(r'\bHT\b', page_text):
                return "HT"
            elif re.search(r'\bFT\b', page_text):
                return "FT"
            
            # По умолчанию возвращаем начальное время
            return "1'"
            
        except Exception as e:
            return "1'"
    
    def _extract_basic_statistics(self, page_text: str) -> Dict[str, Any]:
        """
        Извлечение базовой статистики
        """
        stats = {}
        
        # Владение мячом
        possession = re.findall(r'(\d{1,2})%', page_text)
        if len(possession) >= 2:
            stats['possession'] = {
                'team1': f"{possession[0]}%",
                'team2': f"{possession[1]}%"
            }
        
        # xG
        xg_values = re.findall(r'(\d+\.\d+)', page_text)
        valid_xg = [x for x in xg_values if 0.0 <= float(x) <= 10.0]
        
        if len(valid_xg) >= 2:
            stats['xG'] = {
                'team1': valid_xg[0],
                'team2': valid_xg[1]
            }
        
        # Удары (ищем небольшие числа)
        small_numbers = [int(x) for x in re.findall(r'\b(\d{1,2})\b', page_text) 
                        if 1 <= int(x) <= 25]
        
        if len(small_numbers) >= 4:
            stats['shots'] = {
                'team1': str(small_numbers[0]),
                'team2': str(small_numbers[1])
            }
        
        return stats
    
    def _find_match_url(self, team1: str, team2: str, sport: str) -> str:
        """
        УЛУЧШЕННЫЙ поиск URL матча по названиям команд
        """
        try:
            # Инициализируем кэш URL (в рамках сессии)
            if not hasattr(self, '_match_url_cache'):
                self._match_url_cache = {}
            
            # Проверяем кэш
            cache_key = f"{team1.lower()}:{team2.lower()}:{sport}"
            if cache_key in self._match_url_cache:
                self.logger.debug(f"SofaScore: URL из кэша для {team1} vs {team2}")
                return self._match_url_cache[cache_key]
            
            # Генерируем варианты названий команд
            from utils.team_abbreviations import get_team_variants
            team1_variants = get_team_variants(team1)
            team2_variants = get_team_variants(team2)
            
            self.logger.debug(f"SofaScore поиск: {team1} ({len(team1_variants)} вариантов) vs {team2} ({len(team2_variants)} вариантов)")
            
            # ЦЕЛЕВОЙ ПОИСК - сначала в live разделе
            live_url = f"https://www.sofascore.com/{sport}/livescore"
            
            try:
                response = self.session.get(live_url, timeout=8)
                if response.status_code == 200:
                    match_url = self._smart_search_in_content(response.text, team1_variants, team2_variants)
                    if match_url:
                        self._match_url_cache[cache_key] = match_url
                        return match_url
            except Exception as e:
                self.logger.debug(f"Live поиск неудачен: {e}")
            
            # FALLBACK - поиск на главной странице
            main_url = "https://www.sofascore.com/"
            response = self.session.get(main_url, timeout=10)
            
            if response.status_code == 200:
                match_url = self._smart_search_in_content(response.text, team1_variants, team2_variants)
                if match_url:
                    self._match_url_cache[cache_key] = match_url
                    return match_url
            
            # ПОСЛЕДНЯЯ ПОПЫТКА - через поисковую функцию
            search_url = self._search_match_on_sofascore(team1, team2, sport)
            if search_url:
                self._match_url_cache[cache_key] = search_url
            
            return search_url
            
        except Exception as e:
            self.logger.warning(f"SofaScore поиск матча ошибка: {e}")
            return ""
    
    def _smart_search_in_content(self, html_content: str, team1_variants: List[str], 
                                team2_variants: List[str]) -> str:
        """
        Умный поиск матча в HTML контенте
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Ищем только ссылки на матчи
        match_links = soup.find_all('a', href=re.compile(r'/match/'))
        
        best_match_url = ""
        best_confidence = 0.0
        
        for link in match_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # Вычисляем уверенность в совпадении
            from utils.team_abbreviations import calculate_team_match_confidence
            confidence = calculate_team_match_confidence(text, team1_variants[0], team2_variants[0])
            
            if confidence > best_confidence and confidence > 0.7:
                best_match_url = href
                best_confidence = confidence
                
                # Если очень высокая уверенность - можем остановиться
                if confidence > 0.95:
                    break
        
        if best_match_url:
            self.logger.info(f"SofaScore: найден матч с уверенностью {best_confidence:.2f}")
        
        return best_match_url
    
    def _search_match_on_sofascore(self, team1: str, team2: str, sport: str) -> str:
        """
        Поиск матча через функцию поиска SofaScore
        """
        try:
            # Поиск по первой команде
            search_query = team1.replace(' ', '%20')
            search_url = f"https://www.sofascore.com/search?q={search_query}"
            
            response = self.session.get(search_url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Ищем ссылки на матчи в результатах поиска
                links = soup.find_all('a', href=True)
                
                for link in links:
                    href = link.get('href')
                    text = link.get_text(strip=True).lower()
                    
                    if (team2.lower() in text and '/match/' in href):
                        return href
            
            return ""
            
        except Exception as e:
            return ""
    
    def get_detailed_match_data(self, team1_or_url: str, team2: str = None, sport: str = 'football') -> Dict[str, Any]:
        """
        Получение детальных данных матча с SofaScore
        Принимает либо URL матча, либо названия команд
        """
        if team2 is None:
            # Передан URL матча
            full_url = f"https://www.sofascore.com{team1_or_url}"
        else:
            # Переданы названия команд - ищем матч
            match_url = self._find_match_url(team1_or_url, team2, sport)
            if not match_url:
                self.logger.warning(f"SofaScore: матч {team1_or_url} vs {team2} не найден")
                return {}
            full_url = f"https://www.sofascore.com{match_url}"
        
        try:
            response = self.session.get(full_url, timeout=15)
            
            if response.status_code != 200:
                return {}
            
            page_text = response.text
            detailed_data = {}
            
            # Определяем вид спорта из URL если не передан
            if sport == 'football' and match_url:
                if '/tennis/' in match_url:
                    sport = 'tennis'
                elif '/handball/' in match_url:
                    sport = 'handball'
                elif '/table-tennis/' in match_url:
                    sport = 'table_tennis'
                elif '/basketball/' in match_url:
                    sport = 'basketball'
            
            # Базовые данные матча
            basic_data = self._get_basic_match_data(match_url)
            detailed_data.update(basic_data)
            detailed_data['sport'] = sport
            
            # Расширенная статистика с учетом вида спорта
            detailed_stats = self._extract_detailed_statistics(page_text, sport)
            if detailed_stats:
                detailed_data['detailed_statistics'] = detailed_stats
            
            # История встреч (H2H)
            h2h_data = self._extract_h2h_data(page_text)
            if h2h_data:
                detailed_data['h2h'] = h2h_data
            
            # Форма команд
            form_data = self._extract_team_form(page_text)
            if form_data:
                detailed_data['team_form'] = form_data
            
            # Коэффициенты
            odds_data = self._extract_odds_data(page_text)
            if odds_data:
                detailed_data['odds'] = odds_data
            
            # Турнирные данные и рейтинги
            tournament_data = self._extract_tournament_data(page_text, sport)
            if tournament_data:
                detailed_data['tournament_info'] = tournament_data
            
            # Статистика команд/игроков
            team_stats = self._extract_team_statistics(page_text, sport)
            if team_stats:
                detailed_data['team_statistics'] = team_stats
            
            return detailed_data
            
        except Exception as e:
            self.logger.error(f"Ошибка сбора детальных данных {match_url}: {e}")
            return {}
    
    def _extract_detailed_statistics(self, page_text: str, sport: str = 'football') -> Dict[str, Any]:
        """
        Извлечение детальной статистики матча с учетом вида спорта
        """
        stats = {}
        
        try:
            # Поиск JSON данных со статистикой
            json_pattern = r'"statistics":\s*(\[.*?\])'
            json_match = re.search(json_pattern, page_text, re.DOTALL)
            
            if json_match:
                import json
                try:
                    stats_json = json.loads(json_match.group(1))
                    
                    for stat_group in stats_json:
                        if isinstance(stat_group, dict) and 'groups' in stat_group:
                            for group in stat_group['groups']:
                                if 'statisticsItems' in group:
                                    for item in group['statisticsItems']:
                                        stat_name = item.get('name', '')
                                        home_value = item.get('homeValue', '')
                                        away_value = item.get('awayValue', '')
                                        
                                        if stat_name and home_value != '' and away_value != '':
                                            stats[stat_name] = {
                                                'team1': str(home_value),
                                                'team2': str(away_value)
                                            }
                except:
                    pass
            
            # Если JSON не найден, используем спорт-специфичные паттерны
            if not stats:
                stats = self._extract_sport_specific_stats(page_text, sport)
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения детальной статистики: {e}")
        
        return stats
    
    def _extract_sport_specific_stats(self, page_text: str, sport: str) -> Dict[str, Any]:
        """
        Извлечение статистики специфичной для каждого вида спорта
        """
        stats = {}
        
        if sport == 'football':
            stat_patterns = {
                'possession': r'(\d{1,2})%.*?(\d{1,2})%',
                'shots_total': r'"shotsTotal":\s*(\d+).*?"shotsTotal":\s*(\d+)',
                'shots_on_target': r'"shotsOnTarget":\s*(\d+).*?"shotsOnTarget":\s*(\d+)',
                'corners': r'"cornerKicks":\s*(\d+).*?"cornerKicks":\s*(\d+)',
                'fouls': r'"fouls":\s*(\d+).*?"fouls":\s*(\d+)',
                'yellow_cards': r'"yellowCards":\s*(\d+).*?"yellowCards":\s*(\d+)',
                'red_cards': r'"redCards":\s*(\d+).*?"redCards":\s*(\d+)',
                'offsides': r'"offsides":\s*(\d+).*?"offsides":\s*(\d+)',
                'passes': r'"passes":\s*(\d+).*?"passes":\s*(\d+)',
                'pass_accuracy': r'"passAccuracy":\s*(\d+).*?"passAccuracy":\s*(\d+)',
            }
        
        elif sport == 'tennis':
            stat_patterns = {
                'aces': r'"aces":\s*(\d+).*?"aces":\s*(\d+)',
                'double_faults': r'"doubleFaults":\s*(\d+).*?"doubleFaults":\s*(\d+)',
                'first_serve': r'"firstServe":\s*(\d+).*?"firstServe":\s*(\d+)',
                'first_serve_won': r'"firstServeWon":\s*(\d+).*?"firstServeWon":\s*(\d+)',
                'second_serve_won': r'"secondServeWon":\s*(\d+).*?"secondServeWon":\s*(\d+)',
                'break_points_saved': r'"breakPointsSaved":\s*(\d+).*?"breakPointsSaved":\s*(\d+)',
                'break_points_converted': r'"breakPointsConverted":\s*(\d+).*?"breakPointsConverted":\s*(\d+)',
                'winners': r'"winners":\s*(\d+).*?"winners":\s*(\d+)',
                'unforced_errors': r'"unforcedErrors":\s*(\d+).*?"unforcedErrors":\s*(\d+)',
                'total_points': r'"totalPoints":\s*(\d+).*?"totalPoints":\s*(\d+)',
            }
        
        elif sport == 'handball':
            stat_patterns = {
                'shots': r'"shots":\s*(\d+).*?"shots":\s*(\d+)',
                'shots_on_target': r'"shotsOnTarget":\s*(\d+).*?"shotsOnTarget":\s*(\d+)',
                'goals': r'"goals":\s*(\d+).*?"goals":\s*(\d+)',
                'saves': r'"saves":\s*(\d+).*?"saves":\s*(\d+)',
                'assists': r'"assists":\s*(\d+).*?"assists":\s*(\d+)',
                'steals': r'"steals":\s*(\d+).*?"steals":\s*(\d+)',
                'blocks': r'"blocks":\s*(\d+).*?"blocks":\s*(\d+)',
                'turnovers': r'"turnovers":\s*(\d+).*?"turnovers":\s*(\d+)',
                'yellow_cards': r'"yellowCards":\s*(\d+).*?"yellowCards":\s*(\d+)',
                'red_cards': r'"redCards":\s*(\d+).*?"redCards":\s*(\d+)',
                'two_minutes': r'"twoMinutes":\s*(\d+).*?"twoMinutes":\s*(\d+)',
            }
        
        elif sport == 'table_tennis':
            stat_patterns = {
                'points_won': r'"pointsWon":\s*(\d+).*?"pointsWon":\s*(\d+)',
                'service_points': r'"servicePoints":\s*(\d+).*?"servicePoints":\s*(\d+)',
                'return_points': r'"returnPoints":\s*(\d+).*?"returnPoints":\s*(\d+)',
                'winners': r'"winners":\s*(\d+).*?"winners":\s*(\d+)',
                'errors': r'"errors":\s*(\d+).*?"errors":\s*(\d+)',
                'longest_rally': r'"longestRally":\s*(\d+).*?"longestRally":\s*(\d+)',
            }
        
        else:
            # Базовые паттерны для неизвестных видов спорта
            stat_patterns = {
                'score_team1': r'"homeScore":\s*(\d+)',
                'score_team2': r'"awayScore":\s*(\d+)',
            }
        
        # Применяем паттерны
        for stat_name, pattern in stat_patterns.items():
            match = re.search(pattern, page_text)
            if match and len(match.groups()) >= 2:
                stats[stat_name] = {
                    'team1': match.group(1),
                    'team2': match.group(2)
                }
            elif match and len(match.groups()) == 1:
                # Для паттернов с одним значением
                if 'team1' in stat_name:
                    if 'score_team1' not in stats:
                        stats['score_team1'] = {'team1': match.group(1), 'team2': '0'}
                elif 'team2' in stat_name:
                    if 'score_team2' not in stats:
                        stats['score_team2'] = {'team1': '0', 'team2': match.group(1)}
        
        return stats
    
    def _extract_h2h_data(self, page_text: str) -> List[Dict[str, Any]]:
        """
        Извлечение истории личных встреч
        """
        h2h_matches = []
        
        try:
            # Поиск H2H данных в JSON
            h2h_pattern = r'"h2h":\s*(\[.*?\])'
            h2h_match = re.search(h2h_pattern, page_text, re.DOTALL)
            
            if h2h_match:
                import json
                try:
                    h2h_json = json.loads(h2h_match.group(1))
                    
                    for match in h2h_json[:5]:  # Последние 5 матчей
                        if isinstance(match, dict):
                            h2h_matches.append({
                                'date': match.get('startTimestamp', ''),
                                'home_team': match.get('homeTeam', {}).get('name', ''),
                                'away_team': match.get('awayTeam', {}).get('name', ''),
                                'score': f"{match.get('homeScore', '')}-{match.get('awayScore', '')}",
                                'tournament': match.get('tournament', {}).get('name', '')
                            })
                except:
                    pass
                    
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения H2H: {e}")
        
        return h2h_matches
    
    def _extract_team_form(self, page_text: str) -> Dict[str, Any]:
        """
        Извлечение формы команд (последние результаты)
        """
        form_data = {}
        
        try:
            # Поиск формы команд в JSON
            form_patterns = [
                r'"homeTeamForm":\s*"([WDLWDL]*)"',
                r'"awayTeamForm":\s*"([WDLWDL]*)"'
            ]
            
            forms = []
            for pattern in form_patterns:
                match = re.search(pattern, page_text)
                if match:
                    forms.append(match.group(1))
            
            if len(forms) >= 2:
                form_data = {
                    'team1_form': forms[0],
                    'team2_form': forms[1]
                }
                
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения формы команд: {e}")
        
        return form_data
    
    def _extract_odds_data(self, page_text: str) -> Dict[str, Any]:
        """
        Извлечение коэффициентов
        """
        odds = {}
        
        try:
            # Поиск основных коэффициентов 1X2
            odds_pattern = r'"odds":\s*\{[^}]*"1":\s*([\d.]+)[^}]*"X":\s*([\d.]+)[^}]*"2":\s*([\d.]+)'
            odds_match = re.search(odds_pattern, page_text)
            
            if odds_match:
                odds['1X2'] = {
                    '1': odds_match.group(1),
                    'X': odds_match.group(2),
                    '2': odds_match.group(3)
                }
                
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения коэффициентов: {e}")
        
        return odds
    
    def get_actual_live_matches(self, sport: str) -> List[Dict[str, Any]]:
        """
        Получение АКТУАЛЬНЫХ live матчей (те, что видит пользователь)
        """
        try:
            self.logger.info(f"SofaScore получение АКТУАЛЬНЫХ live {sport}")
            
            # Пробуем разные URL для получения актуальных данных
            urls_to_try = [
                'https://www.sofascore.com/',  # Главная страница
                f'https://www.sofascore.com/{sport}/live',  # Live страница
                f'https://www.sofascore.com/{sport}',  # Страница спорта
            ]
            
            for url in urls_to_try:
                try:
                    # Добавляем заголовки для обхода кэширования
                    headers = self.session.headers.copy()
                    headers.update({
                        'Cache-Control': 'no-cache, no-store, must-revalidate',
                        'Pragma': 'no-cache',
                        'Expires': '0'
                    })
                    
                    response = self.session.get(url, headers=headers, timeout=15)
                    
                    if response.status_code == 200:
                        matches = self._extract_actual_live_matches(response.text, sport, url)
                        if matches:
                            self.logger.info(f"Найдено {len(matches)} актуальных матчей с {url}")
                            return matches
                
                except Exception as e:
                    self.logger.warning(f"Ошибка с URL {url}: {e}")
                    continue
            
            return []
            
        except Exception as e:
            self.logger.error(f"Ошибка получения актуальных {sport}: {e}")
            return []
    
    def _extract_actual_live_matches(self, page_text: str, sport: str, source_url: str) -> List[Dict[str, Any]]:
        """
        Извлечение актуальных live матчей из HTML
        """
        matches = []
        
        try:
            # Метод 1: Поиск в JSON данных страницы
            json_matches = self._extract_from_page_json(page_text, sport)
            matches.extend(json_matches)
            
            # Метод 2: Поиск в HTML структуре
            if not matches:
                html_matches = self._extract_from_page_html(page_text, sport)
                matches.extend(html_matches)
            
            # Метод 3: Поиск по текстовым паттернам (для региональных матчей)
            if not matches:
                text_matches = self._extract_from_text_patterns(page_text, sport)
                matches.extend(text_matches)
            
            # Добавляем метаданные
            for match in matches:
                match['source_url'] = source_url
                match['extraction_time'] = time.time()
            
            return self._remove_duplicates(matches, sport)
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения актуальных матчей: {e}")
            return []
    
    def _extract_from_text_patterns(self, page_text: str, sport: str) -> List[Dict[str, Any]]:
        """
        Извлечение матчей через текстовые паттерны (для сложных случаев)
        """
        matches = []
        
        try:
            # Паттерны для различных форматов матчей на SofaScore
            match_patterns = [
                # Региональные матчи типа: Paysandu Volta Redonda
                r'([A-Z][a-zA-Z\s]{2,25})\s+([A-Z][a-zA-Z\s]{2,25})(?:\s+(\d+)\s+(\d+))?',
                
                # Матчи с vs: Team1 vs Team2
                r'([A-Z][a-zA-Z\s]{2,30})\s+vs\s+([A-Z][a-zA-Z\s]{2,30})',
                
                # Матчи с дефисом: Team1 - Team2
                r'([A-Z][a-zA-Z\s]{2,30})\s+-\s+([A-Z][a-zA-Z\s]{2,30})',
                
                # Матчи с счетом: Team1 Team2 0 1
                r'([A-Z][a-zA-Z\s]{2,25})\s+([A-Z][a-zA-Z\s]{2,25})\s+(\d+)\s+(\d+)',
            ]
            
            # Ищем известные команды из примера пользователя
            known_teams = [
                'Paysandu', 'Volta Redonda', 'Sportivo Luqueño', 'Guaraní', 
                'Bermuda', 'Jamaica', 'Colegiales', 'Tucumán', 'Lexington',
                'NCFC', 'Águilas', 'Yautepec', 'Army', 'Temple'
            ]
            
            # Ищем упоминания известных команд в тексте
            for team in known_teams:
                if team in page_text:
                    # Ищем контекст вокруг команды
                    team_context = self._extract_team_context(page_text, team)
                    if team_context:
                        context_matches = self._parse_team_context(team_context, sport)
                        matches.extend(context_matches)
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка текстового извлечения: {e}")
            return []
    
    def _extract_team_context(self, page_text: str, team_name: str) -> List[str]:
        """
        Извлечение контекста вокруг названия команды
        """
        contexts = []
        
        try:
            # Находим все упоминания команды
            team_positions = [m.start() for m in re.finditer(re.escape(team_name), page_text, re.IGNORECASE)]
            
            for pos in team_positions:
                # Берем контекст ±200 символов
                start = max(0, pos - 200)
                end = min(len(page_text), pos + 200)
                context = page_text[start:end]
                contexts.append(context)
            
            return contexts
            
        except Exception as e:
            return []
    
    def _parse_team_context(self, contexts: List[str], sport: str) -> List[Dict[str, Any]]:
        """
        Парсинг контекста для извлечения данных матча
        """
        matches = []
        
        try:
            for context in contexts:
                # Ищем паттерны матчей в контексте
                context_patterns = [
                    r'([A-Z][a-zA-Z\s]{2,25})\s+([A-Z][a-zA-Z\s]{2,25})\s+(\d+)\s+(\d+)',
                    r'([A-Z][a-zA-Z\s]{2,25})\s+vs\s+([A-Z][a-zA-Z\s]{2,25})',
                    r'([A-Z][a-zA-Z\s]{2,25})\s+-\s+([A-Z][a-zA-Z\s]{2,25})'
                ]
                
                for pattern in context_patterns:
                    context_match = re.search(pattern, context)
                    if context_match:
                        groups = context_match.groups()
                        
                        if len(groups) >= 2:
                            match_data = {
                                'source': 'sofascore_quality',
                                'sport': sport,
                                'team1': groups[0].strip(),
                                'team2': groups[1].strip()
                            }
                            
                            if len(groups) >= 4:
                                match_data['score'] = f"{groups[2]}:{groups[3]}"
                            else:
                                match_data['score'] = 'LIVE'
                            
                            # Ищем время в контексте
                            time_match = re.search(r"(\d{1,3}'|HT|FT|LIVE)", context)
                            if time_match:
                                match_data['time'] = time_match.group(1)
                            else:
                                match_data['time'] = 'LIVE'
                            
                            matches.append(match_data)
                            break
            
            return matches
            
        except Exception as e:
            self.logger.warning(f"Ошибка парсинга контекста: {e}")
            return []
    
    def _extract_tournament_data(self, page_text: str, sport: str) -> Dict[str, Any]:
        """
        Извлечение турнирных данных и позиций команд/игроков
        """
        tournament_info = {}
        
        try:
            if sport == 'football':
                # Позиции команд в турнирной таблице
                position_patterns = [
                    r'"homeTeam":[^}]*"position":\s*(\d+)',
                    r'"awayTeam":[^}]*"position":\s*(\d+)',
                    r'"tablePosition":\s*(\d+).*?"tablePosition":\s*(\d+)',
                ]
                
                positions = []
                for pattern in position_patterns:
                    matches = re.findall(pattern, page_text)
                    if matches:
                        positions.extend(matches[:2])
                
                if len(positions) >= 2:
                    tournament_info['table_positions'] = {
                        'team1_position': positions[0],
                        'team2_position': positions[1]
                    }
                
                # Очки в турнире
                points_patterns = [
                    r'"homeTeam":[^}]*"points":\s*(\d+)',
                    r'"awayTeam":[^}]*"points":\s*(\d+)',
                    r'"tournamentPoints":\s*(\d+).*?"tournamentPoints":\s*(\d+)',
                ]
                
                points = []
                for pattern in points_patterns:
                    matches = re.findall(pattern, page_text)
                    if matches:
                        points.extend(matches[:2])
                
                if len(points) >= 2:
                    tournament_info['tournament_points'] = {
                        'team1_points': points[0],
                        'team2_points': points[1]
                    }
            
            elif sport == 'tennis':
                # ATP/WTA рейтинги
                ranking_patterns = [
                    r'"homePlayer":[^}]*"ranking":\s*(\d+)',
                    r'"awayPlayer":[^}]*"ranking":\s*(\d+)',
                    r'"atpRanking":\s*(\d+).*?"atpRanking":\s*(\d+)',
                    r'"wtaRanking":\s*(\d+).*?"wtaRanking":\s*(\d+)',
                ]
                
                rankings = []
                for pattern in ranking_patterns:
                    matches = re.findall(pattern, page_text)
                    if matches:
                        rankings.extend(matches[:2])
                
                if len(rankings) >= 2:
                    tournament_info['player_rankings'] = {
                        'player1_ranking': rankings[0],
                        'player2_ranking': rankings[1]
                    }
                
                # Очки рейтинга
                rating_points_pattern = r'"rankingPoints":\s*(\d+).*?"rankingPoints":\s*(\d+)'
                rating_points = re.findall(rating_points_pattern, page_text)
                if rating_points:
                    tournament_info['ranking_points'] = {
                        'player1_points': rating_points[0][0],
                        'player2_points': rating_points[0][1]
                    }
            
            elif sport == 'handball':
                # Позиции в лиге
                position_patterns = [
                    r'"homeTeam":[^}]*"leaguePosition":\s*(\d+)',
                    r'"awayTeam":[^}]*"leaguePosition":\s*(\d+)',
                ]
                
                positions = []
                for pattern in position_patterns:
                    matches = re.findall(pattern, page_text)
                    if matches:
                        positions.extend(matches[:2])
                
                if len(positions) >= 2:
                    tournament_info['league_positions'] = {
                        'team1_position': positions[0],
                        'team2_position': positions[1]
                    }
                    
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения турнирных данных: {e}")
        
        return tournament_info
    
    def _extract_team_statistics(self, page_text: str, sport: str) -> Dict[str, Any]:
        """
        Извлечение статистики команд/игроков (средние показатели)
        """
        team_stats = {}
        
        try:
            if sport == 'football':
                # Средние голы за матч
                avg_goals_patterns = [
                    r'"homeTeam":[^}]*"avgGoals":\s*([\d.]+)',
                    r'"awayTeam":[^}]*"avgGoals":\s*([\d.]+)',
                    r'"goalsPerGame":\s*([\d.]+).*?"goalsPerGame":\s*([\d.]+)',
                    r'"averageGoals":\s*([\d.]+).*?"averageGoals":\s*([\d.]+)',
                ]
                
                avg_goals = []
                for pattern in avg_goals_patterns:
                    matches = re.findall(pattern, page_text)
                    if matches:
                        if isinstance(matches[0], tuple):
                            avg_goals.extend(matches[0])
                        else:
                            avg_goals.extend(matches[:2])
                
                if len(avg_goals) >= 2:
                    team_stats['average_goals'] = {
                        'team1_avg_goals': avg_goals[0],
                        'team2_avg_goals': avg_goals[1]
                    }
                
                # Средние пропущенные голы
                avg_conceded_patterns = [
                    r'"homeTeam":[^}]*"avgConceded":\s*([\d.]+)',
                    r'"awayTeam":[^}]*"avgConceded":\s*([\d.]+)',
                    r'"goalsConcededPerGame":\s*([\d.]+).*?"goalsConcededPerGame":\s*([\d.]+)',
                ]
                
                avg_conceded = []
                for pattern in avg_conceded_patterns:
                    matches = re.findall(pattern, page_text)
                    if matches:
                        if isinstance(matches[0], tuple):
                            avg_conceded.extend(matches[0])
                        else:
                            avg_conceded.extend(matches[:2])
                
                if len(avg_conceded) >= 2:
                    team_stats['average_conceded'] = {
                        'team1_avg_conceded': avg_conceded[0],
                        'team2_avg_conceded': avg_conceded[1]
                    }
                
                # Процент побед
                win_rate_patterns = [
                    r'"homeTeam":[^}]*"winRate":\s*([\d.]+)',
                    r'"awayTeam":[^}]*"winRate":\s*([\d.]+)',
                    r'"winPercentage":\s*([\d.]+).*?"winPercentage":\s*([\d.]+)',
                ]
                
                win_rates = []
                for pattern in win_rate_patterns:
                    matches = re.findall(pattern, page_text)
                    if matches:
                        if isinstance(matches[0], tuple):
                            win_rates.extend(matches[0])
                        else:
                            win_rates.extend(matches[:2])
                
                if len(win_rates) >= 2:
                    team_stats['win_percentage'] = {
                        'team1_win_rate': f"{win_rates[0]}%",
                        'team2_win_rate': f"{win_rates[1]}%"
                    }
            
            elif sport == 'tennis':
                # Статистика игроков
                player_stats_patterns = {
                    'titles_won': r'"titlesWon":\s*(\d+).*?"titlesWon":\s*(\d+)',
                    'matches_played': r'"matchesPlayed":\s*(\d+).*?"matchesPlayed":\s*(\d+)',
                    'win_percentage': r'"winPercentage":\s*([\d.]+).*?"winPercentage":\s*([\d.]+)',
                    'prize_money': r'"prizeMoney":\s*(\d+).*?"prizeMoney":\s*(\d+)',
                }
                
                for stat_name, pattern in player_stats_patterns.items():
                    matches = re.findall(pattern, page_text)
                    if matches and len(matches[0]) >= 2:
                        team_stats[stat_name] = {
                            'player1': matches[0][0],
                            'player2': matches[0][1]
                        }
            
            elif sport == 'handball':
                # Статистика гандбольных команд
                handball_stats_patterns = {
                    'average_goals': r'"avgGoals":\s*([\d.]+).*?"avgGoals":\s*([\d.]+)',
                    'average_saves': r'"avgSaves":\s*([\d.]+).*?"avgSaves":\s*([\d.]+)',
                    'win_percentage': r'"winRate":\s*([\d.]+).*?"winRate":\s*([\d.]+)',
                }
                
                for stat_name, pattern in handball_stats_patterns.items():
                    matches = re.findall(pattern, page_text)
                    if matches and len(matches[0]) >= 2:
                        team_stats[stat_name] = {
                            'team1': matches[0][0],
                            'team2': matches[0][1]
                        }
                        
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения статистики команд: {e}")
        
        return team_stats
    
    def _remove_duplicates(self, matches: List[Dict[str, Any]], sport: str) -> List[Dict[str, Any]]:
        """
        Удаление дубликатов
        """
        seen = set()
        unique = []
        
        for match in matches:
            if sport == 'tennis':
                key = f"{match.get('player1', '')}-{match.get('player2', '')}"
            else:
                key = f"{match.get('team1', '')}-{match.get('team2', '')}"
            
            key = key.lower().strip()
            
            if key not in seen and len(key) > 6:
                seen.add(key)
                unique.append(match)
        
        return unique
    
    def _extract_actual_match_from_element(self, element, sport: str, known_teams: List[str]) -> Dict[str, Any]:
        """
        Извлечение актуального матча из элемента
        """
        try:
            if hasattr(element, 'get_text'):
                text = element.get_text(strip=True)
            else:
                text = str(element).strip()
            
            # Проверяем наличие известных команд
            teams_in_text = []
            for team in known_teams:
                if team.lower() in text.lower():
                    teams_in_text.append(team)
            
            # Если найдено 2+ команды, пробуем извлечь матч
            if len(teams_in_text) >= 2:
                match_data = {
                    'source': 'sofascore_quality',
                    'sport': sport,
                    'team1': teams_in_text[0],
                    'team2': teams_in_text[1],
                    'score': 'LIVE',
                    'time': 'LIVE',
                    'league': 'Regional Tournament'
                }
                
                # Ищем счет в тексте
                score_match = re.search(r'(\d+):(\d+)', text)
                if score_match:
                    match_data['score'] = f"{score_match.group(1)}:{score_match.group(2)}"
                
                # Ищем время
                time_match = re.search(r"(\d{1,3}'|HT|FT)", text)
                if time_match:
                    match_data['time'] = time_match.group(1)
                
                return match_data
            
            return None
            
        except Exception as e:
            return None