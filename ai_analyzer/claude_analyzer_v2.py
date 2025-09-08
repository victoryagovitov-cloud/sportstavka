"""
Claude AI анализатор для Варианта 2 - независимый анализ матчей
Claude AI самостоятельно ищет статистику и проводит анализ
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

try:
    import anthropic
except ImportError:
    anthropic = None

from utils.claude_prompt_optimizer import ImprovedClaudePrompt

class ClaudeAnalyzerV2:
    """
    Claude AI анализатор для Варианта 2 - независимый анализ
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Инициализация Claude AI клиента
        self.client = None
        self.api_key = os.getenv('CLAUDE_API_KEY')
        
        if self.api_key and anthropic:
            try:
                self.client = anthropic.Anthropic(api_key=self.api_key)
                self.logger.info("✅ Claude AI клиент инициализирован")
            except Exception as e:
                self.logger.error(f"❌ Ошибка инициализации Claude AI: {e}")
        else:
            self.logger.warning("⚠️ CLAUDE_API_KEY не установлен или anthropic не установлен")
        
        # Настройки анализа
        self.analysis_config = {
            'model': 'claude-3-sonnet-20240229',
            'max_tokens': 4000,
            'temperature': 0.1,  # Низкая температура для консервативного анализа
            'timeout': 120       # 2 минуты на анализ
        }
        
        # Статистика работы
        self.stats = {
            'total_requests': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'total_tokens_used': 0,
            'total_cost': 0.0,
            'average_response_time': 0.0
        }
        
        # Генератор промптов
        self.prompt_generator = ImprovedClaudePrompt()
    
    def analyze_matches_independently(self, matches: List[Dict[str, Any]], 
                                    analysis_type: str = 'conservative') -> Optional[str]:
        """
        Независимый анализ матчей через Claude AI (Вариант 2)
        """
        if not matches:
            self.logger.warning("Нет матчей для анализа")
            return None
        
        if not self.client:
            self.logger.error("Claude AI клиент не инициализирован")
            return self._get_demo_analysis(matches)  # Демо-режим для тестирования
        
        try:
            self.logger.info(f"🧠 Запуск независимого анализа Claude AI для {len(matches)} матчей")
            
            start_time = time.time()
            
            # Создаем оптимизированный промпт
            prompt = self.prompt_generator.create_enhanced_prompt(matches)
            
            # Отправляем запрос к Claude AI
            response = self.client.messages.create(
                model=self.analysis_config['model'],
                max_tokens=self.analysis_config['max_tokens'],
                temperature=self.analysis_config['temperature'],
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            analysis_time = time.time() - start_time
            
            # Извлекаем ответ
            analysis_result = response.content[0].text if response.content else ""
            
            # Обновляем статистику
            self._update_stats(response, analysis_time, success=True)
            
            self.logger.info(f"✅ Claude AI анализ завершен за {analysis_time:.2f}с")
            self.logger.info(f"📊 Использовано токенов: input={response.usage.input_tokens}, output={response.usage.output_tokens}")
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка анализа Claude AI: {e}")
            self._update_stats(None, 0, success=False)
            
            # Fallback к демо-анализу
            return self._get_demo_analysis(matches)
    
    def _get_demo_analysis(self, matches: List[Dict[str, Any]]) -> str:
        """
        Демо-анализ для тестирования (когда Claude AI недоступен)
        """
        self.logger.info("🎭 Генерируем демо-анализ (Claude AI недоступен)")
        
        demo_analyses = []
        
        for i, match in enumerate(matches[:10], 1):  # Максимум 10 матчей
            team1 = match.get('team1', 'Команда А')
            team2 = match.get('team2', 'Команда Б')
            odds = match.get('odds', {})
            
            # Простой анализ коэффициентов
            p1 = float(odds.get('П1', 2.0))
            p2 = float(odds.get('П2', 2.0))
            x = float(odds.get('X', 3.0))
            
            # ИСПРАВЛЕННАЯ логика под философию неничейных матчей
            if min(p1, p2) < 1.3:
                recommendation = "ПРОПУСК"
                reason = "Слишком низкие коэффициенты, нет value"
                risk = "низкий 🟢"
            elif min(p1, p2) > 3.0:
                recommendation = "ПРОПУСК"
                reason = "Высокая неопределенность исхода"
                risk = "высокий 🔴"
            else:
                # В неничейных матчах анализируем продолжение тренда
                if p1 < p2:
                    recommendation = "СТАВКА на П1 (лидер удержит)"
                    reason = "Ведущая команда контролирует игру"
                else:
                    recommendation = "СТАВКА на П2 (отыгрыш возможен)"
                    reason = "Отстающая команда может отыграться"
                risk = "средний 🟡"
            
            demo_analysis = f"""🏆 {team1} vs {team2}
💰 MarathonBet: П1 {odds.get('П1')} | X {odds.get('X')} | П2 {odds.get('П2')}
📊 Статистика: [ДЕМО] Анализ основан только на коэффициентах
🎯 Рекомендация: {recommendation}
💡 Обоснование: {reason}
⚠️ Риск: {risk}

---"""
            
            demo_analyses.append(demo_analysis)
        
        # Формируем полный ответ
        header = f"""🤖 ДЕМО-АНАЛИЗ | 🧪 ТЕСТОВЫЙ РЕЖИМ

📊 Проанализировано: {len(demo_analyses)} из {len(matches)} доступных
⏰ Время: {datetime.now().strftime('%H:%M МСК')}
🎯 Фокус: Консервативные value opportunities
⚠️ ВНИМАНИЕ: Это демо-режим, реальный Claude AI даст более качественный анализ

{'='*50}

"""
        
        footer = f"""{'='*50}

💡 Демо-анализ основан только на коэффициентах MarathonBet
🛡️ Реальный Claude AI найдет независимую статистику команд
📊 Для активации Claude AI установите CLAUDE_API_KEY
🤖 Демо-режим: только для тестирования структуры

⏰ Следующий анализ через активный интервал"""
        
        return header + '\n\n'.join(demo_analyses) + '\n\n' + footer
    
    def _update_stats(self, response, analysis_time: float, success: bool):
        """Обновление статистики работы анализатора"""
        self.stats['total_requests'] += 1
        
        if success and response:
            self.stats['successful_analyses'] += 1
            
            # Токены и стоимость
            if hasattr(response, 'usage'):
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens
                total_tokens = input_tokens + output_tokens
                
                self.stats['total_tokens_used'] += total_tokens
                
                # Примерная стоимость (может отличаться от реальной)
                cost_per_1k_input = 0.003  # $0.003 за 1K input токенов
                cost_per_1k_output = 0.015  # $0.015 за 1K output токенов
                
                request_cost = (input_tokens / 1000 * cost_per_1k_input + 
                              output_tokens / 1000 * cost_per_1k_output)
                
                self.stats['total_cost'] += request_cost
        else:
            self.stats['failed_analyses'] += 1
        
        # Среднее время ответа
        if self.stats['total_requests'] > 0:
            total_time = self.stats.get('total_time', 0) + analysis_time
            self.stats['total_time'] = total_time
            self.stats['average_response_time'] = total_time / self.stats['total_requests']
    
    def get_analysis_stats(self) -> Dict[str, Any]:
        """Получение статистики работы анализатора"""
        success_rate = 0.0
        if self.stats['total_requests'] > 0:
            success_rate = (self.stats['successful_analyses'] / self.stats['total_requests']) * 100
        
        avg_cost_per_analysis = 0.0
        if self.stats['successful_analyses'] > 0:
            avg_cost_per_analysis = self.stats['total_cost'] / self.stats['successful_analyses']
        
        return {
            'total_requests': self.stats['total_requests'],
            'successful_analyses': self.stats['successful_analyses'],
            'failed_analyses': self.stats['failed_analyses'],
            'success_rate': round(success_rate, 2),
            'total_tokens_used': self.stats['total_tokens_used'],
            'total_cost': round(self.stats['total_cost'], 4),
            'average_cost_per_analysis': round(avg_cost_per_analysis, 4),
            'average_response_time': round(self.stats['average_response_time'], 2),
            'client_available': self.client is not None
        }
    
    def reset_stats(self):
        """Сброс статистики"""
        self.stats = {
            'total_requests': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'total_tokens_used': 0,
            'total_cost': 0.0,
            'average_response_time': 0.0
        }
        self.logger.info("📊 Статистика анализатора сброшена")
    
    def test_claude_connection(self) -> bool:
        """Тестирование соединения с Claude AI"""
        if not self.client:
            return False
        
        try:
            # Простой тестовый запрос
            response = self.client.messages.create(
                model=self.analysis_config['model'],
                max_tokens=100,
                messages=[{"role": "user", "content": "Привет! Это тестовый запрос."}]
            )
            
            self.logger.info("✅ Соединение с Claude AI работает")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка соединения с Claude AI: {e}")
            return False

# Глобальная функция для создания анализатора
def create_claude_analyzer_v2(logger: Optional[logging.Logger] = None) -> ClaudeAnalyzerV2:
    """Создание анализатора Claude AI для Варианта 2"""
    return ClaudeAnalyzerV2(logger)