"""
Главный модуль автоматизированного аналитика спортивных ставок
"""
import time
import schedule
import threading
import re
from typing import List, Dict, Any
from datetime import datetime

# Импорты модулей системы
from utils.logger import setup_logger, log_cycle_start, log_cycle_end, log_error
from scrapers.football_scraper import FootballScraper
from scrapers.tennis_scraper import TennisScraper
from scrapers.table_tennis_scraper import TableTennisScraper
from scrapers.handball_scraper import HandballScraper
from scrapers.sofascore_simple_quality import SofaScoreSimpleQuality
from scrapers.multi_source_aggregator import MultiSourceAggregator
from scrapers.manual_live_provider import ManualLiveProvider
from scrapers.demo_data_provider import demo_provider
from ai_analyzer.claude_analyzer import ClaudeAnalyzer
from telegram_bot.reporter import TelegramReporter

from config import (
    SOFASCORE_URLS, SCORES24_URLS, CYCLE_INTERVAL_MINUTES, RETRY_DELAY_SECONDS,
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
        # Инициализируем SofaScore скрапер для детальной статистики
        self.sofascore_scraper = SofaScoreSimpleQuality(self.logger)
        
        # Инициализируем мульти-источник агрегатор
        self.multi_source_aggregator = MultiSourceAggregator(self.logger)
        
        # Инициализируем ручной поставщик актуальных данных
        self.manual_provider = ManualLiveProvider(self.logger)
        
        self.scrapers = {
            'football': FootballScraper(self.logger),
            'tennis': TennisScraper(self.logger),
            'table_tennis': TableTennisScraper(self.logger),
            'handball': HandballScraper(self.logger)
        }
        
        self.claude_analyzer = ClaudeAnalyzer(self.logger)
        self.telegram_reporter = TelegramReporter(self.logger)
        
        self.logger.info("Автоматизированный аналитик спортивных ставок инициализирован")
    
    def _basic_filter_matches(self, matches: List[Dict[str, Any]], sport: str) -> List[Dict[str, Any]]:
        """
        Базовая фильтрация матчей когда основной скрапер недоступен
        """
        filtered = []
        
        for match in matches:
            # Базовые проверки
            if not match.get('team1') or not match.get('team2'):
                continue
            
            score = match.get('score', '0:0')
            
            # Проверяем что счет не ничейный для футбола и гандбола
            if sport in ['football', 'handball']:
                if ':' in score:
                    parts = score.split(':')
                    if len(parts) == 2 and parts[0].strip() == parts[1].strip():
                        continue  # Пропускаем ничьи
            
            # Проверяем качество данных
            data_quality = match.get('data_quality', 0.0)
            if data_quality >= 0.5:  # Минимальное качество данных
                filtered.append(match)
        
        return filtered
    
    def _manual_match_passes_filter(self, match: Dict[str, Any], scraper) -> bool:
        """
        Проверка ручного матча через фильтры скрапера
        """
        try:
            # Для ручных данных применяем более мягкие фильтры
            sport = match.get('sport', 'football')
            
            if sport == 'football':
                # Проверяем что счет не ничейный
                score = match.get('score', '0:0')
                if ':' in score:
                    parts = score.split(':')
                    if len(parts) == 2 and parts[0].strip() == parts[1].strip():
                        return False  # Ничья
                
                # Проверяем важность матча
                importance = match.get('importance', 'LOW')
                if importance in ['HIGH', 'MEDIUM']:
                    return True  # Важные матчи всегда пропускаем
                
                # Для низкоприоритетных проверяем время
                time_str = match.get('time', 'LIVE')
                if time_str in ['HT', 'FT']:
                    return True
                
                # Извлекаем минуту
                minute_match = re.search(r'(\d+)', time_str)
                if minute_match:
                    minute = int(minute_match.group(1))
                    return minute >= 15  # Минимум 15 минут
                
                return True  # По умолчанию пропускаем ручные данные
            
            return True  # Другие виды спорта пропускаем
            
        except Exception as e:
            self.logger.warning(f"Ошибка проверки ручного матча: {e}")
            return True  # По умолчанию пропускаем
    
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
        Сбор матчей по всем видам спорта с использованием мульти-источника
        """
        all_matches = []
        
        # Проверяем здоровье источников
        source_health = self.multi_source_aggregator.get_source_health()
        healthy_sources = [source for source, is_healthy in source_health.items() if is_healthy]
        self.logger.info(f"Доступные источники: {', '.join(healthy_sources)}")
        
        # Используем мульти-источник агрегатор как основной метод
        for sport, scraper in self.scrapers.items():
            try:
                self.logger.info(f"Сбор {sport} матчей (мульти-источник)...")
                
                # Получаем агрегированные матчи из всех источников
                try:
                    aggregated_matches = self.multi_source_aggregator.get_aggregated_matches(sport, 'basic_info')
                    
                    if aggregated_matches:
                        filtered_matches = scraper.filter_matches(aggregated_matches)
                        all_matches.extend(filtered_matches)
                        self.logger.info(f"Мульти-источник: найдено {len(filtered_matches)} подходящих {sport} матчей")
                    else:
                        self.logger.warning(f"Мульти-источник не вернул данные для {sport}")
                        
                except Exception as aggregator_error:
                    self.logger.warning(f"Мульти-источник {sport} не сработал: {aggregator_error}")
                    
                    # Fallback на основной SofaScore скрапер
                    try:
                        self.logger.info(f"Fallback на SofaScore для {sport}")
                        matches = scraper.get_live_matches("")
                        filtered_matches = scraper.filter_matches(matches)
                        all_matches.extend(filtered_matches)
                        self.logger.info(f"SofaScore fallback: найдено {len(filtered_matches)} подходящих {sport} матчей")
                    except Exception as sofascore_error:
                        self.logger.warning(f"SofaScore fallback {sport} не сработал: {sofascore_error}")
                
            except Exception as e:
                log_error(self.logger, e, f"Ошибка сбора {sport} матчей")
                continue
        
        # Если реальные скраперы не нашли матчи, используем актуальные ручные данные
        if not all_matches:
            self.logger.info("Реальные скраперы не нашли матчи, используем актуальные ручные данные")
            manual_matches = self.manual_provider.get_current_live_matches()
            
            # Фильтруем ручные данные через основные скраперы
            for match in manual_matches:
                sport = match.get('sport', 'football')
                scraper = self.scrapers.get(sport)
                
                if scraper:
                    # Проверяем матч через фильтры скрапера
                    if self._manual_match_passes_filter(match, scraper):
                        all_matches.append(match)
            
            self.logger.info(f"Добавлено {len(all_matches)} актуальных ручных матчей")
            
            # Если и ручные данные не прошли фильтры, используем демо
            if not all_matches:
                self.logger.info("Используем демонстрационные данные")
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
                # Используем SofaScore детальный сбор если доступен
                if hasattr(self, 'sofascore_scraper') and match_url.startswith('/'):
                    detailed_data = self.sofascore_scraper.get_detailed_match_data(match_url)
                else:
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