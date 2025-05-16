from flask import Flask, render_template, request, jsonify
import sqlite3
import time
import logging
from datetime import datetime, timedelta
import json
from flask_cors import CORS
import os

# Настройка логгера для Flask приложения
logger = logging.getLogger("paradex_app.web")

app = Flask(__name__)
# Настраиваем CORS для всех источников, чтобы React-приложение могло делать запросы
# Более детальная настройка CORS для лучшей безопасности и производительности
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:3000", "http://localhost", "http://77.110.105.98"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept"],
        "supports_credentials": True,
        "max_age": 3600  # Кеширование CORS preflight запросов на 1 час
    }
})

# Доступные пары бирж
EXCHANGE_PAIRS = [
    ("paradex", "backpack"),
    ("paradex", "hyperliquid"),
    ("backpack", "hyperliquid")
]

# Названия бирж для отображения
EXCHANGE_NAMES = {
    "paradex": "Paradex",
    "backpack": "Backpack",
    "hyperliquid": "Hyperliquid"
}

def get_db_connection():
    # Определяем путь к базе данных в зависимости от окружения
    if os.path.exists('/app'):
        # В Docker-контейнере
        db_path = '/app/data/db.sqlite3'
    else:
        # Локальный запуск
        db_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        db_path = os.path.join(db_dir, 'db.sqlite3')
    
    conn = sqlite3.connect(db_path)
    
    # Оптимизация SQLite для улучшения производительности
    conn.execute("PRAGMA journal_mode = WAL")  # Использование WAL режима журнала
    conn.execute("PRAGMA synchronous = NORMAL")  # Меньше синхронизаций с диском
    conn.execute("PRAGMA cache_size = 10000")  # Увеличиваем размер кеша
    conn.execute("PRAGMA temp_store = MEMORY")  # Временные таблицы в памяти
    conn.execute("PRAGMA mmap_size = 30000000000")  # Используем memory-mapped I/O
    
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS spreads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            signal TEXT,
            backpack_price REAL,
            paradex_price REAL,
            hyperliquid_price REAL,
            exchange_pair TEXT,
            created INTEGER
        )
    ''')
    # Insert sample data if table is empty


@app.route('/')
def index():
    # Перенаправляем на страницу largest_spreads
    return largest_spreads()


@app.route('/largest_spreads')
def largest_spreads():
    time_range = request.args.get('time_range', '24h')
    time_filters = {
        '1m': 1 * 60,
        '5m': 5 * 60,
        '15m': 15 * 60,
        '30m': 30 * 60,
        '1h': 60 * 60,
        '3h': 3 * 60 * 60,
        '6h': 6 * 60 * 60,
        '24h': 24 * 60 * 60
    }
    
    # Убедимся, что time_range находится среди доступных фильтров
    if time_range not in time_filters:
        time_range = '24h'
        
    time_threshold = int(time.time()) - time_filters.get(time_range, 24 * 60 * 60)

    conn = get_db_connection()
    
    # Получим все доступные пары бирж
    exchange_pairs_db = conn.execute('SELECT DISTINCT exchange_pair FROM spreads WHERE exchange_pair IS NOT NULL').fetchall()
    available_pairs = [pair['exchange_pair'] for pair in exchange_pairs_db if pair['exchange_pair']]
    
    # Если нет данных с явно указанными парами, используем предопределенные
    if not available_pairs:
        available_pairs = [f"{pair[0]}_{pair[1]}" for pair in EXCHANGE_PAIRS]
    
    # Создаем базовый запрос
    query = '''
        SELECT symbol, signal, backpack_price, paradex_price, hyperliquid_price, exchange_pair, created, difference
        FROM spreads
        WHERE created >= ? AND (
            (backpack_price != 0 AND paradex_price != 0) OR
            (backpack_price != 0 AND hyperliquid_price != 0) OR
            (paradex_price != 0 AND hyperliquid_price != 0)
        )
    '''
    
    rows = conn.execute(query, (time_threshold,)).fetchall()
    symbols = conn.execute('SELECT DISTINCT symbol FROM spreads WHERE created >= ?', (time_threshold,)).fetchall()
    conn.close()

    largest_spreads = []
    for symbol in symbols:
        symbol_name = symbol['symbol']
        symbol_rows = [row for row in rows if row['symbol'] == symbol_name]
        
        if not symbol_rows:
            continue

        # Для каждой пары бирж находим максимальный спред
        pair_spreads = {}
        
        for pair in available_pairs:
            # Фильтруем строки с валидными данными для этой пары
            pair_rows = [row for row in symbol_rows if row['exchange_pair'] == pair]
            
            if pair_rows:
                pair_spreads[pair] = {
                    'largest_buy': max([row['difference'] for row in pair_rows if row['signal'] == 'BUY'], default=0),
                    'largest_sell': max([row['difference'] for row in pair_rows if row['signal'] == 'SELL'], default=0)
                }
        
        # Если нет валидных спредов для этого символа, пропускаем
        if not pair_spreads:
            continue
        
        # Находим максимальный спред среди всех пар
        max_spread = 0
        max_pair = ""
        for pair_name, spreads in pair_spreads.items():
            pair_max = max(spreads['largest_buy'], spreads['largest_sell'])
            if pair_max > max_spread:
                max_spread = pair_max
                max_pair = pair_name

        # Форматируем название пары
        formatted_pair = max_pair
        if "_" in max_pair:
            ex1, ex2 = max_pair.split("_")
            formatted_pair = f"{EXCHANGE_NAMES.get(ex1, ex1)} - {EXCHANGE_NAMES.get(ex2, ex2)}"

        # Добавляем данные в результат
        spread_info = {
            'symbol': symbol_name,
            'max_spread': max_spread,
            'max_pair': max_pair,
            'formatted_pair': formatted_pair,
            'pair_spreads': pair_spreads
        }
        largest_spreads.append(spread_info)

    # Сортируем по максимальному спреду
    largest_spreads.sort(key=lambda x: x['max_spread'], reverse=True)

    return render_template('largest_spreads.html', largest_spreads=largest_spreads, time_range=time_range)


@app.route('/largest_spreads_api')
def largest_spreads_api():
    """API для получения данных о крупнейших спредах в формате JSON"""
    time_range = request.args.get('time_range', '24h')
    time_filters = {
        '1m': 1 * 60,
        '5m': 5 * 60,
        '15m': 15 * 60,
        '30m': 30 * 60,
        '1h': 60 * 60,
        '3h': 3 * 60 * 60,
        '6h': 6 * 60 * 60,
        '24h': 24 * 60 * 60
    }
    
    # Валидация time_range
    if time_range not in time_filters:
        time_range = '24h'
        
    time_threshold = int(time.time()) - time_filters.get(time_range, 24 * 60 * 60)

    conn = get_db_connection()
    
    try:
        # Получим все доступные пары бирж
        exchange_pairs_db = conn.execute('SELECT DISTINCT exchange_pair FROM spreads WHERE exchange_pair IS NOT NULL').fetchall()
        available_pairs = [pair['exchange_pair'] for pair in exchange_pairs_db if pair['exchange_pair']]
        
        # Если нет данных с явно указанными парами, используем предопределенные
        if not available_pairs:
            available_pairs = [f"{pair[0]}_{pair[1]}" for pair in EXCHANGE_PAIRS]
        
        # Создаем базовый запрос
        query = '''
            SELECT symbol, signal, backpack_price, paradex_price, hyperliquid_price, exchange_pair, created, difference
            FROM spreads
            WHERE created >= ? AND (
                (backpack_price != 0 AND paradex_price != 0) OR
                (backpack_price != 0 AND hyperliquid_price != 0) OR
                (paradex_price != 0 AND hyperliquid_price != 0)
            )
            LIMIT 5000
        '''
        
        rows = conn.execute(query, (time_threshold,)).fetchall()
        symbols = conn.execute('SELECT DISTINCT symbol FROM spreads WHERE created >= ?', (time_threshold,)).fetchall()
        
        largest_spreads = []
        for symbol in symbols:
            symbol_name = symbol['symbol']
            symbol_rows = [row for row in rows if row['symbol'] == symbol_name]
            
            if not symbol_rows:
                continue

            # Для каждой пары бирж находим максимальный спред
            pair_spreads = {}
            
            for pair in available_pairs:
                # Фильтруем строки с валидными данными для этой пары
                pair_rows = [row for row in symbol_rows if row['exchange_pair'] == pair]
                
                if pair_rows:
                    pair_spreads[pair] = {
                        'largest_buy': max([row['difference'] for row in pair_rows if row['signal'] == 'BUY'], default=0),
                        'largest_sell': max([row['difference'] for row in pair_rows if row['signal'] == 'SELL'], default=0)
                    }
            
            # Если нет валидных спредов для этого символа, пропускаем
            if not pair_spreads:
                continue
            
            # Находим максимальный спред среди всех пар
            max_spread = 0
            max_pair = ""
            for pair_name, spreads in pair_spreads.items():
                pair_max = max(spreads['largest_buy'], spreads['largest_sell'])
                if pair_max > max_spread:
                    max_spread = pair_max
                    max_pair = pair_name

            # Форматируем название пары
            formatted_pair = max_pair
            if "_" in max_pair:
                ex1, ex2 = max_pair.split("_")
                formatted_pair = f"{EXCHANGE_NAMES.get(ex1, ex1)} - {EXCHANGE_NAMES.get(ex2, ex2)}"

            # Добавляем данные в результат
            spread_info = {
                'symbol': symbol_name,
                'max_spread': max_spread,
                'max_pair': max_pair,
                'formatted_pair': formatted_pair,
                'pair_spreads': pair_spreads
            }
            largest_spreads.append(spread_info)

        # Сортируем по максимальному спреду
        largest_spreads.sort(key=lambda x: x['max_spread'], reverse=True)
        
        # Добавляем информацию о временном диапазоне
        response = {
            'time_range': time_range,
            'spreads': largest_spreads
        }

        return jsonify(largest_spreads)
    
    except Exception as e:
        logger.error(f"Ошибка при получении данных о крупнейших спредах: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route('/data')
def get_data():
    symbol = request.args.get('symbol', '')
    time_range = request.args.get('time_range', '24h')
    sort_by = request.args.get('sort_by', 'created')
    sort_order = request.args.get('sort_order', 'desc')
    since = request.args.get('since', None)
    # Параметр для фильтрации по паре бирж
    exchange_pair = request.args.get('exchange_pair', 'paradex_backpack')
    
    # Логирование запроса
    logger.info(f"Запрос данных: symbol={symbol}, time_range={time_range}, exchange_pair={exchange_pair}, since={since}")
    
    # Разбираем пару бирж на отдельные биржи
    if '_' in exchange_pair:
        exchange1, exchange2 = exchange_pair.split('_')
    else:
        # По умолчанию paradex и backpack
        exchange1, exchange2 = 'paradex', 'backpack'

    time_filters = {
        '1m': 1 * 60,
        '5m': 5 * 60,
        '15m': 15 * 60,
        '30m': 30 * 60,
        '1h': 60 * 60,
        '3h': 3 * 60 * 60,
        '6h': 6 * 60 * 60,
        '24h': 24 * 60 * 60
    }
    
    # Убедимся, что time_range находится среди доступных фильтров
    if time_range not in time_filters:
        time_range = '24h'
        
    time_threshold = int(time.time()) - time_filters.get(time_range, 24 * 60 * 60)
    
    # Логирование вычисления времени
    logger.info(f"Временной фильтр: {time_range} => {time_filters.get(time_range)} секунд, порог: {time_threshold}")

    conn = get_db_connection()
    
    # Проверяем наличие полей для сырых цен Paradex
    has_raw_prices = False
    has_columns = conn.execute("PRAGMA table_info(spreads)").fetchall()
    column_names = [column[1] for column in has_columns]
    
    if "paradex_raw_price" in column_names or "paradex_raw_ask" in column_names or "paradex_raw_bid" in column_names:
        has_raw_prices = True
        logger.debug("Обнаружены поля для сырых цен Paradex")
    
    # Используем новое поле exchange_pair для фильтрации, если оно есть
    query = f'''
        SELECT id, symbol, signal, backpack_price, paradex_price, hyperliquid_price, created, difference
        FROM spreads
        WHERE symbol = ? AND {exchange1}_price != 0 AND {exchange2}_price != 0
    '''
    
    # Если есть поле exchange_pair, используем его для фильтрации
    if "exchange_pair" in column_names:
        # Базовый запрос с учетом возможного наличия сырых цен
        if has_raw_prices:
            query = f'''
                SELECT id, symbol, signal, backpack_price, paradex_price, hyperliquid_price, 
                       created, difference, exchange_pair, exchange1, exchange2,
                       paradex_raw_price, paradex_raw_ask, paradex_raw_bid, paradex_contract_size
                FROM spreads
                WHERE symbol = ? AND exchange_pair = ?
            '''
        else:
            query = f'''
                SELECT id, symbol, signal, backpack_price, paradex_price, hyperliquid_price, 
                       created, difference, exchange_pair, exchange1, exchange2
                FROM spreads
                WHERE symbol = ? AND exchange_pair = ?
            '''
        params = [symbol, exchange_pair]
    else:
        # Старый вариант запроса
        params = [symbol]

    if since:
        try:
            # Преобразуем timestamp из миллисекунд (JavaScript) в секунды (SQLite)
            # и добавляем небольшой отступ для предотвращения дублирования данных
            since_timestamp = float(since) / 1000.0
            # Используем >= вместо > чтобы не пропустить записи с тем же временем
            query += ' AND created >= ?'
            params.append(since_timestamp)
            logger.info(f"Запрос с временной меткой: {since} мс -> {since_timestamp} с")
        except (ValueError, TypeError):
            # Если возникла ошибка при преобразовании, используем стандартный порог
            query += ' AND created >= ?'
            params.append(time_threshold)
            logger.warning(f"Некорректная временная метка: {since}, используем временной порог: {time_threshold}")
    else:
        # Ограничиваем по времени только если не указан since
        query += ' AND created >= ?'
        params.append(time_threshold)
    
    # Добавляем сортировку
    query += f' ORDER BY {sort_by} {sort_order}'
    
    # Добавляем ограничение на количество записей
    query += ' LIMIT 1000'
    
    # Логирование итогового SQL-запроса
    logger.debug(f"SQL-запрос: {query}, параметры: {params}")
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    
    results = []
    for row in rows:
        # Определяем пару бирж
        if "exchange_pair" in column_names and row['exchange_pair']:
            exch1, exch2 = row['exchange1'], row['exchange2']
        else:
            exch1, exch2 = exchange1, exchange2
            
        # Определяем цены для каждой биржи
        price1 = row[f'{exch1}_price']
        price2 = row[f'{exch2}_price']
        
        # Получаем сырые цены для Paradex, если они доступны
        has_paradex = 'paradex' in [exch1, exch2]
        paradex_raw_price = None
        paradex_contract_size = 1.0
        
        if has_paradex and has_raw_prices:
            # Проверяем, какие поля сырых цен доступны
            if 'paradex_raw_price' in row.keys():
                paradex_raw_price = row['paradex_raw_price']
            elif 'paradex_raw_ask' in row.keys() and 'paradex_raw_bid' in row.keys():
                # Используем ask или bid в зависимости от сигнала
                paradex_raw_price = row['paradex_raw_ask'] if row['signal'] == 'SELL' else row['paradex_raw_bid']
            
            # Получаем размер контракта, если доступен
            if 'paradex_contract_size' in row.keys():
                paradex_contract_size = row['paradex_contract_size'] or 1.0
        
        # Рассчитываем разницу, если ее нет
        difference = row['difference'] if 'difference' in row.keys() else ((price2 / price1 - 1) * 100 if row['signal'] == 'BUY' else (price1 / price2 - 1) * 100)
        
        # Определяем, какая биржа покупка, а какая продажа
        buy_exchange = exch1 if row['signal'] == 'BUY' else exch2
        sell_exchange = exch2 if row['signal'] == 'BUY' else exch1
        
        buy_price = price1 if row['signal'] == 'BUY' else price2
        sell_price = price2 if row['signal'] == 'BUY' else price1
        
        # Форматируем имена бирж в нормальный вид
        formatted_exch1 = EXCHANGE_NAMES.get(exch1, exch1.capitalize())
        formatted_exch2 = EXCHANGE_NAMES.get(exch2, exch2.capitalize())
        
        # Добавляем цены в формате для фронтенда
        point = {
            'id': row['id'],
            'symbol': row['symbol'],
            'signal': row['signal'],
            'difference': difference,
            'buy_exchange': buy_exchange,
            'sell_exchange': sell_exchange,
            'buy_price': buy_price,
            'sell_price': sell_price,
            'created': row['created'] * 1000 if row['created'] < 9999999999 else row['created'],  # Конвертируем в миллисекунды для JS
            
            # Добавляем поля, необходимые для правильного отображения в таблице
            'exchange1': exch1,
            'exchange2': exch2,
            'formatted_exchange1': formatted_exch1,
            'formatted_exchange2': formatted_exch2,
            f'{exch1}_price': price1,
            f'{exch2}_price': price2
        }
        
        # Добавляем информацию о сырых ценах Paradex, если есть
        if has_paradex and paradex_raw_price is not None:
            point['paradex_raw_price'] = paradex_raw_price
            point['paradex_contract_size'] = paradex_contract_size
            point['has_raw_prices'] = True
        
        results.append(point)
    
    # Логируем результаты
    logger.info(f"Найдено {len(results)} записей")
    
    # Важно! Фронтенд ожидает массив, а не объект
    return jsonify(results)


@app.route('/mirror_data')
def get_mirror_data():
    symbol = request.args.get('symbol', '')
    time_range = request.args.get('time_range', '24h')
    sort_by = request.args.get('sort_by', 'created')
    sort_order = request.args.get('sort_order', 'desc')
    since = request.args.get('since', None)
    # Параметр для фильтрации по паре бирж
    exchange_pair = request.args.get('exchange_pair', 'paradex_backpack')
    
    # Логирование запроса
    logger.info(f"Запрос зеркальных данных: symbol={symbol}, time_range={time_range}, exchange_pair={exchange_pair}, since={since}")
    
    # Разбираем пару бирж на отдельные биржи
    if '_' in exchange_pair:
        exchange1, exchange2 = exchange_pair.split('_')
    else:
        # По умолчанию paradex и backpack
        exchange1, exchange2 = 'paradex', 'backpack'

    time_filters = {
        '1m': 1 * 60,
        '5m': 5 * 60,
        '15m': 15 * 60,
        '30m': 30 * 60,
        '1h': 60 * 60,
        '3h': 3 * 60 * 60,
        '6h': 6 * 60 * 60,
        '24h': 24 * 60 * 60
    }
    
    # Убедимся, что time_range находится среди доступных фильтров
    if time_range not in time_filters:
        time_range = '24h'
        
    time_threshold = int(time.time()) - time_filters.get(time_range, 24 * 60 * 60)
    
    # Логирование вычисления времени
    logger.debug(f"Временной фильтр для зеркальных данных: {time_range} => {time_filters.get(time_range)} секунд, порог: {time_threshold}")

    conn = get_db_connection()
    
    # Используем новое поле exchange_pair для фильтрации, если оно есть
    has_exchange_pair = conn.execute("PRAGMA table_info(spreads)").fetchall()
    column_names = [column[1] for column in has_exchange_pair]
    
    if "exchange_pair" in column_names:
        query = f'''
            SELECT id, symbol, signal, backpack_price, paradex_price, hyperliquid_price, created, difference, exchange_pair
            FROM spreads
            WHERE symbol = ? AND exchange_pair = ?
        '''
        params = [symbol, exchange_pair]
    else:
        # Старый вариант запроса
        query = f'''
            SELECT id, symbol, signal, backpack_price, paradex_price, hyperliquid_price, created, 
                CASE 
                    WHEN signal = 'BUY' THEN ({exchange2}_price / {exchange1}_price - 1) * 100
                    WHEN signal = 'SELL' THEN ({exchange1}_price / {exchange2}_price - 1) * 100
                    ELSE 0
                END as inverse_difference
            FROM spreads
            WHERE symbol = ? AND {exchange1}_price != 0 AND {exchange2}_price != 0
        '''
        params = [symbol]

    if since:
        try:
            # Преобразуем timestamp из миллисекунд (JavaScript) в секунды (SQLite)
            since_timestamp = float(since) / 1000.0
            # Используем >= вместо > чтобы не пропустить записи с тем же временем
            query += ' AND created >= ?'
            params.append(since_timestamp)
            logger.info(f"Запрос зеркальных данных с временной меткой: {since} мс -> {since_timestamp} с")
        except (ValueError, TypeError):
            # Если возникла ошибка при преобразовании, используем стандартный порог
            query += ' AND created >= ?'
            params.append(time_threshold)
            logger.warning(f"Ошибка преобразования временной метки: {since}, используем временной порог: {time_threshold}")
    else:
        query += ' AND created >= ?'
        params.append(time_threshold)

    query += f' ORDER BY {sort_by} {sort_order}'
    
    # Добавляем ограничение на количество записей
    query += ' LIMIT 1000'
    
    # Логирование SQL-запроса
    logger.debug(f"Зеркальный SQL-запрос: {query}, параметры: {params}")
    
    rows = conn.execute(query, params).fetchall()
    
    # Логирование количества полученных записей
    logger.info(f"Получено {len(rows)} зеркальных записей")
    
    conn.close()

    data = []
    for row in rows:
        # Инвертируем сигналы: BUY -> SELL, SELL -> BUY
        mirrored_signal = 'SELL' if row['signal'] == 'BUY' else 'BUY'
        
        # Определяем обратную пару бирж
        inverse_pair = f"{exchange2}_{exchange1}"
        
        # Создаем "зеркальные данные", меняя местами биржи
        mirrored_data = {
            'id': row['id'],
            'symbol': row['symbol'],
            'signal': mirrored_signal,
            'backpack_price': row['backpack_price'],
            'paradex_price': row['paradex_price'],
            'hyperliquid_price': row['hyperliquid_price'],
            'created': datetime.fromtimestamp(row['created']).strftime('%Y-%m-%d %H:%M:%S'),
            'exchange_pair': inverse_pair,
            'exchange1': exchange2,  # Меняем местами биржи
            'exchange2': exchange1   # Меняем местами биржи
        }
        
        # Вычисляем зеркальную разницу
        if hasattr(row, 'difference'):
            # Инвертируем разницу (если было +5%, то станет -5%)
            price1 = row[f"{exchange1}_price"]
            price2 = row[f"{exchange2}_price"]
            if row['signal'] == 'BUY':
                # Если был BUY, то стал SELL, меняем формулу
                mirrored_data['difference'] = ((price1 / price2) - 1) * 100
            else:
                # Если был SELL, то стал BUY, меняем формулу
                mirrored_data['difference'] = ((price2 / price1) - 1) * 100
        elif hasattr(row, 'inverse_difference'):
            mirrored_data['difference'] = row['inverse_difference']
        
        data.append(mirrored_data)

    return jsonify(data)


@app.route('/summary')
def get_summary():
    time_range = request.args.get('time_range', '24h')
    time_filters = {
        '1m': 1 * 60,
        '5m': 5 * 60,
        '15m': 15 * 60,
        '30m': 30 * 60,
        '1h': 60 * 60,
        '3h': 3 * 60 * 60,
        '6h': 6 * 60 * 60,
        '24h': 24 * 60 * 60
    }
    
    # Убедимся, что time_range находится среди доступных фильтров
    if time_range not in time_filters:
        time_range = '24h'
        
    time_threshold = int(time.time()) - time_filters.get(time_range, 24 * 60 * 60)

    conn = get_db_connection()
    
    # Проверяем наличие поля exchange_pair
    has_exchange_pair = conn.execute("PRAGMA table_info(spreads)").fetchall()
    column_names = [column[1] for column in has_exchange_pair]
    
    if "exchange_pair" in column_names:
        # Получаем все доступные пары бирж
        exchange_pairs_db = conn.execute('SELECT DISTINCT exchange_pair FROM spreads WHERE exchange_pair IS NOT NULL').fetchall()
        available_pairs = [pair['exchange_pair'] for pair in exchange_pairs_db if pair['exchange_pair']]
        
        # Базовый запрос с фильтрацией по паре бирж и сортировкой по времени (для анализа трендов)
        query = '''
            SELECT symbol, signal, exchange_pair, difference, created,
                   backpack_price, paradex_price, hyperliquid_price
            FROM spreads
            WHERE created >= ? AND exchange_pair IS NOT NULL
            ORDER BY created DESC
            LIMIT 5000
        '''
    else:
        # Старый вариант - генерируем стандартные пары
        available_pairs = [f"{pair[0]}_{pair[1]}" for pair in EXCHANGE_PAIRS]
        
        # Создаем обобщенный SQL запрос
        query = '''
            SELECT symbol, signal, backpack_price, paradex_price, hyperliquid_price, created
            FROM spreads
            WHERE created >= ? AND (
                (backpack_price != 0 AND paradex_price != 0) OR
                (backpack_price != 0 AND hyperliquid_price != 0) OR
                (paradex_price != 0 AND hyperliquid_price != 0)
            )
            ORDER BY created DESC
        '''
    
    rows = conn.execute(query, (time_threshold,)).fetchall()
    conn.close()

    # Подготавливаем структуру для сбора данных по каждой паре бирж
    summary = {}
    
    for pair in available_pairs:
        if "_" in pair:
            exchange1, exchange2 = pair.split("_")
            
            # Фильтруем записи по паре бирж
            if "exchange_pair" in column_names:
                pair_rows = [row for row in rows if row['exchange_pair'] == pair]
            else:
                pair_rows = [row for row in rows 
                            if row[f"{exchange1}_price"] > 0 and row[f"{exchange2}_price"] > 0]
            
            # Пропускаем пары без данных
            if not pair_rows:
                continue
                
            # Получаем символ из последней записи для этой пары
            current_symbol = pair_rows[0]['symbol'] if pair_rows and 'symbol' in pair_rows[0] else "ETH/USDT"
            
            # Преобразуем символ в удобный формат для отображения в таблице
            formatted_symbol = current_symbol
            if "_PERP" in formatted_symbol:
                formatted_symbol = formatted_symbol.replace("_PERP", "").replace("_", "/")
            
            # Собираем все значения разниц с разделением по сигналам
            buy_spreads = []
            sell_spreads = []
            
            for row in pair_rows:
                if "exchange_pair" in column_names and row['difference'] is not None:
                    # Используем уже рассчитанные значения из БД
                    if row['signal'] == 'BUY':
                        buy_spreads.append(row['difference'])
                    elif row['signal'] == 'SELL':
                        sell_spreads.append(row['difference'])
                else:
                    # Вычисляем отношение цен для более точной оценки
                    price1 = row[f"{exchange1}_price"]
                    price2 = row[f"{exchange2}_price"]
                    
                    if price1 <= 0 or price2 <= 0:
                        continue
                        
                    if row['signal'] == 'BUY':
                        # Покупаем на первой, продаем на второй
                        price_ratio = price2 / price1
                        buy_spreads.append((price_ratio - 1) * 100)
                    else:
                        # Покупаем на второй, продаем на первой
                        price_ratio = price1 / price2
                        sell_spreads.append((price_ratio - 1) * 100)
            
            # Применяем статистические методы для более точного анализа
            formatted_pair = f"{EXCHANGE_NAMES.get(exchange1, exchange1)} - {EXCHANGE_NAMES.get(exchange2, exchange2)}"
            
            # Рассчитываем квартили для BUY спредов
            buy_q1, buy_q3, buy_median, buy_min, buy_max = calculate_statistics(buy_spreads)
            
            # Рассчитываем квартили для SELL спредов
            sell_q1, sell_q3, sell_median, sell_min, sell_max = calculate_statistics(sell_spreads)
            
            # Рассчитываем взвешенный средний спред по времени для определения тренда
            recent_weight = 2.0  # Вес недавних записей в 2 раза больше старых
            
            # Используем только последние N записей для трендового анализа
            max_trend_records = 100
            trend_buy_spreads = buy_spreads[:max_trend_records] if buy_spreads else []
            trend_sell_spreads = sell_spreads[:max_trend_records] if sell_spreads else []
            
            # Рассчитываем средние значения с учетом временных весов
            weighted_buy_avg = calculate_weighted_average(trend_buy_spreads, recent_weight)
            weighted_sell_avg = calculate_weighted_average(trend_sell_spreads, recent_weight)
            
            # Определяем текущую рыночную конъюнктуру (арбитражные возможности)
            buy_sell_diff = abs(buy_median - sell_median) if buy_median is not None and sell_median is not None else None
            
            # Определяем волатильность спреда (размах между квартилями)
            buy_volatility = buy_q3 - buy_q1 if buy_q1 is not None and buy_q3 is not None else None
            sell_volatility = sell_q3 - sell_q1 if sell_q1 is not None and sell_q3 is not None else None
            
            # Формируем объект с результатами статистического анализа
            summary[pair] = {
                'name': formatted_pair,
                'symbol': formatted_symbol,  # Добавляем символ пары в ответ
                'formatted_exchange1': EXCHANGE_NAMES.get(exchange1, exchange1),
                'formatted_exchange2': EXCHANGE_NAMES.get(exchange2, exchange2),
                # Данные по BUY спредам
                'median_buy_spread': round(buy_median, 2) if buy_median is not None else None,
                'min_buy_spread': round(buy_min, 2) if buy_min is not None else None,
                'max_buy_spread': round(buy_max, 2) if buy_max is not None else None,
                'buy_volatility': round(buy_volatility, 2) if buy_volatility is not None else None,
                'weighted_buy_avg': round(weighted_buy_avg, 2) if weighted_buy_avg is not None else None,
                
                # Данные по SELL спредам
                'median_sell_spread': round(sell_median, 2) if sell_median is not None else None,
                'min_sell_spread': round(sell_min, 2) if sell_min is not None else None,
                'max_sell_spread': round(sell_max, 2) if sell_max is not None else None,
                'sell_volatility': round(sell_volatility, 2) if sell_volatility is not None else None,
                'weighted_sell_avg': round(weighted_sell_avg, 2) if weighted_sell_avg is not None else None,
                
                # Разница между медианами BUY и SELL (арбитражные возможности)
                'buy_sell_diff': round(buy_sell_diff, 2) if buy_sell_diff is not None else None,
                
                # Для совместимости с предыдущим форматом
                'smallest_buy_spread': round(buy_min, 2) if buy_min is not None else None,
                'smallest_sell_spread': round(sell_min, 2) if sell_min is not None else None,
                'largest_buy_spread': round(buy_max, 2) if buy_max is not None else None,
                'largest_sell_spread': round(sell_max, 2) if sell_max is not None else None,
                'avg_buy_spread': round(weighted_buy_avg, 2) if weighted_buy_avg is not None else None,
                'avg_sell_spread': round(weighted_sell_avg, 2) if weighted_sell_avg is not None else None,
                'avg_buy_sell_diff': round(buy_sell_diff, 2) if buy_sell_diff is not None else None,
                
                # Метаданные для отладки
                'buy_count': len(buy_spreads),
                'sell_count': len(sell_spreads)
            }

    return jsonify(summary)

def calculate_statistics(data):
    """
    Рассчитывает основные статистические показатели для массива данных:
    - Q1 (первый квартиль)
    - Q3 (третий квартиль)
    - Медиана
    - Минимум (с исключением выбросов)
    - Максимум (с исключением выбросов)
    """
    if not data:
        return None, None, None, None, None
    
    # Ограничиваем размер данных для статистики
    MAX_STATS_RECORDS = 5000
    if len(data) > MAX_STATS_RECORDS:
        # Берем только последние записи, они обычно более важны
        data = data[-MAX_STATS_RECORDS:]
        
    # Сортируем данные
    sorted_data = sorted(data)
    n = len(sorted_data)
    
    # Рассчитываем медиану
    if n % 2 == 0:
        median = (sorted_data[n//2-1] + sorted_data[n//2]) / 2
    else:
        median = sorted_data[n//2]
    
    # Находим позиции для Q1 и Q3
    q1_pos = n // 4
    q3_pos = (3 * n) // 4
    
    # Рассчитываем Q1 и Q3
    q1 = sorted_data[q1_pos]
    q3 = sorted_data[q3_pos]
    
    # Межквартильный размах для определения выбросов
    iqr = q3 - q1
    
    # Определяем границы выбросов по правилу 1.5*IQR
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    
    # Фильтруем данные, исключая выбросы
    filtered_data = [x for x in sorted_data if lower_bound <= x <= upper_bound]
    
    # Если после фильтрации данных не осталось, используем исходные
    if not filtered_data:
        filtered_data = sorted_data
    
    # Рассчитываем минимум и максимум без выбросов
    min_value = min(filtered_data)
    max_value = max(filtered_data)
    
    return q1, q3, median, min_value, max_value

def calculate_weighted_average(data, recent_weight=1.5):
    """
    Вычисляет взвешенное среднее, придавая больший вес более недавним значениям.
    Параметр recent_weight определяет насколько важнее недавние данные (по умолчанию в 1.5 раза).
    """
    if not data:
        return None
    
    n = len(data)
    if n == 1:
        return data[0]
    
    # Веса линейно увеличиваются от 1 до recent_weight
    weight_step = (recent_weight - 1) / (n - 1) if n > 1 else 0
    
    weighted_sum = 0
    total_weight = 0
    
    for i, value in enumerate(data):
        weight = 1 + i * weight_step  # Вес увеличивается с индексом (недавние данные имеют больший индекс)
        weighted_sum += value * weight
        total_weight += weight
    
    return weighted_sum / total_weight if total_weight > 0 else None

@app.route('/exchange_pairs')
def get_exchange_pairs():
    """API для получения доступных пар бирж"""
    
    # Всегда используем предопределенные пары бирж
    available_pairs = [f"{pair[0]}_{pair[1]}" for pair in EXCHANGE_PAIRS]
    
    # Форматируем пары для отображения
    formatted_pairs = []
    for pair in available_pairs:
        if "_" in pair:
            exchange1, exchange2 = pair.split("_")
            formatted_pairs.append({
                'id': pair,
                'name': f"{EXCHANGE_NAMES.get(exchange1, exchange1)} - {EXCHANGE_NAMES.get(exchange2, exchange2)}"
            })
    
    return jsonify(formatted_pairs)

@app.route('/symbols')
def get_symbols():
    """API для получения списка доступных торговых пар (символов)"""
    conn = get_db_connection()
    try:
        # Получаем список уникальных символов из базы данных
        symbols = conn.execute('SELECT DISTINCT symbol FROM spreads').fetchall()
        
        # Форматируем результат в список словарей
        result = [{'symbol': row['symbol']} for row in symbols]
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Ошибка при получении списка символов: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=False)