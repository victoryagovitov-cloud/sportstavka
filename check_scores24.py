#!/usr/bin/env python3
"""
Простая проверка scores24.live
"""
import sys
sys.path.append('.')

import requests
import re
import time

def check_scores24():
    print('🔍 ПРОВЕРКА scores24.live')
    print('='*50)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.7339.80 Safari/537.36'
    }
    
    urls = {
        'футбол': 'https://scores24.live/ru/soccer?matchesFilter=live',
        'теннис': 'https://scores24.live/ru/tennis?matchesFilter=live', 
        'настольный теннис': 'https://scores24.live/ru/table-tennis?matchesFilter=live',
        'гандбол': 'https://scores24.live/ru/handball?matchesFilter=live'
    }
    
    for sport, url in urls.items():
        print(f'\n🏈 {sport.upper()}')
        print('-' * 30)
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            print(f'Статус: {response.status_code}')
            
            if response.status_code == 200:
                html = response.text
                print(f'Размер HTML: {len(html):,} символов')
                
                # Ищем признаки live матчей
                indicators = {
                    'live упоминания': html.lower().count('live'),
                    'счет (X:X)': len(re.findall(r'\d+:\d+', html)),
                    'время (XX\')': len(re.findall(r'\d+\'', html)),
                    'vs/- паттерны': len(re.findall(r'\w+\s*[-vs]\s*\w+', html, re.IGNORECASE))
                }
                
                total_indicators = sum(indicators.values())
                print(f'Индикаторы матчей: {total_indicators}')
                
                for name, count in indicators.items():
                    print(f'  • {name}: {count}')
                
                # Ищем конкретные примеры
                scores = re.findall(r'\d+:\d+', html)
                times = re.findall(r'\d+\'', html)
                
                if scores:
                    print(f'Примеры счета: {scores[:5]}')
                if times:
                    print(f'Примеры времени: {times[:5]}')
                
                if total_indicators > 20:
                    print('✅ МНОГО LIVE ДАННЫХ!')
                elif total_indicators > 5:
                    print('⚠️ Есть данные, но мало')
                else:
                    print('❌ Мало live данных')
            else:
                print(f'❌ Ошибка доступа: {response.status_code}')
                
        except Exception as e:
            print(f'❌ Исключение: {e}')
        
        time.sleep(1)

if __name__ == '__main__':
    check_scores24()