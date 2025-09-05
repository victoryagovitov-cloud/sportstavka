"""
Утилиты для работы с временем
"""
from datetime import datetime
import pytz
from config import MOSCOW_TIMEZONE

def get_moscow_time() -> datetime:
    """
    Получить текущее московское время
    """
    moscow_tz = pytz.timezone(MOSCOW_TIMEZONE)
    return datetime.now(moscow_tz)

def format_moscow_time(dt: datetime = None) -> str:
    """
    Форматировать время в московском часовом поясе
    """
    if dt is None:
        dt = get_moscow_time()
    return dt.strftime('%H:%M МСК, %d.%m.%Y')

def get_time_until_match_end(current_minute: int, sport: str) -> str:
    """
    Рассчитать время до конца матча
    """
    if sport == 'football':
        remaining = 90 - current_minute
        if remaining > 0:
            return f"~{remaining} мин."
        else:
            return "Доп. время"
    
    return "В процессе"