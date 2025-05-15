#!/usr/bin/env python3
import sqlite3
import time
import logging
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("paradex_structure_check")

def check_database_connection():
    try:
        conn = sqlite3.connect('/app/data/db.sqlite3')
        conn.close()
        return True
    except:
        return False

def check_database_structure():
    """Проверяет структуру данных Paradex в базе данных"""
    conn = sqlite3.connect('/app/data/db.sqlite3')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Получаем общую статистику
    cursor.execute("SELECT COUNT(*) as total FROM spreads")
    total_count = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as count FROM spreads WHERE paradex_price > 0")
    paradex_count = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM spreads WHERE exchange_pair LIKE 'paradex%'")
    paradex_pair_count = cursor.fetchone()['count']
    
    logger.info(f"Всего записей в базе: {total_count}")
    logger.info(f"Записей с ценой Paradex > 0: {paradex_count}")
    logger.info(f"Записей с exchange_pair LIKE 'paradex%': {paradex_pair_count}")
    
    # Проверяем записи с ценой Paradex, но без exchange_pair
    cursor.execute("""
        SELECT COUNT(*) as count FROM spreads 
        WHERE paradex_price > 0 AND (exchange_pair IS NULL OR exchange_pair NOT LIKE 'paradex%')
    """)
    missing_pair_count = cursor.fetchone()['count']
    logger.info(f"Записей с ценой Paradex > 0 но без правильного exchange_pair: {missing_pair_count}")
    
    if missing_pair_count > 0:
        # Исследуем некоторые из этих проблемных записей
        cursor.execute("""
            SELECT id, symbol, signal, paradex_price, backpack_price, hyperliquid_price, 
                  exchange_pair, exchange1, exchange2, created
            FROM spreads 
            WHERE paradex_price > 0 AND (exchange_pair IS NULL OR exchange_pair NOT LIKE 'paradex%')
            ORDER BY created DESC
            LIMIT 5
        """)
        
        logger.info("Примеры записей с ценой Paradex, но без правильного exchange_pair:")
        for row in cursor.fetchall():
            created_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(row['created']))
            logger.info(f"ID: {row['id']}, Символ: {row['symbol']}, Сигнал: {row['signal']}, "
                      f"Paradex: {row['paradex_price']}, Backpack: {row['backpack_price']}, "
                      f"Hyperliquid: {row['hyperliquid_price']}, "
                      f"exchange_pair: {row['exchange_pair']}, "
                      f"exchange1: {row['exchange1']}, exchange2: {row['exchange2']}, "
                      f"Создано: {created_time}")
    
    # Проверяем записи с Paradex и другими биржами, но без правильного exchange_pair
    cursor.execute("""
        SELECT COUNT(*) as count FROM spreads 
        WHERE paradex_price > 0 AND backpack_price > 0 
          AND (exchange_pair IS NULL OR exchange_pair != 'paradex_backpack')
    """)
    pb_wrong_pair = cursor.fetchone()['count']
    
    cursor.execute("""
        SELECT COUNT(*) as count FROM spreads 
        WHERE paradex_price > 0 AND hyperliquid_price > 0 
          AND (exchange_pair IS NULL OR exchange_pair != 'paradex_hyperliquid')
    """)
    ph_wrong_pair = cursor.fetchone()['count']
    
    logger.info(f"Записей Paradex-Backpack с неправильным exchange_pair: {pb_wrong_pair}")
    logger.info(f"Записей Paradex-Hyperliquid с неправильным exchange_pair: {ph_wrong_pair}")
    
    # Посмотрим, какие вообще exchange_pair есть в базе
    cursor.execute("""
        SELECT DISTINCT exchange_pair, COUNT(*) as count
        FROM spreads
        WHERE exchange_pair IS NOT NULL
        GROUP BY exchange_pair
        ORDER BY count DESC
    """)
    
    logger.info("Существующие пары бирж в базе:")
    for row in cursor.fetchall():
        logger.info(f"Пара: {row['exchange_pair']}, количество записей: {row['count']}")
    
    # Проверяем корректность данных
    cursor.execute("""
        SELECT symbol, COUNT(*) as count
        FROM spreads
        WHERE paradex_price > 0
        GROUP BY symbol
        ORDER BY count DESC
        LIMIT 10
    """)
    
    logger.info("\nСимволы с данными Paradex:")
    for row in cursor.fetchall():
        logger.info(f"Символ: {row['symbol']}, количество записей: {row['count']}")
    
    conn.close()
    
    logger.info("\nРекомендации:")
    if missing_pair_count > 0:
        logger.info("1. Необходимо обновить поле exchange_pair для записей с Paradex")
    if pb_wrong_pair > 0 or ph_wrong_pair > 0:
        logger.info("2. Необходимо исправить неправильные значения exchange_pair")

def fix_exchange_pairs():
    """Обновляет поля exchange_pair, exchange1, exchange2 для записей с Paradex"""
    conn = sqlite3.connect('/app/data/db.sqlite3')
    cursor = conn.cursor()
    
    logger.info("Исправление полей exchange_pair, exchange1, exchange2 для записей с Paradex...")
    
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
    
    conn.commit()
    conn.close()
    
    return pb_updated + ph_updated

def add_missing_data():
    if not os.path.exists('db.sqlite3'):
        print(f"База данных не найдена. Создаю новую...")
        create_database()
    
    conn = sqlite3.connect('/app/data/db.sqlite3')
    cursor = conn.cursor()

if __name__ == "__main__":
    # Сначала проверяем структуру
    check_database_structure()
    
    # Запрашиваем подтверждение на исправление
    answer = input("\nХотите исправить структуру данных? (y/n): ")
    if answer.lower() in ('y', 'yes', 'д', 'да'):
        updated = fix_exchange_pairs()
        logger.info(f"Всего обновлено {updated} записей")
        # Проверяем структуру после исправления
        logger.info("\nСтруктура после исправления:")
        check_database_structure()
    else:
        logger.info("Исправление отменено") 