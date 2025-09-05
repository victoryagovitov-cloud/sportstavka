#!/bin/bash

# Скрипт установки автоматизированного аналитика спортивных ставок

echo "🎯 Установка автоматизированного аналитика спортивных ставок..."

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден. Установите Python 3.8+ и повторите попытку."
    exit 1
fi

echo "✅ Python найден: $(python3 --version)"

# Установка системных зависимостей (Ubuntu/Debian)
if command -v apt-get &> /dev/null; then
    echo "📦 Установка системных зависимостей..."
    sudo apt-get update
    sudo apt-get install -y wget gnupg curl
    
    # Установка Google Chrome
    echo "🌐 Установка Google Chrome..."
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
    sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
    sudo apt-get update
    sudo apt-get install -y google-chrome-stable
    
    # Установка ChromeDriver
    echo "🚗 Установка ChromeDriver..."
    sudo apt-get install -y chromium-chromedriver
    
    echo "✅ Системные зависимости установлены"
fi

# Создание виртуального окружения
echo "🐍 Создание виртуального окружения..."
python3 -m venv venv
source venv/bin/activate

# Установка Python зависимостей
echo "📚 Установка Python зависимостей..."
pip install --upgrade pip
pip install -r requirements.txt

# Создание необходимых директорий
echo "📁 Создание директорий..."
mkdir -p logs

# Копирование конфигурационного файла
echo "⚙️ Настройка конфигурации..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "📝 Создан файл .env из шаблона"
    echo "⚠️  ВАЖНО: Отредактируйте файл .env и установите CLAUDE_API_KEY"
fi

# Установка прав на выполнение
chmod +x run.py

echo ""
echo "🎉 Установка завершена!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Отредактируйте файл .env и установите CLAUDE_API_KEY"
echo "2. Активируйте виртуальное окружение: source venv/bin/activate"
echo "3. Запустите тестовый цикл: python run.py --test"
echo "4. Запустите в продакшене: python run.py"
echo ""
echo "📖 Подробная документация в README.md"