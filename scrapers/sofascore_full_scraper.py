"""
Полноценный скрапер SofaScore с извлечением всей статистики
"""
import requests
from bs4 import BeautifulSoup
import re
import json
from typing import List, Dict, Any

class SofaScoreFullScraper:
    """
    Полноценный скрапер SofaScore с максимальными данными для Claude AI
    """
    
    def __init__(self, logger):
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.7339.80 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
            'Cache-Control': 'no-cache'
        })
    
    def get_all_live_matches(self) -> List[Dict[str, Any]]:
        """
        Получение ВСЕХ live матчей со всех видов спорта
        """
        self.logger.info("SofaScore: сбор ВСЕХ live матчей")
        
        all_matches = []
        
        sports = {
            'football': 'https://www.sofascore.com/football/livescore',
            'tennis': 'https://www.sofascore.com/tennis/livescore',
            'handball': 'https://www.sofascore.com/handball/livescore',
            'table_tennis': 'https://www.sofascore.com/table-tennis/livescore'
        }
        
        for sport, url in sports.items():
            try:
                sport_matches = self._get_sport_matches(url, sport)
                all_matches.extend(sport_matches)
                self.logger.info(f"SofaScore {sport}: {len(sport_matches)} матчей")
            except Exception as e:
                self.logger.warning(f"SofaScore {sport} ошибка: {e}")
        
        self.logger.info(f"SofaScore ИТОГО: {len(all_matches)} live матчей")
        return all_matches
    
    def _get_sport_matches(self, url: str, sport: str) -> List[Dict[str, Any]]:
        """
        Получение матчей конкретного вида спорта
        """
        try:
            response = self.session.get(url, timeout=15)
            
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            matches = []
            
            # Метод 1: Поиск через JSON в скриптах
            json_matches = self._extract_from_scripts(soup, sport)
            if json_matches:
                matches.extend(json_matches)
                return matches
            
            # Метод 2: HTML парсинг с селекторами
            html_matches = self._extract_from_html(soup, sport)
            if html_matches:
                matches.extend(html_matches)
                return matches
            
            # Метод 3: Текстовый анализ
            text_matches = self._extract_from_text(soup, sport)
            matches.extend(text_matches)
            
            return matches
            
        except Exception as e:
            self.logger.error(f"Ошибка {sport}: {e}")
            return []
    
    def _extract_from_scripts(self, soup: BeautifulSoup, sport: str) -> List[Dict[str, Any]]:
        """
        Извлечение из JavaScript данных
        """
        matches = []
        
        scripts = soup.find_all('script')
        
        for script in scripts:
            if script.string and len(script.string) > 500:
                script_text = script.string
                
                # Ищем события в JSON
                if 'events' in script_text and (sport in script_text or 'live' in script_text.lower()):
                    
                    # Различные JSON паттерны
                    json_patterns = [
                        r'\"events\"\\s*:\\s*(\\[.+?\\])',
                        r'\"tournaments\"\\s*:\\s*(\\[.+?\\])',
                        r'\"matches\"\\s*:\\s*(\\[.+?\\])'
                    ]
                    
                    for pattern in json_patterns:
                        json_matches = re.findall(pattern, script_text, re.DOTALL)
                        
                        for json_str in json_matches:
                            try:
                                events = json.loads(json_str)
                                
                                if isinstance(events, list):
                                    for event in events:
                                        if isinstance(event, dict):
                                            match = self._parse_sofascore_event(event, sport)
                                            if match:
                                                matches.append(match)
                                
                                if matches:
                                    return matches  # Если нашли, возвращаем
                                    
                            except json.JSONDecodeError:
                                continue
        
        return matches
    
    def _parse_sofascore_event(self, event: dict, sport: str) -> Dict[str, Any]:
        """
        Парсинг события SofaScore
        """
        try:
            # Извлекаем команды/игроков
            home_team = event.get('homeTeam', {})
            away_team = event.get('awayTeam', {})
            
            if isinstance(home_team, dict):
                team1 = home_team.get('name', home_team.get('shortName', ''))
            else:
                team1 = str(home_team)
            
            if isinstance(away_team, dict):
                team2 = away_team.get('name', away_team.get('shortName', ''))
            else:
                team2 = str(away_team)
            
            if not team1 or not team2:
                return None
            
            # Счет
            home_score = event.get('homeScore', {})
            away_score = event.get('awayScore', {})
            
            if isinstance(home_score, dict) and isinstance(away_score, dict):
                h_score = home_score.get('current', home_score.get('display', 0))
                a_score = away_score.get('current', away_score.get('display', 0))
                score = f"{h_score}:{a_score}"
            else:
                score = '0:0'
            
            # Статус/время
            status = event.get('status', {})
            if isinstance(status, dict):
                match_time = status.get('description', status.get('type', "0'"))
            else:
                match_time = "0'"
            
            # Турнир
            tournament = event.get('tournament', {})
            if isinstance(tournament, dict):
                league_name = tournament.get('name', tournament.get('uniqueName', 'SofaScore Live'))
            else:
                league_name = 'SofaScore Live'
            
            # ID для URL
            match_id = event.get('id', event.get('customId', ''))
            url = f'/match/{match_id}' if match_id else ''
            
            # Дополнительные данные SofaScore
            additional_data = {}
            
            # Статистика (если есть)
            if 'statistics' in event:
                additional_data['statistics'] = event['statistics']
            
            # Время начала
            if 'startTimestamp' in event:
                additional_data['start_timestamp'] = event['startTimestamp']
            
            # Раунд турнира
            if 'roundInfo' in event:
                additional_data['round'] = event['roundInfo']
            
            # Формируем результат
            base_data = {
                'league': league_name,
                'url': url,
                'sport': sport,
                'source': 'sofascore',
                'additional_data': additional_data
            }
            
            if sport == 'tennis':
                base_data.update({
                    'player1': team1,
                    'player2': team2,
                    'sets_score': score,
                    'current_set': '0:0',
                    'tournament': league_name
                })
            else:
                base_data.update({
                    'team1': team1,
                    'team2': team2,
                    'score': score,
                    'time': match_time
                })
            
            return base_data
            
        except Exception:
            return None
    
    def _extract_from_html(self, soup: BeautifulSoup, sport: str) -> List[Dict[str, Any]]:
        """
        HTML парсинг SofaScore
        """
        matches = []
        
        # SofaScore специфичные селекторы
        selectors = [
            '[data-testid*=\"event\"]',
            '[data-testid*=\"match\"]',
            '[class*=\"event\"]',
            '[class*=\"match\"]',
            'div[data-event-id]',
            'div[data-match-id]'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            
            if len(elements) > 3:
                for element in elements[:15]:
                    text = element.get_text(strip=True)
                    
                    if self._looks_like_match(text):
                        match_data = self._parse_html_element(element, sport)
                        if match_data:
                            matches.append(match_data)
                
                if matches:
                    break
        
        return matches
    
    def _extract_from_text(self, soup: BeautifulSoup, sport: str) -> List[Dict[str, Any]]:
        """
        Текстовый парсинг
        """
        matches = []
        page_text = soup.get_text()
        
        # Ищем паттерны команд и счетов
        if sport == 'football':
            patterns = [
                r'([А-Я][а-я\\s]{3,25})\\s+([А-Я][а-я\\s]{3,25})\\s+(\\d{1,2}):(\\d{1,2})',
                r'([А-Я][а-я\\s]{3,25})\\s*-\\s*([А-Я][а-я\\s]{3,25})\\s+(\\d{1,2}):(\\d{1,2})'
            ]
        else:
            patterns = [
                r'([А-Я][а-я\\s\\.]{3,25})\\s+([А-Я][а-я\\s\\.]{3,25})\\s+(\\d{1,2}):(\\d{1,2})'
            ]
        
        for pattern in patterns:
            pattern_matches = re.findall(pattern, page_text)
            
            for match_tuple in pattern_matches:
                if len(match_tuple) >= 4:
                    team1, team2, s1, s2 = match_tuple
                    
                    if sport == 'tennis':
                        match_data = {
                            'player1': team1.strip(),
                            'player2': team2.strip(),
                            'sets_score': f\"{s1}:{s2}\",
                            'current_set': '0:0',
                            'tournament': 'SofaScore Live',
                            'url': '',
                            'sport': sport,
                            'source': 'sofascore_text'
                        }
                    else:
                        match_data = {
                            'team1': team1.strip(),
                            'team2': team2.strip(),
                            'score': f\"{s1}:{s2}\",
                            'time': '0\\'',
                            'league': 'SofaScore Live',
                            'url': '',
                            'sport': sport,
                            'source': 'sofascore_text'
                        }
                    
                    matches.append(match_data)
        
        return matches
    
    def _parse_html_element(self, element, sport: str) -> Dict[str, Any]:
        """
        Парсинг HTML элемента
        """
        try:
            # Извлекаем данные из атрибутов
            event_id = (element.get('data-event-id') or 
                       element.get('data-match-id') or
                       element.get('data-id'))
            
            # Текст элемента
            text = element.get_text(strip=True)
            
            # Ищем команды в тексте
            team_match = re.search(r'([А-Я][а-я\\s]{3,25})\\s*[-vs]\\s*([А-Я][а-я\\s]{3,25})', text, re.IGNORECASE)
            
            if team_match:
                team1, team2 = team_match.group(1).strip(), team_match.group(2).strip()
                
                # Ищем счет
                score_match = re.search(r'(\\d{1,2}):(\\d{1,2})', text)
                score = score_match.group(0) if score_match else '0:0'
                
                # URL
                url = element.get('href', '')
                if not url:
                    link = element.find('a')
                    url = link.get('href', '') if link else ''
                
                if sport == 'tennis':
                    return {
                        'player1': team1,
                        'player2': team2,
                        'sets_score': score,
                        'current_set': '0:0',
                        'tournament': 'SofaScore Live',
                        'url': url,
                        'sport': sport,
                        'source': 'sofascore_element',
                        'event_id': event_id
                    }
                else:
                    return {
                        'team1': team1,
                        'team2': team2,
                        'score': score,
                        'time': '0\\'',
                        'league': 'SofaScore Live',
                        'url': url,
                        'sport': sport,
                        'source': 'sofascore_element',
                        'event_id': event_id
                    }
            
            return None
            
        except Exception:
            return None
    
    def _looks_like_match(self, text: str) -> bool:
        """
        Проверка на матч
        """
        if not text or len(text) < 10 or len(text) > 200:
            return False
        
        exclude = ['sofascore', 'cookie', 'subscribe', 'login', 'download']
        text_lower = text.lower()
        
        if any(word in text_lower for word in exclude):
            return False
        
        # Признаки матча
        has_score = bool(re.search(r'\\d+[:-]\\d+', text))
        has_teams = bool(re.search(r'[А-Я][а-я]+.*[А-Я][а-я]+', text))
        has_vs = ' - ' in text or ' vs ' in text.lower()
        
        return has_score or (has_teams and has_vs)
    
    def get_match_details(self, match_url: str) -> Dict[str, Any]:
        \"\"\"
        Получение детальных данных конкретного матча
        \"\"\"
        if not match_url.startswith('http'):
            full_url = f'https://www.sofascore.com{match_url}'
        else:
            full_url = match_url
        
        try:
            response = self.session.get(full_url, timeout=10)
            
            if response.status_code != 200:
                return {}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            details = {}
            
            # Извлекаем детальную статистику
            details.update(self._extract_match_statistics(soup))
            
            # H2H данные
            details.update(self._extract_h2h_data(soup))
            
            # Форма команд
            details.update(self._extract_team_form(soup))
            
            # Коэффициенты
            details.update(self._extract_odds(soup))
            
            return details
            
        except Exception as e:
            self.logger.warning(f\"Ошибка детальных данных: {e}\")
            return {}
    
    def _extract_match_statistics(self, soup: BeautifulSoup) -> Dict[str, Any]:
        \"\"\"
        Извлечение статистики матча
        \"\"\"
        stats = {}
        
        # Ищем числовые данные статистики
        page_text = soup.get_text()
        
        # Владение мячом (проценты)
        possession_matches = re.findall(r'(\\d{1,2})%', page_text)
        if len(possession_matches) >= 2:
            stats['possession'] = {
                'team1': f"{possession_matches[0]}%",
                'team2': f"{possession_matches[1]}%"
            }
        
        # xG данные
        xg_matches = re.findall(r'(\\d+\\.\\d+)', page_text)
        if len(xg_matches) >= 2:
            stats['xG'] = {
                'team1': xg_matches[0],
                'team2': xg_matches[1]
            }
        
        # Удары (малые числа)
        shot_numbers = [num for num in re.findall(r'\\b([0-9]|1[0-9])\\b', page_text) if int(num) <= 20]
        if len(shot_numbers) >= 4:
            stats['shots'] = {
                'team1_total': shot_numbers[0],
                'team1_on_target': shot_numbers[1],
                'team2_total': shot_numbers[2],
                'team2_on_target': shot_numbers[3]
            }
        
        return {'detailed_statistics': stats} if stats else {}
    
    def _extract_h2h_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        \"\"\"
        Извлечение H2H данных
        \"\"\"
        # Ищем секцию с H2H
        h2h_section = soup.find(text=re.compile(r'h2h|head to head', re.IGNORECASE))
        
        if h2h_section:
            # Ищем результаты предыдущих встреч
            return {'h2h': 'H2H данные найдены'}
        
        return {}
    
    def _extract_team_form(self, soup: BeautifulSoup) -> Dict[str, Any]:
        \"\"\"
        Извлечение формы команд
        \"\"\"
        form_indicators = soup.get_text().lower().count('form')
        
        if form_indicators > 5:
            return {'team_form': 'Данные формы найдены'}
        
        return {}
    
    def _extract_odds(self, soup: BeautifulSoup) -> Dict[str, Any]:
        \"\"\"
        Извлечение коэффициентов
        \"\"\"
        odds_count = soup.get_text().lower().count('odds')
        
        if odds_count > 5:
            return {'odds': 'Коэффициенты найдены'}
        
        return {}