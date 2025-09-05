"""
Модуль для публикации отчетов в Telegram канал
"""
import requests
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from utils.time_utils import format_moscow_time

class TelegramReporter:
    """
    Класс для отправки отчетов в Telegram канал
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def send_report(self, recommendations: List[Dict[str, Any]]) -> bool:
        """
        Отправка отчета с рекомендациями в Telegram канал
        
        Args:
            recommendations: Список рекомендаций для публикации
            
        Returns:
            True если отправка успешна, False иначе
        """
        try:
            if not recommendations:
                return self._send_no_matches_message()
            
            report_text = self._build_report(recommendations)
            return self._send_message(report_text)
            
        except Exception as e:
            self.logger.error(f"Ошибка отправки отчета в Telegram: {e}")
            return False
    
    def _build_report(self, recommendations: List[Dict[str, Any]]) -> str:
        """
        Построение текста отчета
        """
        # Заголовок с временем
        current_time = format_moscow_time()
        header = f"🎯 LIVE-ПРЕДЛОЖЕНИЯ НА {current_time} 🎯"
        
        sections = [header, "——————————————"]
        
        # Группируем рекомендации по видам спорта
        sports_groups = self._group_by_sport(recommendations)
        
        # Добавляем секции для каждого вида спорта
        for sport, matches in sports_groups.items():
            sport_section = self._build_sport_section(sport, matches)
            if sport_section:
                sections.extend(sport_section)
        
        # Подвал
        footer = [
            "——————————————————",
            "💎 @TrueLiveBet – Анализ на основе AI и статистики! 💎",
            "",
            "⚠️ Дисклеймер: Наши прогнозы основаны на анализе, но не гарантируют прибыль."
        ]
        
        sections.extend(footer)
        
        return "\n".join(sections)
    
    def _group_by_sport(self, recommendations: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Группировка рекомендаций по видам спорта
        """
        groups = {}
        
        for rec in recommendations:
            sport = rec.get('sport', 'unknown')
            if sport not in groups:
                groups[sport] = []
            groups[sport].append(rec)
        
        return groups
    
    def _build_sport_section(self, sport: str, matches: List[Dict[str, Any]]) -> List[str]:
        """
        Построение секции для конкретного вида спорта
        """
        sport_headers = {
            'football': '⚽ ФУТБОЛ ⚽',
            'tennis': '🎾 ТЕННИС 🎾',
            'table_tennis': '🏓 НАСТОЛЬНЫЙ ТЕННИС 🏓',
            'handball': '🤾 ГАНДБОЛ 🤾'
        }
        
        header = sport_headers.get(sport, f'🏆 {sport.upper()} 🏆')
        section = [header, "——————————————", ""]
        
        for i, match in enumerate(matches, 1):
            match_text = self._format_match_recommendation(sport, match, i)
            section.append(match_text)
            section.append("")  # Пустая строка между матчами
        
        return section
    
    def _format_match_recommendation(self, sport: str, match: Dict[str, Any], index: int) -> str:
        """
        Форматирование рекомендации для конкретного матча
        """
        if sport == 'football':
            return self._format_football_match(match, index)
        elif sport == 'tennis':
            return self._format_tennis_match(match, index)
        elif sport == 'table_tennis':
            return self._format_table_tennis_match(match, index)
        elif sport == 'handball':
            return self._format_handball_match(match, index)
        else:
            return self._format_generic_match(match, index)
    
    def _format_football_match(self, match: Dict[str, Any], index: int) -> str:
        """
        Форматирование футбольного матча
        """
        team1 = match.get('team1', 'Команда 1')
        team2 = match.get('team2', 'Команда 2')
        score = match.get('score', '0:0')
        time = match.get('time', '0\'')
        league = match.get('league', 'Неизвестная лига')
        
        # Определяем рекомендуемую ставку
        bet_recommendation = self._get_football_bet_recommendation(match)
        odds = self._get_best_odds(match, bet_recommendation)
        
        # Время до конца матча
        remaining_time = self._calculate_remaining_time(time, 'football')
        
        # AI анализ
        analysis = match.get('ai_analysis', 'Анализ недоступен')
        
        lines = [
            f"{index}. ⚽ {team1} – {team2}",
            f"🏟️ Счет: <b>{score}</b> ({time}) | До конца: {remaining_time} | Лига: {league}",
            f"✅ Ставка: <b>{bet_recommendation}</b>",
            f"📊 Кэф: <b>{odds}</b>",
            f"📌 <i>{analysis}</i>"
        ]
        
        return "\n".join(lines)
    
    def _format_tennis_match(self, match: Dict[str, Any], index: int) -> str:
        """
        Форматирование теннисного матча
        """
        player1 = match.get('player1', 'Игрок 1')
        player2 = match.get('player2', 'Игрок 2')
        sets_score = match.get('sets_score', '0-0')
        current_set = match.get('current_set', '0-0')
        tournament = match.get('tournament', 'Неизвестный турнир')
        
        # Определяем рекомендуемую ставку
        bet_recommendation = self._get_tennis_bet_recommendation(match)
        odds = self._get_best_odds(match, bet_recommendation)
        
        # AI анализ
        analysis = match.get('ai_analysis', 'Анализ недоступен')
        
        lines = [
            f"{index}. 🎾 {player1} – {player2}",
            f"🎯 Счет: {sets_score} ({current_set}) | Турнир: {tournament}",
            f"✅ Ставка: <b>{bet_recommendation}</b>",
            f"📊 Кэф: <b>{odds}</b>",
            f"📌 <i>{analysis}</i>"
        ]
        
        return "\n".join(lines)
    
    def _format_table_tennis_match(self, match: Dict[str, Any], index: int) -> str:
        """
        Форматирование матча настольного тенниса
        """
        player1 = match.get('player1', 'Игрок 1')
        player2 = match.get('player2', 'Игрок 2')
        sets_score = match.get('sets_score', '0-0')
        current_set = match.get('current_set', '0-0')
        tournament = match.get('tournament', 'Неизвестный турнир')
        
        # Определяем рекомендуемую ставку
        bet_recommendation = self._get_table_tennis_bet_recommendation(match)
        odds = self._get_best_odds(match, bet_recommendation)
        
        # AI анализ
        analysis = match.get('ai_analysis', 'Анализ недоступен')
        
        lines = [
            f"{index}. 🏓 {player1} – {player2}",
            f"🎯 Счет: {sets_score} ({current_set}) | Турнир: {tournament}",
            f"✅ Ставка: <b>{bet_recommendation}</b>",
            f"📊 Кэф: <b>{odds}</b>",
            f"📌 <i>{analysis}</i>"
        ]
        
        return "\n".join(lines)
    
    def _format_handball_match(self, match: Dict[str, Any], index: int) -> str:
        """
        Форматирование гандбольного матча
        """
        team1 = match.get('team1', 'Команда 1')
        team2 = match.get('team2', 'Команда 2')
        score = match.get('score', '0:0')
        time = match.get('time', '0\'')
        
        # Проверяем, есть ли расчет тоталов
        if 'totals_calculation' in match:
            return self._format_handball_totals(match, index)
        else:
            return self._format_handball_victory(match, index)
    
    def _format_handball_totals(self, match: Dict[str, Any], index: int) -> str:
        """
        Форматирование гандбольного матча с тоталами
        """
        team1 = match.get('team1', 'Команда 1')
        team2 = match.get('team2', 'Команда 2')
        score = match.get('score', '0:0')
        time = match.get('time', '0\'')
        
        totals = match.get('totals_calculation', {})
        predicted_total = totals.get('predicted_total', 'N/A')
        recommendation = totals.get('recommendation', 'N/A')
        reasoning = totals.get('reasoning', 'Анализ недоступен')
        
        lines = [
            f"{index}. 🤾 {team1} – {team2}",
            f"🏟️ Счет: <b>{score}</b> ({time})",
            f"📈 Прогнозный тотал: <b>{predicted_total}</b> голов",
            f"🎯 Рекомендация: <b>{recommendation}</b>",
            f"📌 <i>{reasoning}</i>"
        ]
        
        return "\n".join(lines)
    
    def _format_handball_victory(self, match: Dict[str, Any], index: int) -> str:
        """
        Форматирование гандбольного матча на победу
        """
        team1 = match.get('team1', 'Команда 1')
        team2 = match.get('team2', 'Команда 2')
        score = match.get('score', '0:0')
        time = match.get('time', '0\'')
        
        # Определяем рекомендуемую ставку
        bet_recommendation = self._get_handball_bet_recommendation(match)
        odds = self._get_best_odds(match, bet_recommendation)
        
        # AI анализ
        analysis = match.get('ai_analysis', 'Анализ недоступен')
        
        lines = [
            f"{index}. 🤾 {team1} – {team2}",
            f"🏟️ Счет: <b>{score}</b> ({time})",
            f"✅ Ставка: <b>{bet_recommendation}</b>",
            f"📊 Кэф: <b>{odds}</b>",
            f"📌 <i>{analysis}</i>"
        ]
        
        return "\n".join(lines)
    
    def _format_generic_match(self, match: Dict[str, Any], index: int) -> str:
        """
        Общее форматирование матча
        """
        participants = f"{match.get('team1', match.get('player1', 'Участник 1'))} – {match.get('team2', match.get('player2', 'Участник 2'))}"
        score = match.get('score', match.get('sets_score', '0:0'))
        
        analysis = match.get('ai_analysis', 'Анализ недоступен')
        
        lines = [
            f"{index}. 🏆 {participants}",
            f"🎯 Счет: <b>{score}</b>",
            f"📌 <i>{analysis}</i>"
        ]
        
        return "\n".join(lines)
    
    def _get_football_bet_recommendation(self, match: Dict[str, Any]) -> str:
        """
        Определение рекомендуемой ставки для футбола
        """
        score = match.get('score', '0:0')
        try:
            parts = score.split(':')
            if len(parts) == 2:
                goals1, goals2 = int(parts[0]), int(parts[1])
                if goals1 > goals2:
                    return "П1"
                elif goals2 > goals1:
                    return "П2"
        except:
            pass
        
        return "П1"  # По умолчанию
    
    def _get_tennis_bet_recommendation(self, match: Dict[str, Any]) -> str:
        """
        Определение рекомендуемой ставки для тенниса
        """
        sets_score = match.get('sets_score', '0-0')
        player1 = match.get('player1', 'Игрок 1')
        
        try:
            parts = sets_score.split('-')
            if len(parts) == 2:
                sets1, sets2 = int(parts[0]), int(parts[1])
                if sets1 > sets2:
                    return f"Победа {player1}"
                elif sets2 > sets1:
                    return f"Победа {match.get('player2', 'Игрок 2')}"
        except:
            pass
        
        return f"Победа {player1}"  # По умолчанию
    
    def _get_table_tennis_bet_recommendation(self, match: Dict[str, Any]) -> str:
        """
        Определение рекомендуемой ставки для настольного тенниса
        """
        sets_score = match.get('sets_score', '0-0')
        player1 = match.get('player1', 'Игрок 1')
        
        try:
            parts = sets_score.split('-')
            if len(parts) == 2:
                sets1, sets2 = int(parts[0]), int(parts[1])
                if sets1 > sets2:
                    return f"Победа {player1}"
        except:
            pass
        
        return f"Победа {player1}"  # По умолчанию
    
    def _get_handball_bet_recommendation(self, match: Dict[str, Any]) -> str:
        """
        Определение рекомендуемой ставки для гандбола
        """
        score = match.get('score', '0:0')
        try:
            parts = score.split(':')
            if len(parts) == 2:
                goals1, goals2 = int(parts[0]), int(parts[1])
                if goals1 > goals2:
                    return "П1"
                elif goals2 > goals1:
                    return "П2"
        except:
            pass
        
        return "П1"  # По умолчанию
    
    def _get_best_odds(self, match: Dict[str, Any], bet_type: str) -> str:
        """
        Получение лучших коэффициентов для ставки
        """
        odds_data = match.get('odds', {})
        
        # Ищем подходящие коэффициенты
        for market, values in odds_data.items():
            if isinstance(values, list) and len(values) >= 2:
                if 'П1' in bet_type or 'Победа' in bet_type:
                    return values[0] if values[0] else '1.50'
                elif 'П2' in bet_type:
                    return values[1] if len(values) > 1 and values[1] else '1.50'
        
        return '1.50'  # Коэффициент по умолчанию
    
    def _calculate_remaining_time(self, current_time: str, sport: str) -> str:
        """
        Расчет оставшегося времени матча
        """
        if sport == 'football':
            try:
                minute = int(re.search(r'(\d+)', current_time).group(1))
                remaining = 90 - minute
                if remaining > 0:
                    return f"~{remaining} мин."
                else:
                    return "Доп. время"
            except:
                pass
        
        return "В процессе"
    
    def _send_message(self, text: str) -> bool:
        """
        Отправка сообщения в Telegram
        """
        try:
            payload = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(f"{self.api_url}/sendMessage", json=payload)
            
            if response.status_code == 200:
                self.logger.info("Отчет успешно отправлен в Telegram")
                return True
            else:
                self.logger.error(f"Ошибка отправки в Telegram: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Исключение при отправке в Telegram: {e}")
            return False
    
    def _escape_markdown_v2(self, text: str) -> str:
        """
        Экранирование специальных символов для MarkdownV2
        """
        # Символы, которые нужно экранировать в MarkdownV2
        escape_chars = ['_', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        
        for char in escape_chars:
            text = text.replace(char, f'\\{char}')
        
        return text
    
    def _send_no_matches_message(self) -> bool:
        """
        Отправка сообщения об отсутствии подходящих матчей
        """
        current_time = format_moscow_time()
        next_check_time = self._calculate_next_check_time()
        
        message = f"""
🔍 На текущий момент подходящих LIVE-событий не найдено.

⏰ Следующая проверка в {next_check_time}

💎 @TrueLiveBet – Анализ на основе AI и статистики!
        """.strip()
        
        return self._send_message(message)
    
    def _calculate_next_check_time(self) -> str:
        """
        Расчет времени следующей проверки
        """
        from datetime import datetime, timedelta
        from config import CYCLE_INTERVAL_MINUTES
        
        next_time = datetime.now() + timedelta(minutes=CYCLE_INTERVAL_MINUTES)
        return next_time.strftime('%H:%M МСК')
    
    def test_connection(self) -> bool:
        """
        Тестирование соединения с Telegram API
        """
        try:
            response = requests.get(f"{self.api_url}/getMe")
            if response.status_code == 200:
                bot_info = response.json()
                self.logger.info(f"Подключение к Telegram API успешно. Бот: {bot_info.get('result', {}).get('username', 'Unknown')}")
                return True
            else:
                self.logger.error(f"Ошибка подключения к Telegram API: {response.status_code}")
                return False
        except Exception as e:
            self.logger.error(f"Исключение при тестировании Telegram API: {e}")
            return False