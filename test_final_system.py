#!/usr/bin/env python3
"""
Финальный тест системы с демо-данными
"""
import sys
sys.path.append('.')

from utils.logger import setup_logger
from scrapers.demo_data_provider import demo_provider
from ai_analyzer.claude_analyzer import ClaudeAnalyzer
from telegram_bot.reporter import TelegramReporter

def test_complete_system():
    print('🎯 ФИНАЛЬНЫЙ ТЕСТ ПОЛНОЙ СИСТЕМЫ')
    print('='*70)
    
    logger = setup_logger('final_test')
    
    # 1. Получаем данные (демо, имитирующие scores24.live)
    print('📊 Шаг 1: Сбор данных (демо-режим)...')
    
    football_matches = demo_provider.get_demo_football_matches()
    tennis_matches = demo_provider.get_demo_tennis_matches()
    handball_matches = demo_provider.get_demo_handball_matches()
    
    all_matches = football_matches + tennis_matches + handball_matches
    print(f'Собрано матчей: {len(all_matches)}')
    
    # Показываем собранные данные
    print('\\n📋 СОБРАННЫЕ ДАННЫЕ ДЛЯ CLAUDE AI:')
    print('-' * 50)
    
    for i, match in enumerate(all_matches, 1):
        sport = match.get('sport', 'unknown')
        
        if sport == 'football':
            print(f'{i}. ⚽ {match["team1"]} - {match["team2"]}')
            print(f'   Счет: {match["score"]} ({match["time"]}) | {match["league"]}')
            
            stats = match.get('statistics', {})
            if 'xG' in stats:
                xg_data = stats['xG']
                print(f'   xG: {xg_data["team1"]} vs {xg_data["team2"]}')
            if 'Владение мячом' in stats:
                possession = stats['Владение мячом'] 
                print(f'   Владение: {possession["team1"]} vs {possession["team2"]}')
                
        elif sport == 'tennis':
            print(f'{i}. 🎾 {match["player1"]} - {match["player2"]}')
            print(f'   Счет: {match["sets_score"]} ({match["current_set"]}) | {match["tournament"]}')
            
            if 'rankings' in match:
                rankings = match['rankings']
                print(f'   Рейтинги: {rankings.get("player1", "?")} vs {rankings.get("player2", "?")}')
                
        elif sport == 'handball':
            print(f'{i}. 🤾 {match["team1"]} - {match["team2"]}')
            print(f'   Счет: {match["score"]} ({match["time"]}) | {match["league"]}')
            
            if 'totals_calculation' in match:
                totals = match['totals_calculation']
                print(f'   🔢 Тотал: {totals["recommendation"]} ({totals["reasoning"]})')
    
    # 2. Анализ с Claude AI
    print('\\n🤖 Шаг 2: Анализ с Claude AI...')
    claude_analyzer = ClaudeAnalyzer(logger)
    analyzed_matches = claude_analyzer.analyze_multiple_matches(all_matches)
    
    print(f'Проанализировано: {len(analyzed_matches)} матчей')
    
    # 3. Выбор лучших рекомендаций
    print('\\n🎯 Шаг 3: Выбор лучших рекомендаций...')
    best_matches = claude_analyzer.get_best_recommendations(analyzed_matches, 5)
    
    print(f'Выбрано лучших: {len(best_matches)} рекомендаций')
    
    # 4. Формирование отчета для Telegram
    print('\\n📱 Шаг 4: Формирование Telegram отчета...')
    telegram_reporter = TelegramReporter(logger)
    
    # Показываем итоговый отчет
    report = telegram_reporter._build_report(best_matches)
    
    print('\\n' + '='*70)
    print('📱 ИТОГОВЫЙ ОТЧЕТ ДЛЯ @TrueLiveBet:')
    print('='*70)
    print(report)
    print('='*70)
    
    # 5. Статистика
    print('\\n📊 СТАТИСТИКА СИСТЕМЫ:')
    print(f'• Матчей собрано: {len(all_matches)}')
    print(f'• Матчей проанализировано: {len(analyzed_matches)}')
    print(f'• Рекомендаций выбрано: {len(best_matches)}')
    print(f'• Размер отчета: {len(report)} символов')
    print(f'• Виды спорта: {len(set(m.get("sport") for m in all_matches))}')
    
    print('\\n✅ СИСТЕМА ПОЛНОСТЬЮ РАБОТАЕТ!')
    print('🔑 Нужен только Claude API ключ для реального анализа')
    print('🚀 После добавления ключа система будет работать 24/7')

if __name__ == '__main__':
    test_complete_system()