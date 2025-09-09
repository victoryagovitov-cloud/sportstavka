#!/usr/bin/env python3
"""
Получение актуальных данных футбола: команды + счет + время + лига
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import re
from datetime import datetime

print('📊 ОБНОВЛЕННЫЕ ДАННЫЕ ФУТБОЛА С ЛИГАМИ')
print('=' * 50)

chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--window-size=1920,1080')
chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

url = 'https://www.marathonbet.ru/su/live/26418'

current_time = datetime.now().strftime('%H:%M:%S')
print(f'\n🕐 ВРЕМЯ ОБНОВЛЕНИЯ: {current_time}')

try:
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)
    time.sleep(6)
    
    print('✅ Страница загружена')
    
    # Получаем все таблицы
    tables = driver.find_elements(By.TAG_NAME, 'table')
    print(f'📊 Найдено таблиц: {len(tables)}')
    
    all_matches = []
    
    # Анализируем каждую таблицу
    for table_idx, table in enumerate(tables):
        try:
            # Ищем заголовок лиги для этой таблицы
            table_league = 'Неизвестная лига'
            
            # Проверяем заголовки перед таблицей
            try:
                # Ищем заголовки h1-h6 перед таблицей
                headings = driver.find_elements(By.CSS_SELECTOR, 'h1, h2, h3, h4, h5, h6')
                for heading in headings:
                    heading_text = heading.text.strip()
                    if (heading_text and len(heading_text) > 5 and
                        any(word in heading_text.lower() for word in ['лига', 'чемпионат', 'кубок', 'турнир', 'премьер', 'дивизион', 'acl', '5x5', '3x3'])):
                        table_league = heading_text
                        break
                
                # Альтернативный поиск в div элементах
                if table_league == 'Неизвестная лига':
                    divs = driver.find_elements(By.CSS_SELECTOR, 'div')
                    for div in divs:
                        div_text = div.text.strip()
                        if (div_text and len(div_text) > 10 and len(div_text) < 100 and
                            any(word in div_text.lower() for word in ['лига', 'чемпионат', 'кубок', 'турнир', 'премьер', 'дивизион', 'acl', '5x5', '3x3', 'индия', 'китай', 'россия'])):
                            table_league = div_text
                            break
                            
            except:
                pass
            
            # Анализируем строки таблицы
            rows = table.find_elements(By.TAG_NAME, 'tr')
            
            for row_idx, row in enumerate(rows):
                try:
                    cells = row.find_elements(By.TAG_NAME, 'td')
                    
                    if len(cells) >= 3:
                        main_cell = cells[0].text.strip()
                        
                        if main_cell and len(main_cell) > 10:
                            # Ищем счет
                            score_match = re.search(r'(\d+):(\d+)', main_cell)
                            
                            if score_match:
                                score = score_match.group(0)
                                
                                # Ищем время
                                time_match = re.search(r'(\d{1,2}:\d{2})', main_cell)
                                match_time = time_match.group(0) if time_match else 'LIVE'
                                
                                # Извлекаем команды
                                lines = main_cell.split('\n')
                                teams = []
                                
                                for line in lines:
                                    line = line.strip()
                                    
                                    if (line and 
                                        re.search(r'[А-Яа-яA-Za-z]', line) and
                                        not re.match(r'^\d+$', line) and
                                        not re.match(r'^\d+\.\d+$', line) and
                                        not re.match(r'^\d+:\d+$', line) and
                                        line not in ['1.', '2.', '+', '-', 'X'] and
                                        len(line) >= 3):
                                        
                                        # Очищаем название команды
                                        clean_name = re.sub(r'^\d+\.\s*', '', line).strip()
                                        if clean_name and len(clean_name) >= 3:
                                            teams.append(clean_name)
                                
                                if len(teams) >= 2:
                                    match_info = {
                                        'team1': teams[0],
                                        'team2': teams[1],
                                        'score': score,
                                        'time': match_time,
                                        'league': table_league,
                                        'table': table_idx
                                    }
                                    all_matches.append(match_info)
                                    
                except Exception:
                    continue
                    
        except Exception:
            continue
    
    # Убираем дубликаты
    unique_matches = []
    seen = set()
    
    for match in all_matches:
        key = f"{match['team1'].lower()}_{match['team2'].lower()}_{match['score']}"
        if key not in seen:
            seen.add(key)
            unique_matches.append(match)
    
    print(f'\n⚽ ВСЕ АКТУАЛЬНЫЕ ФУТБОЛЬНЫЕ МАТЧИ:')
    print('=' * 40)
    
    if unique_matches:
        non_draw_count = 0
        
        for i, match in enumerate(unique_matches, 1):
            team1 = match['team1']
            team2 = match['team2']
            score = match['score']
            time = match['time']
            league = match['league']
            
            print(f'\n{i}. {team1} vs {team2}')
            print(f'   Счет: {score} | Время: {time}')
            print(f'   Лига: {league}')
            
            # Анализ
            try:
                home, away = map(int, score.split(':'))
                if home == away:
                    print(f'   Статус: ⚖️ Ничейный')
                else:
                    leader = 'хозяева' if home > away else 'гости'
                    diff = abs(home - away)
                    print(f'   Статус: ✅ Неничейный (ведут {leader} +{diff})')
                    non_draw_count += 1
            except:
                print(f'   Статус: ❓ Ошибка')
        
        print(f'\n📈 ИТОГОВАЯ СТАТИСТИКА:')
        print('-' * 25)
        print(f'   Всего матчей: {len(unique_matches)}')
        print(f'   Неничейных: {non_draw_count}')
        print(f'   Готовых для Claude AI: {non_draw_count}')
        
        if non_draw_count > 0:
            print(f'\n🎉 ПОЛНАЯ ИНФОРМАЦИЯ ПОЛУЧЕНА!')
            print(f'✅ Команды + счета + время + лиги')
            print(f'🚀 ГОТОВО К АНАЛИЗУ CLAUDE AI!')
    
    else:
        print(f'\n❌ Матчи не найдены')

except Exception as e:
    print(f'❌ Ошибка: {e}')

finally:
    try:
        driver.quit()
    except:
        pass