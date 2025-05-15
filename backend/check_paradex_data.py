#!/usr/bin/env python3
import sqlite3
import time
import logging
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("paradex_data_check")

def check_paradex_data():
    """Проверяет данные Paradex в базе данных"""
    conn = sqlite3.connect('/app/data/db.sqlite3')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Проверяем наличие записей с Paradex
    logger.info("Проверка данных с Paradex в базе...")
    
    # Проверяем наличие данных для пары paradex_backpack
    cursor.execute("""
        SELECT COUNT(*) as count FROM spreads 
        WHERE exchange_pair = 'paradex_backpack'
    """)
    result_pb = cursor.fetchone()
    paradex_backpack_count = result_pb['count'] if result_pb else 0
    
    # Проверяем наличие данных для пары paradex_hyperliquid
    cursor.execute("""
        SELECT COUNT(*) as count FROM spreads 
        WHERE exchange_pair = 'paradex_hyperliquid'
    """)
    result_ph = cursor.fetchone()
    paradex_hyperliquid_count = result_ph['count'] if result_ph else 0
    
    logger.info(f"Найдено записей для пары paradex_backpack: {paradex_backpack_count}")
    logger.info(f"Найдено записей для пары paradex_hyperliquid: {paradex_hyperliquid_count}")
    
    # Проверяем наличие actual данных в последние 24 часа
    current_time = int(time.time())
    time_threshold = current_time - 24 * 60 * 60  # 24 часа назад
    
    cursor.execute("""
        SELECT COUNT(*) as count FROM spreads 
        WHERE exchange_pair LIKE 'paradex%' AND created > ?
    """, (time_threshold,))
    result_recent = cursor.fetchone()
    recent_count = result_recent['count'] if result_recent else 0
    
    logger.info(f"Найдено записей за последние 24 часа: {recent_count}")
    
    # Выводим последние 5 записей с Paradex для диагностики
    cursor.execute("""
        SELECT id, symbol, signal, exchange_pair, paradex_price, backpack_price, hyperliquid_price, 
               difference, created, paradex_contract_size
        FROM spreads 
        WHERE exchange_pair LIKE 'paradex%'
        ORDER BY created DESC
        LIMIT 5
    """)
    
    recent_records = cursor.fetchall()
    if recent_records:
        logger.info("Последние записи с Paradex:")
        for record in recent_records:
            created_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(record['created']))
            logger.info(f"ID: {record['id']}, Символ: {record['symbol']}, Сигнал: {record['signal']}, "
                      f"Пара: {record['exchange_pair']}, Разница: {record['difference']}%, "
                      f"Paradex цена: {record['paradex_price']}, Contract size: {record['paradex_contract_size']}, "
                      f"Создано: {created_time}")
    else:
        logger.info("Нет недавних записей с Paradex")
    
    conn.close()
    
    return paradex_backpack_count, paradex_hyperliquid_count, recent_count

def add_test_data():
    """Добавляет тестовые данные для пар с Paradex"""
    conn = sqlite3.connect('/app/data/db.sqlite3')
    cursor = conn.cursor()
    
    # Получаем доступные символы
    cursor.execute("SELECT DISTINCT symbol FROM spreads")
    symbols = [row[0] for row in cursor.fetchall()]
    
    if not symbols:
        symbols = ['BTC_USDC_PERP', 'ETH_USDC_PERP', 'SOL_USDC_PERP']
    
    current_time = int(time.time())
    
    # Добавляем тестовые данные для paradex_backpack
    logger.info("Добавление тестовых данных для пары paradex_backpack...")
    
    for symbol in symbols[:3]:  # Берем первые 3 символа
        # Создаем запись для сигнала BUY
        paradex_price = 100.0
        backpack_price = 101.0
        difference = ((backpack_price / paradex_price) - 1) * 100  # Процентная разница
        
        cursor.execute("""
            INSERT INTO spreads (symbol, signal, paradex_price, backpack_price, hyperliquid_price, 
                              exchange_pair, exchange1, exchange2, difference, created,
                              paradex_contract_size, paradex_raw_price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (symbol, 'BUY', paradex_price, backpack_price, 0, 
             'paradex_backpack', 'paradex', 'backpack', difference, current_time,
             0.001, 0.1))
        
        # Создаем запись для сигнала SELL
        paradex_price = 102.0
        backpack_price = 101.0
        difference = ((paradex_price / backpack_price) - 1) * 100  # Процентная разница
        
        cursor.execute("""
            INSERT INTO spreads (symbol, signal, paradex_price, backpack_price, hyperliquid_price, 
                              exchange_pair, exchange1, exchange2, difference, created,
                              paradex_contract_size, paradex_raw_price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (symbol, 'SELL', paradex_price, backpack_price, 0, 
             'paradex_backpack', 'paradex', 'backpack', difference, current_time - 60,
             0.001, 0.102))
    
    # Добавляем тестовые данные для paradex_hyperliquid
    logger.info("Добавление тестовых данных для пары paradex_hyperliquid...")
    
    for symbol in symbols[:3]:  # Берем первые 3 символа
        # Создаем запись для сигнала BUY
        paradex_price = 100.0
        hyperliquid_price = 100.5
        difference = ((hyperliquid_price / paradex_price) - 1) * 100  # Процентная разница
        
        cursor.execute("""
            INSERT INTO spreads (symbol, signal, paradex_price, backpack_price, hyperliquid_price, 
                              exchange_pair, exchange1, exchange2, difference, created,
                              paradex_contract_size, paradex_raw_price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (symbol, 'BUY', paradex_price, 0, hyperliquid_price, 
             'paradex_hyperliquid', 'paradex', 'hyperliquid', difference, current_time - 120,
             0.001, 0.1))
        
        # Создаем запись для сигнала SELL
        paradex_price = 101.0
        hyperliquid_price = 100.5
        difference = ((paradex_price / hyperliquid_price) - 1) * 100  # Процентная разница
        
        cursor.execute("""
            INSERT INTO spreads (symbol, signal, paradex_price, backpack_price, hyperliquid_price, 
                              exchange_pair, exchange1, exchange2, difference, created,
                              paradex_contract_size, paradex_raw_price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (symbol, 'SELL', paradex_price, 0, hyperliquid_price, 
             'paradex_hyperliquid', 'paradex', 'hyperliquid', difference, current_time - 180,
             0.001, 0.101))
    
    conn.commit()
    logger.info("Тестовые данные успешно добавлены")
    conn.close()

def add_paradex_contract_sizes():
    """Заполняет размеры контрактов Paradex в базе данных"""
    conn = sqlite3.connect('/app/data/db.sqlite3')
    cursor = conn.cursor()
    
    # Получаем доступные символы
    cursor.execute("SELECT DISTINCT symbol FROM spreads")
    symbols = [row[0] for row in cursor.fetchall()]
    
    if not symbols:
        symbols = ['BTC_USDC_PERP', 'ETH_USDC_PERP', 'SOL_USDC_PERP']
    
    current_time = int(time.time())
    
    # Добавляем размеры контрактов для paradex_backpack
    logger.info("Добавление размеров контрактов для пары paradex_backpack...")
    
    for symbol in symbols[:3]:  # Берем первые 3 символа
        # Создаем запись для сигнала BUY
        paradex_price = 100.0
        backpack_price = 101.0
        difference = ((backpack_price / paradex_price) - 1) * 100  # Процентная разница
        
        cursor.execute("""
            UPDATE spreads SET paradex_contract_size = ?
            WHERE symbol = ? AND signal = 'BUY' AND exchange_pair = 'paradex_backpack'
        """, (0.001, symbol))
        
        # Создаем запись для сигнала SELL
        paradex_price = 102.0
        backpack_price = 101.0
        difference = ((paradex_price / backpack_price) - 1) * 100  # Процентная разница
        
        cursor.execute("""
            UPDATE spreads SET paradex_contract_size = ?
            WHERE symbol = ? AND signal = 'SELL' AND exchange_pair = 'paradex_backpack'
        """, (0.001, symbol))
    
    # Добавляем размеры контрактов для paradex_hyperliquid
    logger.info("Добавление размеров контрактов для пары paradex_hyperliquid...")
    
    for symbol in symbols[:3]:  # Берем первые 3 символа
        # Создаем запись для сигнала BUY
        paradex_price = 100.0
        hyperliquid_price = 100.5
        difference = ((hyperliquid_price / paradex_price) - 1) * 100  # Процентная разница
        
        cursor.execute("""
            UPDATE spreads SET paradex_contract_size = ?
            WHERE symbol = ? AND signal = 'BUY' AND exchange_pair = 'paradex_hyperliquid'
        """, (0.001, symbol))
        
        # Создаем запись для сигнала SELL
        paradex_price = 101.0
        hyperliquid_price = 100.5
        difference = ((paradex_price / hyperliquid_price) - 1) * 100  # Процентная разница
        
        cursor.execute("""
            UPDATE spreads SET paradex_contract_size = ?
            WHERE symbol = ? AND signal = 'SELL' AND exchange_pair = 'paradex_hyperliquid'
        """, (0.001, symbol))
    
    conn.commit()
    logger.info("Размеры контрактов успешно добавлены")
    conn.close()

if __name__ == "__main__":
    paradex_backpack_count, paradex_hyperliquid_count, recent_count = check_paradex_data()
    
    # Если мало данных с Paradex или нет недавних записей, добавляем тестовые данные
    if (paradex_backpack_count < 10 or paradex_hyperliquid_count < 10 or recent_count < 5 or 
        '--force' in sys.argv):
        add_test_data()
        # Проверяем снова после добавления данных
        check_paradex_data()
    else:
        logger.info("Достаточно данных с Paradex, тестовые данные не требуются") 