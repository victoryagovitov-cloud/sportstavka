"""
Специализированный сборщик статистики по командам и игрокам
Объединяет данные из множественных источников для полной картины
"""
import requests
import time
import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from datetime import datetime
import json

class TeamStatsCollector:
    """
    Сборщик статистики команд и игроков из множественных источников
    """
    
    def __init__(self, logger):
        self.logger = logger
        
        # HTTP сессия
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Connection': 'keep-alive'
        })
    
    def get_team_statistics(self, team1: str, team2: str, sport: str = 'football') -> Dict[str, Any]:
        """
        Получение полной статистики по командам
        """
        try:
            self.logger.info(f"Сбор статистики для {team1} vs {team2} ({sport})")
            
            stats = {
                'match_info': {
                    'team1': team1,
                    'team2': team2,
                    'sport': sport,
                    'timestamp': datetime.now().isoformat()
                },
                'team1_stats': {},
                'team2_stats': {},
                'h2h_stats': {},
                'match_stats': {},
                'player_stats': {}
            }
            
            # 1. SofaScore статистика
            sofascore_stats = self._get_sofascore_team_stats(team1, team2, sport)
            if sofascore_stats:
                stats.update(sofascore_stats)
            
            # 2. Статистика из MarathonBet (форма, коэффициенты)
            marathonbet_stats = self._get_marathonbet_team_stats(team1, team2, sport)
            if marathonbet_stats:
                stats['betting_stats'] = marathonbet_stats
            
            # 3. Дополнительная статистика из внешних источников
            external_stats = self._get_external_team_stats(team1, team2, sport)
            if external_stats:
                stats['external_stats'] = external_stats
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Ошибка сбора статистики команд: {e}")
            return {}
    
    def _get_sofascore_team_stats(self, team1: str, team2: str, sport: str) -> Dict[str, Any]:
        """
        Статистика команд с SofaScore
        """
        try:
            # Поиск команд на SofaScore
            search_url = f"https://www.sofascore.com/search?q={team1.replace(' ', '%20')}"
            response = self.session.get(search_url, timeout=10)
            
            if response.status_code == 200:
                # Ищем ссылку на команду
                team_link = self._extract_team_link(response.text, team1)
                
                if team_link:
                    # Получаем статистику команды
                    team_stats = self._get_team_page_stats(team_link, team1)
                    return team_stats
            
            return {}
            
        except Exception as e:
            self.logger.warning(f"SofaScore статистика ошибка: {e}")
            return {}
    
    def _get_marathonbet_team_stats(self, team1: str, team2: str, sport: str) -> Dict[str, Any]:
        """
        Букмекерская статистика с MarathonBet
        """
        try:
            # Ищем матч на MarathonBet для получения коэффициентов и трендов
            search_patterns = [
                f"{team1}.*{team2}",
                f"{team2}.*{team1}"
            ]
            
            marathonbet_data = {}
            
            # Получаем страницу с матчем
            response = self.session.get('https://www.marathonbet.ru/su/live/popular?', timeout=10)
            
            if response.status_code == 200:
                for pattern in search_patterns:
                    if re.search(pattern, response.text, re.IGNORECASE):
                        # Извлекаем контекст матча
                        match_context = self._extract_match_context(response.text, team1, team2)
                        
                        if match_context:
                            marathonbet_data = {
                                'odds': self._extract_detailed_odds(match_context),
                                'betting_trends': self._extract_betting_trends(match_context),
                                'market_analysis': self._analyze_betting_market(match_context)
                            }
                        break
            
            return marathonbet_data
            
        except Exception as e:
            self.logger.warning(f"MarathonBet статистика ошибка: {e}")
            return {}
    
    def _get_external_team_stats(self, team1: str, team2: str, sport: str) -> Dict[str, Any]:
        """
        Статистика из внешних источников
        """
        try:
            external_stats = {}
            
            # 1. Transfermarkt для стоимости игроков (футбол)
            if sport == 'football':
                transfermarkt_stats = self._get_transfermarkt_stats(team1, team2)
                if transfermarkt_stats:
                    external_stats['transfermarkt'] = transfermarkt_stats
            
            # 2. ESPN для общей статистики
            espn_stats = self._get_espn_stats(team1, team2, sport)
            if espn_stats:
                external_stats['espn'] = espn_stats
            
            # 3. FotMob для рейтингов
            fotmob_stats = self._get_fotmob_stats(team1, team2, sport)
            if fotmob_stats:
                external_stats['fotmob'] = fotmob_stats
            
            return external_stats
            
        except Exception as e:
            self.logger.warning(f"Внешние источники статистики ошибка: {e}")
            return {}
    
    def _extract_team_link(self, html_content: str, team_name: str) -> Optional[str]:
        """
        Извлечение ссылки на страницу команды
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Ищем ссылки на команды
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                if team_name.lower() in text.lower() and '/team/' in href:
                    return f"https://www.sofascore.com{href}"
            
            return None
            
        except Exception as e:
            return None
    
    def _get_team_page_stats(self, team_url: str, team_name: str) -> Dict[str, Any]:
        """
        Получение статистики со страницы команды
        """
        try:
            response = self.session.get(team_url, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                stats = {
                    'team_info': self._extract_team_info(soup, team_name),
                    'season_stats': self._extract_season_stats(soup),
                    'recent_form': self._extract_recent_form(soup),
                    'league_position': self._extract_league_position(soup),
                    'top_players': self._extract_top_players(soup)
                }
                
                return stats
            
            return {}
            
        except Exception as e:
            self.logger.warning(f"Статистика команды {team_name} ошибка: {e}")
            return {}
    
    def _extract_team_info(self, soup: BeautifulSoup, team_name: str) -> Dict[str, Any]:
        """
        Основная информация о команде
        """
        try:
            team_info = {
                'name': team_name,
                'full_name': '',
                'country': '',
                'founded': '',
                'stadium': '',
                'coach': ''
            }
            
            # Ищем основную информацию в различных селекторах
            info_selectors = [
                '.team-header h1',
                '.team-info .name',
                '.team-details .info'
            ]
            
            for selector in info_selectors:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text(strip=True)
                    if text and len(text) > 2:
                        if not team_info['full_name']:
                            team_info['full_name'] = text
                        break
            
            return team_info
            
        except Exception as e:
            return {'name': team_name}
    
    def _extract_season_stats(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Статистика сезона команды
        """
        try:
            season_stats = {
                'matches_played': 0,
                'wins': 0,
                'draws': 0,
                'losses': 0,
                'goals_for': 0,
                'goals_against': 0,
                'points': 0
            }
            
            # Ищем статистику в таблицах
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 3:
                        # Пытаемся извлечь числовые данные
                        for i, cell in enumerate(cells):
                            text = cell.get_text(strip=True)
                            if text.isdigit():
                                value = int(text)
                                if i == 1 and value < 100:  # Вероятно матчи
                                    season_stats['matches_played'] = value
                                elif i == 2 and value < 50:  # Вероятно победы
                                    season_stats['wins'] = value
            
            return season_stats
            
        except Exception as e:
            return {}
    
    def _extract_recent_form(self, soup: BeautifulSoup) -> List[str]:
        """
        Последние результаты команды
        """
        try:
            form = []
            
            # Ищем индикаторы формы (W, D, L)
            form_patterns = [
                r'([WDL])',  # W-win, D-draw, L-loss
                r'([ПНВ])',  # П-поражение, Н-ничья, В-победа
            ]
            
            page_text = soup.get_text()
            
            for pattern in form_patterns:
                matches = re.findall(pattern, page_text)
                if matches and len(matches) <= 10:  # Разумное количество
                    form.extend(matches[:5])  # Последние 5 матчей
                    break
            
            return form
            
        except Exception as e:
            return []
    
    def _extract_league_position(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Позиция в турнирной таблице
        """
        try:
            position_info = {
                'position': None,
                'points': None,
                'league': None
            }
            
            # Ищем позицию в таблице
            position_patterns = [
                r'(\d+)\s*место',
                r'Position:\s*(\d+)',
                r'#(\d+)'
            ]
            
            page_text = soup.get_text()
            
            for pattern in position_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    position_info['position'] = int(match.group(1))
                    break
            
            return position_info
            
        except Exception as e:
            return {}
    
    def _extract_top_players(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Топ игроки команды
        """
        try:
            players = []
            
            # Ищем списки игроков
            player_selectors = [
                '.player-list .player',
                '.squad .player',
                '.lineup .player'
            ]
            
            for selector in player_selectors:
                elements = soup.select(selector)
                
                for element in elements[:10]:  # Топ 10 игроков
                    player_info = {
                        'name': '',
                        'position': '',
                        'rating': None,
                        'goals': None
                    }
                    
                    text = element.get_text(strip=True)
                    
                    # Извлекаем имя игрока
                    name_pattern = r'([А-ЯA-Z][а-яa-z\s]{2,30})'
                    name_match = re.search(name_pattern, text)
                    if name_match:
                        player_info['name'] = name_match.group(1).strip()
                    
                    # Извлекаем рейтинг
                    rating_pattern = r'(\d+\.\d+)'
                    rating_match = re.search(rating_pattern, text)
                    if rating_match:
                        player_info['rating'] = float(rating_match.group(1))
                    
                    if player_info['name']:
                        players.append(player_info)
            
            return players
            
        except Exception as e:
            return []
    
    def _extract_match_context(self, html_content: str, team1: str, team2: str) -> str:
        """
        Извлечение контекста матча для анализа
        """
        try:
            team1_pos = html_content.lower().find(team1.lower())
            team2_pos = html_content.lower().find(team2.lower())
            
            if team1_pos != -1 and team2_pos != -1:
                start_pos = min(team1_pos, team2_pos) - 1000
                end_pos = max(team1_pos, team2_pos) + 1000
                
                return html_content[max(0, start_pos):min(len(html_content), end_pos)]
            
            return ""
            
        except Exception as e:
            return ""
    
    def _extract_detailed_odds(self, context: str) -> Dict[str, Any]:
        """
        Детальные коэффициенты и рынки
        """
        try:
            odds_data = {
                'main_odds': {},
                'totals': {},
                'handicaps': {},
                'additional_markets': []
            }
            
            # Основные коэффициенты
            main_odds = re.findall(r'(\d+\.\d{1,2})', context)
            valid_main = [odd for odd in main_odds if 1.01 <= float(odd) <= 50.0]
            
            if len(valid_main) >= 3:
                odds_data['main_odds'] = {
                    'П1': valid_main[0],
                    'X': valid_main[1],
                    'П2': valid_main[2]
                }
            
            # Тоталы
            total_patterns = [
                r'Тотал\s+больше\s+(\d+\.?\d*)\s+(\d+\.\d{1,2})',
                r'Тотал\s+меньше\s+(\d+\.?\d*)\s+(\d+\.\d{1,2})',
                r'Over\s+(\d+\.?\d*)\s+(\d+\.\d{1,2})',
                r'Under\s+(\d+\.?\d*)\s+(\d+\.\d{1,2})'
            ]
            
            for pattern in total_patterns:
                totals = re.findall(pattern, context, re.IGNORECASE)
                for total_value, odd in totals:
                    odds_data['totals'][f'Тотал {total_value}'] = odd
            
            return odds_data
            
        except Exception as e:
            return {}
    
    def _extract_betting_trends(self, context: str) -> Dict[str, Any]:
        """
        Тренды ставок
        """
        try:
            trends = {
                'favorite': None,
                'odds_movement': [],
                'betting_volume': None
            }
            
            # Определяем фаворита по коэффициентам
            odds = re.findall(r'(\d+\.\d{1,2})', context)
            valid_odds = [float(odd) for odd in odds if 1.01 <= float(odd) <= 50.0]
            
            if len(valid_odds) >= 3:
                min_odd = min(valid_odds[:3])
                if valid_odds[0] == min_odd:
                    trends['favorite'] = 'team1'
                elif valid_odds[2] == min_odd:
                    trends['favorite'] = 'team2'
                else:
                    trends['favorite'] = 'draw'
            
            return trends
            
        except Exception as e:
            return {}
    
    def _analyze_betting_market(self, context: str) -> Dict[str, Any]:
        """
        Анализ букмекерского рынка
        """
        try:
            market_analysis = {
                'total_markets': 0,
                'odds_range': {},
                'market_types': []
            }
            
            # Подсчитываем количество рынков
            market_keywords = ['тотал', 'фора', 'исход', 'total', 'handicap', 'outcome']
            
            for keyword in market_keywords:
                count = context.lower().count(keyword)
                if count > 0:
                    market_analysis['total_markets'] += count
                    market_analysis['market_types'].append(keyword)
            
            # Анализируем диапазон коэффициентов
            all_odds = re.findall(r'(\d+\.\d{1,2})', context)
            valid_odds = [float(odd) for odd in all_odds if 1.01 <= float(odd) <= 50.0]
            
            if valid_odds:
                market_analysis['odds_range'] = {
                    'min': min(valid_odds),
                    'max': max(valid_odds),
                    'avg': sum(valid_odds) / len(valid_odds)
                }
            
            return market_analysis
            
        except Exception as e:
            return {}
    
    def _get_transfermarkt_stats(self, team1: str, team2: str) -> Dict[str, Any]:
        """
        Статистика стоимости игроков с Transfermarkt
        """
        try:
            # Базовый запрос к Transfermarkt (осторожно с rate limiting)
            transfermarkt_data = {
                'team1_value': None,
                'team2_value': None,
                'top_players': []
            }
            
            # Пока возвращаем заглушку, так как Transfermarkt требует специальной обработки
            return transfermarkt_data
            
        except Exception as e:
            return {}
    
    def _get_espn_stats(self, team1: str, team2: str, sport: str) -> Dict[str, Any]:
        """
        Статистика с ESPN
        """
        try:
            espn_data = {
                'team1_ranking': None,
                'team2_ranking': None,
                'recent_performance': {}
            }
            
            # ESPN требует специальной обработки и может быть заблокирован
            return espn_data
            
        except Exception as e:
            return {}
    
    def _get_fotmob_stats(self, team1: str, team2: str, sport: str) -> Dict[str, Any]:
        """
        Рейтинги с FotMob
        """
        try:
            fotmob_data = {
                'team1_rating': None,
                'team2_rating': None,
                'form_guide': []
            }
            
            # FotMob API требует ключей или специальной обработки
            return fotmob_data
            
        except Exception as e:
            return {}
    
    def get_player_statistics(self, player_name: str, team: str, sport: str = 'football') -> Dict[str, Any]:
        """
        Получение статистики конкретного игрока
        """
        try:
            self.logger.info(f"Сбор статистики игрока {player_name} ({team})")
            
            player_stats = {
                'player_info': {
                    'name': player_name,
                    'team': team,
                    'sport': sport,
                    'timestamp': datetime.now().isoformat()
                },
                'season_stats': {},
                'match_stats': {},
                'ratings': {},
                'market_value': None
            }
            
            # Сбор статистики игрока из доступных источников
            # Пока базовая реализация
            
            return player_stats
            
        except Exception as e:
            self.logger.error(f"Ошибка сбора статистики игрока {player_name}: {e}")
            return {}
    
    def get_comprehensive_match_analysis(self, team1: str, team2: str, sport: str = 'football') -> Dict[str, Any]:
        """
        Комплексный анализ матча с полной статистикой
        """
        try:
            self.logger.info(f"Комплексный анализ {team1} vs {team2}")
            
            analysis = {
                'match_info': {
                    'team1': team1,
                    'team2': team2,
                    'sport': sport,
                    'analysis_time': datetime.now().isoformat()
                },
                'team_statistics': self.get_team_statistics(team1, team2, sport),
                'betting_analysis': self._get_betting_analysis(team1, team2, sport),
                'historical_data': self._get_historical_data(team1, team2, sport),
                'prediction_factors': self._get_prediction_factors(team1, team2, sport)
            }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Ошибка комплексного анализа: {e}")
            return {}
    
    def _get_betting_analysis(self, team1: str, team2: str, sport: str) -> Dict[str, Any]:
        """
        Анализ букмекерских данных
        """
        try:
            betting_analysis = {
                'odds_analysis': {},
                'value_bets': [],
                'market_sentiment': {},
                'recommendations': []
            }
            
            # Анализ на основе коэффициентов от MarathonBet
            marathonbet_stats = self._get_marathonbet_team_stats(team1, team2, sport)
            
            if marathonbet_stats and 'odds' in marathonbet_stats:
                odds = marathonbet_stats['odds']
                
                # Анализ коэффициентов
                if 'main_odds' in odds:
                    main_odds = odds['main_odds']
                    
                    p1 = float(main_odds.get('П1', 999))
                    x = float(main_odds.get('X', 999))
                    p2 = float(main_odds.get('П2', 999))
                    
                    # Определяем фаворита
                    if p1 < p2 and p1 < x:
                        betting_analysis['favorite'] = team1
                        betting_analysis['favorite_odds'] = p1
                    elif p2 < p1 and p2 < x:
                        betting_analysis['favorite'] = team2
                        betting_analysis['favorite_odds'] = p2
                    else:
                        betting_analysis['favorite'] = 'draw'
                        betting_analysis['favorite_odds'] = x
                    
                    # Анализ вероятностей
                    prob_p1 = 1 / p1 * 100 if p1 > 1 else 0
                    prob_x = 1 / x * 100 if x > 1 else 0
                    prob_p2 = 1 / p2 * 100 if p2 > 1 else 0
                    
                    betting_analysis['probabilities'] = {
                        team1: f'{prob_p1:.1f}%',
                        'draw': f'{prob_x:.1f}%',
                        team2: f'{prob_p2:.1f}%'
                    }
            
            return betting_analysis
            
        except Exception as e:
            return {}
    
    def _get_historical_data(self, team1: str, team2: str, sport: str) -> Dict[str, Any]:
        """
        Исторические данные встреч
        """
        try:
            h2h_data = {
                'total_meetings': 0,
                'team1_wins': 0,
                'draws': 0,
                'team2_wins': 0,
                'last_meetings': [],
                'trends': {}
            }
            
            # Базовая реализация - можно расширить
            return h2h_data
            
        except Exception as e:
            return {}
    
    def _get_prediction_factors(self, team1: str, team2: str, sport: str) -> Dict[str, Any]:
        """
        Факторы для предсказания результата
        """
        try:
            factors = {
                'team1_factors': {
                    'home_advantage': None,
                    'recent_form': None,
                    'injury_list': [],
                    'motivation': None
                },
                'team2_factors': {
                    'away_record': None,
                    'recent_form': None,
                    'injury_list': [],
                    'motivation': None
                },
                'match_factors': {
                    'weather': None,
                    'referee': None,
                    'importance': None,
                    'rivalry': None
                }
            }
            
            return factors
            
        except Exception as e:
            return {}