import os
import json
import asyncio
from datetime import datetime
import logging

from py.trader import Trader
from py.paradex import Paradex
from py.backpack import Backpack
from py.hyperliquid import Hyperliquid
from py.database.models import db_async
from py.database.requests import spreads_add
from update_db import update_db, update_difference_values, update_exchange_fields

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("main")

try:
    with open("config.json", 'r', encoding = 'utf-8') as f:
        config = json.load(f)

    SAVE_FOLDER = config['SAVE_FOLDER']
    PARADEX_DATA = config['PARADEX_DATA']
    BACKPACK_DATA = config['BACKPACK_DATA']
    HYPERLIQUID_DATA = config['HYPERLIQUID_DATA']
    TRADER_DATA = config['TRADER_DATA']
    INTERVAL = config['INTERVAL']

except:
    input("[ERROR] Не удалось найти или открыть файл 'config.json'")
    exit()


def show_settings():
    print(f"-------------------- НАСТРОЙКИ ---------------------")
    print(f"   * Папка сохранения:    /{SAVE_FOLDER}")
    print(f"   * Интервал:            1 проверка каждые {INTERVAL} сек.")
    print()


async def clear_database():
    """Очистка базы данных перед запуском программы"""
    try:
        # Импортируем необходимые модули для работы с БД
        from sqlalchemy import text
        from py.database.models import async_session
        
        async with async_session() as session:
            # Очищаем таблицу spreads
            await session.execute(text("DELETE FROM spreads"))
            await session.commit()
            
        return "ok"
    except Exception as e:
        return f"error: {str(e)}"


async def main():
    os.system("cls || clear")

    # Создаем директорию для базы данных, если ее не существует
    db_dir = '/app/data'
    db_path = f'{db_dir}/db.sqlite3'
    
    try:
        os.makedirs(db_dir, exist_ok=True)
        print(f"[INFO] Директория для базы данных: {db_dir}")
        
        # Проверяем права доступа к папке с базой данных
        if os.access(db_dir, os.W_OK):
            print(f"[INFO] Есть права на запись в директорию {db_dir}")
        else:
            print(f"[WARN] Нет прав на запись в директорию {db_dir}")
        
        # Создаем файл базы данных, если его нет, и устанавливаем права
        if not os.path.exists(db_path):
            with open(db_path, 'w') as f:
                pass
            print(f"[INFO] Создан пустой файл базы данных: {db_path}")
        
        # Устанавливаем права доступа
        os.chmod(db_path, 0o666)
        print(f"[INFO] Установлены права доступа к файлу базы данных")
        
        # Проверяем, доступен ли файл базы данных для записи
        if os.access(db_path, os.W_OK):
            print(f"[INFO] Есть права на запись в файл {db_path}")
        else:
            print(f"[WARN] Нет прав на запись в файл {db_path}")
    except Exception as e:
        print(f"[ERROR] Ошибка при подготовке базы данных: {e}")

    try:
        # Обновляем структуру базы данных при необходимости
        print("[INFO] Обновление структуры базы данных...")
        update_db()
        update_exchange_fields()
        update_difference_values()
        
        await db_async()
        
        # Закомментировано очищение базы данных, чтобы сохранять данные между запусками
        # clear_status = await clear_database()
        # if clear_status == "ok":
        #     print("[DB] База данных успешно очищена")
        # else:
        #     print(f"[DB] Ошибка при очистке базы данных: {clear_status}")

        print("[START] Программа успешно запущена\n")

        show_settings()

        trader = Trader(TRADER_DATA)
        paradex = Paradex(PARADEX_DATA)
        backpack = Backpack(BACKPACK_DATA)
        hyperliquid = Hyperliquid(HYPERLIQUID_DATA)
        
        # Подписываемся на WebSocket всех бирж
        await backpack.subscribe()
        await paradex.subscribe()
        await hyperliquid.subscribe()

        while True:
            print()
            date = datetime.now().strftime("%H:%M:%S")

        
            backpack_status, backpack_markets = await backpack.get_markets()

            if backpack_status != "ok":
                print(f"[{date}] Ошибка от Backpack: {backpack_status}")
                await asyncio.sleep(INTERVAL)
                continue

            print(f"[{date}] Площадки Backpack: {len(backpack_markets)} шт.")

            
            hyperliquid_status, hyperliquid_markets = await hyperliquid.get_markets()

            if hyperliquid_status != "ok":
                print(f"[{date}] Ошибка от Hyperliquid: {hyperliquid_status}")
                await asyncio.sleep(INTERVAL)
                continue

            print(f"[{date}] Площадки Hyperliquid: {len(hyperliquid_markets)} шт.")
            
            paradex_status, paradex_markets = await paradex.get_markets()

            if paradex_status != "ok":
                print(f"[{date}] Ошибка от Paradex: {paradex_status}")
                await asyncio.sleep(INTERVAL)
                continue
            
            print(f"[{date}] Площадки Paradex: {len(paradex_markets)} шт.")


            status, markets = trader.get_general_markets(paradex_markets, backpack_markets, hyperliquid_markets)
            
            if status != "ok":
                print(f"[{date}] Ошибка от Trader: {status}")
                await asyncio.sleep(INTERVAL)
                continue
            
            print(f"[{date}] Общих площадок: {len(markets)} шт.")


            status, spreads = trader.get_spreads(markets)

            if status != "ok":
                print(f"[{date}] Не удалось произвести вычисления: {status}")
                await asyncio.sleep(INTERVAL)
                continue
            
            # Добавляем подробное логирование для диагностики проблем с данными
            print(f"[{date}] Получено спредов для записи в БД: {len(spreads)}")
            if len(spreads) == 0:
                print(f"[{date}] ВНИМАНИЕ: Список спредов пуст! Проверьте фильтры в trader.get_spreads()")
                # Проверим первые 3 общих рынка, чтобы понять, почему нет спредов
                for i, market in enumerate(markets[:3]):
                    print(f"[{date}] Пример рынка #{i+1}: {market.get('symbol')}")
                    print(f"  Paradex: bid={market.get('paradex_bid', 0)}, ask={market.get('paradex_ask', 0)}")
                    print(f"  Backpack: bid={market.get('backpack_bid', 0)}, ask={market.get('backpack_ask', 0)}")
                    print(f"  Hyperliquid: bid={market.get('hyperliquid_bid', 0)}, ask={market.get('hyperliquid_ask', 0)}")


            status = await spreads_add(spreads)
            print(f"[{date}] Сохранение в БД: {status}")
            
            # Проверяем статус сохранения
            if status != "ok":
                print(f"[{date}] ОШИБКА СОХРАНЕНИЯ: {status}")
            elif len(spreads) > 0:
                print(f"[{date}] Успешно сохранено {len(spreads)} записей в БД")



            await asyncio.sleep(INTERVAL)
            
    except Exception as e:
        print(f"[FATAL] Критическая ошибка при выполнении основной функции: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"[FATAL] Критическая ошибка: {e}")
        # Убираем интерактивный ввод, который блокирует контейнер
        # input(f"[FATAL] Критическая ошибка: {e}")