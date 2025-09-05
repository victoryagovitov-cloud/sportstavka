#!/usr/bin/env python3
"""
Простой тест без браузера
"""
import sys
sys.path.append('.')

import requests
import re
import time

def test_scores24_simple():
    print('🔍 ПРОСТОЙ ТЕСТ scores24.live БЕЗ БРАУЗЕРА')
    print('='*50)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
    }
    
    urls_to_test = [
        'https://scores24.live/ru/soccer?matchesFilter=live',
        'https://scores24.live/ru/tennis?matchesFilter=live',
        'https://scores24.live/ru/table-tennis?matchesFilter=live',
        'https://scores24.live/ru/handball?matchesFilter=live'
    ]
    
    for url in urls_to_test:
        sport = url.split('/')[-1].split('?')[0]
        print(f'\\n🏈 Тестирую {sport}...')
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            print(f'Статус: {response.status_code}')
            
            if response.status_code == 200:
                html = response.text
                print(f'Размер HTML: {len(html)} символов')
                
                # Ищем признаки live контента
                live_indicators = {
                    'live_text': html.lower().count('live'),
                    'scores': len(re.findall(r'\\d+[:-]\\d+', html)),
                    'times': len(re.findall(r"\\d+['\мин]", html)),
                    'vs_matches': len(re.findall(r'\\w+\\s*[-vs]\\s*\\w+', html, re.IGNORECASE))
                }
                
                print(f'Индикаторы LIVE:')
                for indicator, count in live_indicators.items():
                    print(f'  {indicator}: {count}')
                
                # Ищем возможные API endpoints в HTML
                api_matches = re.findall(r'["\\']/(?:api|dapi)/[^"\\s]*', html)
                if api_matches:
                    print(f'Найдено API endpoints: {len(set(api_matches))}')
                    for api in list(set(api_matches))[:3]:
                        print(f'  - {api}')
                
                total_indicators = sum(live_indicators.values())
                if total_indicators > 20:
                    print(f'✅ {sport}: Много LIVE данных ({total_indicators} индикаторов)')
                else:
                    print(f'⚠️ {sport}: Мало данных ({total_indicators} индикаторов)')
            else:
                print(f'❌ Ошибка доступа: {response.status_code}')
                
        except Exception as e:
            print(f'❌ Исключение: {e}')
        
        time.sleep(1)  # Пауза между запросами

if __name__ == '__main__':
    test_scores24_simple()