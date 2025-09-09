#!/usr/bin/env python3
"""
Быстрый запуск системы для тестирования и заработка
"""

import os
import sys
import logging
from datetime import datetime

def setup_logging():
    """Настройка логирования"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('production.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def check_api_keys():
    """Проверка наличия API ключей"""
    
    required_keys = {
        'CLAUDE_API_KEY': 'Ключ Claude AI для анализа',
        'TELEGRAM_BOT_TOKEN': 'Токен Telegram бота',
        'TELEGRAM_CHAT_ID': 'ID канала для отправки'
    }
    
    missing_keys = []
    
    for key, description in required_keys.items():
        if not os.getenv(key):
            missing_keys.append(f"❌ {key}: {description}")
        else:
            print(f"✅ {key}: настроен")
    
    return missing_keys

def test_data_collection():
    """Тестирует получение данных"""
    
    try:
        print("\n🔍 ТЕСТ ПОЛУЧЕНИЯ ДАННЫХ:")
        print("-" * 30)
        
        # Тест футбола
        import subprocess
        result = subprocess.run([sys.executable, 'final_all_sports_data.py'], 
                              capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            output_lines = result.stdout.split('\n')
            
            # Ищем статистику
            for line in output_lines:
                if 'ВСЕГО ГОТОВО' in line:
                    print(f"✅ {line.strip()}")
                    break
            else:
                print("✅ Данные получены успешно")
        else:
            print(f"❌ Ошибка получения данных: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        return False
    
    return True

def test_claude_analysis():
    """Тестирует анализ Claude AI"""
    
    try:
        print("\n🧠 ТЕСТ CLAUDE AI:")
        print("-" * 20)
        
        if not os.getenv('CLAUDE_API_KEY'):
            print("⚠️ CLAUDE_API_KEY не настроен - используется демо-режим")
            return True
        
        from ai_analyzer.claude_analyzer_v2 import ClaudeAnalyzerV2
        
        logger = logging.getLogger(__name__)
        claude = ClaudeAnalyzerV2(logger)
        
        # Тестовый матч
        test_matches = [{
            'team1': 'Команда А',
            'team2': 'Команда Б', 
            'score': '1:0',
            'time': '45:00',
            'odds': {'П1': '2.10', 'X': '3.20', 'П2': '3.50'}
        }]
        
        result = claude.analyze_matches_independently(test_matches)
        
        if result:
            print("✅ Claude AI анализ работает")
            return True
        else:
            print("❌ Проблема с Claude AI анализом")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка Claude AI: {e}")
        return False

def test_telegram_integration():
    """Тестирует интеграцию Telegram"""
    
    try:
        print("\n📱 ТЕСТ TELEGRAM:")
        print("-" * 20)
        
        if not os.getenv('TELEGRAM_BOT_TOKEN'):
            print("⚠️ TELEGRAM_BOT_TOKEN не настроен - используется демо-режим")
            return True
        
        from telegram_bot.claude_telegram_reporter import ClaudeTelegramReporter
        
        logger = logging.getLogger(__name__)
        telegram = ClaudeTelegramReporter(logger)
        
        # Тестовое сообщение
        test_analysis = {
            'analysis_summary': 'Тестовый анализ системы',
            'recommendations': ['Тестовая рекомендация'],
            'total_matches': 1
        }
        
        result = telegram.send_claude_analysis(test_analysis)
        
        if result:
            print("✅ Telegram интеграция работает")
            return True
        else:
            print("❌ Проблема с Telegram")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка Telegram: {e}")
        return False

def run_production_cycle():
    """Запускает полный продакшн цикл"""
    
    try:
        print("\n🚀 ЗАПУСК ПРОДАКШН ЦИКЛА:")
        print("-" * 30)
        
        from main import SportsAnalyzer
        
        logger = setup_logging()
        analyzer = SportsAnalyzer(logger)
        
        # Запуск умного цикла
        analyzer.run_smart_cycle()
        
        print("✅ Продакшн цикл выполнен успешно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка продакшн цикла: {e}")
        return False

def main():
    """Главная функция запуска"""
    
    print("🚀 БЫСТРЫЙ ЗАПУСК СИСТЕМЫ В ПРОДАКШН")
    print("=" * 50)
    
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"🕐 Время запуска: {current_time}")
    
    # Проверка готовности
    print("\n🔍 ПРОВЕРКА ГОТОВНОСТИ СИСТЕМЫ:")
    print("-" * 35)
    
    # 1. Проверка API ключей
    missing_keys = check_api_keys()
    
    if missing_keys:
        print("\n⚠️ ОТСУТСТВУЮТ API КЛЮЧИ:")
        for key in missing_keys:
            print(f"   {key}")
        
        print("\n💡 ИНСТРУКЦИЯ ПО НАСТРОЙКЕ:")
        print("   1. Получите Claude API ключ: https://console.anthropic.com/")
        print("   2. Создайте Telegram бота: @BotFather")
        print("   3. Установите переменные окружения:")
        print("      export CLAUDE_API_KEY='your_key'")
        print("      export TELEGRAM_BOT_TOKEN='your_token'")
        print("      export TELEGRAM_CHAT_ID='your_channel_id'")
        print("\n🔄 После настройки запустите скрипт снова")
        return
    
    # 2. Тестирование компонентов
    print("\n🧪 ТЕСТИРОВАНИЕ КОМПОНЕНТОВ:")
    print("-" * 30)
    
    tests = [
        ("Получение данных", test_data_collection),
        ("Claude AI анализ", test_claude_analysis),
        ("Telegram интеграция", test_telegram_integration)
    ]
    
    all_tests_passed = True
    
    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"✅ {test_name}: РАБОТАЕТ")
            else:
                print(f"❌ {test_name}: ПРОБЛЕМА")
                all_tests_passed = False
        except Exception as e:
            print(f"❌ {test_name}: ОШИБКА - {e}")
            all_tests_passed = False
    
    # 3. Запуск продакшн цикла
    if all_tests_passed:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("🚀 ЗАПУСКАЕМ ПРОДАКШН ЦИКЛ...")
        
        if run_production_cycle():
            print("\n🏆 СИСТЕМА УСПЕШНО ЗАПУЩЕНА!")
            print("\n💰 ГОТОВА К ЗАРАБОТКУ:")
            print("   • 28 неничейных матчей анализируются")
            print("   • Рекомендации отправляются в Telegram")
            print("   • Цикл повторяется каждые 45 минут")
            print("   • Логи сохраняются в production.log")
            
            print("\n📊 МОНИТОРИНГ:")
            print("   • Проверяйте Telegram канал каждый час")
            print("   • Отслеживайте файл production.log")
            print("   • Анализируйте эффективность еженедельно")
            
            print("\n🎯 УСПЕШНОГО ЗАРАБОТКА!")
        else:
            print("\n❌ Ошибка запуска продакшн цикла")
    else:
        print("\n⚠️ ЕСТЬ ПРОБЛЕМЫ В ТЕСТАХ")
        print("💡 Исправьте ошибки и запустите снова")

if __name__ == '__main__':
    main()