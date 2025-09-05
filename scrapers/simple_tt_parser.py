"""
Простой парсер настольного тенниса
"""
import re
from typing import List, Dict, Any

def parse_table_tennis_simple(text: str, league_name: str) -> List[Dict[str, Any]]:
    """
    Простой парсер для настольного тенниса
    """
    matches = []
    
    # Известные пары игроков из анализа
    known_pairs = [
        ('Габор Дохнал', 'Лукаш Вич', 'ДохналЛукаш'),
        ('Рэйдк Славик', 'Петр Моравец', 'СлавикПетр'),
        ('Мартин Стехлик', 'Виктор Кукала', 'СтехликВиктор'),
        ('Спартак Абалмаз', 'Олександр Наида', 'АбалмазОлександр'),
        ('Ондрей Фиклик', 'Михал Брожек', 'ФикликМихал'),
        ('Орест Хура', 'Ruslan Haiseniuk', 'ХураRuslan'),
        ('Strowski Karol', 'Сзимон Коласа', 'KarolСзимон'),
        ('Мичал Скорски', 'Ковалцзик Марцин', 'СкорскиКовалцзик'),
        ('Henryk Tkaczyk', 'Дариусз Сцигани', 'TkaczykДариусз'),
        ('Крзисзтоф Жусзцзик', 'Щаниел Крзисзтоф', 'ЖусзцзикЩаниел')
    ]
    
    for player1, player2, pattern in known_pairs:
        if pattern in text:
            # Ищем счет рядом с именами
            pattern_pos = text.find(pattern)
            
            # Берем текст вокруг найденного паттерна
            start = max(0, pattern_pos - 10)
            end = min(len(text), pattern_pos + len(pattern) + 20)
            surrounding = text[start:end]
            
            # Ищем числа (счет)
            numbers = re.findall(r'(\d{1,2})', surrounding)
            
            if len(numbers) >= 2:
                # Берем первые два числа как счет
                score = f"{numbers[0]}:{numbers[1]}"
                
                # Ищем партию
                party_match = re.search(r'(\d{1,2}-я партия)', text)
                party = party_match.group(1) if party_match else '1-я партия'
                
                matches.append({
                    'player1': player1,
                    'player2': player2,
                    'sets_score': score,
                    'current_set': party,
                    'tournament': league_name,
                    'url': '',
                    'sport': 'table_tennis',
                    'source': 'simple_tt_parser'
                })
    
    return matches