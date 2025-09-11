"""
Скрипт для настройки MCP Browser окружения
"""
import subprocess
import sys
import os
import logging

def install_requirements():
    """Установка зависимостей для MCP Browser"""
    print("🔧 Установка зависимостей для MCP Browser...")
    
    try:
        # Устанавливаем MCP SDK
        subprocess.run([sys.executable, "-m", "pip", "install", "mcp"], check=True)
        print("✅ MCP SDK установлен")
        
        # Устанавливаем дополнительные зависимости
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements_mcp.txt"], check=True)
        print("✅ Дополнительные зависимости установлены")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка установки зависимостей: {e}")
        return False

def install_browser_use():
    """Установка browser-use MCP сервера"""
    print("🌐 Установка browser-use MCP сервера...")
    
    try:
        # Устанавливаем browser-use через uvx
        subprocess.run(["uvx", "browser-use", "--help"], check=True)
        print("✅ browser-use MCP сервер доступен")
        return True
        
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"❌ Ошибка установки browser-use: {e}")
        print("💡 Попробуйте установить uvx: pip install uv")
        return False

def test_mcp_connection():
    """Тест подключения к MCP серверу"""
    print("🧪 Тестирование подключения к MCP серверу...")
    
    try:
        import asyncio
        from mcp_browser_client import test_mcp_browser
        
        # Запускаем тест
        asyncio.run(test_mcp_browser())
        print("✅ MCP подключение работает")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования MCP: {e}")
        return False

def main():
    """Основная функция настройки"""
    print("🚀 Настройка MCP Browser окружения")
    print("=" * 50)
    
    # 1. Устанавливаем зависимости
    if not install_requirements():
        print("❌ Не удалось установить зависимости")
        return False
    
    # 2. Проверяем browser-use
    if not install_browser_use():
        print("❌ Не удалось установить browser-use")
        return False
    
    # 3. Тестируем подключение
    if not test_mcp_connection():
        print("❌ Не удалось подключиться к MCP серверу")
        return False
    
    print("=" * 50)
    print("🎉 MCP Browser окружение настроено успешно!")
    print("💡 Теперь можно использовать MCPBetBoomScraper в коде")
    
    return True

if __name__ == "__main__":
    main()