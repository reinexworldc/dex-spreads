import sqlite3
import os
import logging
import time

# Получаем логгер для модуля
logger = logging.getLogger("paradex_app.db_update")

# Функция для определения пути к базе данных
def get_db_path():
    """
    Определяет путь к файлу базы данных в зависимости от окружения
    """
    if os.path.exists('/app'):
        # В Docker-контейнере
        db_dir = '/app/data'
    else:
        # Локальный запуск
        db_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        # Создаем директорию, если не существует
        os.makedirs(db_dir, exist_ok=True)
    
    return os.path.join(db_dir, 'db.sqlite3')

def create_spreads_table_if_not_exists():
    """
    Создает таблицу spreads, если она не существует
    """
    logger.info("Проверка наличия таблицы spreads...")
    
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Проверяем, существует ли таблица spreads
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='spreads'")
        if not cursor.fetchone():
            logger.info("Таблица spreads не найдена. Создаем...")
            
            # Создаем таблицу spreads
            cursor.execute("""
                CREATE TABLE spreads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    signal TEXT,
                    backpack_price REAL,
                    paradex_price REAL,
                    hyperliquid_price REAL DEFAULT 0,
                    created INTEGER,
                    exchange_pair TEXT,
                    exchange1 TEXT,
                    exchange2 TEXT,
                    difference REAL DEFAULT 0,
                    paradex_raw_price REAL DEFAULT 0,
                    paradex_raw_bid REAL DEFAULT 0,
                    paradex_raw_ask REAL DEFAULT 0,
                    paradex_contract_size REAL DEFAULT 1.0,
                    drift_price REAL DEFAULT 0
                )
            """)
            
            conn.commit()
            logger.info("Таблица spreads успешно создана")
        else:
            logger.info("Таблица spreads уже существует")
    
    except Exception as e:
        logger.error(f"Ошибка при создании таблицы spreads: {e}")
        conn.rollback()
    finally:
        conn.close()

def update_database_structure():
    """
    Обновляет структуру базы данных, добавляя недостающие столбцы для поддержки Drift
    """
    logger.info("Проверка и обновление структуры базы данных...")
    
    # Подключаемся к базе данных
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Проверяем существующие столбцы в таблице spreads
        cursor.execute("PRAGMA table_info(spreads)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        # Добавляем столбец drift_price, если его нет
        if 'drift_price' not in column_names:
            logger.info("Добавление столбца drift_price в таблицу spreads...")
            cursor.execute("ALTER TABLE spreads ADD COLUMN drift_price REAL DEFAULT 0")
        
        # Добавляем столбцы exchange1 и exchange2, если их нет
        if 'exchange1' not in column_names:
            logger.info("Добавление столбца exchange1 в таблицу spreads...")
            cursor.execute("ALTER TABLE spreads ADD COLUMN exchange1 TEXT DEFAULT ''")
        
        if 'exchange2' not in column_names:
            logger.info("Добавление столбца exchange2 в таблицу spreads...")
            cursor.execute("ALTER TABLE spreads ADD COLUMN exchange2 TEXT DEFAULT ''")
        
        # Добавляем столбцы для сырых цен Paradex
        if 'paradex_raw_price' not in column_names:
            logger.info("Добавление столбца paradex_raw_price в таблицу spreads...")
            cursor.execute("ALTER TABLE spreads ADD COLUMN paradex_raw_price REAL DEFAULT 0")
        
        if 'paradex_raw_bid' not in column_names:
            logger.info("Добавление столбца paradex_raw_bid в таблицу spreads...")
            cursor.execute("ALTER TABLE spreads ADD COLUMN paradex_raw_bid REAL DEFAULT 0")
        
        if 'paradex_raw_ask' not in column_names:
            logger.info("Добавление столбца paradex_raw_ask в таблицу spreads...")
            cursor.execute("ALTER TABLE spreads ADD COLUMN paradex_raw_ask REAL DEFAULT 0")
        
        if 'paradex_contract_size' not in column_names:
            logger.info("Добавление столбца paradex_contract_size в таблицу spreads...")
            cursor.execute("ALTER TABLE spreads ADD COLUMN paradex_contract_size REAL DEFAULT 1.0")
        
        # Подтверждаем изменения
        conn.commit()
        logger.info("Структура базы данных успешно обновлена")
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении базы данных: {e}")
        conn.rollback()
    finally:
        conn.close()

def update_difference_values():
    """
    Заполняет колонку difference на основе существующих данных о ценах,
    используя логарифмический метод для более точного расчета спредов.
    """
    logger.info("Обновление значений разницы цен (логарифмический метод)...")
    
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Получаем все записи с заполненными ценами и exchange_pair
        cursor.execute("""
            SELECT id, symbol, signal, paradex_price, backpack_price, hyperliquid_price, exchange_pair, exchange1, exchange2
            FROM spreads
            WHERE exchange_pair IS NOT NULL AND exchange_pair != ''
        """)
        
        rows = cursor.fetchall()
        logger.info(f"Найдено {len(rows)} записей для обновления")
        
        # Группируем данные по символу и паре бирж
        grouped_data = {}
        for row in rows:
            symbol = row['symbol']
            exchange_pair = row['exchange_pair']
            key = f"{symbol}_{exchange_pair}"
            
            if key not in grouped_data:
                grouped_data[key] = []
                
            grouped_data[key].append(row)
        
        total_updated = 0
        
        # Обрабатываем каждую группу отдельно
        for key, group_rows in grouped_data.items():
            logger.info(f"Обработка группы: {key}, записей: {len(group_rows)}")
            
            updated_in_group = 0
            
            for row in group_rows:
                exchange_pair = row['exchange_pair']
                if not exchange_pair or '_' not in exchange_pair:
                    continue
                    
                exchange1, exchange2 = exchange_pair.split('_')
                price1 = row[f'{exchange1}_price']
                price2 = row[f'{exchange2}_price']
                
                if price1 is None or price2 is None or price1 <= 0 or price2 <= 0:
                    continue
                
                # Вычисляем разницу цен
                if row['signal'] == 'BUY':
                    # Формула для логарифмического спреда
                    log_spread = 100 * (price2 / price1 - 1)
                    difference = log_spread
                else:  # SELL
                    # Формула для логарифмического спреда
                    log_spread = 100 * (price1 / price2 - 1)
                    difference = log_spread
                
                # Обновляем запись в базе данных
                cursor.execute("""
                    UPDATE spreads 
                    SET difference = ? 
                    WHERE id = ?
                """, (difference, row['id']))
                
                updated_in_group += 1
            
            # Логируем статистику по группе
            logger.info(f"Обновлено в группе {key}: {updated_in_group} записей")
            
            total_updated += updated_in_group
            
        # Подтверждаем изменения
        conn.commit()
        
        # Выводим общую статистику
        logger.info(f"Всего обновлено {total_updated} записей")
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении значений разницы: {e}")
        conn.rollback()
    finally:
        conn.close()

def create_indexes():
    """
    Создает индексы для оптимизации запросов
    """
    logger.info("Создание индексов для оптимизации запросов...")
    
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Индекс для быстрого поиска по символу
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbol ON spreads (symbol)")
        
        # Индекс для быстрого поиска по времени создания
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_created ON spreads (created)")
        
        # Индекс для быстрого поиска по паре бирж
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_exchange_pair ON spreads (exchange_pair)")
        
        # Индекс для быстрого поиска по сигналу
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_signal ON spreads (signal)")
        
        # Составной индекс для частых запросов
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbol_exchange_pair ON spreads (symbol, exchange_pair)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbol_created ON spreads (symbol, created)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbol_exchange_pair_created ON spreads (symbol, exchange_pair, created)")
        
        conn.commit()
        logger.info("Индексы успешно созданы")
    
    except Exception as e:
        logger.error(f"Ошибка при создании индексов: {e}")
        conn.rollback()
    finally:
        conn.close()

def update_db():
    """
    Основная функция обновления базы данных
    """
    # Получаем путь к базе данных
    db_path = get_db_path()
    db_dir = os.path.dirname(db_path)
    
    # Создаем директорию для базы данных, если она не существует
    os.makedirs(db_dir, exist_ok=True)
    
    # Настраиваем логирование
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('paradex_data_importer.log')
        ]
    )
    
    # Создаем таблицу spreads, если она не существует
    create_spreads_table_if_not_exists()
    
    # Обновляем структуру базы данных
    update_database_structure()
    
    # Создаем индексы для оптимизации запросов
    create_indexes()

def update_exchange_fields():
    """
    Заполняет поля exchange1 и exchange2 на основе значения exchange_pair
    """
    logger.info("Обновление полей exchange1 и exchange2...")
    
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Получаем все записи с заполненным exchange_pair
        cursor.execute("""
            SELECT id, exchange_pair, exchange1, exchange2
            FROM spreads
            WHERE exchange_pair IS NOT NULL AND exchange_pair != ''
        """)
        
        rows = cursor.fetchall()
        logger.info(f"Найдено {len(rows)} записей для обновления полей exchange1 и exchange2")
        
        updated_count = 0
        
        for row in rows:
            id, exchange_pair, exchange1, exchange2 = row
            
            # Если поля exchange1 и exchange2 уже заполнены, пропускаем
            if exchange1 and exchange2 and exchange1 != '' and exchange2 != '':
                continue
                
            # Разбиваем exchange_pair на exchange1 и exchange2
            exchanges = exchange_pair.split('_')
            if len(exchanges) != 2:
                continue
                
            # Обновляем поля exchange1 и exchange2
            cursor.execute("""
                UPDATE spreads
                SET exchange1 = ?, exchange2 = ?
                WHERE id = ?
            """, (exchanges[0], exchanges[1], id))
            
            updated_count += 1
        
        conn.commit()
        logger.info(f"Обновлено {updated_count} записей")
    
    except Exception as e:
        logger.error(f"Ошибка при обновлении полей exchange1 и exchange2: {e}")
        conn.rollback()
    finally:
        conn.close()

def cleanup_old_data(retention_days=1):
    """
    Удаляет старые данные из базы данных для оптимизации размера и производительности.
    По умолчанию оставляет данные только за последний день.
    
    :param retention_days: Количество дней, за которые сохраняются данные
    """
    logger.info(f"Очистка старых данных (старше {retention_days} дней)...")
    
    # Рассчитываем временную метку для удаления данных
    retention_seconds = retention_days * 24 * 60 * 60
    cutoff_timestamp = int(time.time()) - retention_seconds
    
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Получаем количество записей до удаления
        cursor.execute("SELECT COUNT(*) FROM spreads")
        total_records_before = cursor.fetchone()[0]
        logger.info(f"Всего записей в базе данных: {total_records_before}")
        
        # Удаляем старые записи
        cursor.execute("DELETE FROM spreads WHERE created < ?", (cutoff_timestamp,))
        deleted_count = cursor.rowcount
        
        # Выполняем VACUUM для освобождения места на диске
        conn.execute("VACUUM")
        
        conn.commit()
        
        # Получаем количество записей после удаления
        cursor.execute("SELECT COUNT(*) FROM spreads")
        total_records_after = cursor.fetchone()[0]
        
        logger.info(f"Удалено {deleted_count} устаревших записей")
        logger.info(f"Осталось записей в базе данных: {total_records_after}")
        
        # Если было удалено много записей, перестраиваем индексы
        if deleted_count > 1000:
            logger.info("Перестраиваем индексы для оптимизации производительности...")
            conn.execute("ANALYZE")
    
    except Exception as e:
        logger.error(f"Ошибка при очистке старых данных: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    # Сначала очищаем старые данные, оставляя только последний день
    cleanup_old_data(1)
    logger.info("Очистка старых данных завершена")
    
    # Затем запускаем обычные процессы обновления
    update_database_structure()
    logger.info("Проверка структуры базы данных завершена")
    update_db()
    # Создаем индексы для оптимизации запросов
    create_indexes()
    # Обновляем поля exchange1 и exchange2
    update_exchange_fields()
    # Заполняем значения разницы для существующих записей
    update_difference_values()
    logger.info("Все обновления базы данных завершены") 