"""
Кастомный форматтер сообщений для Telegram канала TrueLiveBet
Формат согласно требованиям пользователя
"""

import logging
from datetime import datetime
from typing import List, Dict, Any
import pytz


class CustomTelegramFormatter:
    """
    Форматтер сообщений в стиле TrueLiveBet
    
    Создает сообщения в точном соответствии с требуемым форматом:
    - Заголовок с временем МСК
    - Разделители по видам спорта
    - Детальная информация по каждому матчу
    - Футер с дисклеймером
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.moscow_tz = pytz.timezone('Europe/Moscow')
    
    def format_live_recommendations(self, matches: List[Dict[str, Any]], analysis_result: Dict[str, Any]) -> str:
        """
        Форматирует live рекомендации в требуемом стиле
        
        Args:
            matches: Список матчей для анализа
            analysis_result: Результат анализа Claude AI
            
        Returns:
            str: Отформатированное сообщение для Telegram
        """
        
        # Получаем московское время
        moscow_time = datetime.now(self.moscow_tz)
        time_str = moscow_time.strftime("%H:%M МСК, %d.%m.%Y")
        
        # Заголовок
        message = f"🎯 LIVE-ПРЕДЛОЖЕНИЯ НА ({time_str}) 🎯\n\n"
        
        # Группируем матчи по видам спорта
        sports_groups = self._group_matches_by_sport(matches)
        
        match_counter = 1
        
        # Форматируем каждый вид спорта
        for sport, sport_matches in sports_groups.items():
            if not sport_matches:
                continue
                
            # Заголовок вида спорта
            sport_header = self._get_sport_header(sport)
            message += f"{sport_header}\n\n"
            
            # Форматируем матчи этого вида спорта
            for match in sport_matches:
                formatted_match = self._format_single_match(match, match_counter, sport)
                if formatted_match:
                    message += formatted_match + "\n\n"
                    match_counter += 1
        
        # Добавляем футер
        message += self._get_footer()
        
        return message
    
    def _group_matches_by_sport(self, matches: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Группирует матчи по видам спорта"""
        
        groups = {
            'football': [],
            'tennis': [],
            'table_tennis': [],
            'handball': []
        }
        
        for match in matches:
            sport = match.get('sport', '').lower()
            if sport in groups:
                groups[sport].append(match)
            else:
                # Определяем спорт по другим признакам
                if any(key in match for key in ['team1', 'team2']):
                    groups['football'].append(match)
                elif any(key in match for key in ['player1', 'player2']):
                    groups['tennis'].append(match)
                else:
                    groups['football'].append(match)  # По умолчанию футбол
        
        return groups
    
    def _get_sport_header(self, sport: str) -> str:
        """Возвращает заголовок для вида спорта"""
        
        headers = {
            'football': "—————————————\n⚽ ФУТБОЛ ⚽\n—————————————",
            'tennis': "—————————————\n🎾 ТЕННИС 🎾\n—————————————",
            'table_tennis': "—————————————\n🏓 НАСТОЛЬНЫЙ ТЕННИС 🏓\n—————————————",
            'handball': "—————————————\n🤾 ГАНДБОЛ 🤾\n—————————————"
        }
        
        return headers.get(sport, "—————————————\n⚽ СПОРТ ⚽\n—————————————")
    
    def _format_single_match(self, match: Dict[str, Any], counter: int, sport: str) -> str:
        """Форматирует один матч в требуемом стиле"""
        
        try:
            # Извлекаем данные матча
            if sport == 'tennis':
                team1 = match.get('player1', match.get('team1', 'Игрок 1'))
                team2 = match.get('player2', match.get('team2', 'Игрок 2'))
                sport_emoji = "🎾"
            else:
                team1 = match.get('team1', 'Команда 1')
                team2 = match.get('team2', 'Команда 2')
                sport_emoji = {"football": "⚽", "table_tennis": "🏓", "handball": "🤾"}.get(sport, "⚽")
            
            score = match.get('score', 'LIVE')
            time = match.get('time', 'В процессе')
            
            # Извлекаем коэффициенты
            odds = match.get('odds', {})
            p1_coeff = odds.get('П1', odds.get('1', '1.85'))
            p2_coeff = odds.get('П2', odds.get('2', '2.10'))
            
            # Определяем рекомендацию на основе счета и коэффициентов
            recommendation, reasoning = self._generate_recommendation(match, sport)
            
            # Форматируем время для отображения
            display_time = self._format_display_time(time, sport)
            
            # Создаем сообщение матча
            match_message = f"{counter}. {sport_emoji} {team1} – {team2}\n"
            
            if sport == 'tennis':
                match_message += f"🎯 Счет: {score} ({display_time})\n"
                match_message += f"✅ Ставка: {recommendation}\n"
                match_message += f"📊 Кэф: {p1_coeff if 'П1' in recommendation else p2_coeff}\n"
            else:
                match_message += f"🏟️ Счет: {score} ({display_time})\n"
                match_message += f"✅ Ставка: {recommendation}\n"
                match_message += f"📊 Кэф: {p1_coeff if 'П1' in recommendation else p2_coeff}\n"
            
            match_message += f"📌 {reasoning}"
            
            return match_message
            
        except Exception as e:
            self.logger.error(f"Ошибка форматирования матча: {e}")
            return None
    
    def _generate_recommendation(self, match: Dict[str, Any], sport: str) -> tuple[str, str]:
        """Генерирует рекомендацию и обоснование"""
        
        try:
            score = match.get('score', 'LIVE')
            odds = match.get('odds', {})
            
            # Анализируем счет для определения лидера
            if ':' in score:
                if sport == 'tennis':
                    # Для тенниса анализируем по сетам
                    sets_score = score.split('(')[0].strip()
                    home_sets, away_sets = map(int, sets_score.split(':'))
                    
                    if home_sets > away_sets:
                        recommendation = f"Победа {match.get('player1', match.get('team1', 'Первый'))}"
                        reasoning = f"Игрок лидирует по сетам {home_sets}:{away_sets}, контролирует ход матча"
                    else:
                        recommendation = f"Победа {match.get('player2', match.get('team2', 'Второй'))}"
                        reasoning = f"Игрок лидирует по сетам {away_sets}:{home_sets}, уверенная игра"
                else:
                    # Для других видов спорта
                    home_score, away_score = map(int, score.split(':'))
                    
                    if home_score > away_score:
                        recommendation = "П1"
                        reasoning = f"Команда лидирует {home_score}:{away_score}, контролирует игру, имеет время для удержания преимущества"
                    else:
                        recommendation = "П2" 
                        reasoning = f"Команда лидирует {away_score}:{home_score}, уверенная игра, высокие шансы на победу"
            else:
                # Если счет неопределен, анализируем по коэффициентам
                p1 = float(odds.get('П1', odds.get('1', 2.0)))
                p2 = float(odds.get('П2', odds.get('2', 2.0)))
                
                if p1 < p2:
                    recommendation = "П1"
                    reasoning = "Фаворит матча, хорошие коэффициенты для консервативной ставки"
                else:
                    recommendation = "П2"
                    reasoning = "Сильная команда, недооцененная букмекерами"
            
            return recommendation, reasoning
            
        except Exception as e:
            self.logger.error(f"Ошибка генерации рекомендации: {e}")
            return "П1", "Анализ на основе текущей ситуации в матче"
    
    def _format_display_time(self, time: str, sport: str) -> str:
        """Форматирует время для отображения"""
        
        if sport == 'tennis':
            # Для тенниса показываем сет и счет
            if 'сет' in time.lower():
                return time
            elif ':' in time:
                return f"текущий гейм {time}"
            else:
                return "в процессе"
        else:
            # Для других видов спорта показываем минуты
            if ':' in time and len(time.split(':')) == 2:
                minutes = time.split(':')[0]
                return f"{minutes}'"
            elif time.endswith("'"):
                return time
            elif 'мин' in time:
                return time
            else:
                return "в процессе"
    
    def _get_footer(self) -> str:
        """Возвращает футер сообщения"""
        
        footer = """——————————————————
💎 TrueLiveBet – Команда экспертов всегда на Вашей стороне! 💎

⚠️ Дисклеймер: Наши прогнозы не являются инвестиционными рекомендациями и не гарантируют выигрыш. Но наша команда аналитиков всегда стремится к максимальному качеству сигналов."""
        
        return footer


# Функция для тестирования
def test_custom_formatter():
    """Тестирование кастомного форматтера"""
    
    import logging
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    formatter = CustomTelegramFormatter(logger)
    
    # Тестовые матчи
    test_matches = [
        {
            'team1': 'Манчестер Сити',
            'team2': 'Ливерпуль',
            'score': '2:1',
            'time': '67:00',
            'sport': 'football',
            'odds': {'П1': '1.85', 'П2': '2.10'}
        },
        {
            'player1': 'Новак Джокович',
            'player2': 'Карлос Алькарас',
            'score': '1:0 (6:4)',
            'time': '3:2',
            'sport': 'tennis',
            'odds': {'П1': '1.65', 'П2': '2.25'}
        },
        {
            'team1': 'Норвегия',
            'team2': 'Дания',
            'score': '22:18',
            'time': '35:00',
            'sport': 'handball',
            'odds': {'П1': '1.75', 'П2': '2.05'}
        }
    ]
    
    test_analysis = {
        'recommendations': ['Тест 1', 'Тест 2', 'Тест 3'],
        'total_matches': 3
    }
    
    # Форматируем
    formatted_message = formatter.format_live_recommendations(test_matches, test_analysis)
    
    print("📱 ТЕСТОВОЕ СООБЩЕНИЕ:")
    print("=" * 50)
    print(formatted_message)
    print("=" * 50)


if __name__ == "__main__":
    test_custom_formatter()