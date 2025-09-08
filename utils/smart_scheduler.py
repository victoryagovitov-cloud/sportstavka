"""
Умное расписание анализа с учетом московского времени и активности матчей
Оптимизирует частоту анализа под реальные потребности пользователей
"""

import pytz
from datetime import datetime, time as dt_time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging

class ActivityPeriod(Enum):
    """Периоды активности"""
    NIGHT_SLEEP = "night_sleep"          # 00:00-07:00 - сон
    MORNING_LOW = "morning_low"          # 07:00-12:00 - утро, мало матчей
    AFTERNOON_HIGH = "afternoon_high"    # 12:00-18:00 - день, много матчей
    EVENING_PEAK = "evening_peak"        # 18:00-23:00 - вечер, пик активности
    LATE_EVENING = "late_evening"        # 23:00-00:00 - поздний вечер

@dataclass
class ScheduleConfig:
    """Конфигурация расписания для периода"""
    period: ActivityPeriod
    interval_minutes: int
    enabled: bool
    description: str
    target_audience: str
    max_matches_per_message: int = 10

class SmartScheduler:
    """
    Умный планировщик анализа с учетом московского времени
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.moscow_tz = pytz.timezone('Europe/Moscow')
        
        # Конфигурация расписания
        self.schedule_config = {
            ActivityPeriod.NIGHT_SLEEP: ScheduleConfig(
                period=ActivityPeriod.NIGHT_SLEEP,
                interval_minutes=0,  # Отключено
                enabled=False,
                description="Ночь - спим, анализ не нужен",
                target_audience="Никого (все спят)",
                max_matches_per_message=0
            ),
            
            ActivityPeriod.MORNING_LOW: ScheduleConfig(
                period=ActivityPeriod.MORNING_LOW,
                interval_minutes=120,  # Каждые 2 часа
                enabled=True,
                description="Утро - редкие обновления, мало матчей",
                target_audience="Ранние пташки, планирующие день",
                max_matches_per_message=5
            ),
            
            ActivityPeriod.AFTERNOON_HIGH: ScheduleConfig(
                period=ActivityPeriod.AFTERNOON_HIGH,
                interval_minutes=60,  # Каждый час
                enabled=True,
                description="День - активный период, много матчей",
                target_audience="Офисные работники, активные беттеры",
                max_matches_per_message=8
            ),
            
            ActivityPeriod.EVENING_PEAK: ScheduleConfig(
                period=ActivityPeriod.EVENING_PEAK,
                interval_minutes=30,  # Каждые 30 минут
                enabled=True,
                description="Вечер - пик активности, максимум матчей",
                target_audience="Основная аудитория после работы",
                max_matches_per_message=10
            ),
            
            ActivityPeriod.LATE_EVENING: ScheduleConfig(
                period=ActivityPeriod.LATE_EVENING,
                interval_minutes=90,  # Каждые 1.5 часа
                enabled=True,
                description="Поздний вечер - снижение активности",
                target_audience="Поздние пользователи, завершение дня",
                max_matches_per_message=6
            )
        }
        
        # Статистика использования
        self.usage_stats = {
            'total_cycles': 0,
            'messages_sent': 0,
            'matches_analyzed': 0,
            'tokens_used': 0,
            'period_stats': {period: 0 for period in ActivityPeriod}
        }
    
    def get_current_period(self, moscow_time: Optional[datetime] = None) -> ActivityPeriod:
        """
        Определение текущего периода активности по московскому времени
        """
        if moscow_time is None:
            moscow_time = datetime.now(self.moscow_tz)
        
        hour = moscow_time.hour
        
        if 0 <= hour < 7:
            return ActivityPeriod.NIGHT_SLEEP
        elif 7 <= hour < 12:
            return ActivityPeriod.MORNING_LOW
        elif 12 <= hour < 18:
            return ActivityPeriod.AFTERNOON_HIGH
        elif 18 <= hour < 23:
            return ActivityPeriod.EVENING_PEAK
        else:  # 23-24
            return ActivityPeriod.LATE_EVENING
    
    def should_run_analysis(self, moscow_time: Optional[datetime] = None) -> Tuple[bool, str]:
        """
        Определение, нужно ли запускать анализ в данное время
        """
        if moscow_time is None:
            moscow_time = datetime.now(self.moscow_tz)
        
        current_period = self.get_current_period(moscow_time)
        config = self.schedule_config[current_period]
        
        if not config.enabled:
            return False, f"Период {current_period.value} отключен: {config.description}"
        
        # Проверяем, прошло ли достаточно времени с последнего анализа
        # (эта логика должна интегрироваться с основной системой)
        
        return True, f"Период {current_period.value}: анализ каждые {config.interval_minutes} минут"
    
    def get_optimal_interval(self, moscow_time: Optional[datetime] = None) -> int:
        """
        Получение оптимального интервала для текущего времени
        """
        current_period = self.get_current_period(moscow_time)
        config = self.schedule_config[current_period]
        return config.interval_minutes if config.enabled else 0
    
    def get_max_matches_for_period(self, moscow_time: Optional[datetime] = None) -> int:
        """
        Максимальное количество матчей для отправки в текущий период
        """
        current_period = self.get_current_period(moscow_time)
        config = self.schedule_config[current_period]
        return config.max_matches_per_message
    
    def calculate_daily_schedule(self, date: Optional[datetime] = None) -> List[Dict]:
        """
        Расчет расписания на день
        """
        if date is None:
            date = datetime.now(self.moscow_tz).replace(hour=0, minute=0, second=0, microsecond=0)
        
        daily_schedule = []
        current_time = date
        
        while current_time.date() == date.date():
            period = self.get_current_period(current_time)
            config = self.schedule_config[period]
            
            if config.enabled:
                daily_schedule.append({
                    'time': current_time.strftime('%H:%M'),
                    'period': period.value,
                    'interval': config.interval_minutes,
                    'max_matches': config.max_matches_per_message,
                    'description': config.description
                })
                
                # Следующий запуск
                next_time = current_time.replace(minute=current_time.minute + config.interval_minutes)
                if next_time.minute >= 60:
                    next_time = next_time.replace(hour=next_time.hour + 1, minute=next_time.minute - 60)
                current_time = next_time
            else:
                # Переходим к следующему периоду
                if period == ActivityPeriod.NIGHT_SLEEP:
                    current_time = current_time.replace(hour=7, minute=0)
                else:
                    current_time = current_time.replace(minute=current_time.minute + 60)
        
        return daily_schedule
    
    def calculate_monthly_cost_optimized(self, price_per_1k_tokens: float = 0.01) -> Dict:
        """
        Расчет оптимизированной месячной стоимости
        """
        # Расчет циклов по периодам
        daily_cycles_by_period = {
            ActivityPeriod.NIGHT_SLEEP: 0,      # Отключено
            ActivityPeriod.MORNING_LOW: 2.5,    # 5 часов ÷ 2 часа = 2.5 циклов
            ActivityPeriod.AFTERNOON_HIGH: 6,   # 6 часов ÷ 1 час = 6 циклов
            ActivityPeriod.EVENING_PEAK: 10,    # 5 часов ÷ 0.5 часа = 10 циклов
            ActivityPeriod.LATE_EVENING: 0.67   # 1 час ÷ 1.5 часа = 0.67 циклов
        }
        
        total_daily_cycles = sum(daily_cycles_by_period.values())
        monthly_cycles = total_daily_cycles * 30
        
        # Стоимость
        tokens_per_cycle = 268 * 1650  # 442,200 токенов
        cost_per_cycle = (tokens_per_cycle / 1000) * price_per_1k_tokens
        monthly_cost = monthly_cycles * cost_per_cycle
        
        # Сравнение с постоянным режимом
        constant_cycles_per_month = (30 * 24 * 60) // 45  # 960 циклов
        constant_monthly_cost = constant_cycles_per_month * cost_per_cycle
        savings = constant_monthly_cost - monthly_cost
        savings_percent = (savings / constant_monthly_cost) * 100
        
        return {
            'optimized_schedule': {
                'daily_cycles': round(total_daily_cycles, 2),
                'monthly_cycles': round(monthly_cycles, 2),
                'monthly_cost': round(monthly_cost, 2),
                'cost_per_cycle': round(cost_per_cycle, 2),
                'cost_per_analysis': round(cost_per_cycle / 268, 4)
            },
            'constant_schedule': {
                'monthly_cycles': constant_cycles_per_month,
                'monthly_cost': round(constant_monthly_cost, 2)
            },
            'savings': {
                'amount': round(savings, 2),
                'percent': round(savings_percent, 2)
            },
            'period_breakdown': daily_cycles_by_period
        }
    
    def get_user_experience_optimization(self) -> Dict[str, List[str]]:
        """
        Оптимизация пользовательского опыта
        """
        return {
            'anti_spam_measures': [
                'Ночью сообщения отключены (00:00-07:00)',
                'Утром редкие обновления (каждые 2 часа)',
                'Максимум 10 матчей в одном сообщении',
                'Группировка по важности матчей',
                'Краткие уведомления вместо длинных отчетов'
            ],
            'engagement_optimization': [
                'Пик активности вечером (каждые 30 минут)',
                'Качественные матчи днем (каждый час)',
                'Персонализация по времени активности',
                'Возможность настройки частоты пользователем',
                'Важные матчи отправляются вне расписания'
            ],
            'retention_strategies': [
                'Избежание спама через умное расписание',
                'Качество > количество сообщений',
                'Учет психологии беттинга (не поощряем лудоманию)',
                'Фокус на value opportunities, а не на частоте',
                'Образовательный контент между анализами'
            ]
        }
    
    def suggest_user_settings_tiers(self) -> Dict[str, Dict]:
        """
        Предложение уровней настроек для разных типов пользователей
        """
        return {
            'conservative': {
                'name': 'Консервативный',
                'description': 'Для осторожных беттеров',
                'schedule': {
                    'morning': 'Отключено',
                    'afternoon': 'Каждые 3 часа (только топ-матчи)',
                    'evening': 'Каждые 2 часа (лучшие возможности)',
                    'night': 'Отключено'
                },
                'max_matches': 3,
                'focus': 'Только высокое value, низкий риск'
            },
            'balanced': {
                'name': 'Сбалансированный',
                'description': 'Для умеренных беттеров',
                'schedule': {
                    'morning': 'Каждые 2 часа',
                    'afternoon': 'Каждый час',
                    'evening': 'Каждые 45 минут',
                    'night': 'Отключено'
                },
                'max_matches': 6,
                'focus': 'Баланс value и частоты'
            },
            'active': {
                'name': 'Активный',
                'description': 'Для опытных беттеров',
                'schedule': {
                    'morning': 'Каждый час',
                    'afternoon': 'Каждые 30 минут',
                    'evening': 'Каждые 20 минут',
                    'night': 'Каждые 3 часа'
                },
                'max_matches': 10,
                'focus': 'Максимальное покрытие возможностей'
            }
        }
    
    def get_schedule_summary(self) -> str:
        """
        Получение краткого описания расписания
        """
        moscow_now = datetime.now(self.moscow_tz)
        current_period = self.get_current_period(moscow_now)
        current_config = self.schedule_config[current_period]
        
        summary = f"""
🕐 ТЕКУЩЕЕ ВРЕМЯ: {moscow_now.strftime('%H:%M')} (Москва)
📊 ТЕКУЩИЙ ПЕРИОД: {current_period.value}
⏱️ ИНТЕРВАЛ: {current_config.interval_minutes} минут
✅ СТАТУС: {'Включено' if current_config.enabled else 'Отключено'}
🎯 ОПИСАНИЕ: {current_config.description}
👥 АУДИТОРИЯ: {current_config.target_audience}
📨 Макс. матчей в сообщении: {current_config.max_matches_per_message}
"""
        return summary.strip()

# Глобальный планировщик
SMART_SCHEDULER = SmartScheduler()

def get_current_analysis_interval() -> int:
    """Получение текущего интервала анализа"""
    return SMART_SCHEDULER.get_optimal_interval()

def should_run_analysis_now() -> Tuple[bool, str]:
    """Проверка, нужно ли запускать анализ сейчас"""
    return SMART_SCHEDULER.should_run_analysis()

def get_max_matches_for_telegram() -> int:
    """Максимальное количество матчей для телеграм сообщения"""
    return SMART_SCHEDULER.get_max_matches_for_period()