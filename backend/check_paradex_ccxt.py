#!/usr/bin/env python3
import ccxt
import json
import time
import logging
import os
import sys
from datetime import datetime
from pprint import pprint

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("paradex_ccxt_check.log")
    ]
)
logger = logging.getLogger("paradex_ccxt_check")

def load_config():
    """Загружает конфигурацию из файла config.json"""
    try:
        with open("config.json", 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка при загрузке конфигурации: {e}")
        return {}

def check_exchange_availability():
    """Проверяет доступность биржи Paradex в CCXT"""
    try:
        # Получаем список доступных бирж
        exchanges = ccxt.exchanges
        
        # Проверяем наличие Paradex в списке
        if 'paradex' in exchanges:
            logger.info("Биржа Paradex поддерживается в CCXT!")
            return True
        else:
            logger.warning("Биржа Paradex НЕ найдена в списке поддерживаемых CCXT бирж")
            # Предлагаем альтернативы
            logger.info("Доступные биржи в CCXT:")
            # Выводим первые 10 бирж и количество всех доступных
            logger.info(f"Всего доступно {len(exchanges)} бирж, первые 10: {exchanges[:10]}")
            return False
    except Exception as e:
        logger.error(f"Ошибка при проверке доступности: {e}")
        return False

def check_using_alternative_exchange():
    """Проверяет альтернативные биржи с похожими API"""
    try:
        # Проверяем использование dYdX как возможной альтернативы
        logger.info("Попытка использования dYdX как альтернативы...")
        exchange = ccxt.dydx({
            'enableRateLimit': True,
        })
        
        # Проверяем подключение
        logger.info(f"Подключение к {exchange.id}...")
        markets = exchange.load_markets()
        
        logger.info(f"Успешно подключено к {exchange.id}")
        logger.info(f"Доступно {len(markets)} рынков")
        
        # Получаем несколько примеров пар
        symbols = list(markets.keys())[:5]
        logger.info(f"Примеры доступных пар: {symbols}")
        
        return True, exchange, symbols
    except Exception as e:
        logger.error(f"Ошибка при проверке альтернативной биржи: {e}")
        return False, None, None

def try_connecting_via_ccxt(exchange_id, api_key=None, secret_key=None):
    """Пытается подключиться к бирже через CCXT"""
    try:
        # Проверяем наличие класса биржи
        if not hasattr(ccxt, exchange_id):
            logger.error(f"Биржа {exchange_id} не найдена в CCXT")
            return False, None
        
        # Создаем настройки
        config = {
            'enableRateLimit': True,
        }
        
        if api_key:
            config['apiKey'] = api_key
        
        if secret_key:
            config['secret'] = secret_key
        
        # Создаем объект биржи
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class(config)
        
        # Проверяем подключение
        logger.info(f"Подключение к {exchange.id}...")
        markets = exchange.load_markets()
        
        logger.info(f"Успешно подключено к {exchange.id}")
        logger.info(f"Доступно {len(markets)} рынков")
        
        return True, exchange
    except ccxt.BaseError as e:
        logger.error(f"Ошибка CCXT при подключении к {exchange_id}: {e}")
        return False, None
    except Exception as e:
        logger.error(f"Общая ошибка при подключении к {exchange_id}: {e}")
        return False, None

def direct_api_call():
    """Прямой вызов API Paradex через requests"""
    try:
        import requests
        
        # API URL
        base_url = "https://api.paradex.trade/v1"
        
        # Запрос к API
        response = requests.get(f"{base_url}/markets", timeout=10)
        
        if response.status_code == 200:
            markets_data = response.json()
            logger.info(f"Прямой API запрос успешен. Получено {len(markets_data)} рынков")
            return True, markets_data
        else:
            logger.error(f"Ошибка прямого API запроса: {response.status_code} - {response.text}")
            return False, None
    except Exception as e:
        logger.error(f"Ошибка при выполнении прямого API запроса: {e}")
        return False, None

def check_paradex_implementation():
    """Проверяет, есть ли класс для Paradex, который можно расширить"""
    try:
        # Путь к директории Python
        python_dir = os.path.dirname(sys.executable)
        
        # Путь к установленным пакетам
        site_packages = os.path.join(python_dir, 'lib', 'site-packages')
        
        # Путь к директории ccxt
        ccxt_dir = os.path.join(site_packages, 'ccxt')
        
        # Проверяем существование файла paradex.py
        paradex_file = os.path.join(ccxt_dir, 'paradex.py')
        paradex_exists = os.path.exists(paradex_file)
        
        logger.info(f"Файл реализации Paradex ({paradex_file}): {'существует' if paradex_exists else 'не существует'}")
        
        # Проверяем похожие файлы
        if not paradex_exists:
            logger.info("Поиск похожих реализаций бирж в CCXT...")
            
            try:
                # Получаем список файлов в директории ccxt
                files = [f for f in os.listdir(ccxt_dir) if f.endswith('.py') and not f.startswith('_')]
                
                # Находим файлы с похожими API (например, dYdX)
                similar_files = [f for f in files if 'dydx' in f or 'perp' in f]
                
                logger.info(f"Похожие реализации: {similar_files}")
                
                return False, similar_files
            except Exception as e:
                logger.error(f"Ошибка при поиске похожих реализаций: {e}")
                return False, []
        
        return paradex_exists, []
    except Exception as e:
        logger.error(f"Ошибка при проверке реализации Paradex: {e}")
        return False, []

def check_paradex_api():
    """Проверяет API Paradex и выполняет все необходимые проверки"""
    logger.info("Запуск проверки Paradex через CCXT")
    
    # Проверяем доступность Paradex в CCXT
    exchange_available = check_exchange_availability()
    
    if exchange_available:
        # Если Paradex доступен, пытаемся подключиться
        logger.info("Попытка подключения к Paradex через CCXT...")
        
        # Загружаем конфигурацию
        config = load_config()
        paradex_config = config.get('paradex', {})
        
        # Получаем API ключи
        api_key = paradex_config.get('api_key', '')
        secret_key = paradex_config.get('secret_key', '')
        
        success, exchange = try_connecting_via_ccxt('paradex', api_key, secret_key)
        
        if success and exchange:
            logger.info("Успешное подключение к Paradex через CCXT!")
            
            # Получаем список доступных пар
            symbols = list(exchange.markets.keys())
            logger.info(f"Доступные пары на Paradex: {symbols[:10]} (показаны первые 10 из {len(symbols)})")
            
            # Получаем информацию о нескольких парах
            for symbol in symbols[:3]:
                try:
                    ticker = exchange.fetch_ticker(symbol)
                    logger.info(f"Тикер для {symbol}: {ticker}")
                    
                    orderbook = exchange.fetch_order_book(symbol)
                    logger.info(f"Стакан для {symbol}: bids={len(orderbook['bids'])}, asks={len(orderbook['asks'])}")
                except Exception as e:
                    logger.error(f"Ошибка при получении данных для {symbol}: {e}")
        else:
            logger.error("Не удалось подключиться к Paradex через CCXT")
    else:
        # Проверяем реализацию Paradex
        has_implementation, similar_implementations = check_paradex_implementation()
        
        if has_implementation:
            logger.info("Найдена реализация Paradex, но она не в списке поддерживаемых бирж")
        else:
            logger.info("Реализация Paradex не найдена")
            
            # Пробуем альтернативную биржу
            alternative_success, alt_exchange, alt_symbols = check_using_alternative_exchange()
            
            if alternative_success:
                logger.info("Успешно подключились к альтернативной бирже")
                
                # Получаем информацию о нескольких парах
                for symbol in alt_symbols:
                    try:
                        ticker = alt_exchange.fetch_ticker(symbol)
                        logger.info(f"Тикер для {symbol}: {ticker}")
                    except Exception as e:
                        logger.error(f"Ошибка при получении данных для {symbol}: {e}")
            
            # Выполняем прямой API вызов
            direct_success, direct_data = direct_api_call()
            
            if direct_success:
                logger.info("Прямой API вызов успешен")
                # Выводим первые несколько рынков
                if direct_data and len(direct_data) > 0:
                    logger.info("Примеры рынков:")
                    for market in direct_data[:3]:
                        logger.info(f"Рынок: {market}")
    
    logger.info("Проверка завершена")

if __name__ == "__main__":
    check_paradex_api() 