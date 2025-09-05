#!/usr/bin/env python3
"""
Инспектор структуры scores24.live
"""
import sys
sys.path.append('.')

import requests
import re
import json
from bs4 import BeautifulSoup

def inspect_scores24():
    print('🔍 ИНСПЕКЦИЯ СТРУКТУРЫ scores24.live')
    print('='*60)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.7339.80 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    }
    
    url = 'https://scores24.live/ru/soccer?matchesFilter=live'
    
    try:
        print(f'📡 Загружаем: {url}')
        response = requests.get(url, headers=headers, timeout=15)
        
        print(f'Статус: {response.status_code}')
        print(f'Размер: {len(response.text):,} символов')
        
        if response.status_code == 200:
            html = response.text
            
            # Парсим с BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            print('\\n🔍 Поиск JSON данных в HTML...')
            
            # Ищем скрипты с данными
            scripts = soup.find_all('script')
            print(f'Найдено скриптов: {len(scripts)}')
            
            for i, script in enumerate(scripts):
                if script.string:
                    script_text = script.string
                    
                    # Ищем JSON с данными матчей
                    json_patterns = [
                        r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
                        r'window\.__PRELOADED_STATE__\s*=\s*({.+?});',
                        r'window\.__DATA__\s*=\s*({.+?});',
                        r'"matches"\s*:\s*(\[.+?\])',
                        r'"fixtures"\s*:\s*(\[.+?\])',
                        r'"events"\s*:\s*(\[.+?\])'
                    ]
                    
                    for pattern in json_patterns:
                        matches = re.findall(pattern, script_text, re.DOTALL)
                        if matches:
                            print(f'\\n✅ Найден JSON в скрипте {i+1}:')
                            print(f'Паттерн: {pattern}')
                            print(f'Размер данных: {len(matches[0]):,} символов')
                            
                            try:
                                # Пробуем парсить JSON
                                data = json.loads(matches[0])
                                print(f'✅ JSON валиден!')
                                
                                if isinstance(data, dict):
                                    print(f'Ключи: {list(data.keys())[:10]}')
                                    
                                    # Ищем матчи в структуре
                                    def find_matches(obj, path=''):
                                        if isinstance(obj, dict):
                                            for key, value in obj.items():
                                                new_path = f'{path}.{key}' if path else key
                                                if key.lower() in ['matches', 'fixtures', 'events', 'games']:
                                                    if isinstance(value, list) and value:
                                                        print(f'🎯 Найдены матчи в: {new_path}')
                                                        print(f'Количество: {len(value)}')
                                                        if value:
                                                            print(f'Пример: {value[0] if isinstance(value[0], dict) else str(value[0])[:100]}')
                                                        return value
                                                elif isinstance(value, (dict, list)):
                                                    result = find_matches(value, new_path)
                                                    if result:
                                                        return result
                                        elif isinstance(obj, list):
                                            for i, item in enumerate(obj[:5]):  # Проверяем первые 5
                                                result = find_matches(item, f'{path}[{i}]')
                                                if result:
                                                    return result
                                        return None
                                    
                                    matches_data = find_matches(data)
                                    if matches_data:
                                        return matches_data
                                        
                                elif isinstance(data, list) and data:
                                    print(f'Массив из {len(data)} элементов')
                                    if data:
                                        print(f'Первый элемент: {data[0] if isinstance(data[0], dict) else str(data[0])[:100]}')
                                        return data
                                        
                            except json.JSONDecodeError as e:
                                print(f'❌ JSON невалиден: {e}')
                                print(f'Начало: {matches[0][:200]}...')
            
            # Если JSON не найден, ищем другие способы
            print('\\n🔍 Поиск альтернативных данных...')
            
            # Ищем возможные API endpoints
            api_urls = re.findall(r'["\'](?:https?://[^"\s]+/)?(?:api|dapi)/[^"\s]+["\']', html)
            if api_urls:
                print(f'Найдено API URLs: {len(set(api_urls))}')
                for api_url in list(set(api_urls))[:5]:
                    clean_url = api_url.strip('\"\\\'')
                    print(f'  • {clean_url}')
            
            # Ищем data атрибуты
            data_attrs = re.findall(r'data-[\w-]+=["\'][^"\']+["\']', html)
            unique_attrs = list(set([attr.split('=')[0] for attr in data_attrs]))
            print(f'\\nData атрибуты: {len(unique_attrs)}')
            for attr in unique_attrs[:10]:
                print(f'  • {attr}')
            
            return None
            
    except Exception as e:
        print(f'❌ ОШИБКА: {e}')
        return None

if __name__ == '__main__':
    matches = inspect_scores24()
    if matches:
        print(f'\\n✅ НАЙДЕНЫ ДАННЫЕ МАТЧЕЙ: {len(matches)}')
    else:
        print('\\n❌ Данные матчей не найдены в JSON')
        print('Сайт может использовать WebSocket или другие методы загрузки')