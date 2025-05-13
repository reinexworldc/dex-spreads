from py.database.models import Spread
from py.database.models import async_session


async def spreads_add(spreads: list[dict]):
    status = "ok"

    try:
        async with async_session() as session:
            for spread in spreads:
                signal = spread.get("signal")

                if signal == "SKIP":
                    continue
                
                symbol = spread.get("symbol")
                paradex_price = spread.get("paradex_price", 0)
                backpack_price = spread.get("backpack_price", 0)
                hyperliquid_price = spread.get("hyperliquid_price", 0)
                created = spread.get("created")
                
                # Получаем данные о сырых ценах Paradex, если они есть
                paradex_raw_price = spread.get("paradex_raw_price", 0)
                paradex_raw_bid = spread.get("paradex_raw_bid", 0)
                paradex_raw_ask = spread.get("paradex_raw_ask", 0)
                paradex_contract_size = spread.get("paradex_contract_size", 1.0)
                
                # Определяем пару бирж для спреда
                exchange_pair = None
                exchange1 = None
                exchange2 = None
                difference = 0
                
                # Определяем пару бирж на основе цен
                if paradex_price > 0 and backpack_price > 0:
                    exchange_pair = spread.get("exchange_pair") or 'paradex_backpack'
                    exchange1 = 'paradex'
                    exchange2 = 'backpack'
                    
                    # Если exchange_pair уже указан в spread, используем его
                    if spread.get("exchange_pair") and spread.get("difference") is not None:
                        difference = spread.get("difference")
                    else:
                        # Расчет процентной разницы по новой формуле
                        if signal == 'BUY':
                            # Для BUY: покупаем на exchange1, продаем на exchange2
                            buy_price = paradex_price
                            sell_price = backpack_price
                            difference = ((sell_price - buy_price) / buy_price) * 100
                        else:
                            # Для SELL: покупаем на exchange2, продаем на exchange1
                            buy_price = backpack_price
                            sell_price = paradex_price
                            difference = ((sell_price - buy_price) / buy_price) * 100
                        
                elif backpack_price > 0 and hyperliquid_price > 0:
                    exchange_pair = spread.get("exchange_pair") or 'backpack_hyperliquid'
                    exchange1 = 'backpack'
                    exchange2 = 'hyperliquid'
                    
                    # Если exchange_pair уже указан в spread, используем его
                    if spread.get("exchange_pair") and spread.get("difference") is not None:
                        difference = spread.get("difference")
                    else:
                        # Расчет процентной разницы по новой формуле
                        if signal == 'BUY':
                            # Для BUY: покупаем на exchange1, продаем на exchange2
                            buy_price = backpack_price
                            sell_price = hyperliquid_price
                            difference = ((sell_price - buy_price) / buy_price) * 100
                        else:
                            # Для SELL: покупаем на exchange2, продаем на exchange1
                            buy_price = hyperliquid_price
                            sell_price = backpack_price
                            difference = ((sell_price - buy_price) / buy_price) * 100
                        
                elif paradex_price > 0 and hyperliquid_price > 0:
                    exchange_pair = spread.get("exchange_pair") or 'paradex_hyperliquid'
                    exchange1 = 'paradex'
                    exchange2 = 'hyperliquid'
                    
                    # Если exchange_pair уже указан в spread, используем его
                    if spread.get("exchange_pair") and spread.get("difference") is not None:
                        difference = spread.get("difference")
                    else:
                        # Расчет процентной разницы по новой формуле
                        if signal == 'BUY':
                            # Для BUY: покупаем на exchange1, продаем на exchange2
                            buy_price = paradex_price
                            sell_price = hyperliquid_price
                            difference = ((sell_price - buy_price) / buy_price) * 100
                        else:
                            # Для SELL: покупаем на exchange2, продаем на exchange1
                            buy_price = hyperliquid_price
                            sell_price = paradex_price
                            difference = ((sell_price - buy_price) / buy_price) * 100

                session.add(Spread(symbol = symbol,
                                signal = signal,
                                backpack_price = backpack_price, 
                                paradex_price = paradex_price,
                                hyperliquid_price = hyperliquid_price,
                                created = created,
                                exchange_pair = exchange_pair,
                                exchange1 = exchange1,
                                exchange2 = exchange2,
                                difference = difference,
                                # Добавляем сырые цены Paradex и размер контракта
                                paradex_raw_price = paradex_raw_price,
                                paradex_raw_bid = paradex_raw_bid,
                                paradex_raw_ask = paradex_raw_ask,
                                paradex_contract_size = paradex_contract_size))
            
            await session.commit()

    except Exception as e:
        status = e

    return status