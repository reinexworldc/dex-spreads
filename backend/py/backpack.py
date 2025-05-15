import json
import asyncio
import websockets
import threading
import time
import logging
import ssl

from py.trader import get_general_symbol

# Получаем логгер для нашего модуля
logger = logging.getLogger("paradex_app.backpack")

class Backpack:
    def __init__(self, settings: dict):
        self.symbols = settings['SYMBOLS']
        self.websocket = None
        self.is_connected = False
        self.reconnect_interval = 1  # начальная задержка перед переподключением в секундах
        self.max_reconnect_interval = 30  # максимальная задержка перед переподключением

        # Хранение лучших цен для каждого символа
        self._markets_data = {}
        self._markets_lock = threading.RLock()
        
        # Инициализация данных рынков
        for symbol in self.symbols:
            self._markets_data[symbol] = {
                "ask": 0,
                "bid": 0,
                "last_update": 0
            }

    def is_websocket_connected(self):
        """Безопасно проверяет, подключен ли веб-сокет"""
        if self.websocket is None:
            return False
            
        try:
            # Проверяем состояние соединения с помощью состояния ws.open
            return self.websocket.open
        except AttributeError:
            # Если атрибут open не доступен, пробуем closed
            try:
                return not self.websocket.closed
            except AttributeError:
                # Если ни один атрибут не доступен, считаем соединение разорванным
                return False

    async def connect(self):
        """Устанавливает WebSocket соединение с Backpack Exchange"""
        if self.is_websocket_connected():
            self.is_connected = True
            return

        try:
            uri = "wss://ws.backpack.exchange/"
            
            # Создаем SSL-контекст с отключенной проверкой сертификата
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Настраиваем WebSocket с опциями для автоматического pong и ping_timeout
            self.websocket = await websockets.connect(
                uri,
                ping_interval=20,  # Отправляем ping каждые 20 секунд
                ping_timeout=10,   # Ждем pong не более 10 секунд
                close_timeout=5,   # Ждем закрытия соединения не более 5 секунд
                ssl=ssl_context    # Устанавливаем SSL-контекст без проверки сертификата
            )
            self.is_connected = True
            logger.info("Успешно подключен к Backpack WebSocket")
            self.reconnect_interval = 1  # Сбрасываем интервал переподключения после успешного подключения
        except Exception as e:
            self.is_connected = False
            logger.error(f"Ошибка подключения к Backpack WebSocket: {e}")
            raise

    async def subscribe(self):
        """Подписывается на обновления рыночных данных по всем символам"""
        status = "ok"

        try:
            # Подключаемся к WebSocket
            await self.connect()

            # Подписываемся на каналы bookTicker для каждого символа (для получения лучших bid/ask)
            params = [f"bookTicker.{symbol}" for symbol in self.symbols]
            subscribe_message = {
                "method": "SUBSCRIBE",
                "params": params,
                "id": 1
            }
            await self.websocket.send(json.dumps(subscribe_message))
            logger.info(f"Отправлен запрос на подписку bookTicker: {params}")

            # Запускаем асинхронную задачу для прослушивания сообщений
            asyncio.create_task(self.listen())
            logger.info(f"Подписка на {len(self.symbols)} символов Backpack завершена")

        except Exception as e:
            status = str(e)
            logger.error(f"Ошибка при подписке на Backpack: {e}")
            
        return status

    async def listen(self):
        """Слушаем сообщения WebSocket и обрабатываем их"""
        while True:  # Бесконечный цикл для поддержания соединения
            try:
                # Проверяем соединение и переподключаемся при необходимости
                if not self.is_websocket_connected():
                    logger.info("WebSocket соединение закрыто или отсутствует, переподключение...")
                    try:
                        await self.connect()
                        
                        # После переподключения заново подписываемся на каналы
                        params = [f"bookTicker.{symbol}" for symbol in self.symbols]
                        subscribe_message = {
                            "method": "SUBSCRIBE",
                            "params": params,
                            "id": 1
                        }
                        await self.websocket.send(json.dumps(subscribe_message))
                        logger.info(f"Переподключено и отправлен запрос на подписку bookTicker: {params}")
                    except Exception as e:
                        logger.error(f"Ошибка при переподключении: {e}")
                        await asyncio.sleep(self.reconnect_interval)
                        # Увеличиваем интервал переподключения с экспоненциальной задержкой
                        self.reconnect_interval = min(self.reconnect_interval * 2, self.max_reconnect_interval)
                        continue
                
                # Получаем сообщение
                message = await self.websocket.recv()
                
                # Обрабатываем сообщение
                json_data = json.loads(message)
                
                # Проверяем, это ответ на подписку или обновление данных
                if "result" in json_data:
                    logger.info(f"Получен ответ на подписку: {json_data}")
                    continue
                
                data = json_data.get("data", {}) or json_data
                
                # Обрабатываем только сообщения bookTicker
                if data.get("e") == "bookTicker":
                    symbol = data.get('s')
                    if not symbol or symbol not in self._markets_data:
                        continue
                    
                    # Обновляем данные рынка
                    with self._markets_lock:
                        ask_price = float(data.get("a", 0))
                        bid_price = float(data.get("b", 0))
                        
                        # Используем текущее время для временной метки вместо update_id
                        # так как update_id привел к несовместимым форматам дат
                        current_timestamp = time.time()
                        
                        self._markets_data[symbol] = {
                            "ask": ask_price,
                            "bid": bid_price,
                            "last_update": current_timestamp
                        }
                
            except websockets.exceptions.ConnectionClosed as e:
                self.is_connected = False
                logger.warning(f"Backpack WebSocket соединение закрыто: {e}")
                # При разрыве соединения ждем перед повторным подключением
                await asyncio.sleep(self.reconnect_interval)
                # Увеличиваем интервал переподключения с экспоненциальной задержкой
                self.reconnect_interval = min(self.reconnect_interval * 2, self.max_reconnect_interval)
                
            except Exception as e:
                logger.error(f"Ошибка в обработке сообщений Backpack: {e}")
                # При любой другой ошибке тоже ждем перед следующей итерацией
                await asyncio.sleep(self.reconnect_interval)
                # Увеличиваем интервал переподключения
                self.reconnect_interval = min(self.reconnect_interval * 2, self.max_reconnect_interval)

    async def get_markets(self):
        """Возвращает данные рынков из WebSocket"""
        status = "ok"
        markets = []

        try:
            with self._markets_lock:
                for symbol, data in self._markets_data.items():
                    # Проверяем, что у нас есть валидные данные
                    if data["ask"] > 0 and data["bid"] > 0:
                        # Используем текущее время, если last_update некорректный
                        last_update = data["last_update"]
                        if not isinstance(last_update, (int, float)) or last_update < 1000000000:
                            last_update = time.time()
                            
                        markets.append({
                            "symbol": get_general_symbol(symbol),
                            "ask": data["ask"],
                            "bid": data["bid"],
                            "last_update": last_update
                        })

            if not markets:
                raise ValueError("Не удалось получить маркеты от Backpack. Дождитесь обновления данных через WebSocket.")

        except Exception as e:
            status = str(e)
            logger.error(f"Ошибка при получении данных рынков Backpack: {e}")

        return status, markets
