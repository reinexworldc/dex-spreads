#!/usr/bin/env python3
import requests
import json
import time
import logging
import os
import sys
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("paradex_api_check.log")
    ]
)
logger = logging.getLogger("paradex_api_check")

# URL API Paradex
BASE_URL = "https://api.paradex.trade/v1"
TESTNET_URL = "https://api.testnet.paradex.trade/v1"

def load_config():
    """Загружает конфигурацию из файла config.json"""
    try:
        with open("config.json", 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка при загрузке конфигурации: {e}")
        return {}

def create_headers(jwt_token=None):
    """Создаёт заголовки для запросов к API"""
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    
    if jwt_token:
        headers['Authorization'] = f'Bearer {jwt_token}'
    
    return headers

def check_api_status(use_testnet=False):
    """Проверяет доступность API Paradex"""
    try:
        url = f"{TESTNET_URL if use_testnet else BASE_URL}/status"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            status_data = response.json()
            logger.info(f"API статус: {status_data}")
            return True, status_data
        else:
            logger.error(f"Ошибка API статуса: {response.status_code} - {response.text}")
            return False, None
    except Exception as e:
        logger.error(f"Ошибка при проверке API: {e}")
        return False, None

def get_markets(jwt_token=None, use_testnet=False):
    """Получает список доступных рынков (пар) с Paradex"""
    try:
        url = f"{TESTNET_URL if use_testnet else BASE_URL}/markets"
        headers = create_headers(jwt_token)
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            markets_data = response.json()
            logger.info(f"Получено {len(markets_data)} рынков")
            return True, markets_data
        else:
            logger.error(f"Ошибка получения рынков: {response.status_code} - {response.text}")
            return False, None
    except Exception as e:
        logger.error(f"Ошибка при получении рынков: {e}")
        return False, None

def get_ticker(market, jwt_token=None, use_testnet=False):
    """Получает данные тикера для указанного рынка"""
    try:
        url = f"{TESTNET_URL if use_testnet else BASE_URL}/ticker"
        headers = create_headers(jwt_token)
        params = {'market': market}
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            ticker_data = response.json()
            logger.info(f"Получены данные тикера для {market}: {ticker_data}")
            return True, ticker_data
        else:
            logger.error(f"Ошибка получения тикера для {market}: {response.status_code} - {response.text}")
            return False, None
    except Exception as e:
        logger.error(f"Ошибка при получении тикера для {market}: {e}")
        return False, None

def get_orderbook(market, jwt_token=None, use_testnet=False):
    """Получает книгу ордеров для указанного рынка"""
    try:
        url = f"{TESTNET_URL if use_testnet else BASE_URL}/orderbook"
        headers = create_headers(jwt_token)
        params = {'market': market}
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            orderbook_data = response.json()
            logger.info(f"Получена книга ордеров для {market}, bids: {len(orderbook_data.get('bids', []))}, asks: {len(orderbook_data.get('asks', []))}")
            return True, orderbook_data
        else:
            logger.error(f"Ошибка получения книги ордеров для {market}: {response.status_code} - {response.text}")
            return False, None
    except Exception as e:
        logger.error(f"Ошибка при получении книги ордеров для {market}: {e}")
        return False, None

def get_contract_sizes(markets_data):
    """Извлекает размеры контрактов из данных о рынках"""
    contract_sizes = {}
    
    if not markets_data:
        return contract_sizes
    
    for market in markets_data:
        market_id = market.get('id')
        # Преобразуем формат ID рынка для соответствия с нашими данными
        symbol = market_id.replace('-', '_') if market_id else None
        
        if symbol:
            base_asset = market.get('baseAsset', {})
            quote_asset = market.get('quoteAsset', {})
            
            # Получаем размер контракта и шаг цены
            base_size = float(market.get('baseSize', '1.0'))
            tick_size = float(market.get('tickSize', '0.01'))
            
            contract_sizes[symbol] = base_size
            
            logger.info(f"Рынок: {market_id}, Символ: {symbol}, Размер контракта: {base_size}, "
                       f"Мин. шаг цены: {tick_size}")
    
    return contract_sizes

def save_contract_sizes(contract_sizes, filename="contract_sizes.json"):
    """Сохраняет размеры контрактов в JSON файл"""
    try:
        with open(filename, 'w') as f:
            json.dump(contract_sizes, f, indent=4)
        logger.info(f"Размеры контрактов сохранены в {filename}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при сохранении размеров контрактов: {e}")
        return False

def fetch_and_display_market_data(jwt_token=None, use_testnet=False):
    """Получает и отображает данные о рынках и ценах"""
    
    # Проверяем статус API
    api_status, status_data = check_api_status(use_testnet)
    if not api_status:
        logger.error("API Paradex недоступен, прерываю выполнение")
        return False
    
    # Получаем список рынков
    markets_success, markets_data = get_markets(jwt_token, use_testnet)
    if not markets_success or not markets_data:
        logger.error("Не удалось получить данные о рынках")
        return False
    
    # Получаем размеры контрактов
    contract_sizes = get_contract_sizes(markets_data)
    
    # Сохраняем размеры контрактов
    save_contract_sizes(contract_sizes)
    
    # Проверяем данные тикеров для основных рынков
    main_markets = ["BTC-USD-PERP", "ETH-USD-PERP", "SOL-USD-PERP"]
    market_data = []
    
    for market_id in main_markets:
        # Получаем данные тикера
        ticker_success, ticker_data = get_ticker(market_id, jwt_token, use_testnet)
        
        # Получаем книгу ордеров
        orderbook_success, orderbook_data = get_orderbook(market_id, jwt_token, use_testnet)
        
        market_info = {
            "market_id": market_id,
            "ticker": ticker_data if ticker_success else None,
            "orderbook": orderbook_data if orderbook_success else None,
            "contract_size": contract_sizes.get(market_id.replace('-', '_'), None)
        }
        
        market_data.append(market_info)
    
    # Выводим сводку
    logger.info("\n=== СВОДКА ДАННЫХ PARADEX ===")
    logger.info(f"Время проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Режим: {'Тестовая сеть (testnet)' if use_testnet else 'Основная сеть (mainnet)'}")
    logger.info(f"Всего доступных рынков: {len(markets_data)}")
    logger.info(f"Размеры контрактов получены: {len(contract_sizes)}")
    
    for market_info in market_data:
        market_id = market_info["market_id"]
        ticker = market_info["ticker"]
        orderbook = market_info["orderbook"]
        contract_size = market_info["contract_size"]
        
        logger.info(f"\nРЫНОК: {market_id}")
        logger.info(f"Размер контракта: {contract_size}")
        
        if ticker:
            logger.info(f"Тикер: Цена: {ticker.get('price')}, 24ч Объем: {ticker.get('volume24h')}")
        else:
            logger.info("Данные тикера недоступны")
        
        if orderbook:
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if bids:
                best_bid = bids[0]
                logger.info(f"Лучшая ставка (best bid): Цена: {best_bid[0]}, Объем: {best_bid[1]}")
            
            if asks:
                best_ask = asks[0]
                logger.info(f"Лучшее предложение (best ask): Цена: {best_ask[0]}, Объем: {best_ask[1]}")
            
            logger.info(f"Всего ставок: {len(bids)}, Всего предложений: {len(asks)}")
        else:
            logger.info("Данные книги ордеров недоступны")
    
    logger.info("\n=== ПРОВЕРКА ЗАВЕРШЕНА ===")
    return True

def main():
    """Основная функция"""
    logger.info("Запуск проверки API Paradex")
    
    # Загружаем конфигурацию
    config = load_config()
    paradex_config = config.get('paradex', {})
    
    # Получаем JWT токен из конфигурации или из переменной окружения
    jwt_token = paradex_config.get('jwt_token', os.environ.get('PARADEX_JWT', ''))
    
    # Определяем, использовать ли тестовую сеть
    use_testnet = paradex_config.get('testnet', False)
    
    # Если JWT токен не указан, выводим предупреждение
    if not jwt_token:
        logger.warning("JWT токен не указан. Некоторые запросы могут быть недоступны.")
    
    # Получаем и отображаем данные о рынках
    success = fetch_and_display_market_data(jwt_token, use_testnet)
    
    if success:
        logger.info("Проверка API Paradex завершена успешно")
    else:
        logger.error("Проверка API Paradex завершена с ошибками")

if __name__ == "__main__":
    main() 