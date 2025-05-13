#!/usr/bin/env python
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
import time

# Настраиваем пути для корректного импорта
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("paradex_contract_test.log")
    ]
)
logger = logging.getLogger("paradex_contract_test")

# Импортируем классы из основного проекта
from py.paradex import Paradex  

def load_config():
    """Загружает конфигурацию из файла config.json"""
    try:
        with open("config.json", 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        logger.info("Конфигурация успешно загружена")
        return config
    except Exception as e:
        logger.error(f"Не удалось загрузить конфигурацию: {e}")
        # Возвращаем значения по умолчанию
        return {
            "PARADEX_DATA": {
                "JWT": "",
                "TESTNET": True
            }
        }

async def check_contract_sizes(paradex):
    """Проверяет загрузку размеров контрактов из API"""
    logger.info("=== Проверка загрузки размеров контрактов ===")
    
    # Создаем HTTP сессию
    await paradex._create_session()
    
    # Загружаем размеры контрактов
    await paradex._load_contract_sizes()
    
    # Проверяем загруженные размеры
    logger.info(f"Всего загружено {len(paradex.contract_sizes)} размеров контрактов")
    
    # Выводим размеры для основных активов
    important_symbols = ["BTC-USD-PERP", "ETH-USD-PERP", "SOL-USD-PERP"]
    
    for symbol in important_symbols:
        if symbol in paradex.contract_sizes:
            contract_size = paradex.contract_sizes[symbol]
            logger.info(f"Контракт {symbol}: {contract_size}")
        else:
            logger.error(f"Размер контракта для {symbol} не найден!")

async def test_price_normalization(paradex):
    """Тестирует нормализацию цен с размерами контрактов"""
    logger.info("=== Тестирование нормализации цен ===")
    
    # Тестовые данные для важных активов и их ожидаемые результаты
    test_cases = [
        {
            "symbol": "BTC-USD-PERP",
            "raw_bid": 93.5,       # ~$93.5 за 0.001 BTC
            "raw_ask": 94.0,
            "expected_bid": 93500,  # ~$93,500 за 1 BTC
            "expected_ask": 94000   # ~$94,000 за 1 BTC
        },
        {
            "symbol": "ETH-USD-PERP",
            "raw_bid": 18.2,       # ~$18.2 за 0.01 ETH
            "raw_ask": 18.4,
            "expected_bid": 1820,   # ~$1,820 за 1 ETH
            "expected_ask": 1840    # ~$1,840 за 1 ETH
        },
        {
            "symbol": "SOL-USD-PERP",
            "raw_bid": 14.1,       # ~$14.1 за 0.1 SOL
            "raw_ask": 14.2,
            "expected_bid": 141,    # ~$141 за 1 SOL
            "expected_ask": 142     # ~$142 за 1 SOL
        }
    ]
    
    for test in test_cases:
        symbol = test["symbol"]
        raw_bid = test["raw_bid"]
        raw_ask = test["raw_ask"]
        
        # Получаем размер контракта
        contract_size = paradex.contract_sizes.get(symbol, 1.0)
        
        if contract_size <= 0:
            logger.error(f"Некорректный размер контракта для {symbol}: {contract_size}")
            continue
        
        # Нормализуем цены
        normalized_bid = raw_bid / contract_size
        normalized_ask = raw_ask / contract_size
        
        # Проверяем результаты
        expected_bid = test["expected_bid"]
        expected_ask = test["expected_ask"]
        
        logger.info(f"Тест {symbol}:")
        logger.info(f"  Размер контракта: {contract_size}")
        logger.info(f"  Сырые цены: bid={raw_bid}, ask={raw_ask}")
        logger.info(f"  Нормализованные цены: bid={normalized_bid}, ask={normalized_ask}")
        
        bid_error = abs(normalized_bid - expected_bid) / expected_bid * 100
        ask_error = abs(normalized_ask - expected_ask) / expected_ask * 100
        
        if bid_error < 5 and ask_error < 5:
            logger.info(f"  ✅ Результат ВЕРНЫЙ (погрешность: bid={bid_error:.2f}%, ask={ask_error:.2f}%)")
        else:
            logger.error(f"  ❌ Результат НЕВЕРНЫЙ: ожидалось bid={expected_bid}, ask={expected_ask}")
            logger.error(f"  Погрешность: bid={bid_error:.2f}%, ask={ask_error:.2f}%")

async def test_raw_price_validation(paradex):
    """Тестирует валидацию сырых цен"""
    logger.info("=== Тестирование валидации сырых цен ===")
    
    test_cases = [
        {"symbol": "BTC-USD-PERP", "raw_price": 90, "expected": True},    # ~$90 за 0.001 BTC - валидно
        {"symbol": "BTC-USD-PERP", "raw_price": 10, "expected": False},   # слишком низкая
        {"symbol": "BTC-USD-PERP", "raw_price": 200, "expected": False},  # слишком высокая
        
        {"symbol": "ETH-USD-PERP", "raw_price": 20, "expected": True},    # ~$20 за 0.01 ETH - валидно
        {"symbol": "ETH-USD-PERP", "raw_price": 5, "expected": False},    # слишком низкая
        {"symbol": "ETH-USD-PERP", "raw_price": 60, "expected": False},   # слишком высокая
        
        {"symbol": "SOL-USD-PERP", "raw_price": 15, "expected": True},    # ~$15 за 0.1 SOL - валидно
        {"symbol": "SOL-USD-PERP", "raw_price": 2, "expected": False},    # слишком низкая
        {"symbol": "SOL-USD-PERP", "raw_price": 60, "expected": False}    # слишком высокая
    ]
    
    for test in test_cases:
        symbol = test["symbol"]
        raw_price = test["raw_price"]
        expected = test["expected"]
        
        result = paradex._is_raw_price_valid(symbol, raw_price)
        
        if result == expected:
            logger.info(f"✅ {symbol} с ценой {raw_price}: валидация {'прошла' if result else 'не прошла'} (ожидалось: {expected})")
        else:
            logger.error(f"❌ {symbol} с ценой {raw_price}: валидация {'прошла' if result else 'не прошла'}, но ожидалось {expected}")

async def main():
    """
    Основная функция для тестирования контрактов Paradex
    """
    logger.info("=" * 80)
    logger.info("ДИАГНОСТИКА РАЗМЕРОВ КОНТРАКТОВ PARADEX")
    logger.info("=" * 80)
    
    # Загружаем конфигурацию
    config = load_config()
    paradex_config = config.get('PARADEX_DATA', {})
    
    # Создаем экземпляр класса Paradex
    paradex = Paradex(paradex_config)
    
    try:
        # Тестируем загрузку размеров контрактов
        await check_contract_sizes(paradex)
        
        # Тестируем нормализацию цен
        await test_price_normalization(paradex)
        
        # Тестируем валидацию сырых цен
        await test_raw_price_validation(paradex)
        
        logger.info("=" * 80)
        logger.info("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении тестов: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    try:
        # Запускаем асинхронный код
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Программа остановлена пользователем.")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        import traceback
        logger.error(traceback.format_exc()) 