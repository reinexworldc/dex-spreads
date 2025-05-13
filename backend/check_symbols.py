#!/usr/bin/env python3
import sqlite3
import time
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("paradex_symbols_check")

def check_paradex_symbols():
    """Проверяет по каким символам есть данные Paradex"""
    conn = sqlite3.connect('db.sqlite3')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Получаем символы с данными Paradex
    cursor.execute("""
        SELECT symbol, COUNT(*) as count,
               MIN(created) as first_created,
               MAX(created) as last_created
        FROM spreads
        WHERE paradex_price > 0
        GROUP BY symbol
        ORDER BY count DESC
    """)
    
    rows = cursor.fetchall()
    
    logger.info(f"Найдено {len(rows)} символов с данными Paradex:")
    
    for row in rows:
        first_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(row['first_created']))
        last_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(row['last_created']))
        
        # Вычисляем период в днях
        period_days = (row['last_created'] - row['first_created']) / (60 * 60 * 24)
        
        logger.info(f"Символ: {row['symbol']}, записей: {row['count']}, "
                  f"период: {period_days:.1f} дней, "
                  f"первая запись: {first_time}, последняя запись: {last_time}")
    
    # Получаем доступные символы в системе
    cursor.execute("SELECT DISTINCT symbol FROM spreads")
    all_symbols = cursor.fetchall()
    
    logger.info(f"\nВсего доступно {len(all_symbols)} символов в базе")
    
    # Смотрим пример последних записей с Paradex
    cursor.execute("""
        SELECT id, symbol, signal, exchange_pair, paradex_price, backpack_price, hyperliquid_price, 
               difference, created, paradex_contract_size
        FROM spreads 
        WHERE paradex_price > 0
        ORDER BY created DESC
        LIMIT 10
    """)
    
    recent_records = cursor.fetchall()
    if recent_records:
        logger.info("\nПоследние записи с Paradex:")
        
        for record in recent_records:
            created_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(record['created']))
            
            # Проверяем существование колонки paradex_raw_price
            has_raw_price = False
            try:
                raw_price = record['paradex_raw_price']
                has_raw_price = True
            except IndexError:
                raw_price = 'N/A'
            
            logger.info(f"ID: {record['id']}, Символ: {record['symbol']}, Сигнал: {record['signal']}, "
                      f"Пара: {record['exchange_pair']}, Разница: {record['difference']}%, "
                      f"Paradex цена: {record['paradex_price']}, "
                      f"Contract size: {record['paradex_contract_size']}, "
                      f"Создано: {created_time}")
    
    conn.close()

if __name__ == "__main__":
    check_paradex_symbols() 