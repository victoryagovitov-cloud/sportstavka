"""
Провайдер демонстрационных данных для тестирования системы
"""
from typing import List, Dict, Any
import random
from datetime import datetime

class DemoDataProvider:
    """
    Генератор демонстрационных данных для тестирования
    """
    
    def __init__(self):
        self.football_teams = [
            ('Реал Мадрид', 'Барселона', 'La Liga'),
            ('Манчестер Сити', 'Ливерпуль', 'Premier League'),
            ('Бавария', 'Боруссия Дортмунд', 'Bundesliga'),
            ('ПСЖ', 'Марсель', 'Ligue 1'),
            ('Милан', 'Интер', 'Serie A'),
            ('Зенит', 'Спартак', 'РПЛ')
        ]
        
        self.tennis_players = [
            ('Новак Джокович', 'Карлос Алькарас', 'ATP Masters 1000'),
            ('Арина Соболенко', 'Ига Швентек', 'WTA 1000'),
            ('Даниил Медведев', 'Александр Зверев', 'ATP 500'),
            ('Коко Гауфф', 'Елена Рыбакина', 'WTA 500')
        ]
        
        self.handball_teams = [
            ('Германия', 'Франция', 'EHF Euro 2024'),
            ('Дания', 'Норвегия', 'EHF Euro 2024'),
            ('Испания', 'Швеция', 'EHF Euro 2024')
        ]
    
    def get_demo_football_matches(self) -> List[Dict[str, Any]]:
        """
        Генерирует демонстрационные футбольные матчи
        """
        matches = []
        
        for i, (team1, team2, league) in enumerate(self.football_teams[:3]):
            # Генерируем случайный не ничейный счет
            goals1 = random.randint(0, 3)
            goals2 = random.randint(0, 3)
            while goals1 == goals2:  # Избегаем ничьей
                goals2 = random.randint(0, 3)
            
            minute = random.randint(20, 85)
            
            match = {
                'team1': team1,
                'team2': team2,
                'score': f'{goals1}:{goals2}',
                'time': f'{minute}\'',
                'league': league,
                'url': f'/match/demo_{i+1}',
                'sport': 'football',
                'priority': i,
                'statistics': {
                    'Владение мячом': {
                        'team1': f'{random.randint(45, 70)}%',
                        'team2': f'{random.randint(30, 55)}%'
                    },
                    'xG': {
                        'team1': f'{random.uniform(0.5, 3.0):.1f}',
                        'team2': f'{random.uniform(0.3, 2.5):.1f}'
                    },
                    'Удары в створ': {
                        'team1': str(random.randint(3, 12)),
                        'team2': str(random.randint(1, 8))
                    },
                    'Угловые': {
                        'team1': str(random.randint(2, 10)),
                        'team2': str(random.randint(1, 6))
                    }
                },
                'prediction': f'{team1} имеет {random.randint(55, 85)}% шансов на победу',
                'trends': {
                    'Давление': f'{team1} доминирует',
                    'Атаки': f'{team1} {random.randint(15, 25)}, {team2} {random.randint(8, 18)}'
                },
                'h2h': [
                    {'date': '2024-04-21', 'score': '2:1', 'league': league},
                    {'date': '2024-01-14', 'score': '1:2', 'league': league},
                    {'date': '2023-10-28', 'score': '2:0', 'league': league}
                ],
                'odds': {
                    'Основной исход': [f'{random.uniform(1.5, 2.5):.2f}', 
                                     f'{random.uniform(3.0, 4.0):.2f}', 
                                     f'{random.uniform(3.5, 6.0):.2f}']
                },
                'table': {
                    team1: {'position': str(random.randint(1, 5)), 'points': str(random.randint(60, 80))},
                    team2: {'position': str(random.randint(3, 8)), 'points': str(random.randint(50, 75))}
                },
                'results': {
                    'team1': {
                        'statistics': {
                            'wins': random.randint(6, 9),
                            'draws': random.randint(0, 2),
                            'losses': random.randint(0, 2),
                            'win_percentage': random.randint(70, 90)
                        }
                    },
                    'team2': {
                        'statistics': {
                            'wins': random.randint(4, 7),
                            'draws': random.randint(1, 3),
                            'losses': random.randint(1, 4),
                            'win_percentage': random.randint(50, 75)
                        }
                    }
                }
            }
            matches.append(match)
        
        return matches
    
    def get_demo_tennis_matches(self) -> List[Dict[str, Any]]:
        """
        Генерирует демонстрационные теннисные матчи
        """
        matches = []
        
        for i, (player1, player2, tournament) in enumerate(self.tennis_players[:2]):
            # Генерируем счет где ведущий выиграл первый сет
            sets1 = random.choice([1, 2])
            sets2 = 0 if sets1 == 2 else random.choice([0, 1])
            
            current_set = f'{random.randint(3, 6)}:{random.randint(1, 4)}'
            
            match = {
                'player1': player1,
                'player2': player2,
                'sets_score': f'{sets1}:{sets2}',
                'current_set': current_set,
                'tournament': tournament,
                'url': f'/match/tennis_demo_{i+1}',
                'sport': 'tennis',
                'priority': i,
                'statistics': {
                    'Эйсы': {
                        'player1': str(random.randint(5, 15)),
                        'player2': str(random.randint(2, 10))
                    },
                    'Двойные ошибки': {
                        'player1': str(random.randint(0, 3)),
                        'player2': str(random.randint(1, 5))
                    },
                    '1-я подача': {
                        'player1': f'{random.randint(65, 80)}%',
                        'player2': f'{random.randint(55, 75)}%'
                    }
                },
                'h2h': [
                    {'date': '2024-06-15', 'score': '2:1', 'tournament': 'French Open'},
                    {'date': '2024-01-28', 'score': '1:2', 'tournament': 'Australian Open'}
                ],
                'odds': {
                    'Победа': [f'{random.uniform(1.3, 1.8):.2f}', f'{random.uniform(2.0, 3.5):.2f}']
                },
                'rankings': {
                    'player1': f'ATP #{random.randint(1, 5)}',
                    'player2': f'ATP #{random.randint(3, 10)}'
                },
                'results': {
                    'player1': {
                        'statistics': {
                            'wins': random.randint(8, 10),
                            'losses': random.randint(0, 2),
                            'win_percentage': random.randint(80, 95),
                            'sets_won': random.randint(18, 25),
                            'sets_lost': random.randint(5, 12)
                        }
                    }
                }
            }
            matches.append(match)
        
        return matches
    
    def get_demo_handball_matches(self) -> List[Dict[str, Any]]:
        """
        Генерирует демонстрационные гандбольные матчи с расчетом тоталов
        """
        matches = []
        
        for i, (team1, team2, league) in enumerate(self.handball_teams[:2]):
            # Генерируем счет с разностью >= 4
            goals1 = random.randint(20, 30)
            goals2 = random.randint(15, 25)
            if abs(goals1 - goals2) < 4:
                goals2 = goals1 - 4 if goals1 > goals2 else goals1 + 4
            
            # Время во втором тайме
            minute = random.randint(15, 40)
            played_minutes = 30 + minute
            total_goals = goals1 + goals2
            
            # Расчет тоталов
            predicted_total_raw = (total_goals / played_minutes) * 60
            predicted_total = int(predicted_total_raw) + 1  # Округляем в большую сторону
            total_over = predicted_total - 4
            total_under = predicted_total + 4
            
            if total_goals > played_minutes:
                tempo = "БЫСТРЫЙ"
                recommendation = f"ТБ {total_over}"
                recommendation_type = "over"
            else:
                tempo = "МЕДЛЕННЫЙ"
                recommendation = f"ТМ {total_under}"
                recommendation_type = "under"
            
            match = {
                'team1': team1,
                'team2': team2,
                'score': f'{goals1}:{goals2}',
                'time': f'2T {minute}\'',
                'league': league,
                'url': f'/match/handball_demo_{i+1}',
                'sport': 'handball',
                'totals_calculation': {
                    'total_goals': total_goals,
                    'played_minutes': played_minutes,
                    'predicted_total': predicted_total,
                    'total_over': total_over,
                    'total_under': total_under,
                    'tempo': tempo,
                    'recommendation': recommendation,
                    'recommendation_type': recommendation_type,
                    'reasoning': f'{tempo} темп игры ({total_goals} голов за {played_minutes} минут)'
                },
                'odds': {
                    'Основной исход': [f'{random.uniform(1.8, 2.5):.2f}', 
                                     f'{random.uniform(3.0, 3.8):.2f}'],
                    'Тотал': [f'{random.uniform(1.7, 2.0):.2f}', f'{random.uniform(1.8, 2.1):.2f}']
                },
                'results': {
                    'team1': {
                        'statistics': {
                            'wins': random.randint(7, 9),
                            'draws': random.randint(0, 1),
                            'losses': random.randint(0, 2),
                            'avg_goals_scored': random.uniform(25.0, 30.0),
                            'avg_goals_conceded': random.uniform(20.0, 25.0)
                        }
                    }
                }
            }
            matches.append(match)
        
        return matches

# Глобальный экземпляр
demo_provider = DemoDataProvider()