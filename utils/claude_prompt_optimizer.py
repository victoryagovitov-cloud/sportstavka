"""
Оптимизатор промптов для Claude AI и форматирование для телеграм каналов
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json

class ClaudePromptOptimizer:
    """
    Оптимизация промптов для Claude AI анализа
    """
    
    def __init__(self):
        self.prompt_templates = {
            'basic': self._get_basic_prompt_template(),
            'detailed': self._get_detailed_prompt_template(),
            'conservative': self._get_conservative_prompt_template()
        }
    
    def create_optimized_prompt(self, matches: List[Dict[str, Any]], 
                              prompt_type: str = 'conservative') -> str:
        """
        Создание оптимизированного промпта для Claude AI
        """
        template = self.prompt_templates.get(prompt_type, self.prompt_templates['conservative'])
        
        # Подготавливаем данные матчей
        matches_data = self._prepare_matches_for_claude(matches)
        
        # Формируем промпт
        prompt = template.format(
            matches_count=len(matches),
            matches_data=matches_data,
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S МСК')
        )
        
        return prompt
    
    def _get_conservative_prompt_template(self) -> str:
        """
        Консервативный промпт для минимизации рисков
        """
        return """🎯 ЗАДАЧА: Консервативный анализ спортивных матчей для минимизации рисков

📊 ДАННЫЕ: {matches_count} матчей от российского букмекера MarathonBet
⏰ ВРЕМЯ АНАЛИЗА: {timestamp}

{matches_data}

🧠 ТРЕБОВАНИЯ К АНАЛИЗУ:

1. 🔍 НЕЗАВИСИМЫЙ ПОИСК СТАТИСТИКИ:
   • Найди актуальную статистику каждой команды/игрока в интернете
   • Проанализируй последние 5-10 результатов
   • Изучи личные встречи команд (H2H)
   • Оцени текущую форму и состав
   • Учти травмы ключевых игроков

2. 💰 АНАЛИЗ СПРАВЕДЛИВОСТИ КОЭФФИЦИЕНТОВ:
   • Соответствуют ли коэффициенты реальной силе команд?
   • Есть ли недооцененные или переоцененные исходы?
   • Какова справедливая вероятность каждого исхода?
   • Где букмекер мог ошибиться в оценке?

3. 🎯 КОНСЕРВАТИВНЫЕ РЕКОМЕНДАЦИИ:
   • Фокус на минимизации рисков
   • Избегание слишком низких коэффициентов (<1.3)
   • Поиск value opportunities с умеренным риском
   • Рекомендации только при высокой уверенности

4. 📊 ФОРМАТ ОТВЕТА ДЛЯ ТЕЛЕГРАМ КАНАЛА:
   Для каждого матча используй СТРОГО этот формат:

   🏆 КОМАНДА1 vs КОМАНДА2
   💰 Коэффициенты: П1 X.XX | X X.XX | П2 X.XX
   📊 Статистика: [краткая сводка по командам]
   🎯 Рекомендация: [СТАВКА/ПРОПУСК] на [исход] 
   💡 Обоснование: [1-2 предложения почему]
   ⚠️ Риск: [низкий/средний/высокий]
   
   ---

🛡️ ФИЛОСОФИЯ: Анализ ведущих фаворитов в live матчах
💡 ПРИНЦИП: Только матчи с неничейным счетом (кто-то уже ведет)
🎯 ЦЕЛЬ: Продолжение тренда vs отыгрыш - НЕ ставки на ничью!
⚠️ ВАЖНО: НЕ рекомендуй ничью в матчах где кто-то уже ведет!

    def _get_detailed_prompt_template(self) -> str:
        """
        Детальный промпт для глубокого анализа
        """
        return """🔍 ЗАДАЧА: Профессиональный анализ спортивных матчей

📊 ДАННЫЕ: {matches_count} матчей с коэффициентами MarathonBet
⏰ ВРЕМЯ: {timestamp}

{matches_data}

🧠 ГЛУБОКИЙ АНАЛИЗ:

1. 📈 СТАТИСТИЧЕСКИЙ АНАЛИЗ:
   • Последние результаты команд/игроков
   • Форма в последних 10 матчах
   • Статистика личных встреч
   • Домашние/выездные показатели
   • Мотивация и важность матча

2. 💰 БУКМЕКЕРСКИЙ АНАЛИЗ:
   • Движение коэффициентов
   • Сравнение с другими букмекерами
   • Выявление value opportunities
   • Анализ маржи букмекера

3. 🎯 РЕКОМЕНДАЦИИ:
   • Конкретные ставки с обоснованием
   • Размер рекомендуемой ставки
   • Альтернативные варианты
   • Предупреждения о рисках

ФОРМАТ ОТВЕТА: [подробный анализ для каждого матча]"""

    def _get_basic_prompt_template(self) -> str:
        """
        Базовый промпт для быстрого анализа
        """
        return """Проанализируй {matches_count} спортивных матчей:

{matches_data}

Для каждого матча дай:
- Краткий анализ команд
- Оценку коэффициентов  
- Рекомендацию (ставка/пропуск)
- Краткое обоснование"""

    def _prepare_matches_for_claude(self, matches: List[Dict[str, Any]]) -> str:
        """
        Подготовка данных матчей для промпта Claude AI
        """
        matches_text = []
        
        for i, match in enumerate(matches, 1):
            team1 = match.get('team1', 'N/A')
            team2 = match.get('team2', 'N/A')
            sport = match.get('sport', 'football')
            odds = match.get('odds', {})
            score = match.get('score', 'LIVE')
            time_info = match.get('time', 'LIVE')
            league = match.get('league', 'Unknown')
            
            # Формируем описание матча
            match_description = f"""
МАТЧ {i}: {team1} vs {team2}
Вид спорта: {sport}
Лига/турнир: {league}
Текущий счет: {score}
Время: {time_info}
Коэффициенты MarathonBet: П1 {odds.get('П1', '?')} | X {odds.get('X', '?')} | П2 {odds.get('П2', '?')}"""
            
            # Добавляем нашу предварительную аналитику (если есть)
            claude_analysis = match.get('claude_odds_analysis', {})
            if claude_analysis:
                betting_rec = claude_analysis.get('betting_recommendation', '')
                risk_level = claude_analysis.get('risk_level', '')
                
                match_description += f"""
Предварительная оценка системы: {betting_rec} (риск: {risk_level})"""
            
            matches_text.append(match_description.strip())
        
        return '\n\n'.join(matches_text)

class TelegramFormatter:
    """
    Форматирование анализа Claude AI для телеграм каналов
    """
    
    def __init__(self):
        self.message_templates = {
            'header': self._get_header_template(),
            'match': self._get_match_template(), 
            'footer': self._get_footer_template()
        }
        
        # Эмодзи для разных рекомендаций
        self.recommendation_emojis = {
            'ставка': '✅',
            'пропуск': '❌',
            'осторожно': '⚠️',
            'value': '💎',
            'риск': '🚨'
        }
        
        # Эмодзи для рисков
        self.risk_emojis = {
            'низкий': '🟢',
            'средний': '🟡', 
            'высокий': '🔴'
        }
    
    def format_analysis_for_telegram(self, claude_analysis: str, 
                                   period: str, matches_analyzed: int,
                                   total_available: int) -> str:
        """
        Форматирование анализа Claude AI для телеграм канала
        """
        # Заголовок сообщения
        header = self._format_header(period, matches_analyzed, total_available)
        
        # Парсим анализ Claude AI и форматируем каждый матч
        formatted_matches = self._parse_and_format_claude_analysis(claude_analysis)
        
        # Подвал с дополнительной информацией
        footer = self._format_footer()
        
        # Объединяем все части
        full_message = f"{header}\n\n{formatted_matches}\n\n{footer}"
        
        return full_message
    
    def _get_header_template(self) -> str:
        """Шаблон заголовка сообщения"""
        return """🤖 АНАЛИЗ CLAUDE AI | {period}

📊 Проанализировано: {matches_analyzed} из {total_available} доступных
⏰ Время: {timestamp}
🎯 Фокус: Консервативные value opportunities

{'='*50}"""

    def _get_match_template(self) -> str:
        """Шаблон для одного матча"""
        return """🏆 {team1} vs {team2}
💰 Коэффициенты: П1 {p1} | X {x} | П2 {p2}
📊 Статистика: {stats_summary}
{recommendation_emoji} Рекомендация: {recommendation}
💡 Обоснование: {reasoning}
{risk_emoji} Риск: {risk_level}"""

    def _get_footer_template(self) -> str:
        """Шаблон подвала сообщения"""
        return """{'='*50}

💡 Анализ основан на независимом поиске статистики
🛡️ Философия: минимизация рисков
📊 Источник коэффициентов: MarathonBet
🤖 Анализ: Claude AI

⏰ Следующий анализ: {next_analysis_time}"""

    def _format_header(self, period: str, matches_analyzed: int, total_available: int) -> str:
        """Форматирование заголовка"""
        period_emojis = {
            'morning_low': '🌅 УТРЕННИЙ',
            'afternoon_high': '☀️ ДНЕВНОЙ', 
            'evening_peak': '🌆 ВЕЧЕРНИЙ',
            'late_evening': '🌙 ПОЗДНИЙ'
        }
        
        period_display = period_emojis.get(period, '📊 АНАЛИЗ')
        timestamp = datetime.now().strftime('%H:%M МСК')
        
        return f"""🤖 АНАЛИЗ CLAUDE AI | {period_display}

📊 Проанализировано: {matches_analyzed} из {total_available} доступных
⏰ Время: {timestamp}
🎯 Фокус: Консервативные value opportunities

{'='*50}"""

    def _parse_and_format_claude_analysis(self, claude_analysis: str) -> str:
        """
        Парсинг анализа Claude AI и форматирование для телеграм
        """
        # TODO: Реализовать парсинг ответа Claude AI
        # Пока возвращаем заглушку с примером формата
        
        example_formatted = """🏆 Гибралтар vs Фарерские острова
💰 Коэффициенты: П1 4.64 | X 2.64 | П2 4.84
📊 Статистика: Гибралтар проиграл 4 из 5, Фареры выиграли 2 из 5
✅ Рекомендация: СТАВКА на X (ничья)
💡 Обоснование: Команды равной силы, коэффициент 2.64 недооценен
🟡 Риск: средний

---

🏆 Казахстан vs Украина  
💰 Коэффициенты: П1 3.70 | X 3.70 | П2 1.30
📊 Статистика: Украина в топ-30 FIFA, Казахстан в топ-100
❌ Рекомендация: ПРОПУСК
💡 Обоснование: Слишком очевидный фаворит, низкое value
🟢 Риск: низкий (но низкое value)"""
        
        return example_formatted
    
    def _format_footer(self, next_analysis_time: Optional[str] = None) -> str:
        """Форматирование подвала"""
        if not next_analysis_time:
            # Рассчитываем следующий анализ на основе текущего времени
            # TODO: Интеграция с SmartScheduler
            next_analysis_time = "через 60 минут"
        
        return f"""{'='*50}

💡 Анализ основан на независимом поиске статистики
🛡️ Философия: минимизация рисков  
📊 Источник коэффициентов: MarathonBet
🤖 Анализ: Claude AI

⏰ Следующий анализ: {next_analysis_time}"""

class ImprovedClaudePrompt:
    """
    Улучшенная система промптов для Claude AI
    """
    
    @staticmethod
    def create_enhanced_prompt(matches: List[Dict[str, Any]]) -> str:
        """
        Создание улучшенного промпта для Claude AI
        """
        matches_data = []
        
        for i, match in enumerate(matches, 1):
            team1 = match.get('team1', '')
            team2 = match.get('team2', '')
            sport = match.get('sport', 'football')
            odds = match.get('odds', {})
            score = match.get('score', 'LIVE')
            time_info = match.get('time', 'LIVE')
            league = match.get('league', '')
            
            # Наша предварительная аналитика
            our_analysis = match.get('claude_odds_analysis', {})
            betting_rec = our_analysis.get('betting_recommendation', '')
            risk_level = our_analysis.get('risk_level', '')
            probabilities = our_analysis.get('probability_analysis', {})
            
            match_data = {
                'id': i,
                'team1': team1,
                'team2': team2, 
                'sport': sport,
                'league': league,
                'current_score': score,
                'match_time': time_info,
                'marathonbet_odds': {
                    'team1_win': odds.get('П1'),
                    'draw': odds.get('X'), 
                    'team2_win': odds.get('П2')
                },
                'our_preliminary_analysis': {
                    'recommendation': betting_rec,
                    'risk_assessment': risk_level,
                    'calculated_probabilities': probabilities
                }
            }
            
            matches_data.append(match_data)
        
        # Формируем улучшенный промпт
        prompt = f"""🎯 ЗАДАЧА: Независимый анализ спортивных матчей для консервативных ставок

📅 КОНТЕКСТ:
• Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (Москва)
• Количество матчей: {len(matches)}
• Источник коэффициентов: MarathonBet (российский букмекер)
• Целевая аудитория: Консервативные беттеры

📊 ДАННЫЕ МАТЧЕЙ:
{json.dumps(matches_data, ensure_ascii=False, indent=2)}

🧠 ТРЕБОВАНИЯ К АНАЛИЗУ:

1. 🔍 ДЛЯ КАЖДОГО МАТЧА:
   • Найди независимую статистику команд/игроков в интернете
   • Проанализируй последние результаты и форму
   • Изучи историю личных встреч (H2H)
   • Оцени влияние травм и дисквалификаций
   • Учти мотивационные факторы

2. 💰 АНАЛИЗ КОЭФФИЦИЕНТОВ:
   • Справедливы ли коэффициенты MarathonBet?
   • Есть ли недооцененные исходы (value betting)?
   • Где букмекер мог ошибиться?
   • Сравни с ожидаемыми вероятностями

3. 🎯 КОНСЕРВАТИВНЫЕ РЕКОМЕНДАЦИИ:
   • Рекомендуй ставку ТОЛЬКО при высокой уверенности
   • Избегай коэффициенты ниже 1.3 (слишком низкое value)
   • Фокус на value opportunities с умеренным риском
   • При сомнениях - рекомендуй пропуск

4. 📱 ФОРМАТ ДЛЯ ТЕЛЕГРАМ КАНАЛА:

СТРОГО используй этот формат для каждого матча:

🏆 [КОМАНДА1] vs [КОМАНДА2]
💰 MarathonBet: П1 [X.XX] | X [X.XX] | П2 [X.XX]
📊 Статистика: [краткая сводка ключевых фактов]
🎯 Рекомендация: [СТАВКА на исход / ПРОПУСК]
💡 Обоснование: [1-2 предложения с ключевыми аргументами]
⚠️ Риск: [низкий 🟢 / средний 🟡 / высокий 🔴]

---

🛡️ ПРИНЦИПЫ:
• Независимость от букмекерских оценок
• ТОЛЬКО матчи с неничейным счетом (кто-то уже ведет)
• Анализ: продолжение тренда vs отыгрыш
• НЕ рекомендуй ничью в матчах где есть лидер!
• Консервативный подход к рискам

💰 ЦЕЛЬ: Анализ ведущих фаворитов для консервативных ставок

        return prompt

# Глобальные функции для быстрого использования
def create_claude_prompt(matches: List[Dict[str, Any]], prompt_type: str = 'conservative') -> str:
    """Быстрое создание промпта для Claude AI"""
    optimizer = ClaudePromptOptimizer()
    return optimizer.create_optimized_prompt(matches, prompt_type)

def format_for_telegram(claude_response: str, period: str, matches_count: int, total_available: int) -> str:
    """Быстрое форматирование для телеграм"""
    formatter = TelegramFormatter()
    return formatter.format_analysis_for_telegram(claude_response, period, matches_count, total_available)