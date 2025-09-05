"""
Конфигурация для автоматизированного аналитика спортивных ставок
"""
import os
from typing import Dict, List

# API конфигурация
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY', '')  # Будет добавлен позже
TELEGRAM_BOT_TOKEN = "7824400107:AAGZqPdS0E0N3HsYpD8TW9m8c-bapFd-RHk"
TELEGRAM_CHAT_ID = "@TrueLiveBet"

# URL для SofaScore (новый основной источник)
SOFASCORE_URLS = {
    'football': 'https://www.sofascore.com/football/livescore',
    'tennis': 'https://www.sofascore.com/tennis/livescore',
    'table_tennis': 'https://www.sofascore.com/table-tennis/livescore',
    'handball': 'https://www.sofascore.com/handball/livescore'
}

# URL для scores24.live (резервный источник)
SCORES24_URLS = {
    'football': 'https://scores24.live/ru/soccer?matchesFilter=live',
    'tennis': 'https://scores24.live/ru/tennis?matchesFilter=live', 
    'table_tennis': 'https://scores24.live/ru/table-tennis?matchesFilter=live',
    'handball': 'https://scores24.live/ru/handball?matchesFilter=live'
}

# Настройки парсинга
SELENIUM_OPTIONS = [
    '--headless',
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--disable-gpu',
    '--window-size=1920,1080',
    '--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.7339.80 Safari/537.36'
]

# Путь к ChromeDriver
CHROMEDRIVER_PATH = '/usr/local/bin/chromedriver'

# Временные настройки
CYCLE_INTERVAL_MINUTES = 45
RETRY_DELAY_SECONDS = 120
MOSCOW_TIMEZONE = 'Europe/Moscow'

# Фильтры для матчей
FOOTBALL_FILTER = {
    'min_minute': 15,
    'max_minute': 90,
    'exclude_draw': True
}

TENNIS_FILTER = {
    'min_games_lead': 4,
    'exclude_even_sets': True
}

TABLE_TENNIS_FILTER = {
    'required_set_leads': [1, 2],  # 1:0 или 2:0
    'exclude_even_sets': True
}

HANDBALL_FILTER = {
    'min_goal_difference': 4,
    'exclude_draw': True,
    'min_minute_second_half': 10,
    'max_minute_second_half': 45
}

# Топ лиги по приоритету
TOP_LEAGUES = {
    'football': [
        'Premier League', 'La Liga', 'Serie A', 'Bundesliga', 'Ligue 1',
        'Champions League', 'Europa League', 'World Cup', 'Euro',
        'Премьер-лига', 'РПЛ'
    ],
    'tennis': [
        'ATP Masters', 'WTA 1000', 'Grand Slam', 'ATP 500', 'WTA 500',
        'ATP 250', 'WTA 250'
    ]
}

# Настройки логирования
LOG_FILE = 'debug.log'
LOG_LEVEL = 'INFO'

# Максимальное количество рекомендаций в отчете
MAX_RECOMMENDATIONS = 5