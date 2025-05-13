#!/usr/bin/env python3
import sqlite3
import time
import json
import sys
import os
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("paradex_data_check.log")
    ]
)
logger = logging.getLogger("paradex_data_check")

def get_db_connection():
    """Создает соединение с базой данных"""
    conn = sqlite3.connect('db.sqlite3')
    conn.row_factory = sqlite3.Row
    return conn

def update_exchange_pairs():
    """Обновляет поля exchange_pair, exchange1, exchange2 для записей с Paradex"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        logger.info("Обновление полей exchange_pair, exchange1, exchange2 для записей с Paradex...")
        
        # Обновляем записи где paradex_price > 0 и backpack_price > 0
        cursor.execute("""
            UPDATE spreads
            SET exchange_pair = 'paradex_backpack',
                exchange1 = 'paradex',
                exchange2 = 'backpack'
            WHERE paradex_price > 0 AND backpack_price > 0
              AND (exchange_pair IS NULL OR exchange_pair != 'paradex_backpack')
        """)
        pb_updated = cursor.rowcount
        logger.info(f"Обновлено записей Paradex-Backpack: {pb_updated}")
        
        # Обновляем записи где paradex_price > 0 и hyperliquid_price > 0
        cursor.execute("""
            UPDATE spreads
            SET exchange_pair = 'paradex_hyperliquid',
                exchange1 = 'paradex',
                exchange2 = 'hyperliquid'
            WHERE paradex_price > 0 AND hyperliquid_price > 0
              AND (exchange_pair IS NULL OR exchange_pair != 'paradex_hyperliquid')
        """)
        ph_updated = cursor.rowcount
        logger.info(f"Обновлено записей Paradex-Hyperliquid: {ph_updated}")
        
        # Обновляем поле difference для записей с Paradex
        cursor.execute("""
            UPDATE spreads
            SET difference = 
                CASE 
                    WHEN signal = 'BUY' AND exchange_pair = 'paradex_backpack' 
                        THEN ((backpack_price / paradex_price) - 1) * 100
                    WHEN signal = 'SELL' AND exchange_pair = 'paradex_backpack' 
                        THEN ((paradex_price / backpack_price) - 1) * 100
                    WHEN signal = 'BUY' AND exchange_pair = 'paradex_hyperliquid' 
                        THEN ((hyperliquid_price / paradex_price) - 1) * 100
                    WHEN signal = 'SELL' AND exchange_pair = 'paradex_hyperliquid' 
                        THEN ((paradex_price / hyperliquid_price) - 1) * 100
                    ELSE difference
                END
            WHERE (exchange_pair = 'paradex_backpack' OR exchange_pair = 'paradex_hyperliquid')
        """)
        diff_updated = cursor.rowcount
        logger.info(f"Обновлено значений разницы: {diff_updated}")
        
        # Обновляем поле paradex_contract_size если оно не установлено
        cursor.execute("""
            UPDATE spreads
            SET paradex_contract_size = 
                CASE 
                    WHEN symbol LIKE 'BTC%' THEN 0.001
                    WHEN symbol LIKE 'ETH%' THEN 0.01
                    WHEN symbol LIKE 'SOL%' THEN 0.1
                    WHEN symbol LIKE 'AVAX%' THEN 0.1
                    WHEN symbol LIKE 'BNB%' THEN 0.01
                    ELSE 1.0
                END
            WHERE (exchange_pair LIKE 'paradex%') AND 
                  (paradex_contract_size IS NULL OR paradex_contract_size <= 0)
        """)
        size_updated = cursor.rowcount
        logger.info(f"Обновлено значений размера контракта: {size_updated}")
        
        # Обновляем сырые цены paradex_raw_price если они не установлены
        cursor.execute("""
            UPDATE spreads
            SET paradex_raw_price = paradex_price * paradex_contract_size
            WHERE (exchange_pair LIKE 'paradex%') AND 
                  (paradex_raw_price IS NULL OR paradex_raw_price <= 0) AND
                  paradex_price > 0 AND paradex_contract_size > 0
        """)
        raw_updated = cursor.rowcount
        logger.info(f"Обновлено сырых цен: {raw_updated}")
        
        conn.commit()
        conn.close()
        
        return pb_updated + ph_updated + diff_updated + size_updated + raw_updated
    
    except Exception as e:
        logger.error(f"Ошибка при обновлении полей: {e}")
        import traceback
        traceback.print_exc()
        return 0

def check_paradex_data():
    """Проверяет наличие данных с Paradex в базе данных"""
    conn = get_db_connection()
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
               difference, created, paradex_contract_size, paradex_raw_price
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
            raw_price = record.get('paradex_raw_price', 'N/A')
            logger.info(f"ID: {record['id']}, Символ: {record['symbol']}, Сигнал: {record['signal']}, "
                      f"Пара: {record['exchange_pair']}, Разница: {record['difference']}%, "
                      f"Paradex цена: {record['paradex_price']}, Contract size: {record['paradex_contract_size']}, "
                      f"Raw price: {raw_price}, "
                      f"Создано: {created_time}")
    else:
        logger.info("Нет недавних записей с Paradex")
    
    conn.close()
    
    return paradex_backpack_count, paradex_hyperliquid_count, recent_count

def main():
    """Основная функция"""
    logger.info("Запуск проверки и обновления данных Paradex")
    
    # Проверяем наличие данных с Paradex
    paradex_backpack_count, paradex_hyperliquid_count, recent_count = check_paradex_data()
    
    # Обновляем поля в существующих записях
    logger.info("Обновление полей в существующих записях...")
    updated_count = update_exchange_pairs()
    logger.info(f"Всего обновлено {updated_count} записей")
    
    # Проверяем данные еще раз после обновления
    if updated_count > 0:
        logger.info("Повторная проверка данных после обновления:")
        check_paradex_data()
    
    logger.info("Работа завершена.")

if __name__ == "__main__":
    main() 