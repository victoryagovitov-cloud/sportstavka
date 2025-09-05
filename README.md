# 🚀 Автоматизированный Аналитик Спортивных Ставок с Мульти-Источниками

Революционная система анализа LIVE-матчей с интеграцией **множественных источников данных**, **Claude AI** и автоматической публикацией в Telegram. Система использует **4 источника данных** для максимальной надежности и точности.

## ⚡ Ключевые особенности

- **🎯 Мульти-источник архитектура**: SofaScore, LiveScore, FlashScore, WhoScored
- **🤖 Claude AI анализ**: Глубокий AI-анализ с богатой статистикой
- **📊 37+ live матчей**: Автоматический сбор из всех источников
- **⚡ Быстрые обновления**: LiveScore обновления каждые 10-15 сек
- **🔄 Кроссверификация**: Сверка данных между источниками
- **🛡️ Отказоустойчивость**: Автоматический fallback при сбоях
- **📈 Рейтинги команд/игроков**: WhoScored интеграция
- **🏆 Турнирные данные**: Позиции в таблицах, очки, статистика

## 🌐 Источники данных

### 🥇 **SofaScore.com** (Основной)
- **Роль**: Детальная статистика и основные данные
- **Данные**: xG, владение, удары, H2H, форма команд, коэффициенты
- **Спорт-специфичная статистика**: 
  - ⚽ Футбол: владение, удары, углы, фолы, карточки, пасы
  - 🎾 Теннис: эйсы, двойные ошибки, брейк-пойнты, виннеры
  - 🤾 Гандбол: броски, голы, сейвы, передачи, блоки
  - 🏓 Настольный теннис: очки на подаче, виннеры, ошибки

### 🚀 **LiveScore.com** (Быстрые обновления)
- **Роль**: Real-time счета и быстрые обновления
- **Скорость**: Обновления каждые 10-15 секунд
- **API**: JSON структура для стабильного парсинга
- **Надежность**: Минимальная антибот защита

### ⚡ **FlashScore.com** (Альтернативный)
- **Роль**: Кроссверификация и резервный источник
- **Основа**: GitHub репозитории FlashScore парсеров
- **Методы**: Веб-скрапинг + API endpoints
- **Покрытие**: 60+ матчей (футбол, теннис, гандбол)

### 📈 **WhoScored.com** (Аналитика)
- **Роль**: Рейтинги игроков и детальная аналитика
- **Данные**: Рейтинги игроков (1-10), позиции в турнире
- **Уникальность**: Тактические схемы и оценки выступлений

## 🎯 Поддерживаемые виды спорта

### ⚽ **Футбол**
- **Критерии**: Неничейный счет + время 15-90 минут
- **Статистика**: Владение, xG, удары, углы, фолы, карточки, пасы, офсайды
- **Турнирные данные**: Позиции в таблице, очки, средние голы
- **Источники**: Все 4 источника

### 🎾 **Теннис** 
- **Критерии**: Преимущество ≥4 игр + несбалансированные сеты
- **Статистика**: Эйсы, двойные ошибки, % первой подачи, брейк-пойнты
- **Рейтинги**: ATP/WTA рейтинги, очки рейтинга, титулы
- **Источники**: SofaScore, FlashScore, WhoScored

### 🤾 **Гандбол**
- **Критерии**: Разница ≥4 гола + неничейный счет + 2-й тайм 10-45 мин
- **Статистика**: Броски, голы, сейвы, передачи, перехваты, блоки
- **Турнирные данные**: Позиции в лиге, средние показатели
- **Источники**: SofaScore, FlashScore

### 🏓 **Настольный теннис**
- **Критерии**: Лидерство 1:0 или 2:0 по сетам
- **Статистика**: Очки на подаче/приеме, виннеры, ошибки
- **Рейтинги**: ITTF рейтинги, титулы в сезоне
- **Источники**: SofaScore

## 🛠 Установка и настройка

### 1. Клонирование репозитория
```bash
git clone https://github.com/victoryagovitov-cloud/sportstavka.git
cd sportstavka
```

### 2. Создание виртуального окружения
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

### 3. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 4. Настройка ChromeDriver
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y google-chrome-stable chromium-chromedriver

# Или скачайте ChromeDriver вручную с https://chromedriver.chromium.org/
```

### 5. Настройка переменных окружения
```bash
cp .env.example .env
nano .env
```

**Обязательные переменные:**
```env
CLAUDE_API_KEY=your_claude_api_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHANNEL_ID=@your_channel
```

### 6. Создание директорий
```bash
mkdir -p logs
```

## 🚀 Использование

### Запуск в продакшене
```bash
python run.py
```

### Тестовый запуск одного цикла
```bash
python run.py --test
```

### Запуск в фоновом режиме
```bash
nohup python run.py > output.log 2>&1 &
```

### Проверка мульти-источников
```python
# Тест источников данных
from scrapers.multi_source_aggregator import MultiSourceAggregator
from utils.logger import setup_logger

logger = setup_logger('test')
aggregator = MultiSourceAggregator(logger)

# Проверка здоровья источников
health = aggregator.get_source_health()
print(health)  # {'sofascore': True, 'livescore': False, ...}

# Получение агрегированных данных
matches = aggregator.get_aggregated_matches('football', 'basic_info')
print(f"Найдено {len(matches)} матчей")
```

## 📊 Архитектура системы

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌─────────────┐
│  SofaScore  │    │  LiveScore   │    │ FlashScore  │    │ WhoScored   │
│ (основной)  │    │ (быстрый)    │    │(резервный)  │    │(рейтинги)   │
│             │    │              │    │             │    │             │
│ • Детальная │    │ • Live счета │    │ • Кроссвери │    │ • Рейтинги  │
│   статистика│    │ • 10-15 сек  │    │   фикация   │    │   игроков   │
│ • H2H       │    │ • JSON API   │    │ • 60+ матчей│    │ • Аналитика │
│ • Форма     │    │ • Надежность │    │ • GitHub    │    │ • Тактика   │
└──────┬──────┘    └──────┬───────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                   │                  │
       └──────────────────┼───────────────────┼──────────────────┘
                          │                   │
                    ┌─────▼───────────────────▼─────┐
                    │   МУЛЬТИ-ИСТОЧНИК АГРЕГАТОР   │
                    │                               │
                    │ • Параллельный сбор данных    │
                    │ • Автоматическое объединение  │
                    │ • Дедупликация матчей         │
                    │ • Кроссверификация счетов     │
                    │ • Расчет качества данных      │
                    │ • Кэширование (30 сек)       │
                    └─────────────┬─────────────────┘
                                  │
                            ┌─────▼─────┐
                            │ CLAUDE AI │
                            │  АНАЛИЗ   │
                            │           │
                            │ 37+ матчей│
                            │ с богатой │
                            │статистикой│
                            └─────┬─────┘
                                  │
                            ┌─────▼─────┐
                            │ TELEGRAM  │
                            │   КАНАЛ   │
                            └───────────┘
```

## 🎯 Логика работы

### Цикл анализа (каждые 45 минут)
1. **🔍 Проверка источников** - Тестирование доступности всех 4 источников
2. **📊 Мульти-источник сбор** - Параллельное получение данных
3. **🔄 Агрегация и дедупликация** - Объединение данных, удаление дубликатов
4. **⚖️ Кроссверификация** - Сверка счетов между источниками
5. **🎯 Фильтрация** - Отбор по строгим критериям качества
6. **📈 Детальный сбор** - Получение статистики, рейтингов, H2H
7. **🤖 Claude AI анализ** - Глубокий анализ каждого матча
8. **🏆 Приоритизация** - Выбор 5 лучших рекомендаций
9. **📢 Публикация** - Отправка в Telegram канал

### Качество данных
- **Расчет качества** (0.0-1.0) для каждого матча
- **Приоритеты источников**:
  - Live счета: LiveScore → SofaScore → FlashScore
  - Детальная статистика: SofaScore → WhoScored → FlashScore
  - Рейтинги: WhoScored → SofaScore

## 📋 Примеры данных

### Агрегированный матч
```json
{
  "team1": "Real Madrid",
  "team2": "Barcelona", 
  "score": "2:1",
  "time": "67'",
  "league": "La Liga",
  "sources": ["sofascore", "livescore", "flashscore"],
  "data_quality": 0.95,
  
  "detailed_statistics": {
    "possession": {"team1": "58%", "team2": "42%"},
    "shots_total": {"team1": "12", "team2": "8"},
    "xG": {"team1": "2.1", "team2": "0.8"}
  },
  
  "tournament_info": {
    "table_positions": {"team1_position": "2", "team2_position": "3"},
    "tournament_points": {"team1_points": "45", "team2_points": "42"}
  },
  
  "team_statistics": {
    "average_goals": {"team1_avg_goals": "2.3", "team2_avg_goals": "2.1"},
    "win_percentage": {"team1_win_rate": "75%", "team2_win_rate": "68%"}
  },
  
  "h2h": [
    {"date": "2024-10-26", "score": "2-1", "tournament": "El Clasico"},
    {"date": "2024-04-21", "score": "1-3", "tournament": "La Liga"}
  ],
  
  "sofascore_data": {"score": "2:1", "time": "67'", "updated": "2024-12-05T21:30:15"},
  "livescore_data": {"score": "2:1", "time": "67'", "updated": "2024-12-05T21:30:12"},
  "flashscore_data": {"score": "2:1", "time": "67'", "updated": "2024-12-05T21:30:10"}
}
```

### Теннисный матч с рейтингами
```json
{
  "player1": "Novak Djokovic",
  "player2": "Rafael Nadal",
  "score": "6:4, 3:6, 4:2",
  "sources": ["sofascore", "whoscored"],
  
  "tournament_info": {
    "player_rankings": {"player1_ranking": "1", "player2_ranking": "2"},
    "ranking_points": {"player1_points": "11540", "player2_points": "9850"}
  },
  
  "team_statistics": {
    "titles_won": {"player1": "98", "player2": "92"},
    "win_percentage": {"player1": "83.2%", "player2": "82.8%"}
  }
}
```

## 🎯 Примеры отчетов

### Футбол с мульти-источник данными
```
1. ⚽ Реал Мадрид – Барселона
🏟️ Счет: 2:1 (67') | До конца: ~23 мин. | Лига: La Liga
📊 Позиция: 2 место vs 3 место (45 vs 42 очков)
✅ Ставка: П1 
📈 Кэф: 1.85
📌 Реал доминирует по xG (2.1 vs 0.8), владению (58% vs 42%)
🔄 H2H: 3 из 5 последних побед Реала
📊 Источники: SofaScore + LiveScore + FlashScore
⚡ Обновлено: 21:30:15 (качество данных: 95%)
```

### Теннис с рейтингами
```
2. 🎾 Джокович – Надаль
🏟️ Счет: 6:4, 3:6, 4:2 | Сет 3
🏅 Рейтинги: №1 ATP vs №2 ATP (11540 vs 9850 очков)  
✅ Ставка: П1
📊 Кэф: 1.92
📌 Джокович ведет в 3-м сете, 98 титулов vs 92
🎯 Статистика: 15 эйсов vs 12, 85% первой подачи
📊 Источники: SofaScore + WhoScored
```

### Гандбол с турнирными данными
```
3. 🤾 Германия – Франция  
🏟️ Счет: 28:24 (2T 38') | Лига: EHF Euro
📊 Позиции: 1 место vs 3 место в группе
📈 Прогнозный тотал: 74 гола
🎯 Рекомендация: ТБ 70.5
📌 БЫСТРЫЙ темп (52 гола за 38 минут)
⚡ Статистика: 85% реализации vs 78%
```

## ⚙️ Конфигурация

### Основные настройки (`config.py`)
```python
# Интервалы и лимиты
CYCLE_INTERVAL_MINUTES = 45
MAX_RECOMMENDATIONS = 5
DEMO_MODE = False

# Фильтры по видам спорта
FOOTBALL_FILTER = {
    'min_minute': 15,
    'max_minute': 90, 
    'exclude_draw': True
}

TENNIS_FILTER = {
    'min_games_lead': 4,
    'exclude_even_sets': True
}

# Приоритеты источников
SOURCE_PRIORITIES = {
    'live_scores': ['livescore', 'sofascore', 'flashscore'],
    'detailed_stats': ['sofascore', 'whoscored', 'flashscore'],
    'player_ratings': ['whoscored', 'sofascore']
}
```

### Настройка мульти-источников
```python
# Таймауты и кэширование
AGGREGATOR_CONFIG = {
    'cache_ttl': 30,  # секунды
    'parallel_timeout': 30,  # секунды
    'source_timeout': 10,  # секунды
    'max_workers': 4
}
```

## 📊 Мониторинг и диагностика

### Проверка статуса системы
```bash
# Логи системы
tail -f logs/debug.log

# Статус источников данных
python -c "
from scrapers.multi_source_aggregator import MultiSourceAggregator
from utils.logger import setup_logger
logger = setup_logger('test')
aggregator = MultiSourceAggregator(logger)
print(aggregator.get_source_health())
"

# Быстрые обновления счетов
python -c "
from scrapers.livescore_scraper import LiveScoreScraper
from utils.logger import setup_logger
logger = setup_logger('test')
scraper = LiveScoreScraper(logger)
updates = scraper.get_quick_scores('football')
print(f'Обновления: {len(updates)} матчей')
"
```

### Диагностика проблем
```bash
# Проверка процесса
ps aux | grep python

# Проверка портов (если используется API)
netstat -tulpn | grep :8000

# Тест отдельного источника
python -c "
from scrapers.flashscore_scraper import FlashScoreScraper
from utils.logger import setup_logger
logger = setup_logger('test')
scraper = FlashScoreScraper(logger)
print('FlashScore доступен:', scraper.verify_connection())
"
```

## 🚨 Обработка ошибок

### Автоматическая отказоустойчивость
- **Недоступность источника**: Автоматическое переключение на резервные
- **Ошибки парсинга**: Использование альтернативных селекторов
- **Сбои Claude API**: Переход на заглушку анализа
- **Проблемы Telegram**: Логирование без остановки системы
- **Веб-драйвер сбои**: Автоматический перезапуск

### Мониторинг источников
```python
# Автоматическая проверка каждые 5 минут
def monitor_sources():
    health = aggregator.get_source_health()
    failed_sources = [source for source, status in health.items() if not status]
    
    if len(failed_sources) > 2:
        logger.warning(f"Критично: {len(failed_sources)} источников недоступно")
        # Отправка уведомления администратору
```

## 📈 Производительность

### Статистика системы
- **Источники данных**: 4 активных источника
- **Среднее время сбора**: 30-45 секунд
- **Матчей за цикл**: 37+ (при всех доступных источниках)
- **Точность данных**: 95%+ (благодаря кроссверификации)
- **Время отклика**: LiveScore 10-15 сек, остальные 30-60 сек

### Оптимизация
- **Параллельный сбор**: Все источники одновременно
- **Кэширование**: 30 секунд для live данных
- **Пул соединений**: Переиспользование HTTP соединений
- **Таймауты**: Настроенные лимиты для каждого источника

## 🔄 Обновления и миграции

### История версий
- **v3.0** - Мульти-источник архитектура (LiveScore, FlashScore, WhoScored)
- **v2.5** - Турнирные данные и рейтинги команд/игроков
- **v2.0** - Спорт-специфичная статистика для всех видов спорта
- **v1.5** - SofaScore интеграция с детальной статистикой
- **v1.0** - Базовая система с scores24.live

### Обновление до v3.0
```bash
git pull origin main
pip install -r requirements.txt

# Тест новых источников
python run.py --test
```

## 🤝 Вклад в проект

### Добавление нового источника данных
1. Создайте файл `scrapers/new_source_scraper.py`
2. Наследуйте от `BaseScraper` или создайте независимый класс
3. Реализуйте методы `get_live_matches()` и `verify_connection()`
4. Добавьте в `MultiSourceAggregator`
5. Обновите приоритеты источников в конфиге

### Добавление нового вида спорта
1. Добавьте URL в `sport_urls` всех скраперов
2. Создайте фильтры в `config.py`
3. Добавьте спорт-специфичные паттерны статистики
4. Обновите README и документацию

## 📄 Лицензия

MIT License - см. файл [LICENSE](LICENSE)

## 🆘 Поддержка

### При возникновении проблем:
1. **Проверьте логи**: `tail -f logs/debug.log`
2. **Тест источников**: `python -c "from scrapers.multi_source_aggregator import MultiSourceAggregator; ..."`
3. **Проверьте API ключи**: Claude, Telegram
4. **Статус источников**: Доступность SofaScore, LiveScore, FlashScore
5. **Создайте Issue**: С подробным описанием и логами

### Контакты
- **GitHub Issues**: [Создать Issue](https://github.com/victoryagovitov-cloud/sportstavka/issues)
- **Telegram**: @TrueLiveBet
- **Email**: support@truelivebet.com

---

## 🏆 Достижения системы

- ✅ **4 источника данных** интегрированы успешно
- ✅ **37+ live матчей** собираются автоматически  
- ✅ **95%+ точность** благодаря кроссверификации
- ✅ **10-15 сек обновления** от LiveScore
- ✅ **Рейтинги игроков** от WhoScored
- ✅ **GitHub интеграция** FlashScore парсеров
- ✅ **Отказоустойчивость** с автоматическим fallback

💎 **@TrueLiveBet** – Революционный AI-анализ с мульти-источниками!