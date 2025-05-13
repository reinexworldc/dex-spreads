import json
import asyncio
import websockets
import threading
import aiohttp
import time
import random
import ssl
import os
import logging
import urllib3  # Добавляем для отключения предупреждений о SSL
from datetime import datetime
from typing import Dict, Any, List, Tuple

from py.trader import get_general_symbol

# Отключаем предупреждения о небезопасных HTTPS запросах
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Создаем логгер для Paradex
logger = logging.getLogger("paradex_app.paradex")

class Paradex:
    def __init__(self, settings: dict):
        self.mode = "testnet" if settings['TESTNET'] else "prod"
        self.session = None
        self.websocket = None
        
        # JWT токен для аутентификации
        self.jwt_token = settings.get('PARADEX_JWT', '')
        
        # ID сообщений для JSON-RPC
        self.message_id = 0
        
        # Получаем список символов, или если не указаны, используем те же, что и в Backpack
        self.symbols = settings.get('SYMBOLS', [])
        
        # Словарь для хранения данных рынков (аналогично Backpack)
        self._markets_data = {}
        self._markets_lock = threading.RLock()
        
        # Словарь для хранения размеров контрактов по символам
        self.contract_sizes = {}
        
        # Флаг для отслеживания статуса подключения
        self._is_connected = False
        self._is_authenticated = False
        self._last_received = 0
        
        # API для начального получения списка символов, если не указаны явно
        self._api_url = f"https://api.{self.mode}.paradex.trade/v1"
        self._ws_url = f"wss://ws.api.{self.mode}.paradex.trade/v1"
        
        # Устанавливаем стандартные размеры контрактов
        self._set_default_contract_sizes()

    def _set_default_contract_sizes(self):
        """Устанавливает стандартные размеры контрактов для основных активов"""
        # Размеры контрактов больше не требуются для нормализации цен,
        # но сохраняем их для справки и возможного будущего использования
        default_sizes = {
            "BTC-USD-PERP": 0.001,
            "ETH-USD-PERP": 0.01,
            "SOL-USD-PERP": 0.1,
            "AVAX-USD-PERP": 0.1,
            "BNB-USD-PERP": 0.01,
            "DOGE-USD-PERP": 1.0,
            "SUI-USD-PERP": 1.0,
            "JTO-USD-PERP": 1.0,
            "JUP-USD-PERP": 1.0,
            "HYPE-USD-PERP": 1.0,
            "APT-USD-PERP": 0.1
        }
        
        # Добавляем основные размеры контрактов
        for symbol, size in default_sizes.items():
            self.contract_sizes[symbol] = float(size)
            # Добавляем альтернативный формат с подчеркиваниями
            alt_symbol = symbol.replace('-', '_')
            self.contract_sizes[alt_symbol] = float(size)
            
        logger.info(f"Установлены размеры контрактов для {len(default_sizes)} символов (для справки)")
        
        # ВАЖНО: объясняем, что больше не используем нормализацию цен
        logger.info("ПРИМЕЧАНИЕ: Normalization больше не используется. Paradex уже предоставляет цены в USD за единицу актива.")
        logger.info("Используем сырые цены без нормализации.")

    def _get_next_id(self):
        """Генерирует новый ID для JSON-RPC запросов"""
        self.message_id += 1
        return self.message_id

    async def _create_session(self):
        """Создает HTTP сессию для REST API запросов с отключенной проверкой SSL"""
        if self.session is None or self.session.closed:
            # Создаем SSL контекст с отключенной проверкой сертификата
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Создаем session с отключенной проверкой SSL
            self.session = aiohttp.ClientSession(
                headers={'Accept': 'application/json'},
                connector=aiohttp.TCPConnector(ssl=ssl_context)
            )
            logger.info("Создана HTTP сессия с отключенной проверкой SSL")

    async def _get_symbols(self):
        """Получает список всех доступных символов через REST API, если не указаны явно"""
        if self.symbols:
            return
            
        await self._create_session()
        
        try:
            # Отключаем проверку SSL
            async with self.session.get(f"{self._api_url}/markets/summary", params={'market': 'ALL'}, ssl=False) as response:
                if response.status != 200:
                    raise ValueError(f"Не удалось получить список символов: {response.status}")
                
                data = await response.json()
                results = data.get("results", [])
                
                self.symbols = [result.get("symbol") for result in results if result.get("symbol")]
                
                logger.info(f"[INFO] Получено {len(self.symbols)} символов от Paradex API")
            
            # Загружаем информацию о размерах контрактов
            await self._load_contract_sizes()
        
        except Exception as e:
            logger.error(f"[ERROR] Не удалось получить список символов: {e}")
            # Установим несколько базовых символов как запасной вариант
            self.symbols = ["BTC-USD-PERP", "ETH-USD-PERP", "SOL-USD-PERP"]

    async def _load_contract_sizes(self):
        """Загружает размеры контрактов для всех символов с отключенной проверкой SSL"""
        try:
            logger.info("Начинаю загрузку размеров контрактов с API Paradex...")
            
            # Создаем сессию если её нет
            if not self.session:
                await self._create_session()
            
            headers = {'Accept': 'application/json'}
            if self.jwt_token:
                headers['Authorization'] = f'Bearer {self.jwt_token}'
                logger.debug("JWT токен добавлен в запрос API")
            else:
                logger.warning("JWT токен не предоставлен, запрос может быть ограничен")
                
            logger.debug(f"Запрос к API: {self._api_url}/markets")
            
            # Первая попытка - стандартный путь
            try:
                async with self.session.get(f"{self._api_url}/markets", headers=headers, ssl=False) as response:
                    response_status = response.status
                    logger.info(f"Получен ответ от API markets со статусом: {response_status}")
                    
                    if response_status == 200:
                        data = await response.json()
                        await self._parse_contract_sizes(data)
                        return
                    else:
                        logger.warning(f"Не удалось получить данные через основной эндпоинт: {response_status}")
            except Exception as e:
                logger.warning(f"Ошибка при основном запросе контрактов: {e}")
            
            # Вторая попытка - альтернативный эндпоинт
            try:
                logger.info("Пробую альтернативный эндпоинт для получения контрактов...")
                async with self.session.get(f"{self._api_url}/bbo", headers=headers, ssl=False) as response:
                    if response.status == 200:
                        logger.info("Получены данные через эндпоинт BBO")
                        # Данные по размерам контрактов здесь не предоставляются
                        # Будем использовать стандартные значения
                        logger.info("Используем стандартные размеры контрактов")
                        return
                    else:
                        logger.warning(f"Альтернативный запрос не удался: {response.status}")
            except Exception as e:
                logger.warning(f"Ошибка при альтернативном запросе контрактов: {e}")
                
            # Если все запросы не удались, логируем это и используем стандартные значения
            logger.info("Используем стандартные размеры контрактов, т.к. все запросы к API не удались")
            
        except Exception as e:
            logger.error(f"Общая ошибка при загрузке размеров контрактов: {e}")
            from traceback import format_exc
            logger.error(format_exc())

    async def _parse_contract_sizes(self, data):
        """Обрабатывает данные о контрактах, полученные от API"""
        try:
            # Проверяем формат ответа
            if isinstance(data, list):
                # Прямой список рынков
                markets_data = data
            else:
                # Вложенная структура
                markets_data = data.get("markets", [])
                if not markets_data:
                    logger.warning("API не вернул данные о рынках в ответе")
                    return
            
            # Счетчики успешных и неуспешных обработок
            success_count = 0
            error_count = 0
            
            for market in markets_data:
                try:
                    # Получаем ID рынка
                    market_id = market.get('id') or market.get('symbol')
                    if not market_id:
                        error_count += 1
                        continue
                        
                    # Преобразуем формат ID для соответствия с нашими данными
                    symbol = market_id
                    alternate_symbol = market_id.replace('-', '_')
                    
                    # Получаем размер контракта
                    contract_size = None
                    if 'baseSize' in market:
                        contract_size = market.get('baseSize')
                    elif 'contractSize' in market:
                        contract_size = market.get('contractSize')
                    
                    if contract_size is None:
                        error_count += 1
                        continue
                    
                    # Преобразуем размер контракта в число
                    try:
                        contract_size = float(contract_size)
                        if contract_size <= 0:
                            raise ValueError("Размер контракта меньше или равен нулю")
                    except (ValueError, TypeError):
                        error_count += 1
                        continue
                    
                    # Сохраняем размер контракта в обоих форматах символа
                    self.contract_sizes[symbol] = contract_size
                    self.contract_sizes[alternate_symbol] = contract_size
                    
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    logger.debug(f"Ошибка при обработке рынка: {e}")
            
            logger.info(f"Обработка размеров контрактов: успешно - {success_count}, ошибок - {error_count}")
            
            # Проверяем наличие основных символов
            important_symbols = ["BTC-USD-PERP", "ETH-USD-PERP", "SOL-USD-PERP"]
            for symbol in important_symbols:
                if symbol in self.contract_sizes:
                    logger.info(f"Размер контракта для {symbol}: {self.contract_sizes[symbol]}")
                else:
                    logger.warning(f"Не найден размер контракта для важного символа {symbol}")
        
        except Exception as e:
            logger.error(f"Ошибка при парсинге данных о контрактах: {e}")

    async def connect(self):
        """Устанавливает WebSocket соединение с Paradex с отключенной проверкой SSL"""
        if self.websocket is not None and not self.websocket.closed:
            return
            
        try:
            # Отключаем проверку SSL сертификата
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Параметры подключения с увеличенным таймаутом
            connection_options = {
                'ssl': ssl_context,
                'ping_interval': 30,  # Интервал отправки ping-сообщений в секундах
                'ping_timeout': 10,   # Таймаут ожидания pong в секундах
                'close_timeout': 10,  # Таймаут закрытия соединения в секундах
                'max_size': 10 * 1024 * 1024  # Максимальный размер сообщения (10MB)
            }
            
            # Создаем WebSocket подключение
            logger.info(f"Подключение к Paradex WebSocket: {self._ws_url}")
            self.websocket = await websockets.connect(self._ws_url, **connection_options)
            self._is_connected = True
            self._last_received = time.time()
            logger.info(f"[INFO] Успешно подключен к Paradex WebSocket")
            
            # Аутентификация после подключения
            if self.jwt_token:
                auth_success = await self._authenticate()
                if auth_success:
                    logger.info("Аутентификация успешна")
                else:
                    logger.warning("Аутентификация не удалась")
            
            # Запускаем задачу проверки состояния соединения
            asyncio.create_task(self._heartbeat())
            
            return True
        except Exception as e:
            logger.error(f"[ERROR] Ошибка подключения к Paradex WebSocket: {e}")
            self._is_connected = False
            self._is_authenticated = False
            return False

    async def _authenticate(self):
        """Аутентификация по JWT токену"""
        if not self.jwt_token:
            logger.warning("JWT токен не предоставлен, аутентификация невозможна")
            return False
            
        try:
            auth_message = {
                "jsonrpc": "2.0",
                "method": "auth",
                "params": {
                    "bearer": self.jwt_token
                },
                "id": self._get_next_id()
            }
            
            logger.debug(f"Отправка запроса аутентификации")
            await self.websocket.send(json.dumps(auth_message))
            
            # Ожидаем ответ на аутентификацию с таймаутом
            try:
                response = await asyncio.wait_for(self.websocket.recv(), timeout=10)
                auth_response = json.loads(response)
                
                # Проверяем успешность аутентификации
                if "result" in auth_response:
                    self._is_authenticated = True
                    logger.info("[INFO] Успешная аутентификация в Paradex")
                    return True
                else:
                    error = auth_response.get("error", {})
                    logger.error(f"[ERROR] Ошибка аутентификации: {error.get('message', 'Неизвестная ошибка')}")
                    self._is_authenticated = False
                    return False
            except asyncio.TimeoutError:
                logger.error("[ERROR] Таймаут при ожидании ответа на аутентификацию")
                self._is_authenticated = False
                return False
                
        except Exception as e:
            logger.error(f"[ERROR] Ошибка при аутентификации: {e}")
            self._is_authenticated = False
            return False

    async def subscribe(self):
        """Подписывается на обновления рыночных данных по всем символам"""
        status = "ok"
        
        try:
            # Получаем список символов, если не указаны явно
            await self._get_symbols()
            
            # Подключаемся к WebSocket
            connection_result = await self.connect()
            if not connection_result:
                return "error: failed to connect"
            
            # Инициализируем словарь данных рынков
            with self._markets_lock:
                for symbol in self.symbols:
                    self._markets_data[symbol] = {
                        "ask": 0,
                        "bid": 0,
                        "last_update": 0
                    }
            
            # Подписываемся на обновления orderbook (book.SYMBOL)
            successful_subscriptions = 0
            failed_subscriptions = 0
            
            for symbol in self.symbols:
                try:
                    subscribe_message = {
                        "jsonrpc": "2.0",
                        "method": "subscribe",
                        "params": {
                            "channel": f"bbo.{symbol}"  # формат: bbo.BTC-USD-PERP
                        },
                        "id": self._get_next_id()
                    }
                    
                    # Логируем запрос на подписку для отладки
                    logger.debug(f"Отправка запроса на подписку: {json.dumps(subscribe_message)}")
                    
                    await self.websocket.send(json.dumps(subscribe_message))
                    
                    # Ждем и обрабатываем ответ на подписку с таймаутом
                    try:
                        response = await asyncio.wait_for(self.websocket.recv(), timeout=5)
                        sub_response = json.loads(response)
                        
                        # Проверяем успешность подписки
                        if "error" in sub_response:
                            error = sub_response.get("error", {})
                            logger.error(f"Ошибка подписки на {symbol}: {error.get('message', 'Неизвестная ошибка')}")
                            failed_subscriptions += 1
                        else:
                            logger.debug(f"Успешная подписка на {symbol}")
                            successful_subscriptions += 1
                    except asyncio.TimeoutError:
                        logger.error(f"Таймаут при ожидании ответа на подписку для {symbol}")
                        failed_subscriptions += 1
                    
                    # Ждем небольшую паузу между подписками, чтобы не превысить лимиты
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Ошибка при подписке на {symbol}: {e}")
                    failed_subscriptions += 1
            
            # Запускаем асинхронную задачу для прослушивания сообщений
            asyncio.create_task(self.listen())
            
            logger.info(f"[INFO] Подписка завершена: успешно - {successful_subscriptions}, ошибок - {failed_subscriptions}")
            
            if failed_subscriptions > 0 and successful_subscriptions == 0:
                status = "error: all subscriptions failed"
            elif failed_subscriptions > 0:
                status = "warning: some subscriptions failed"
            
        except Exception as e:
            status = f"error: {str(e)}"
            logger.error(f"[ERROR] Ошибка при подписке на Paradex: {e}")
            
        return status

    async def listen(self):
        """Асинхронно прослушивает сообщения WebSocket и обновляет данные рынков"""
        try:
            message_counter = 0
            while True:
                if not self._is_connected:
                    await self.connect()
                    
                message = await self.websocket.recv()
                self._last_received = time.time()
                
                # Парсим полученные данные
                data = json.loads(message)
                
                # Увеличиваем счетчик и логируем первые 5 сообщений для отладки
                message_counter += 1
                if message_counter <= 5:
                    logger.debug(f"Paradex WebSocket сообщение #{message_counter}: {message}")
                
                # Проверяем наличие ошибки в ответе
                if "error" in data:
                    error = data.get("error", {})
                    logger.error(f"Ошибка от Paradex WebSocket: {error.get('message', 'Неизвестная ошибка')}")
                    continue
                
                # Обрабатываем различные типы сообщений по полю 'method'
                method = data.get("method")
                
                if method == "subscription":
                    # Это сообщение подписки - обрабатываем данные
                    params = data.get("params", {})
                    channel = params.get("channel", "")
                    
                    # Проверяем тип канала
                    if channel.startswith("bbo."):
                        # Вызываем обработчик обновления книги заявок
                        await self._handle_book_update(data)
                    else:
                        # Логируем другие каналы
                        if random.random() < 0.05:  # Логируем 5% сообщений, чтобы не перегружать логи
                            logger.debug(f"Получены данные для канала {channel}")
                
                elif method == "reply":
                    # Ответ на наш запрос
                    result = data.get("result")
                    request_id = data.get("id")
                    logger.debug(f"Получен ответ на запрос ID {request_id}")
                
                else:
                    # Для отладки неизвестных сообщений
                    if random.random() < 0.01:  # логируем примерно 1% обновлений
                        logger.debug(f"Неизвестное сообщение от Paradex: {message}")
                
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Соединение с Paradex закрыто")
            # Пытаемся переподключиться
            asyncio.create_task(self._reconnect())
        except Exception as e:
            logger.error(f"Ошибка при прослушивании Paradex: {e}")
            from traceback import format_exc
            logger.error(format_exc())
            # Пытаемся переподключиться при других ошибках
            asyncio.create_task(self._reconnect())

    async def _handle_book_update(self, message):
        """Обрабатывает обновления книги заявок"""
        try:
            params = message.get("params", {})
            
            # Проверяем формат сообщения
            if "result" in params:
                # Старый формат с tick
                result = params.get("result", {})
                symbol = result.get("market", "")
                tick = result.get("tick", {})
                
                if not symbol or not tick:
                    logger.warning(f"Получено неполное обновление книги заявок: {message}")
                    return
                    
                # Текущее время в миллисекундах
                timestamp = int(time.time() * 1000)
                
                # Получаем текущий лучший бид и аск
                bids = tick.get("bids", [])
                asks = tick.get("asks", [])
                
                if not bids or not asks:
                    return
                    
                # Берем лучшую цену бид и аск
                best_bid = bids[0]
                best_ask = asks[0]
                
                if not best_bid or not best_ask:
                    return
                    
                # Извлекаем цены
                bid_price = float(best_bid[0])
                ask_price = float(best_ask[0])
            else:
                # Новый формат: прямой доступ к данным
                data = params.get("data", {})
                symbol = data.get("market", "")
                
                if not symbol:
                    logger.warning(f"Получено сообщение без указания рынка: {message}")
                    return
                
                # Текущее время в миллисекундах
                timestamp = data.get("last_updated_at", int(time.time() * 1000))
                
                # Получаем bid и ask напрямую из data
                bid_str = data.get("bid")
                ask_str = data.get("ask")
                
                if not bid_str or not ask_str:
                    logger.debug(f"Сообщение без bid/ask данных: {message}")
                    return
                
                # Конвертируем строки в float
                try:
                    bid_price = float(bid_str)
                    ask_price = float(ask_str)
                except (ValueError, TypeError):
                    logger.warning(f"Невозможно конвертировать bid/ask в числа: {bid_str}, {ask_str}")
                    return
            
            # Если цены отрицательные или равны нулю, выходим
            if ask_price <= 0 or bid_price <= 0:
                logger.warning(f"Для {symbol} получены невалидные цены: ask={ask_price}, bid={bid_price}")
                return
                
            # Определяем тип инструмента
            is_option = False
            if '-' in symbol:
                parts = symbol.split('-')
                if len(parts) >= 3 and (parts[-1] == 'C' or parts[-1] == 'P'):
                    # Это опцион (Call или Put)
                    is_option = True
            
            # Базовый актив для проверки реалистичности цен (только для неопционных инструментов)
            if not is_option:
                base_asset = symbol.split('-')[0] if '-' in symbol else symbol.split('_')[0]
                
                # Проверяем реалистичность цен для известных активов и не-опционных контрактов
                price_checks = {
                    "BTC": (80000, 100000),  # BTC ~$90000
                    "ETH": (1500, 3000),     # ETH ~$2000
                    "SOL": (100, 300),       # SOL ~$200
                    "AVAX": (10, 50),        # AVAX ~$30
                    "SUI": (0.5, 3),         # SUI ~$1-2
                    "BNB": (400, 650),       # BNB ~$500
                    "DOGE": (0.08, 0.2),     # DOGE ~$0.1
                    "JTO": (0.5, 5),         # JTO ~$1-3
                }
                
                # Проверяем, находится ли цена в разумном диапазоне для известных активов
                if base_asset in price_checks and '-PERP' in symbol:
                    min_price, max_price = price_checks[base_asset]
                    
                    # Если цены не попадают в диапазон, логируем это
                    if not (min_price <= ask_price <= max_price) or not (min_price <= bid_price <= max_price):
                        logger.warning(f"Нереалистичные цены для {symbol}: ask={ask_price}, bid={bid_price}, ожидаемый диапазон: {min_price}-{max_price}")
                        # Но не выходим, чтобы не блокировать данные
            
            # Сохраняем данные без нормализации - Paradex уже дает реальные цены активов
            if symbol not in self._markets_data:
                self._markets_data[symbol] = {}
                
            self._markets_data[symbol].update({
                "ask": ask_price,
                "bid": bid_price,
                "last_update": timestamp,
                "is_option": is_option  # Добавляем флаг, чтобы знать, что это опцион
            })
            
            # Логируем только для важных активов и редко
            log_option = is_option and random.random() < 0.005  # Реже логируем опционы
            log_main = not is_option and random.random() < 0.01  # Чаще логируем основные активы
            
            if log_option or log_main:
                if is_option:
                    logger.info(f"Paradex цены для опциона {symbol}: ask={ask_price}, bid={bid_price}")
                else:
                    base_asset = symbol.split('-')[0] if '-' in symbol else symbol.split('_')[0]
                    if base_asset in ["BTC", "ETH", "SOL", "AVAX"]:
                        logger.info(f"Paradex цены для {symbol}: ask={ask_price}, bid={bid_price}")
        
        except Exception as e:
            logger.error(f"Ошибка при обработке обновления книги заявок: {e}")
            from traceback import format_exc
            logger.error(format_exc())

    async def _heartbeat(self):
        """Периодическая проверка состояния соединения"""
        while True:
            await asyncio.sleep(30)  # Проверка каждые 30 секунд
            
            # Если нет соединения, пытаемся переподключиться
            if not self.websocket or self.websocket.closed:
                logger.warning("Отсутствует соединение с Paradex, пытаемся переподключиться")
                await self._reconnect()
                continue
                
            # Проверяем давность последнего сообщения
            if self._last_received > 0:
                time_since_last = time.time() - self._last_received
                if time_since_last > 60:  # Более 60 секунд без сообщений
                    logger.warning(f"Долгое отсутствие сообщений от Paradex ({time_since_last:.1f} сек.), переподключение")
                    await self._reconnect()
                    continue
            
            # Отправляем пинг для проверки соединения
            try:
                pong = await self.websocket.ping()
                await asyncio.wait_for(pong, timeout=10)
                logger.debug("Ping-pong с Paradex успешен")
            except Exception as e:
                logger.warning(f"Ошибка отправки ping к Paradex: {e}, переподключение")
                await self._reconnect()

    async def _reconnect(self):
        """Переподключение к серверу при обрыве соединения"""
        # Закрываем текущее соединение, если оно есть
        try:
            if self.websocket:
                await self.websocket.close()
        except:
            pass
        
        self.websocket = None
        
        # Ждем немного перед повторным подключением
        await asyncio.sleep(5)
        
        # Пытаемся подключиться снова
        logger.info("Попытка переподключения к Paradex...")
        await self.subscribe()

    async def get_markets(self) -> Tuple[str, List[Dict[str, Any]]]:
        status = "ok"
        markets = []
        
        try:
            priority_symbols = ["BTC-USD-PERP", "ETH-USD-PERP", "SOL-USD-PERP", "AVAX-USD-PERP"]
            regular_symbols = []
            
            for symbol in self._markets_data.keys():
                if symbol in priority_symbols:
                    pass
                else:
                    # Проверяем, является ли символ опционом
                    is_option = self._markets_data[symbol].get("is_option", False)
                    
                    # Для основного списка пропускаем опционы
                    if not is_option and '-PERP' in symbol:
                        regular_symbols.append(symbol)
            
            all_symbols = priority_symbols + sorted(regular_symbols)
            
            for symbol in all_symbols:
                if symbol not in self._markets_data:
                    continue
                
                data = self._markets_data[symbol]
                
                # Пропускаем опционы в основном списке
                if data.get("is_option", False):
                    continue
                
                base_asset = symbol.split('-')[0] if '-' in symbol else symbol.split('_')[0]
                
                market_data = {
                    "symbol": symbol,
                    "base_asset": base_asset,
                    "quote_asset": "USDC",
                    "ask": data["ask"],
                    "bid": data["bid"],
                    "last_update": data.get("last_update", 0)
                }
                
                markets.append(market_data)
            
            logger.info(f"Возвращено {len(markets)} рынков из Paradex (исключая опционы)")
                
        except Exception as e:
            logger.error(f"Ошибка при получении данных рынков: {e}")
            from traceback import format_exc
            logger.error(format_exc())
            status = f"error: {str(e)}"
            
        return status, markets