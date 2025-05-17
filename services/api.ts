/**
 * Базовый API-клиент для взаимодействия с бэкендом
 */

// Объявляем глобальный тип для Window
declare global {
  interface Window {
    ENV_CONFIG?: {
      API_URL: string;
    };
  }
}

// Функция для получения базового URL API
function getApiBaseUrl() {
  if (typeof window !== 'undefined' && window.ENV_CONFIG && window.ENV_CONFIG.API_URL) {
    return window.ENV_CONFIG.API_URL;
  }
  
  // Используем полный URL с портом для доступа к Flask-серверу
  if (typeof window !== 'undefined') {
    // В продакшене используем относительный путь к API через Nginx
    if (window.location.hostname !== 'localhost') {
      return '/api';
    }
    // Локальная разработка - указываем явно адрес Flask без /api префикса
    // т.к. префикс добавляется в каждом методе API
    return 'http://localhost:5000';
  }
  
  // Для SSR или Docker среды
  return process.env.NEXT_PUBLIC_API_URL || '/api';
}

// Базовый URL для API запросов
const API_BASE_URL = getApiBaseUrl();

/**
 * Интерфейс для данных о спреде
 */
export interface SpreadData {
  id: number;
  symbol: string;
  signal: string;
  difference: number;
  buy_exchange: string;
  sell_exchange: string;
  buy_price: number;
  sell_price: number;
  created: number;
  exchange1: string;
  exchange2: string;
  formatted_exchange1: string;
  formatted_exchange2: string;
  [key: string]: any; // Для поддержки динамических полей prices
}

/**
 * Интерфейс для данных о крупнейших спредах
 */
export interface LargestSpread {
  symbol: string;
  max_spread: number;
  max_pair: string;
  formatted_pair: string;
  pair_spreads: {
    [key: string]: {
      largest_buy: number;
      largest_sell: number;
    };
  };
}

/**
 * Интерфейс для пары бирж
 */
export interface ExchangePair {
  id: string;
  name: string;
}

/**
 * Интерфейс для параметров запроса данных
 */
export interface DataQueryParams {
  symbol: string;
  exchange_pair: string;
  time_range: string;
  sort_by?: string;
  sort_order?: string;
  since?: number | null;
}

/**
 * Интерфейс для данных о символе
 */
export interface SymbolData {
  symbol: string;
}

/**
 * Интерфейс для данных стакана ордеров (orderbook)
 */
export interface OrderbookData {
  symbol: string;
  exchange: string;
  timestamp: number;
  bids: {
    price: number;
    volume: number;
  }[];
  asks: {
    price: number;
    volume: number;
  }[];
  spread: number;
  totalVolume: number;
  updatedAt: string;
  is_generated?: boolean;
  error?: string;
}

/**
 * Функция для получения данных о спредах
 */
export async function fetchSpreadData(params: DataQueryParams): Promise<SpreadData[]> {
  const queryParams = new URLSearchParams({
    symbol: params.symbol,
    exchange_pair: params.exchange_pair,
    time_range: params.time_range,
  });

  if (params.sort_by) queryParams.append('sort_by', params.sort_by);
  if (params.sort_order) queryParams.append('sort_order', params.sort_order);
  if (params.since) queryParams.append('since', params.since.toString());

  try {
    const response = await fetch(`${API_BASE_URL}/api/data?${queryParams.toString()}`);
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching spread data:', error);
    throw error;
  }
}

/**
 * Функция для получения сводной информации о спредах
 */
export async function fetchSummary(timeRange: string): Promise<Record<string, any>> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/summary?time_range=${timeRange}`);
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching summary:', error);
    throw error;
  }
}

/**
 * Функция для получения списка доступных пар бирж
 */
export async function fetchExchangePairs(): Promise<ExchangePair[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/exchange_pairs`);
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching exchange pairs:', error);
    throw error;
  }
}

/**
 * Функция для получения списка доступных торговых пар
 */
export async function fetchSymbols(): Promise<SymbolData[]> {
  try {
    // Эндпоинт для получения списка символов нужно реализовать на бэкенде
    const response = await fetch(`${API_BASE_URL}/api/symbols`);
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching symbols:', error);
    throw error;
  }
}

/**
 * Функция для получения данных о крупнейших спредах
 */
export async function fetchLargestSpreads(timeRange: string): Promise<LargestSpread[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/largest_spreads_api?time_range=${timeRange}`);
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching largest spreads:', error);
    throw error;
  }
}

/**
 * Функция для получения данных о стакане ордеров (orderbook)
 */
export async function fetchOrderbookData(exchange: string, symbol: string, retryCount = 2): Promise<OrderbookData> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/orderbook?exchange=${exchange}&symbol=${symbol}`);
    
    // Получаем данные из ответа, даже если статус не OK, чтобы извлечь сообщение об ошибке
    const data = await response.json();
    
    if (!response.ok) {
      // Если сервер возвращает ошибку и статус >= 500, можно попробовать повторить запрос
      if (retryCount > 0 && response.status >= 500) {
        console.info(`Повторная попытка запроса orderbook для ${exchange} ${symbol}, осталось попыток: ${retryCount}`);
        // Ждем 500мс перед повторной попыткой
        await new Promise(resolve => setTimeout(resolve, 500));
        return fetchOrderbookData(exchange, symbol, retryCount - 1);
      }
      
      // Включаем сообщение об ошибке из ответа сервера, если оно есть
      throw new Error(
        data.error 
          ? `API error (${response.status}): ${data.error}` 
          : `API error: ${response.status}`
      );
    }
    
    // Проверяем, есть ли в данных признак ошибки
    if (data.error) {
      console.warn(`Orderbook API вернул ошибку: ${data.error}`);
      throw new Error(`API error: ${data.error}`);
    }
    
    // Нормализуем данные - убедимся, что bids и asks всегда массивы
    if (data.bids && !Array.isArray(data.bids)) {
      data.bids = [data.bids];
    }
    
    if (data.asks && !Array.isArray(data.asks)) {
      data.asks = [data.asks];
    }
    
    return data;
  } catch (error) {
    console.error(`Error fetching orderbook data for ${exchange} ${symbol}:`, error);
    
    // Не генерируем локальные фейковые данные, а пробрасываем ошибку дальше
    throw error;
  }
} 