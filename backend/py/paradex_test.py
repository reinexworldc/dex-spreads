#!/usr/bin/env python
import asyncio
import json
import time
import os
from datetime import datetime
import sys

# Настраиваем пути для корректного импорта
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Импортируем классы из основного проекта
from py.trader import Trader
from py.paradex import Paradex  
from py.backpack import Backpack
from py.hyperliquid import Hyperliquid


def load_config():
    """Загружает конфигурацию из файла config.json"""
    try:
        config_path = os.path.join(parent_dir, "config.json")
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print("[INFO] Конфигурация успешно загружена")
        return config
    except Exception as e:
        print(f"[ERROR] Не удалось загрузить конфигурацию: {e}")
        # Возвращаем значения по умолчанию
        return {
            "PARADEX_DATA": {
                "API_KEY": "",
                "API_SECRET": ""
            },
            "BACKPACK_DATA": {},
            "HYPERLIQUID_DATA": {},
            "TRADER_DATA": {
                "MIN_DIFFERENCE": 0.5
            }
        }


async def analyze_price_formats(paradex_markets, backpack_markets, hyperliquid_markets):
    """
    Анализирует форматы цен между разными биржами для сравнения.
    """
    print("\n" + "="*80)
    print("АНАЛИЗ ФОРМАТОВ ЦЕН")
    print("="*80)
    
    # Проверка наличия данных
    if not paradex_markets:
        print("[WARNING] Нет данных от Paradex для анализа")
    if not backpack_markets:
        print("[WARNING] Нет данных от Backpack для анализа")
    if not hyperliquid_markets:
        print("[WARNING] Нет данных от Hyperliquid для анализа")
    
    # Если нет данных ни от одной биржи, прерываем анализ
    if not paradex_markets and not backpack_markets and not hyperliquid_markets:
        print("[ERROR] Нет данных ни от одной биржи для анализа")
        return
    
    # Создаем словари для быстрого поиска по базовому активу
    paradex_by_asset = {}
    for market in paradex_markets:
        symbol = market.get('symbol', '')
        # Извлекаем базовый актив (BTC, ETH, SOL и т.д.)
        base_asset = symbol.split('-')[0] if '-' in symbol else symbol.split('_')[0]
        # Для Paradex предпочитаем бессрочные контракты
        if "PERP" in symbol:
            paradex_by_asset[base_asset] = market
    
    backpack_by_asset = {}
    for market in backpack_markets:
        symbol = market.get('symbol', '')
        # Извлекаем базовый актив (BTC, ETH, SOL и т.д.)
        base_asset = symbol.split('_')[0] if '_' in symbol else ''
        if base_asset:
            backpack_by_asset[base_asset] = market
    
    hyperliquid_by_asset = {}
    for market in hyperliquid_markets:
        symbol = market.get('symbol', '')
        # Извлекаем базовый актив (BTC, ETH, SOL и т.д.)
        base_asset = symbol.split('_')[0] if '_' in symbol else symbol
        if base_asset:
            hyperliquid_by_asset[base_asset] = market
    
    # Вывод основной информации о словарях для отладки
    print(f"\nНайдено активов по биржам:")
    print(f"  • Paradex:     {len(paradex_by_asset)} активов")
    print(f"  • Backpack:    {len(backpack_by_asset)} активов")
    print(f"  • Hyperliquid: {len(hyperliquid_by_asset)} активов")
    
    # Находим общие активы
    common_assets_pb = set(paradex_by_asset.keys()) & set(backpack_by_asset.keys())
    common_assets_ph = set(paradex_by_asset.keys()) & set(hyperliquid_by_asset.keys())
    common_assets_bh = set(backpack_by_asset.keys()) & set(hyperliquid_by_asset.keys())
    
    print(f"\nОбщие активы между биржами:")
    print(f"  • Paradex & Backpack:     {len(common_assets_pb)} активов")
    print(f"  • Paradex & Hyperliquid:  {len(common_assets_ph)} активов")
    print(f"  • Backpack & Hyperliquid: {len(common_assets_bh)} активов")
    
    # Анализируем форматы цен для общих активов между Paradex и Backpack
    if common_assets_pb:
        print("\nСравнение цен между Paradex и Backpack:")
        print("-" * 100)
        print(f"{'Актив':<6} | {'Paradex Bid':<15} | {'Paradex Ask':<15} | {'Backpack Bid':<15} | {'Backpack Ask':<15} | {'Прямое соотношение':<20} | {'Обратное произведение':<20}")
        print("-" * 100)
        
        for asset in sorted(common_assets_pb):
            p_market = paradex_by_asset[asset]
            b_market = backpack_by_asset[asset]
            
            p_bid = p_market.get('bid', 0)
            p_ask = p_market.get('ask', 0)
            b_bid = b_market.get('bid', 0)
            b_ask = b_market.get('ask', 0)
            
            # Средние значения для более стабильного сравнения
            p_avg = (p_bid + p_ask) / 2 if p_bid > 0 and p_ask > 0 else (p_bid or p_ask)
            b_avg = (b_bid + b_ask) / 2 if b_bid > 0 and b_ask > 0 else (b_bid or b_ask)
            
            # Расчет соотношений
            direct_ratio = b_avg / p_avg if p_avg > 0 else 0
            inverse_product = p_avg * b_avg
            
            print(f"{asset:<6} | {p_bid:<15.8f} | {p_ask:<15.8f} | {b_bid:<15.2f} | {b_ask:<15.2f} | {direct_ratio:<20.2f} | {inverse_product:<20.2f}")
    
    # Анализируем форматы цен для общих активов между Paradex и Hyperliquid
    if common_assets_ph:
        print("\nСравнение цен между Paradex и Hyperliquid:")
        print("-" * 100)
        print(f"{'Актив':<6} | {'Paradex Bid':<15} | {'Paradex Ask':<15} | {'Hyperliq Bid':<15} | {'Hyperliq Ask':<15} | {'Прямое соотношение':<20} | {'Обратное произведение':<20}")
        print("-" * 100)
        
        for asset in sorted(common_assets_ph):
            p_market = paradex_by_asset[asset]
            h_market = hyperliquid_by_asset[asset]
            
            p_bid = p_market.get('bid', 0)
            p_ask = p_market.get('ask', 0)
            h_bid = h_market.get('bid', 0)
            h_ask = h_market.get('ask', 0)
            
            # Средние значения для более стабильного сравнения
            p_avg = (p_bid + p_ask) / 2 if p_bid > 0 and p_ask > 0 else (p_bid or p_ask)
            h_avg = (h_bid + h_ask) / 2 if h_bid > 0 and h_ask > 0 else (h_bid or h_ask)
            
            # Расчет соотношений
            direct_ratio = h_avg / p_avg if p_avg > 0 else 0
            inverse_product = p_avg * h_avg
            
            print(f"{asset:<6} | {p_bid:<15.8f} | {p_ask:<15.8f} | {h_bid:<15.2f} | {h_ask:<15.2f} | {direct_ratio:<20.2f} | {inverse_product:<20.2f}")
    
    # Анализируем форматы цен для общих активов между Backpack и Hyperliquid (для референса)
    if common_assets_bh:
        print("\nСравнение цен между Backpack и Hyperliquid (для референса):")
        print("-" * 100)
        print(f"{'Актив':<6} | {'Backpack Bid':<15} | {'Backpack Ask':<15} | {'Hyperliq Bid':<15} | {'Hyperliq Ask':<15} | {'Соотношение':<15}")
        print("-" * 100)
        
        for asset in sorted(common_assets_bh):
            b_market = backpack_by_asset[asset]
            h_market = hyperliquid_by_asset[asset]
            
            b_bid = b_market.get('bid', 0)
            b_ask = b_market.get('ask', 0)
            h_bid = h_market.get('bid', 0)
            h_ask = h_market.get('ask', 0)
            
            # Средние значения для более стабильного сравнения
            b_avg = (b_bid + b_ask) / 2 if b_bid > 0 and b_ask > 0 else (b_bid or b_ask)
            h_avg = (h_bid + h_ask) / 2 if h_bid > 0 and h_ask > 0 else (h_bid or h_ask)
            
            # Расчет соотношения (должно быть близко к 1 для корректных цен)
            ratio = b_avg / h_avg if h_avg > 0 else 0
            
            print(f"{asset:<6} | {b_bid:<15.2f} | {b_ask:<15.2f} | {h_bid:<15.2f} | {h_ask:<15.2f} | {ratio:<15.6f}")
    
    # Анализ и определение формата цен Paradex
    if common_assets_pb or common_assets_ph:
        # Выберем референсные цены от любой доступной биржи
        reference_prices = {}
        
        # Сначала приоритетно берем цены от Backpack
        for asset in common_assets_pb:
            market = backpack_by_asset[asset]
            b_bid = market.get('bid', 0)
            b_ask = market.get('ask', 0)
            if b_bid > 0 and b_ask > 0:
                reference_prices[asset] = (b_bid + b_ask) / 2
        
        # Затем, если актив не найден в Backpack, берем цены от Hyperliquid
        for asset in common_assets_ph:
            if asset not in reference_prices:
                market = hyperliquid_by_asset[asset]
                h_bid = market.get('bid', 0)
                h_ask = market.get('ask', 0)
                if h_bid > 0 and h_ask > 0:
                    reference_prices[asset] = (h_bid + h_ask) / 2
        
        # Определяем формат цен Paradex
        print("\nОпределение формата цен Paradex:")
        print("-" * 80)
        print(f"{'Актив':<6} | {'Paradex Цена':<15} | {'Референс Цена':<15} | {'Формат':<10} | {'Множитель/Константа':<20}")
        print("-" * 80)
        
        # Голосование для определения наиболее вероятного формата
        format_votes = {"direct": 0, "inverse": 0, "unknown": 0}
        
        for asset, ref_price in reference_prices.items():
            if asset in paradex_by_asset:
                market = paradex_by_asset[asset]
                p_bid = market.get('bid', 0)
                p_ask = market.get('ask', 0)
                p_avg = (p_bid + p_ask) / 2 if p_bid > 0 and p_ask > 0 else (p_bid or p_ask)
                
                if p_avg > 0 and ref_price > 0:
                    # Определяем формат
                    direct_ratio = ref_price / p_avg
                    inverse_product = p_avg * ref_price
                    
                    format_type = "unknown"
                    if direct_ratio > 100:
                        format_type = "direct"
                        format_votes["direct"] += 1
                    elif 1000 < inverse_product < 10000000:
                        format_type = "inverse"
                        format_votes["inverse"] += 1
                    else:
                        format_votes["unknown"] += 1
                    
                    # Определяем множитель или константу в зависимости от формата
                    factor = 0
                    if format_type == "direct":
                        factor = direct_ratio
                    elif format_type == "inverse":
                        factor = inverse_product
                    
                    print(f"{asset:<6} | {p_avg:<15.8f} | {ref_price:<15.2f} | {format_type:<10} | {factor:<20.2f}")
        
        # Определяем общий формат на основе голосования
        most_common_format = max(format_votes, key=format_votes.get)
        print(f"\nНаиболее вероятный формат цен Paradex: {most_common_format}")
        print(f"Голоса: прямой = {format_votes['direct']}, обратный = {format_votes['inverse']}, неопределенный = {format_votes['unknown']}")
        
        if most_common_format == "direct":
            print("Интерпретация: Paradex использует меньшие значения, которые нужно умножать на коэффициент")
            print("Пример: BTC_real_price = BTC_paradex_price * ~6600")
        elif most_common_format == "inverse":
            print("Интерпретация: Paradex использует обратные значения цен")
            print("Пример: BTC_real_price = constant / BTC_paradex_price")
    
    # Анализируем дополнительные поля в данных Paradex (для первого доступного актива)
    if paradex_by_asset:
        for asset in ["BTC", "ETH", "SOL"]:  # Сначала проверяем популярные активы
            if asset in paradex_by_asset:
                print(f"\nСтруктура данных Paradex для {asset}:")
                market = paradex_by_asset[asset]
                if "raw_data" in market:
                    try:
                        print(json.dumps(market.get("raw_data", {}), indent=2))
                    except:
                        print(str(market.get("raw_data", {})))
                else:
                    print(json.dumps(market, indent=2))
                break


async def determine_price_format(trader, paradex_markets, backpack_markets, hyperliquid_markets):
    """
    Анализирует и определяет наиболее подходящий формат цен Paradex
    """
    print("\nАнализ формата цен для корректного преобразования...")
    
    # Рассчитываем среднюю цену для каждого актива на других биржах
    reference_prices = {}
    for market in backpack_markets + hyperliquid_markets:
        symbol = market.get('symbol', '')
        base_asset = symbol.split('_')[0] if '_' in symbol else symbol
        
        bid = market.get('bid', 0)
        ask = market.get('ask', 0)
        
        if bid > 0 and ask > 0:
            if base_asset not in reference_prices:
                reference_prices[base_asset] = []
            reference_prices[base_asset].append((bid + ask) / 2)
    
    # Вычисляем средние референсные цены
    avg_reference_prices = {}
    for asset, prices in reference_prices.items():
        if prices:
            avg_reference_prices[asset] = sum(prices) / len(prices)
    
    # Анализируем формат цен для основных активов
    format_votes = {"direct": 0, "inverse": 0, "unknown": 0}
    conversion_factors = {}
    inverse_factors = {}
    
    for market in paradex_markets:
        symbol = market.get('symbol', '')
        base_asset = symbol.split('-')[0] if '-' in symbol else symbol.split('_')[0]
        
        if base_asset in avg_reference_prices:
            bid = market.get('bid', 0)
            ask = market.get('ask', 0)
            paradex_avg = (bid + ask) / 2 if bid > 0 and ask > 0 else (bid or ask)
            
            if paradex_avg > 0:
                ref_price = avg_reference_prices[base_asset]
                
                # Анализируем соотношения
                direct_ratio = ref_price / paradex_avg
                inverse_product = paradex_avg * ref_price
                
                # Определяем формат
                format_type = "unknown"
                if direct_ratio > 100:  # Если отношение большое, вероятно, нужно прямое умножение
                    format_type = "direct"
                    conversion_factors[base_asset] = direct_ratio
                elif 1000 < inverse_product < 10000000:  # Если произведение в определенном диапазоне, вероятно обратная зависимость
                    format_type = "inverse"
                    inverse_factors[base_asset] = inverse_product
                
                format_votes[format_type] += 1
                
                # Выводим отладочную информацию для ключевых активов
                if base_asset in ["BTC", "ETH", "SOL"]:
                    print(f"Актив: {base_asset}, Paradex: {paradex_avg:.8f}, Референс: {ref_price:.2f}, "
                          f"Соотношение: {direct_ratio:.2f}, Произведение: {inverse_product:.2f}, "
                          f"Формат: {format_type}")
    
    # Определяем преобладающий формат
    most_common_format = max(format_votes, key=format_votes.get)
    
    print(f"\nВыбран формат: {most_common_format} (голоса: прямой={format_votes['direct']}, "
          f"обратный={format_votes['inverse']}, неизвестный={format_votes['unknown']})")
    
    if most_common_format == "direct":
        print("\nМножители для прямого преобразования:")
        for asset, factor in sorted(conversion_factors.items()):
            print(f"  '{asset}': {factor:.2f},")
    else:
        print("\nКонстанты для обратного преобразования:")
        for asset, factor in sorted(inverse_factors.items()):
            print(f"  '{asset}': {factor:.2f},")


async def main():
    """
    Основная функция для анализа формата цен Paradex
    """
    print("Тестирование и анализ формата цен Paradex")
    print("-" * 60)
    
    # Загружаем конфигурацию
    config = load_config()
    
    # Создаем экземпляры классов для работы с биржами
    paradex = Paradex(config.get('PARADEX_DATA', {}))
    backpack = Backpack(config.get('BACKPACK_DATA', {}))
    hyperliquid = Hyperliquid(config.get('HYPERLIQUID_DATA', {}))
    trader = Trader(config.get('TRADER_DATA', {'MIN_DIFFERENCE': 0.5}))
    
    # Подключаемся к биржам
    print("\nПодключение к биржам...")
    
    connection_attempts = 0
    max_attempts = 3
    
    while connection_attempts < max_attempts:
        try:
            print("Подключение к Paradex...")
            await paradex.subscribe()
            print("Подключение к Backpack...")
            await backpack.subscribe()
            print("Подключение к Hyperliquid...")
            await hyperliquid.subscribe()
            print("Подключение успешно выполнено!")
            break
        except Exception as e:
            connection_attempts += 1
            print(f"[ПОПЫТКА {connection_attempts}/{max_attempts}] Ошибка подключения: {e}")
            if connection_attempts >= max_attempts:
                print("[ВНИМАНИЕ] Достигнуто максимальное количество попыток. Продолжаем с доступными соединениями.")
            else:
                print("Повторная попытка через 2 секунды...")
                await asyncio.sleep(2)
    
    # Получаем данные о рынках
    print("\nПолучение данных о рынках...")
    
    status_paradex, paradex_markets = await paradex.get_markets()
    if status_paradex != "ok":
        print(f"[ОШИБКА] Не удалось получить данные от Paradex: {status_paradex}")
        paradex_markets = []
    
    status_backpack, backpack_markets = await backpack.get_markets()
    if status_backpack != "ok":
        print(f"[ОШИБКА] Не удалось получить данные от Backpack: {status_backpack}")
        backpack_markets = []
    
    status_hyperliquid, hyperliquid_markets = await hyperliquid.get_markets()
    if status_hyperliquid != "ok":
        print(f"[ОШИБКА] Не удалось получить данные от Hyperliquid: {status_hyperliquid}")
        hyperliquid_markets = []
    
    # Вывод базовой информации о полученных данных
    print(f"\nПолучено рынков:")
    print(f"  • Paradex:     {len(paradex_markets)} шт.")
    print(f"  • Backpack:    {len(backpack_markets)} шт.")
    print(f"  • Hyperliquid: {len(hyperliquid_markets)} шт.")
    
    # Анализируем форматы цен
    await analyze_price_formats(paradex_markets, backpack_markets, hyperliquid_markets)
    
    # Определяем формат цен и конвертации для Paradex
    await determine_price_format(trader, paradex_markets, backpack_markets, hyperliquid_markets)
    
    # Проверяем работу метода get_general_markets из класса Trader
    if paradex_markets and (backpack_markets or hyperliquid_markets):
        print("\nВызов метода get_general_markets для проверки работы...")
        status, markets = trader.get_general_markets(paradex_markets, backpack_markets, hyperliquid_markets)
        
        if status == "ok":
            print(f"Успешно найдено {len(markets)} общих рынков")
            
            # Выводим примеры обработанных данных
            if markets:
                print("\nПримеры нормализованных цен:")
                for i, market in enumerate(markets[:3]):  # Выводим первые 3 рынка
                    print(f"\nРынок {i+1}: {market['symbol']}")
                    for exchange in ['paradex', 'backpack', 'hyperliquid']:
                        if exchange in market:
                            print(f"  • {exchange.capitalize()}:")
                            print(f"    - Цена покупки (bid): {market[exchange].get('bid')}")
                            print(f"    - Цена продажи (ask): {market[exchange].get('ask')}")
                            if 'raw_bid' in market[exchange]:
                                print(f"    - Исходная цена покупки: {market[exchange].get('raw_bid')}")
                                print(f"    - Исходная цена продажи: {market[exchange].get('raw_ask')}")
        else:
            print(f"Ошибка при поиске общих рынков: {status}")


if __name__ == "__main__":
    try:
        # Запускаем асинхронный код
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nПрограмма остановлена пользователем.")
    except Exception as e:
        print(f"\n[ОШИБКА] {e}")
        import traceback
        traceback.print_exc() 