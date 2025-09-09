"""
Telegram репортер для результатов анализа Claude AI (Вариант 2)
"""

import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from telegram_bot.custom_message_formatter import CustomTelegramFormatter

try:
    from telegram import Bot
    from telegram.error import TelegramError
except ImportError:
    Bot = None
    TelegramError = Exception

class ClaudeTelegramReporter:
    """
    Репортер для отправки анализа Claude AI в телеграм каналы
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Настройки телеграм бота
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.channel_id = os.getenv('TELEGRAM_CHANNEL_ID')
        
        # Инициализация кастомного форматтера
        self.custom_formatter = CustomTelegramFormatter(logger)
        
        # Инициализация бота
        self.bot = None
        if self.bot_token and Bot:
            try:
                self.bot = Bot(token=self.bot_token)
                self.logger.info("✅ Telegram бот инициализирован")
            except Exception as e:
                self.logger.error(f"❌ Ошибка инициализации Telegram бота: {e}")
        else:
            self.logger.warning("⚠️ TELEGRAM_BOT_TOKEN не установлен или python-telegram-bot не установлен")
        
        # Настройки сообщений
        self.message_config = {
            'max_message_length': 4096,  # Лимит Telegram
            'split_long_messages': True,
            'add_timestamps': True,
            'use_markdown': True
        }
        
        # Статистика отправки
        self.send_stats = {
            'total_messages': 0,
            'successful_sends': 0,
            'failed_sends': 0,
            'total_characters': 0
        }
    
    def send_claude_analysis(self, claude_analysis: str, period: str, 
                           matches_count: int, total_available: int) -> bool:
        """
        Отправка анализа Claude AI в телеграм канал
        """
        if not claude_analysis:
            self.logger.warning("Пустой анализ Claude AI - отправка пропущена")
            return False
        
        try:
            # Форматируем сообщение для телеграм
            formatted_message = self._format_message_for_telegram(
                claude_analysis, period, matches_count, total_available
            )
            
            # Отправляем сообщение
            success = self._send_telegram_message(formatted_message)
            
            if success:
                self.logger.info(f"📨 Анализ Claude AI отправлен в телеграм канал")
                self._update_send_stats(formatted_message, success=True)
            else:
                self.logger.error(f"❌ Не удалось отправить анализ в телеграм")
                self._update_send_stats(formatted_message, success=False)
            
            return success
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки в телеграм: {e}")
            return False
    
    def _format_message_for_telegram(self, claude_analysis: str, period: str,
                                   matches_count: int, total_available: int) -> str:
        """
        Форматирование сообщения Claude AI для телеграм канала
        """
        # Определяем эмодзи для периода
        period_emojis = {
            'morning_low': '🌅',
            'afternoon_high': '☀️',
            'evening_peak': '🌆', 
            'late_evening': '🌙'
        }
        
        period_emoji = period_emojis.get(period, '📊')
        current_time = datetime.now().strftime('%H:%M МСК')
        
        # Заголовок
        header = f"""{period_emoji} АНАЛИЗ CLAUDE AI

📊 Матчей: {matches_count} из {total_available} доступных
⏰ Время: {current_time}
🎯 Независимый анализ букмекерских коэффициентов

{'='*40}"""
        
        # Основной контент (анализ Claude AI)
        main_content = claude_analysis
        
        # Подвал
        footer = f"""{'='*40}

🤖 Анализ: Claude AI (независимый поиск статистики)
📊 Источник коэффициентов: MarathonBet
🛡️ Философия: консервативные ставки
💡 Принцип: лучше пропустить, чем рисковать

🔔 Канал: @your_betting_channel"""
        
        # Объединяем части
        full_message = f"{header}\n\n{main_content}\n\n{footer}"
        
        # Проверяем длину и обрезаем при необходимости
        if len(full_message) > self.message_config['max_message_length']:
            # Обрезаем основной контент, сохраняя заголовок и подвал
            available_length = (self.message_config['max_message_length'] - 
                              len(header) - len(footer) - 20)  # 20 символов запас
            
            truncated_content = main_content[:available_length] + "\n\n[...анализ обрезан...]"
            full_message = f"{header}\n\n{truncated_content}\n\n{footer}"
            
            self.logger.warning(f"⚠️ Сообщение обрезано до {len(full_message)} символов")
        
        return full_message
    
    def _send_telegram_message(self, message: str) -> bool:
        """
        Отправка сообщения в телеграм канал
        """
        if not self.bot or not self.channel_id:
            # Демо режим - логируем сообщение
            self.logger.info("🎭 ДЕМО РЕЖИМ - Сообщение для телеграм канала:")
            self.logger.info("="*60)
            self.logger.info(message)
            self.logger.info("="*60)
            return True
        
        try:
            # Отправляем реальное сообщение
            self.bot.send_message(
                chat_id=self.channel_id,
                text=message,
                parse_mode='HTML' if self.message_config['use_markdown'] else None,
                disable_web_page_preview=True
            )
            
            return True
            
        except TelegramError as e:
            self.logger.error(f"❌ Ошибка Telegram API: {e}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки сообщения: {e}")
            return False
    
    def _update_send_stats(self, message: str, success: bool):
        """Обновление статистики отправки"""
        self.send_stats['total_messages'] += 1
        self.send_stats['total_characters'] += len(message)
        
        if success:
            self.send_stats['successful_sends'] += 1
        else:
            self.send_stats['failed_sends'] += 1
    
    def get_send_stats(self) -> Dict[str, Any]:
        """Получение статистики отправки"""
        success_rate = 0.0
        if self.send_stats['total_messages'] > 0:
            success_rate = (self.send_stats['successful_sends'] / 
                          self.send_stats['total_messages']) * 100
        
        avg_message_length = 0
        if self.send_stats['total_messages'] > 0:
            avg_message_length = (self.send_stats['total_characters'] / 
                                self.send_stats['total_messages'])
        
        return {
            'total_messages': self.send_stats['total_messages'],
            'successful_sends': self.send_stats['successful_sends'],
            'failed_sends': self.send_stats['failed_sends'],
            'success_rate': round(success_rate, 2),
            'total_characters': self.send_stats['total_characters'],
            'average_message_length': round(avg_message_length, 2),
            'bot_available': self.bot is not None
        }
    
    def test_telegram_connection(self) -> bool:
        """Тестирование соединения с телеграм"""
        if not self.bot:
            self.logger.info("🎭 Telegram бот в демо режиме")
            return True
        
        try:
            # Тестовое сообщение
            self.bot.send_message(
                chat_id=self.channel_id,
                text="🧪 Тест соединения с каналом"
            )
            
            self.logger.info("✅ Соединение с Telegram работает")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка соединения с Telegram: {e}")
            return False

# Глобальная функция для создания репортера
def create_claude_telegram_reporter(logger: Optional[logging.Logger] = None) -> ClaudeTelegramReporter:
    """Создание телеграм репортера для Claude AI"""
    return ClaudeTelegramReporter(logger)