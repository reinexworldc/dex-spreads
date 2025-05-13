import time

def get_general_symbol(symbol: str) -> str:
    """
    Приводит символы с разных бирж к единому формату.
    
    Форматы:
    - Paradex: BTC-USD-PERP или BTC-PERP (бессрочные фьючерсы)
    - Paradex: BTC-USD-[STRIKE]-[C/P] (опционы)
    - Backpack: BTC_USDC_PERP (бессрочные фьючерсы)
    - Hyperliquid: BTC (базовый актив без суффикса)
    
    Результат: BTC_USDC_PERP для бессрочных фьючерсов
    """
    # Базовый актив - первая часть символа (BTC, ETH, SOL и т.д.)
    if '-' in symbol:
        base_asset = symbol.split('-')[0]
    elif '_' in symbol:
        base_asset = symbol.split('_')[0]
    else:
        base_asset = symbol  # Для Hyperliquid, где символ уже в базовом формате
    
    return f"{base_asset}_USDC_PERP"


class Trader:
    def __init__(self, settings: dict):
        self.min_difference = settings['MIN_DIFFERENCE']
        # Список возможных комбинаций бирж для расчета спредов
        self.exchange_pairs = [
            ("paradex", "backpack"),
            ("paradex", "hyperliquid"),
            ("backpack", "hyperliquid")
        ]


    def get_general_markets(self, paradex_markets, backpack_markets, hyperliquid_markets):
        """Получение общих рынков из разных бирж"""
        status = "ok"
        markets_data = {}

        try:
            # Обработка данных от Paradex
            for market in paradex_markets:
                symbol = market['symbol']
                general_symbol = get_general_symbol(symbol)
                
                # Нормализованные цены
                bid = market['bid']
                ask = market['ask']
                
                # Сырые цены Paradex и размер контракта
                raw_bid = market.get('original_bid', 0)
                raw_ask = market.get('original_ask', 0)
                contract_size = market.get('contract_size', 1.0)
                
                if general_symbol not in markets_data:
                    markets_data[general_symbol] = {}
                
                markets_data[general_symbol]['symbol'] = general_symbol
                markets_data[general_symbol]['paradex_bid'] = bid
                markets_data[general_symbol]['paradex_ask'] = ask
                
                # Добавляем сырые цены и размер контракта
                markets_data[general_symbol]['paradex_raw_bid'] = raw_bid
                markets_data[general_symbol]['paradex_raw_ask'] = raw_ask
                markets_data[general_symbol]['paradex_contract_size'] = contract_size
            
            # Обработка данных от Backpack
            for market in backpack_markets:
                symbol = market['symbol']
                general_symbol = get_general_symbol(symbol)
                
                if general_symbol not in markets_data:
                    markets_data[general_symbol] = {}
                    markets_data[general_symbol]['symbol'] = general_symbol
                
                markets_data[general_symbol]['backpack_bid'] = market['bid'] 
                markets_data[general_symbol]['backpack_ask'] = market['ask']
            
            # Обработка данных от Hyperliquid
            for market in hyperliquid_markets:
                symbol = market['symbol']
                general_symbol = get_general_symbol(symbol)
                
                if general_symbol not in markets_data:
                    markets_data[general_symbol] = {}
                    markets_data[general_symbol]['symbol'] = general_symbol
                
                markets_data[general_symbol]['hyperliquid_bid'] = market['bid']
                markets_data[general_symbol]['hyperliquid_ask'] = market['ask']
        
        except Exception as e:
            status = f"error: {str(e)}"
            return status, []
        
        return status, list(markets_data.values())


    def get_spreads(self, general_markets):
        """Получение арбитражных спредов"""
        
        status = "ok"
        spreads = []

        try:
            timestamp = int(time.time())
            
            # Логи для отладки
            print(f"[TRADER] Начинаю анализ {len(general_markets)} рынков")
            print(f"[TRADER] Минимальная разница для спреда: {self.min_difference}%")
            
            # Подсчет для статистики
            markets_with_both_exchanges = 0
            spreads_found = 0
            
            # Вычисляем спреды для каждой торговой пары в general_markets
            for market in general_markets:
                # Извлекаем все данные по market
                symbol = market.get('symbol')
                
                # Получаем цены bid и ask от разных бирж
                paradex_bid = market.get('paradex_bid')
                paradex_ask = market.get('paradex_ask')
                backpack_bid = market.get('backpack_bid')
                backpack_ask = market.get('backpack_ask')
                hyperliquid_bid = market.get('hyperliquid_bid')
                hyperliquid_ask = market.get('hyperliquid_ask')
                
                # Получаем сырые цены Paradex и размер контракта, если они есть
                paradex_raw_bid = market.get('paradex_raw_bid', 0)
                paradex_raw_ask = market.get('paradex_raw_ask', 0)
                paradex_contract_size = market.get('paradex_contract_size', 1.0)
                
                # Проверка минимальной разницы между bid и ask
                min_difference = self.min_difference / 100
                
                # Логируем данные о биржах для этого символа
                if market_should_be_logged(symbol):
                    print(f"[TRADER] {symbol} цены:")
                    if paradex_bid and paradex_ask:
                        print(f"  ➤ Paradex: bid={paradex_bid}, ask={paradex_ask}")
                    if backpack_bid and backpack_ask:
                        print(f"  ➤ Backpack: bid={backpack_bid}, ask={backpack_ask}")
                    if hyperliquid_bid and hyperliquid_ask:
                        print(f"  ➤ Hyperliquid: bid={hyperliquid_bid}, ask={hyperliquid_ask}")
                
                # ---------------------------- Paradex -> Backpack ----------------------------
                if paradex_bid and backpack_ask and paradex_bid > 0 and backpack_ask > 0:
                    markets_with_both_exchanges += 1
                    # Спред от paradex[bid] к backpack[ask]
                    if backpack_ask > paradex_bid * (1 + min_difference):
                        spreads_found += 1
                        spreads.append({
                            "symbol": symbol,
                            "signal": "BUY",
                            "paradex_price": paradex_bid,
                            "backpack_price": backpack_ask,
                            "created": timestamp,
                            "exchange_pair": "paradex_backpack",
                            "exchange1": "paradex",
                            "exchange2": "backpack",
                            # Добавляем сырые цены и размер контракта
                            "paradex_raw_price": paradex_raw_bid,
                            "paradex_raw_bid": paradex_raw_bid,
                            "paradex_raw_ask": paradex_raw_ask,
                            "paradex_contract_size": paradex_contract_size
                        })
                        if market_should_be_logged(symbol):
                            spread_percent = ((backpack_ask - paradex_bid) / paradex_bid) * 100
                            print(f"  ✅ Найден спред BUY {symbol}: {spread_percent:.2f}% (Paradex -> Backpack)")
                    elif market_should_be_logged(symbol):
                        spread_percent = ((backpack_ask - paradex_bid) / paradex_bid) * 100
                        print(f"  ❌ Спред BUY {symbol} слишком мал: {spread_percent:.2f}% < {self.min_difference}% (Paradex -> Backpack)")
                
                # ---------------------------- Backpack -> Paradex ----------------------------
                if backpack_bid and paradex_ask and backpack_bid > 0 and paradex_ask > 0:                
                    # Спред от backpack[bid] к paradex[ask]
                    if paradex_ask > backpack_bid * (1 + min_difference):
                        spreads_found += 1
                        spreads.append({
                            "symbol": symbol,
                            "signal": "SELL",
                            "paradex_price": paradex_ask,
                            "backpack_price": backpack_bid,
                            "created": timestamp,
                            "exchange_pair": "paradex_backpack",
                            "exchange1": "paradex",
                            "exchange2": "backpack",
                            # Добавляем сырые цены и размер контракта
                            "paradex_raw_price": paradex_raw_ask,
                            "paradex_raw_bid": paradex_raw_bid,
                            "paradex_raw_ask": paradex_raw_ask,
                            "paradex_contract_size": paradex_contract_size
                        })
                        if market_should_be_logged(symbol):
                            spread_percent = ((paradex_ask - backpack_bid) / backpack_bid) * 100
                            print(f"  ✅ Найден спред SELL {symbol}: {spread_percent:.2f}% (Backpack -> Paradex)")
                    elif market_should_be_logged(symbol):
                        spread_percent = ((paradex_ask - backpack_bid) / backpack_bid) * 100
                        print(f"  ❌ Спред SELL {symbol} слишком мал: {spread_percent:.2f}% < {self.min_difference}% (Backpack -> Paradex)")
                
                # ---------------------------- Paradex -> Hyperliquid ----------------------------
                if paradex_bid and hyperliquid_ask and paradex_bid > 0 and hyperliquid_ask > 0:
                    # Спред от paradex[bid] к hyperliquid[ask]
                    if hyperliquid_ask > paradex_bid * (1 + min_difference):
                        spreads.append({
                            "symbol": symbol,
                            "signal": "BUY",
                            "paradex_price": paradex_bid,
                            "hyperliquid_price": hyperliquid_ask,
                            "created": timestamp,
                            "exchange_pair": "paradex_hyperliquid",
                            "exchange1": "paradex",
                            "exchange2": "hyperliquid",
                            # Добавляем сырые цены и размер контракта
                            "paradex_raw_price": paradex_raw_bid,
                            "paradex_raw_bid": paradex_raw_bid,
                            "paradex_raw_ask": paradex_raw_ask,
                            "paradex_contract_size": paradex_contract_size
                        })
                
                # ---------------------------- Hyperliquid -> Paradex ----------------------------
                if hyperliquid_bid and paradex_ask and hyperliquid_bid > 0 and paradex_ask > 0:
                    # Спред от hyperliquid[bid] к paradex[ask]
                    if paradex_ask > hyperliquid_bid * (1 + min_difference):
                        spreads.append({
                            "symbol": symbol,
                            "signal": "SELL",
                            "paradex_price": paradex_ask,
                            "hyperliquid_price": hyperliquid_bid,
                            "created": timestamp,
                            "exchange_pair": "paradex_hyperliquid",
                            "exchange1": "paradex",
                            "exchange2": "hyperliquid",
                            # Добавляем сырые цены и размер контракта
                            "paradex_raw_price": paradex_raw_ask,
                            "paradex_raw_bid": paradex_raw_bid,
                            "paradex_raw_ask": paradex_raw_ask,
                            "paradex_contract_size": paradex_contract_size
                        })
                
                # ---------------------------- Backpack -> Hyperliquid ----------------------------
                if backpack_bid and hyperliquid_ask and backpack_bid > 0 and hyperliquid_ask > 0:
                    # Спред от backpack[bid] к hyperliquid[ask]
                    if hyperliquid_ask > backpack_bid * (1 + min_difference):
                        spreads.append({
                            "symbol": symbol,
                            "signal": "BUY",
                            "backpack_price": backpack_bid,
                            "hyperliquid_price": hyperliquid_ask,
                            "created": timestamp,
                            "exchange_pair": "backpack_hyperliquid",
                            "exchange1": "backpack",
                            "exchange2": "hyperliquid"
                        })
                
                # ---------------------------- Hyperliquid -> Backpack ----------------------------
                if hyperliquid_bid and backpack_ask and hyperliquid_bid > 0 and backpack_ask > 0:
                    # Спред от hyperliquid[bid] к backpack[ask]
                    if backpack_ask > hyperliquid_bid * (1 + min_difference):
                        spreads.append({
                            "symbol": symbol,
                            "signal": "SELL",
                            "backpack_price": backpack_ask,
                            "hyperliquid_price": hyperliquid_bid,
                            "created": timestamp,
                            "exchange_pair": "backpack_hyperliquid",
                            "exchange1": "backpack",
                            "exchange2": "hyperliquid"
                        })
                
            print(f"[TRADER] Итого: найдено {spreads_found} спредов из {markets_with_both_exchanges} рынков с данными от разных бирж")
                
        except Exception as e:
            status = f"error: {str(e)}"
            spreads = []

        return status, spreads


# Вспомогательная функция для определения, нужно ли логировать данный символ
def market_should_be_logged(symbol):
    """Определяет, нужно ли выводить логи для данного символа"""
    important_symbols = ["BTC_USDC_PERP", "ETH_USDC_PERP", "SOL_USDC_PERP", "AVAX_USDC_PERP"]
    return symbol in important_symbols
