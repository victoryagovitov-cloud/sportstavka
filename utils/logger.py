"""
Модуль для логирования
"""
import logging
import os
from datetime import datetime
from config import LOG_FILE, LOG_LEVEL

def setup_logger(name: str = 'sports_analyzer') -> logging.Logger:
    """
    Настройка логгера для приложения
    """
    # Создаем директорию для логов если не существует
    os.makedirs('logs', exist_ok=True)
    
    # Создаем логгер
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL))
    
    # Очищаем существующие обработчики
    logger.handlers.clear()
    
    # Форматтер для логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Файловый обработчик
    file_handler = logging.FileHandler(f'logs/{LOG_FILE}', encoding='utf-8')
    file_handler.setLevel(getattr(logging, LOG_LEVEL))
    file_handler.setFormatter(formatter)
    
    # Консольный обработчик
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, LOG_LEVEL))
    console_handler.setFormatter(formatter)
    
    # Добавляем обработчики к логгеру
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def log_error(logger: logging.Logger, error: Exception, context: str = ""):
    """
    Логирование ошибок с контекстом
    """
    error_msg = f"{context}: {str(error)}" if context else str(error)
    logger.error(error_msg, exc_info=True)

def log_cycle_start(logger: logging.Logger):
    """
    Логирование начала нового цикла анализа
    """
    logger.info("="*50)
    logger.info(f"НАЧАЛО НОВОГО ЦИКЛА АНАЛИЗА: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*50)

def log_cycle_end(logger: logging.Logger, success: bool = True):
    """
    Логирование окончания цикла анализа
    """
    status = "УСПЕШНО" if success else "С ОШИБКАМИ"
    logger.info(f"ЦИКЛ АНАЛИЗА ЗАВЕРШЕН {status}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*50)