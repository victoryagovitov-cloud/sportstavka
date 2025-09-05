"""
Главный модуль автоматизированного аналитика спортивных ставок
"""
import time
import schedule
import threading
from typing import List, Dict, Any
from datetime import datetime

# Импорты модулей системы
from utils.logger import setup_logger, log_cycle_start, log_cycle_end, log_error
from scrapers.football_scraper import FootballScraper
from scrapers.tennis_scraper import TennisScraper
from scrapers.table_tennis_scraper import TableTennisScraper
from scrapers.handball_scraper import HandballScraper
from scrapers.demo_data_provider import demo_provider
from ai_analyzer.claude_analyzer import ClaudeAnalyzer
from telegram_bot.reporter import TelegramReporter

from config import (
    SCORES24_URLS, CYCLE_INTERVAL_MINUTES, RETRY_DELAY_SECONDS,
    MAX_RECOMMENDATIONS
)

class SportsAnalyzer:
    """
    Главный класс автоматизированного аналитика спортивных ставок
    """
    
    def __init__(self):
        self.logger = setup_logger('SportsAnalyzer')
        self.running = False
        
        # Инициализация компонентов
        self.scrapers = {
            'football': FootballScraper(self.logger),
            'tennis': TennisScraper(self.logger),
            'table_tennis': TableTennisScraper(self.logger),
            'handball': HandballScraper(self.logger)
        }
        
        self.claude_analyzer = ClaudeAnalyzer(self.logger)
        self.telegram_reporter = TelegramReporter(self.logger)
        
        self.logger.info("Автоматизированный аналитик спортивных ставок инициализирован")
    
    def start(self):
        """
        Запуск автоматизированного анализа
        """
        self.logger.info("Запуск автоматизированного аналитика...")
        
        # Тестируем соединения
        if not self._test_connections():
            self.logger.error("Критические ошибки подключений. Остановка.")
            return
        
        # Настраиваем планировщик
        schedule.every(CYCLE_INTERVAL_MINUTES).minutes.do(self.run_analysis_cycle)
        
        # Запускаем первый цикл сразу
        self.run_analysis_cycle()
        
        # Основной цикл
        self.running = True
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Проверяем каждую минуту
            except KeyboardInterrupt:
                self.logger.info("Получен сигнал остановки")
                self.stop()
            except Exception as e:
                log_error(self.logger, e, "Ошибка в основном цикле")
                time.sleep(RETRY_DELAY_SECONDS)
    
    def stop(self):
        """
        Остановка анализатора
        """
        self.logger.info("Остановка автоматизированного аналитика...")
        self.running = False
        
        # Закрываем все драйверы
        for scraper in self.scrapers.values():
            try:
                scraper.close_driver()
            except:
                pass
    
    def run_analysis_cycle(self):
        """
        Выполнение одного цикла анализа
        """
        log_cycle_start(self.logger)
        
        try:
            # 1. Сбор данных по всем видам спорта
            all_matches = self._collect_all_matches()
            
            if not all_matches:
                self.logger.warning("Не найдено подходящих матчей")
                self.telegram_reporter.send_report([])
                log_cycle_end(self.logger, success=True)
                return
            
            # 2. Детальный сбор данных для отобранных матчей
            detailed_matches = self._collect_detailed_data(all_matches)
            
            # 3. Анализ с помощью Claude AI
            analyzed_matches = self.claude_analyzer.analyze_multiple_matches(detailed_matches)
            
            # 4. Выбор лучших рекомендаций
            best_recommendations = self.claude_analyzer.get_best_recommendations(
                analyzed_matches, MAX_RECOMMENDATIONS
            )
            
            # 5. Публикация отчета в Telegram
            success = self.telegram_reporter.send_report(best_recommendations)
            
            if success:
                self.logger.info(f"Цикл завершен успешно. Опубликовано {len(best_recommendations)} рекомендаций")
                log_cycle_end(self.logger, success=True)
            else:
                self.logger.error("Ошибка публикации отчета")
                log_cycle_end(self.logger, success=False)
                
        except Exception as e:
            log_error(self.logger, e, "Критическая ошибка в цикле анализа")
            log_cycle_end(self.logger, success=False)
    
    def _test_connections(self) -> bool:
        """
        Тестирование всех соединений
        """
        self.logger.info("Тестирование соединений...")
        
        # Тестируем Telegram
        if not self.telegram_reporter.test_connection():
            self.logger.error("Ошибка подключения к Telegram API")
            return False
        
        self.logger.info("Все соединения работают корректно")
        return True
    
    def _collect_all_matches(self) -> List[Dict[str, Any]]:
        """
        Сбор матчей по всем видам спорта
        """
        all_matches = []
        
        # Сначала пробуем реальные скраперы
        for sport, scraper in self.scrapers.items():
            try:
                self.logger.info(f"Сбор {sport} матчей...")
                url = SCORES24_URLS.get(sport)
                if not url:
                    continue
                
                # Получаем live матчи с таймаутом
                try:
                    matches = scraper.get_live_matches(url)
                    filtered_matches = scraper.filter_matches(matches)
                    all_matches.extend(filtered_matches)
                    self.logger.info(f"Найдено {len(filtered_matches)} подходящих {sport} матчей")
                except Exception as scraper_error:
                    self.logger.warning(f"Скрапер {sport} не сработал: {scraper_error}")
                    continue
                
            except Exception as e:
                log_error(self.logger, e, f"Ошибка сбора {sport} матчей")
                continue
        
        # Если реальные скраперы не нашли матчи, используем демо-данные для тестирования
        if not all_matches:
            self.logger.info("Реальные матчи не найдены, используем демонстрационные данные")
            demo_matches = self._get_demo_matches()
            all_matches.extend(demo_matches)
        
        self.logger.info(f"Всего найдено {len(all_matches)} подходящих матчей")
        return all_matches
    
    def _get_demo_matches(self) -> List[Dict[str, Any]]:
        """
        Получение демонстрационных данных
        """
        demo_matches = []
        
        # Добавляем демо-матчи разных видов спорта
        demo_matches.extend(demo_provider.get_demo_football_matches())
        demo_matches.extend(demo_provider.get_demo_tennis_matches())
        demo_matches.extend(demo_provider.get_demo_handball_matches())
        
        self.logger.info(f"Сгенерировано {len(demo_matches)} демонстрационных матчей")
        return demo_matches
    
    def _collect_detailed_data(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Сбор детальных данных для отобранных матчей
        """
        detailed_matches = []
        
        for match in matches:
            try:
                sport = match.get('sport')
                match_url = match.get('url')
                
                if not sport or not match_url:
                    continue
                
                scraper = self.scrapers.get(sport)
                if not scraper:
                    continue
                
                self.logger.info(f"Сбор детальных данных для {sport} матча: {match_url}")
                
                # Собираем подробные данные
                detailed_data = scraper.collect_match_data(match_url)
                
                # Объединяем с базовой информацией
                detailed_data.update(match)
                
                detailed_matches.append(detailed_data)
                
            except Exception as e:
                log_error(self.logger, e, f"Ошибка сбора детальных данных для матча")
                continue
        
        self.logger.info(f"Собраны детальные данные для {len(detailed_matches)} матчей")
        return detailed_matches
    
    def run_single_cycle(self):
        """
        Запуск одного цикла анализа (для тестирования)
        """
        self.logger.info("Запуск тестового цикла анализа...")
        self.run_analysis_cycle()

def main():
    """
    Главная функция
    """
    analyzer = SportsAnalyzer()
    
    try:
        analyzer.start()
    except KeyboardInterrupt:
        print("\nПолучен сигнал остановки...")
    finally:
        analyzer.stop()
        print("Анализатор остановлен")

if __name__ == "__main__":
    main()