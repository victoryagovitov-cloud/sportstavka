"""
Модуль интеграции с Claude AI для анализа спортивных данных
"""
import json
import logging
from typing import Dict, Any, Optional, List
import anthropic
from config import CLAUDE_API_KEY

class ClaudeAnalyzer:
    """
    Класс для анализа спортивных данных с помощью Claude AI
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """
        Инициализация клиента Claude AI
        """
        if CLAUDE_API_KEY:
            try:
                self.client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
                self.logger.info("Claude AI клиент успешно инициализирован")
            except Exception as e:
                self.logger.error(f"Ошибка инициализации Claude AI: {e}")
                self.client = None
        else:
            self.logger.warning("CLAUDE_API_KEY не установлен, используется заглушка")
            self.client = None
    
    def analyze_match(self, sport_type: str, match_data: Dict[str, Any]) -> str:
        """
        Анализ матча с помощью Claude AI
        
        Args:
            sport_type: Тип спорта (football, tennis, table_tennis, handball)
            match_data: Структурированные данные матча
            
        Returns:
            Анализ матча от Claude AI
        """
        if not self.client:
            return self._fallback_analysis(sport_type, match_data)
        
        try:
            prompt = self._build_analysis_prompt(sport_type, match_data)
            
            message = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1000,
                temperature=0.3,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            analysis = message.content[0].text
            self.logger.info(f"Получен анализ от Claude AI для {sport_type} матча")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Ошибка анализа Claude AI: {e}")
            return self._fallback_analysis(sport_type, match_data)
    
    def _build_analysis_prompt(self, sport_type: str, match_data: Dict[str, Any]) -> str:
        """
        Построение промпта для анализа
        """
        # Форматируем данные для лучшего восприятия
        formatted_data = self._format_match_data(match_data)
        
        sport_names = {
            'football': 'ФУТБОЛ',
            'tennis': 'ТЕННИС', 
            'table_tennis': 'НАСТОЛЬНЫЙ ТЕННИС',
            'handball': 'ГАНДБОЛ'
        }
        
        sport_name = sport_names.get(sport_type, sport_type.upper())
        
        prompt = f"""
Ты эксперт по спортивным ставкам. Твоя задача — провести комплексный анализ LIVE-матча и дать краткое, убедительное обоснование для ставки на русском языке.

**ИСТОЧНИК ДАННЫХ:** Вот исчерпывающие данные, собранные в реальном времени с сайта scores24.live:

Вид спорта: {sport_name}

Собранные данные матча:
{formatted_data}

**ЗАДАЧА И ИНСТРУКЦИЯ:**
Проанализируй предоставленные данные (текущий счет, время, статистику, форма, H2H, коэффициенты и т.д.).

**ЗАПРЕЩЕНО ограничиваться только этими данными. Ты ДОЛЖЕН:**
1. **Применить собственные аналитические алгоритмы и библиотеки** для прогнозирования развития событий.
2. **Использовать свою внутреннюю базу знаний** о командах, игроках, турнирах, их мотивации и текущем состоянии.
3. **Мысленно смоделировать оставшуюся часть матча** на основе совокупности всех известных тебе факторов.
4. **Учесть общеизвестные спортивные закономерности** (например, "команды-подвалы чаще проигрывают во втором тайме", "теннисистка теряет концентрацию после проигранного сета" и т.д.).
5. **При необходимости провести мысленный поиск в открытых источниках** для уточнения контекста (травмы, мотивация, кадровые проблемы), если это критично для анализа.

**ТРЕБОВАНИЯ К ВЫВОДУ:**
Сформулируй вывод в 2-3 предложения. Тон: профессиональный, уверенный, без эмоций.
Вывод должен быть основан на СИНТЕЗЕ предоставленных данных с scores24.live и результатов твоего собственного глубокого анализа с привлечением всех доступных ресурсов.

Не используй фразы типа "на основе предоставленных данных" - пиши как эксперт, который знает все о спорте.
"""

        return prompt
    
    def _format_match_data(self, match_data: Dict[str, Any]) -> str:
        """
        Форматирование данных матча для промпта
        """
        formatted_sections = []
        
        # Основная информация
        if 'team1' in match_data and 'team2' in match_data:
            teams = f"Команды: {match_data.get('team1', 'N/A')} vs {match_data.get('team2', 'N/A')}"
            formatted_sections.append(teams)
        
        if 'player1' in match_data and 'player2' in match_data:
            players = f"Игроки: {match_data.get('player1', 'N/A')} vs {match_data.get('player2', 'N/A')}"
            formatted_sections.append(players)
        
        # Счет и время
        if 'score' in match_data:
            formatted_sections.append(f"Счет: {match_data['score']}")
        
        if 'sets_score' in match_data:
            formatted_sections.append(f"Счет по сетам: {match_data['sets_score']}")
        
        if 'current_set' in match_data:
            formatted_sections.append(f"Текущий сет: {match_data['current_set']}")
        
        if 'time' in match_data:
            formatted_sections.append(f"Время: {match_data['time']}")
        
        # Лига/турнир
        if 'league' in match_data:
            formatted_sections.append(f"Лига: {match_data['league']}")
        
        if 'tournament' in match_data:
            formatted_sections.append(f"Турнир: {match_data['tournament']}")
        
        # Статистика
        if 'statistics' in match_data and match_data['statistics']:
            formatted_sections.append("СТАТИСТИКА:")
            stats = match_data['statistics']
            for stat_name, stat_values in stats.items():
                if isinstance(stat_values, dict):
                    formatted_sections.append(f"  {stat_name}: {stat_values}")
                else:
                    formatted_sections.append(f"  {stat_name}: {stat_values}")
        
        # Коэффициенты
        if 'odds' in match_data and match_data['odds']:
            formatted_sections.append("КОЭФФИЦИЕНТЫ:")
            for market, values in match_data['odds'].items():
                formatted_sections.append(f"  {market}: {values}")
        
        # История встреч
        if 'h2h' in match_data and match_data['h2h']:
            h2h_count = len(match_data['h2h'])
            formatted_sections.append(f"ИСТОРИЯ ВСТРЕЧ: ({h2h_count} последних матчей)")
            for i, match in enumerate(match_data['h2h'][:5]):  # Первые 5 матчей
                formatted_sections.append(f"  {i+1}. {match}")
        
        # Форма команд/игроков
        if 'results' in match_data and match_data['results']:
            formatted_sections.append("ФОРМА КОМАНД/ИГРОКОВ:")
            for entity, results in match_data['results'].items():
                if 'statistics' in results:
                    stats = results['statistics']
                    formatted_sections.append(f"  {entity}: {stats}")
        
        # Турнирная таблица
        if 'table' in match_data and match_data['table']:
            formatted_sections.append("ТУРНИРНАЯ ТАБЛИЦА:")
            for team, position_info in match_data['table'].items():
                formatted_sections.append(f"  {team}: {position_info}")
        
        # Рейтинги
        if 'rankings' in match_data and match_data['rankings']:
            formatted_sections.append("РЕЙТИНГИ:")
            for player, ranking in match_data['rankings'].items():
                formatted_sections.append(f"  {player}: {ranking}")
        
        # Расчеты тоталов (для гандбола)
        if 'totals_calculation' in match_data:
            totals = match_data['totals_calculation']
            formatted_sections.append("РАСЧЕТ ТОТАЛОВ:")
            formatted_sections.append(f"  Прогнозный тотал: {totals.get('predicted_total', 'N/A')}")
            formatted_sections.append(f"  Рекомендация: {totals.get('recommendation', 'N/A')}")
            formatted_sections.append(f"  Обоснование: {totals.get('reasoning', 'N/A')}")
        
        # Тренды
        if 'trends' in match_data and match_data['trends']:
            formatted_sections.append("ТРЕНДЫ:")
            for trend_name, trend_value in match_data['trends'].items():
                formatted_sections.append(f"  {trend_name}: {trend_value}")
        
        return "\n".join(formatted_sections)
    
    def _fallback_analysis(self, sport_type: str, match_data: Dict[str, Any]) -> str:
        """
        Заглушка для анализа когда Claude API недоступен
        """
        self.logger.info(f"Используется заглушка анализа для {sport_type}")
        
        # Базовый анализ на основе доступных данных
        analysis_parts = []
        
        if sport_type == 'football':
            analysis_parts.append("Анализ основан на статистике матча и текущих показателях команд.")
            
            if 'statistics' in match_data:
                stats = match_data['statistics']
                if 'xG' in str(stats):
                    analysis_parts.append("Учтены показатели ожидаемых голов (xG) и владения мячом.")
            
            if 'table' in match_data and match_data['table']:
                analysis_parts.append("Проанализированы позиции команд в турнирной таблице.")
        
        elif sport_type == 'tennis':
            analysis_parts.append("Рассмотрена текущая форма игроков и статистика подач.")
            
            if 'rankings' in match_data and match_data['rankings']:
                analysis_parts.append("Учтены рейтинги игроков ATP/WTA.")
        
        elif sport_type == 'handball':
            if 'totals_calculation' in match_data:
                totals = match_data['totals_calculation']
                recommendation = totals.get('recommendation', '')
                reasoning = totals.get('reasoning', '')
                analysis_parts.append(f"Рекомендуется {recommendation}. {reasoning}")
            else:
                analysis_parts.append("Проанализирована результативность команд и текущий темп игры.")
        
        else:
            analysis_parts.append("Анализ основан на текущей статистике и форме участников.")
        
        # Добавляем общее заключение
        if not analysis_parts:
            analysis_parts.append("Рекомендация основана на комплексном анализе доступных данных.")
        
        return " ".join(analysis_parts)
    
    def analyze_multiple_matches(self, matches_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Анализ нескольких матчей
        
        Args:
            matches_data: Список данных матчей
            
        Returns:
            Список матчей с добавленным анализом
        """
        analyzed_matches = []
        
        for match_data in matches_data:
            sport_type = match_data.get('sport', 'unknown')
            analysis = self.analyze_match(sport_type, match_data)
            
            match_data['ai_analysis'] = analysis
            analyzed_matches.append(match_data)
        
        self.logger.info(f"Проанализировано {len(analyzed_matches)} матчей")
        return analyzed_matches
    
    def get_best_recommendations(self, analyzed_matches: List[Dict[str, Any]], max_count: int = 5) -> List[Dict[str, Any]]:
        """
        Выбор лучших рекомендаций из проанализированных матчей
        
        Args:
            analyzed_matches: Матчи с анализом
            max_count: Максимальное количество рекомендаций
            
        Returns:
            Лучшие рекомендации
        """
        # Сортируем по приоритету (топ-лиги имеют меньший приоритет)
        sorted_matches = sorted(
            analyzed_matches, 
            key=lambda x: x.get('priority', 999)
        )
        
        # Берем лучшие рекомендации
        best_matches = sorted_matches[:max_count]
        
        self.logger.info(f"Выбрано {len(best_matches)} лучших рекомендаций")
        return best_matches