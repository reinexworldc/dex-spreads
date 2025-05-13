import json
import asyncio
import threading
import time
import websockets
import logging
from typing import List, Dict, Tuple, Any, Optional

from py.trader import get_general_symbol

# Получаем логгер для нашего модуля
logger = logging.getLogger("paradex_app.hyperliquid")

class Hyperliquid:
    def __init__(self, settings: dict):
        self.testnet = settings.get('TESTNET', False)
        
        # Определяем базовый URL API в зависимости от режима (тестнет или основная сеть)
        self.ws_url = "wss://api.hyperliquid-testnet.xyz/ws" if self.testnet else "wss://api.hyperliquid.xyz/ws"
        
        # Получение символов, если они указаны явно
        self.symbols = settings.get('SYMBOLS', [])
        
        # Данные о рынках с блокировкой для потокобезопасности
        self._markets_data = {}
        self._markets_lock = threading.RLock()
        
        # WebSocket соединение
        self.ws = None
        self._ws_connected = False
        self._ws_subscriptions = set()
        
        # Маппинг имен ассетов для единообразного представления
        self.asset_mapping = {
            "BTC": "BTC",
            "ETH": "ETH",
            "SOL": "SOL",
            "XRP": "XRP",
            "BNB": "BNB",
            "DOGE": "DOGE",
            "AVAX": "AVAX",
            "ADA": "ADA",
            "LINK": "LINK",
            "SUI": "SUI",
            "DOT": "DOT",
            "AAVE": "AAVE",
            "LTC": "LTC",
            "JUP": "JUP",
            "ARB": "ARB"
        }
        
        # Инициализация данных рынков
        for symbol in self.symbols:
            self._markets_data[symbol] = {
                "ask": 0,
                "bid": 0,
                "last_update": 0
            }

    async def _connect_websocket(self):
        """Устанавливает WebSocket соединение с Hyperliquid"""
        if self.ws is not None and self.ws.open:
            self._ws_connected = True
            return
            
        try:
            self.ws = await websockets.connect(self.ws_url)
            self._ws_connected = True
            logger.info("Успешно подключен к Hyperliquid WebSocket")
            
            # Запускаем обработчик сообщений WebSocket
            asyncio.create_task(self._ws_message_handler())
            
            # Отправляем ping каждые 15 секунд для поддержания соединения
            asyncio.create_task(self._ws_ping_handler())
            
        except Exception as e:
            self._ws_connected = False
            logger.error(f"Ошибка подключения к Hyperliquid WebSocket: {e}")
            raise

    async def _ws_message_handler(self):
        """Обрабатывает входящие сообщения WebSocket"""
        try:
            while self._ws_connected and self.ws.open:
                message = await self.ws.recv()
                data = json.loads(message)
                
                # Обработка различных типов сообщений
                channel = data.get('channel')
                
                if channel == 'l2Book':
                    # Обработка данных ордербука
                    await self._process_l2_book_data(data.get('data', {}))
                    
                elif channel == 'allMids':
                    # Обработка данных средних цен всех монет
                    await self._process_all_mids_data(data.get('data', {}))
                    
                elif channel == 'pong':
                    # Ответ на ping, ничего делать не нужно
                    pass
                    
        except websockets.exceptions.ConnectionClosed:
            self._ws_connected = False
            logger.warning("Hyperliquid WebSocket соединение закрыто. Переподключение...")
            await asyncio.sleep(1)
            asyncio.create_task(self._connect_websocket())
            
        except Exception as e:
            self._ws_connected = False
            logger.error(f"Ошибка в обработке сообщений Hyperliquid WebSocket: {e}")
            await asyncio.sleep(5)
            asyncio.create_task(self._connect_websocket())

    async def _ws_ping_handler(self):
        """Отправляет ping сообщения для поддержания WebSocket соединения"""
        while self._ws_connected and self.ws.open:
            try:
                await self.ws.send(json.dumps({"method": "ping"}))
                await asyncio.sleep(15)  # Ping каждые 15 секунд
            except Exception as e:
                logger.error(f"Ошибка при отправке ping: {e}")
                break

    async def _process_l2_book_data(self, data):
        """Обрабатывает данные ордербука"""
        try:
            coin = data.get('coin')
            if not coin or coin not in self.symbols:
                return
                
            levels = data.get('levels', {})
            asks = levels[0] if isinstance(levels, list) and len(levels) > 0 else []
            bids = levels[1] if isinstance(levels, list) and len(levels) > 1 else []
            
            # Берем лучшую цену на покупку и продажу, если они есть
            best_ask = float(asks[0]['px']) if asks else 0
            best_bid = float(bids[0]['px']) if bids else 0
            
            timestamp = data.get('time', int(time.time() * 1000))
            
            if best_ask > 0 and best_bid > 0:
                with self._markets_lock:
                    self._markets_data[coin] = {
                        "ask": best_ask,
                        "bid": best_bid,
                        "last_update": timestamp
                    }
                    
        except Exception as e:
            logger.error(f"Ошибка при обработке данных ордербука для {data.get('coin', 'Unknown')}: {e}")

    async def _process_all_mids_data(self, data):
        """Обрабатывает данные средних цен для всех монет"""
        try:
            mids = data.get('mids', {})
            timestamp = int(time.time() * 1000)
            
            with self._markets_lock:
                for coin, mid_price_str in mids.items():
                    if coin in self.symbols:
                        mid_price = float(mid_price_str)
                        # Если у нас нет данных о бид и аск, используем среднюю цену для обеих
                        if self._markets_data[coin]["ask"] == 0 or self._markets_data[coin]["bid"] == 0:
                            self._markets_data[coin] = {
                                "ask": mid_price * 1.001,  # Добавляем небольшой спред
                                "bid": mid_price * 0.999,  # для оценки бид/аск
                                "last_update": timestamp
                            }
                            
        except Exception as e:
            logger.error(f"Ошибка при обработке данных средних цен: {e}")

    async def _subscribe_to_markets(self):
        """Подписывается на обновления данных рынков"""
        if not self._ws_connected or not self.ws.open:
            await self._connect_websocket()
            
        try:
            # Подписываемся на l2Book для каждого символа
            for symbol in self.symbols:
                if symbol not in self._ws_subscriptions:
                    subscription_msg = {
                        "method": "subscribe",
                        "subscription": {
                            "type": "l2Book",
                            "coin": symbol
                        }
                    }
                    await self.ws.send(json.dumps(subscription_msg))
                    self._ws_subscriptions.add(symbol)
                    logger.info(f"Подписка на l2Book для {symbol}")
                    await asyncio.sleep(0.1)  # Небольшая задержка между подписками
            
            # Также подписываемся на allMids для получения средних цен всех монет
            subscription_msg = {
                "method": "subscribe",
                "subscription": {
                    "type": "allMids"
                }
            }
            await self.ws.send(json.dumps(subscription_msg))
            logger.info(f"Подписка на allMids")
            
        except Exception as e:
            logger.error(f"Ошибка при подписке на данные рынков: {e}")

    async def _get_market_names(self) -> List[str]:
        """Получает список доступных рынков с помощью HTTP API"""
        import aiohttp
        
        try:
            api_url = "https://api.hyperliquid-testnet.xyz/info" if self.testnet else "https://api.hyperliquid.xyz/info"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json={"type": "meta"}) as response:
                    if response.status != 200:
                        raise ValueError(f"Ошибка API: {response.status}")
                    
                    data = await response.json()
                    assets = [asset['name'] for asset in data.get('universe', [])]
                    logger.info(f"Получено {len(assets)} ассетов от Hyperliquid API")
                    return assets
                    
        except Exception as e:
            logger.error(f"Не удалось получить список рынков с Hyperliquid: {e}")
            # Возвращаем основные ассеты в качестве запасного варианта
            return ["BTC", "ETH", "SOL"]

    async def subscribe(self):
        """Инициализирует подключение и подписки на WebSocket"""
        status = "ok"
        
        try:
            # Если символы не указаны явно, получаем их из API
            if not self.symbols:
                self.symbols = await self._get_market_names()
                # Инициализация данных рынков
                for symbol in self.symbols:
                    self._markets_data[symbol] = {
                        "ask": 0,
                        "bid": 0,
                        "last_update": 0
                    }
            
            # Подключаемся к WebSocket и подписываемся на обновления
            await self._connect_websocket()
            await self._subscribe_to_markets()
            
            logger.info(f"Подписка на {len(self.symbols)} символов Hyperliquid завершена")
            
        except Exception as e:
            status = str(e)
            logger.error(f"Ошибка при подписке на Hyperliquid: {e}")
        
        return status

    async def get_markets(self) -> Tuple[str, List[Dict[str, Any]]]:
        """Возвращает данные рынков в формате, совместимом с другими биржами"""
        status = "ok"
        markets = []
        
        try:
            # Проверяем, что WebSocket подключен
            if not self._ws_connected or not self.ws.open:
                await self._connect_websocket()
                await self._subscribe_to_markets()
                # Даем немного времени для получения данных
                await asyncio.sleep(1)
            
            with self._markets_lock:
                for symbol, data in self._markets_data.items():
                    # Проверяем, что у нас есть валидные данные
                    if data["ask"] > 0 and data["bid"] > 0:
                        # Маппинг названия ассета в общий формат
                        general_symbol = get_general_symbol(symbol)
                        
                        markets.append({
                            "symbol": general_symbol,
                            "ask": data["ask"],
                            "bid": data["bid"],
                            "last_update": data["last_update"]
                        })
            
            if not markets:
                # Если нет данных, пробуем переподключиться и подождать еще немного
                logger.warning("Нет данных с Hyperliquid, пробуем переподключиться")
                await self._connect_websocket()
                await self._subscribe_to_markets()
                await asyncio.sleep(2)
                
                with self._markets_lock:
                    for symbol, data in self._markets_data.items():
                        if data["ask"] > 0 and data["bid"] > 0:
                            general_symbol = get_general_symbol(symbol)
                            markets.append({
                                "symbol": general_symbol,
                                "ask": data["ask"],
                                "bid": data["bid"],
                                "last_update": data["last_update"]
                            })
            
            if not markets:
                raise ValueError("Не удалось получить данные рынков от Hyperliquid")
            
        except Exception as e:
            status = str(e)
            logger.error(f"Ошибка при получении данных рынков Hyperliquid: {e}")
        
        return status, markets 