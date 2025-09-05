#!/usr/bin/env python3
"""
Демонстрационный запуск без браузера
"""
import sys
sys.path.append('.')

from utils.logger import setup_logger
from scrapers.demo_data_provider import demo_provider
from ai_analyzer.claude_analyzer import ClaudeAnalyzer
from telegram_bot.reporter import TelegramReporter

def demo_analysis_cycle():
    """
    Демонстрационный цикл анализа
    """
    logger = setup_logger('demo_analyzer')
    
    print('🎯 ДЕМОНСТРАЦИОННЫЙ ЦИКЛ АНАЛИЗА')
    print('='*60)
    
    # Получаем демо-данные
    print('📊 Генерация демонстрационных данных...')
    all_matches = []
    all_matches.extend(demo_provider.get_demo_football_matches())
    all_matches.extend(demo_provider.get_demo_tennis_matches())
    all_matches.extend(demo_provider.get_demo_handball_matches())
    
    print(f'Сгенерировано {len(all_matches)} демо-матчей')
    
    # Анализ с Claude AI
    print('\\n🤖 Анализ с Claude AI...')
    claude_analyzer = ClaudeAnalyzer(logger)
    analyzed_matches = claude_analyzer.analyze_multiple_matches(all_matches)
    
    print(f'Проанализировано {len(analyzed_matches)} матчей')
    
    # Выбор лучших рекомендаций
    print('\\n🎯 Выбор лучших рекомендаций...')
    best_matches = claude_analyzer.get_best_recommendations(analyzed_matches, 5)
    
    print(f'Выбрано {len(best_matches)} лучших рекомендаций')
    
    # Показываем данные для Claude
    print('\\n📋 ДАННЫЕ, ПЕРЕДАННЫЕ В CLAUDE AI:')
    print('-' * 50)
    
    for i, match in enumerate(best_matches, 1):
        sport = match.get('sport', 'unknown')
        
        if sport == 'football':
            print(f'\\n{i}. ⚽ ФУТБОЛ: {match["team1"]} - {match["team2"]}')
            print(f'   Счет: {match["score"]} ({match["time"]}) | {match["league"]}')
            
            if 'statistics' in match:
                stats = match['statistics']
                print(f'   xG: {stats.get("xG", {})}')
                print(f'   Владение: {stats.get("Владение мячом", {})}')
                print(f'   Удары в створ: {stats.get("Удары в створ", {})}')
            
            if 'prediction' in match:
                print(f'   Прогноз: {match["prediction"]}')
                
            if 'odds' in match:
                print(f'   Коэффициенты: {match["odds"]}')
                
            print(f'   ✨ Анализ Claude: {match.get("ai_analysis", "Анализ выполнен")}')
        
        elif sport == 'tennis':
            print(f'\\n{i}. 🎾 ТЕННИС: {match["player1"]} - {match["player2"]}')
            print(f'   Счет: {match["sets_score"]} ({match["current_set"]}) | {match["tournament"]}')
            
            if 'statistics' in match:
                stats = match['statistics']
                print(f'   Эйсы: {stats.get("Эйсы", {})}')
                print(f'   1-я подача: {stats.get("1-я подача", {})}')
            
            if 'rankings' in match:
                print(f'   Рейтинги: {match["rankings"]}')
                
            print(f'   ✨ Анализ Claude: {match.get("ai_analysis", "Анализ выполнен")}')
        
        elif sport == 'handball':
            print(f'\\n{i}. 🤾 ГАНДБОЛ: {match["team1"]} - {match["team2"]}')
            print(f'   Счет: {match["score"]} ({match["time"]}) | {match["league"]}')
            
            if 'totals_calculation' in match:
                totals = match['totals_calculation']
                print(f'   📈 Прогнозный тотал: {totals["predicted_total"]} голов')
                print(f'   🎯 Рекомендация: {totals["recommendation"]}')
                print(f'   📊 Темп: {totals["tempo"]} ({totals["reasoning"]})')
                
            print(f'   ✨ Анализ Claude: {match.get("ai_analysis", "Анализ выполнен")}')
    
    # Формирование отчета для Telegram
    print('\\n📱 Формирование отчета для Telegram...')
    telegram_reporter = TelegramReporter(logger)
    
    # Показываем как будет выглядеть отчет
    report_text = telegram_reporter._build_report(best_matches)
    print('\\n📋 ИТОГОВЫЙ ОТЧЕТ ДЛЯ TELEGRAM:')
    print('-' * 50)
    print(report_text[:1000] + '...' if len(report_text) > 1000 else report_text)
    
    print('\\n✅ ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА!')
    print('Система готова к работе с реальными данными scores24.live')

if __name__ == '__main__':
    demo_analysis_cycle()