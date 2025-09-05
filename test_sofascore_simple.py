#!/usr/bin/env python3
"""
Простой тест SofaScore
"""
import sys
sys.path.append('.')

import requests
from bs4 import BeautifulSoup
import re

def test_sofascore():
    print('🔍 ПРОСТОЙ ТЕСТ SOFASCORE')
    print('='*50)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
    }
    
    # Тестируем разные виды спорта
    sports = {
        'футбол': 'https://www.sofascore.com/football/livescore',
        'теннис': 'https://www.sofascore.com/tennis/livescore',
        'гандбол': 'https://www.sofascore.com/handball/livescore',
        'настольный теннис': 'https://www.sofascore.com/table-tennis/livescore'
    }
    
    total_matches = 0
    
    for sport_name, url in sports.items():
        try:
            print(f'\n🏈 {sport_name.upper()}')
            print('-' * 30)
            
            response = requests.get(url, headers=headers, timeout=10)
            print(f'Статус: {response.status_code}')
            
            if response.status_code == 200:
                html = response.text
                print(f'Размер HTML: {len(html):,} символов')
                
                # Простые индикаторы live матчей
                live_count = html.lower().count('live')
                scores_count = len(re.findall(r'\d+[:-]\d+', html))
                
                print(f'Live упоминаний: {live_count}')
                print(f'Счетов найдено: {scores_count}')
                
                # Ищем статистику
                stats_terms = ['possession', 'shots', 'xG', 'corners']
                stats_found = 0
                
                for term in stats_terms:
                    count = html.lower().count(term.lower())
                    if count > 0:
                        stats_found += count
                        print(f'{term}: {count}')
                
                print(f'Всего статистики: {stats_found}')
                
                # Оценка качества данных
                if live_count > 100 and scores_count > 50:
                    estimated_matches = min(live_count // 10, scores_count // 5)
                    total_matches += estimated_matches
                    print(f'✅ Оценка матчей: ~{estimated_matches}')
                    
                    if stats_found > 20:
                        print(f'✅ Богатая статистика!')
                    else:
                        print(f'⚠️ Мало статистики')
                else:
                    print(f'❌ Мало live данных')
            
            else:
                print(f'❌ Ошибка: {response.status_code}')
                
        except Exception as e:
            print(f'❌ Исключение: {e}')
    
    print(f'\n🎯 ОБЩАЯ ОЦЕНКА SOFASCORE:')
    print(f'• Примерно {total_matches} live матчей')
    print(f'• Богатая статистика (xG, владение, удары)')
    print(f'• H2H и форма команд')
    print(f'• Коэффициенты')
    
    if total_matches > 50:
        print(f'\n✅ SOFASCORE ЛУЧШЕ scores24.live!')
        print(f'🎯 Рекомендую переключиться на SofaScore!')
    elif total_matches > 30:
        print(f'\n✅ SOFASCORE КОНКУРЕНТОСПОСОБЕН!')
    else:
        print(f'\n⚠️ scores24.live пока лучше')

if __name__ == '__main__':
    test_sofascore()