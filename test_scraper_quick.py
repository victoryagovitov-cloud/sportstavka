#!/usr/bin/env python3
"""
Быстрый тест скрапера scores24.live
"""
import sys
sys.path.append('.')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time
import re
from config import SELENIUM_OPTIONS, CHROMEDRIVER_PATH

def quick_test():
    print('🔍 БЫСТРЫЙ ТЕСТ СКРАПЕРА scores24.live')
    print('='*50)
    
    # Настройка браузера с минимальными задержками
    chrome_options = Options()
    for option in SELENIUM_OPTIONS:
        chrome_options.add_argument(option)
    chrome_options.add_argument('--disable-images')  # Отключаем картинки
    chrome_options.add_argument('--disable-javascript')  # Отключаем JS для ускорения
    
    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(30)  # Таймаут загрузки страницы
    
    try:
        print('📡 Загружаем страницу футбола...')
        driver.get('https://scores24.live/ru/soccer?matchesFilter=live')
        time.sleep(5)  # Минимальное ожидание
        
        print('🔍 Анализируем содержимое страницы...')
        
        # Получаем весь текст страницы
        page_text = driver.page_source
        print(f'Размер HTML: {len(page_text)} символов')
        
        # Ищем признаки матчей в HTML
        match_indicators = [
            re.findall(r'(\w+\s*-\s*\w+)', page_text),  # Команда - Команда
            re.findall(r'(\d+:\d+)', page_text),         # Счет
            re.findall(r"(\d+['\мин])", page_text),      # Время
        ]
        
        print(f'Найдено паттернов команд: {len(match_indicators[0])}')
        print(f'Найдено паттернов счета: {len(match_indicators[1])}')
        print(f'Найдено паттернов времени: {len(match_indicators[2])}')
        
        # Показываем примеры найденного
        if match_indicators[0]:
            print('\\nПримеры команд:')
            for team_match in match_indicators[0][:5]:
                print(f'  - {team_match}')
        
        if match_indicators[1]:
            print('\\nПримеры счета:')
            for score in match_indicators[1][:5]:
                print(f'  - {score}')
                
        if match_indicators[2]:
            print('\\nПримеры времени:')
            for time_match in match_indicators[2][:5]:
                print(f'  - {time_match}')
        
        # Проверяем наличие live контента
        live_content = 'live' in page_text.lower()
        print(f'\\n🔴 LIVE контент обнаружен: {"✅" if live_content else "❌"}')
        
        # Ищем ссылки на матчи
        match_links = re.findall(r'href="([^"]*(?:match|event)[^"]*)"', page_text)
        print(f'🔗 Найдено ссылок на матчи: {len(match_links)}')
        
        if match_links:
            print('Примеры ссылок:')
            for link in match_links[:3]:
                print(f'  - {link}')
        
        return len(match_indicators[0]) > 0 or len(match_links) > 0
        
    except Exception as e:
        print(f'❌ ОШИБКА: {e}')
        return False
    finally:
        driver.quit()

if __name__ == '__main__':
    success = quick_test()
    if success:
        print('\\n✅ ДАННЫЕ НАЙДЕНЫ! Сайт содержит информацию о матчах')
    else:
        print('\\n❌ ДАННЫЕ НЕ НАЙДЕНЫ! Возможно сайт использует динамическую загрузку')