#!/usr/bin/env python3
"""
Скрипт для запуска автоматизированного аналитика спортивных ставок
"""
import sys
import os
import argparse

# Добавляем текущую директорию в путь Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import SportsAnalyzer

def main():
    parser = argparse.ArgumentParser(description='Автоматизированный аналитик спортивных ставок')
    parser.add_argument('--test', action='store_true', 
                       help='Запустить один тестовый цикл анализа')
    parser.add_argument('--daemon', action='store_true',
                       help='Запустить в режиме демона (непрерывно)')
    
    args = parser.parse_args()
    
    analyzer = SportsAnalyzer()
    
    try:
        if args.test:
            print("Запуск тестового цикла...")
            analyzer.run_single_cycle()
            print("Тестовый цикл завершен")
        else:
            print("Запуск автоматизированного аналитика...")
            print("Для остановки нажмите Ctrl+C")
            analyzer.start()
    except KeyboardInterrupt:
        print("\nПолучен сигнал остановки...")
    finally:
        analyzer.stop()
        print("Анализатор остановлен")

if __name__ == "__main__":
    main()