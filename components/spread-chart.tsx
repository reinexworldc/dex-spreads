"use client"

import { useEffect, useState, useRef } from "react"
import { Line } from "react-chartjs-2"
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  type ChartOptions,
  type ChartType,
} from "chart.js"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import { ZoomIn, ZoomOut, RefreshCw, Hand, Move, Clock, Download } from "lucide-react"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { fetchSpreadData, type SpreadData } from "@/services/api"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { motion } from "framer-motion"

// Register ChartJS components без zoom плагина (добавим его динамически)
ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend)

// Доступные временные фреймы
const TIME_FRAMES = [
  { value: "1m", label: "1 минута" },
  { value: "5m", label: "5 минут" },
  { value: "15m", label: "15 минут" },
  { value: "30m", label: "30 минут" },
  { value: "1h", label: "1 час" },
  { value: "3h", label: "3 часа" },
  { value: "6h", label: "6 часов" },
  { value: "24h", label: "1 день" }
]

// Функция для получения размера интервала в миллисекундах
const getIntervalSize = (timeFrame: string): number => {
  switch (timeFrame) {
    case '1m': return 60 * 1000; // 1 минута
    case '5m': return 5 * 60 * 1000; // 5 минут
    case '15m': return 15 * 60 * 1000; // 15 минут
    case '30m': return 30 * 60 * 1000; // 30 минут
    case '1h': return 60 * 60 * 1000; // 1 час
    case '3h': return 3 * 60 * 60 * 1000; // 3 часа
    case '6h': return 6 * 60 * 60 * 1000; // 6 часов
    case '24h': return 24 * 60 * 60 * 1000; // 24 часа
    default: return 60 * 1000; // по умолчанию 1 минута
  }
}

// Форматирование метки времени в часы:минуты
const formatTimestamp = (timestamp: number): string => {
  const date = new Date(timestamp)
  return `${date.getHours()}:${date.getMinutes().toString().padStart(2, "0")}`
}

// Форматирование метки времени с учетом временного фрейма
const formatTimestampByTimeFrame = (timestamp: number, timeFrame: string): string => {
  const date = new Date(timestamp)
  
  // Для краткосрочных фреймов показываем только часы:минуты
  if (['1m', '5m', '15m', '30m', '1h'].includes(timeFrame)) {
    return `${date.getHours()}:${date.getMinutes().toString().padStart(2, "0")}`
  }
  
  // Для долгосрочных фреймов показываем день и час
  return `${date.getDate()}/${date.getMonth() + 1} ${date.getHours()}:00`
}

// Агрегация данных по временным интервалам
const aggregateDataByTimeFrame = (data: SpreadData[], timeFrame: string): { time: number, value: number }[] => {
  if (!data.length) return []
  
  const intervalSize = getIntervalSize(timeFrame)
  const result: { time: number, value: number, count: number }[] = []
  
  // Сортируем данные по времени
  const sortedData = [...data].sort((a, b) => a.created - b.created)
  
  // Определяем начальный и конечный интервалы
  const startTime = Math.floor(sortedData[0].created / intervalSize) * intervalSize
  const endTime = Math.floor(Date.now() / intervalSize) * intervalSize
  
  // Создаем массив всех временных интервалов от начала до текущего момента
  const timeIntervals: number[] = []
  for (let time = startTime; time <= endTime; time += intervalSize) {
    timeIntervals.push(time)
  }
  
  // Инициализируем результаты для всех временных интервалов
  timeIntervals.forEach(time => {
    result.push({ time, value: 0, count: 0 })
  })
  
  // Группируем точки по временным интервалам
  sortedData.forEach(item => {
    const time = Math.floor(item.created / intervalSize) * intervalSize
    const existingBucket = result.find(bucket => bucket.time === time)
    
    if (existingBucket) {
      existingBucket.value += item.difference
      existingBucket.count += 1
    }
  })
  
  // Вычисляем среднее значение для каждого интервала и удаляем пустые интервалы
  return result
    .filter(bucket => bucket.count > 0)  // Удаляем интервалы без данных
    .map(bucket => ({
      time: bucket.time,
      value: bucket.value / bucket.count
    }))
}

// Преобразование данных API в формат для графика с учетом временного фрейма
const processChartData = (data: SpreadData[], exchange1: string, exchange2: string, timeFrame: string) => {
  // Агрегируем данные по временным интервалам
  const aggregatedData = aggregateDataByTimeFrame(data, timeFrame)
  
  const labels = aggregatedData.map(item => formatTimestampByTimeFrame(item.time, timeFrame))
  const values = aggregatedData.map(item => item.value)
  
  // Находим экстремумы (максимальные и минимальные значения) - больше не нужно для аннотаций
  // Но оставим для возможного использования в будущем
  let maxValue = -Infinity;
  let minValue = Infinity;
  
  values.forEach((value) => {
    if (value > maxValue) {
      maxValue = value;
    }
    if (value < minValue) {
      minValue = value;
    }
  });

  return {
    labels,
    datasets: [
      {
        label: `Спред между ${exchange1} и ${exchange2} (%)`,
        data: values,
        borderColor: "rgb(99, 102, 241)",
        backgroundColor: "rgba(99, 102, 241, 0.5)",
        tension: 0.3,
        pointRadius: aggregatedData.length < 100 ? 2 : 0, // Показываем точки только если их немного
        pointHoverRadius: 5, // Show points on hover
      },
    ],
    // Больше не добавляем информацию об экстремумах
  }
}

interface SpreadChartProps {
  pair: string
  exchange1: string
  exchange2: string
  timeFrame?: string
  onTimeFrameChange?: (timeFrame: string) => void
}

type ToolMode = "cursor" | "hand" | "zoom"

// Функция для создания ключа кэша
const createCacheKey = (pair: string, exchange1: string, exchange2: string, timeFrame: string): string => {
  return `spread-data-${pair}-${exchange1}-${exchange2}-${timeFrame}`;
}

// Функция для кэширования данных с учетом ограничений localStorage
const cacheData = (key: string, data: any, metaOnly: boolean = false) => {
  if (typeof window === 'undefined') return false;
  
  try {
    // Если нужно обновить только метаданные, то обновляем их и выходим
    if (metaOnly) {
      localStorage.setItem(`${key}-meta`, JSON.stringify({ 
        lastAccess: Date.now() 
      }));
      return true;
    }

    // Подготавливаем данные для сохранения
    const dataStr = JSON.stringify(data);
    
    // Проверяем размер данных (в байтах)
    const dataSize = new Blob([dataStr]).size;
    const MAX_SIZE = 2 * 1024 * 1024; // 2MB - устанавливаем ограничение для перестраховки
    
    if (dataSize > MAX_SIZE) {
      console.warn(`Данные слишком большие для кэширования (${(dataSize/1024/1024).toFixed(2)}MB). Сокращаем выборку.`);
      
      // Если это массив, сохраняем только последние N элементов
      if (Array.isArray(data) && data.length > 100) {
        // Берем только последние элементы (недавние данные важнее)
        const reducedData = data.slice(-Math.floor(data.length * 0.5)); // 50% последних элементов
        return cacheData(key, reducedData); // Рекурсивно пробуем сохранить сокращенный набор
      }
      
      // Если это не массив или массив слишком мал, просто логируем ошибку
      console.error('Данные слишком большие для кэширования и не могут быть сокращены');
      return false;
    }
    
    // Проверяем свободное место перед сохранением
    // Грубая оценка: берем текущее потребление localStorage и сравниваем с примерным лимитом
    let totalSize = 0;
    for (let i = 0; i < localStorage.length; i++) {
      const itemKey = localStorage.key(i);
      if (itemKey) {
        const item = localStorage.getItem(itemKey);
        if (item) {
          totalSize += item.length * 2; // Примерная оценка размера в байтах (UTF-16 = 2 байта/символ)
        }
      }
    }
    
    const STORAGE_LIMIT = 5 * 1024 * 1024; // 5MB - консервативная оценка
    if (totalSize + dataSize > STORAGE_LIMIT) {
      console.warn('Недостаточно места в localStorage. Запускаем очистку старых данных...');
      manageCache(true); // Принудительная очистка
    }
    
    // Сохраняем данные
    localStorage.setItem(key, dataStr);
    
    // Обновляем метаданные
    localStorage.setItem(`${key}-meta`, JSON.stringify({ 
      lastAccess: Date.now(),
      size: dataSize
    }));
    
    return true;
  } catch (e) {
    // Обрабатываем ошибку квоты
    if (e instanceof DOMException && (
        e.name === 'QuotaExceededError' || 
        e.name === 'NS_ERROR_DOM_QUOTA_REACHED')) {
      
      console.error('Превышена квота localStorage. Запускаем экстренную очистку кэша...');
      
      // Аварийная очистка: удаляем старые данные
      manageCache(true);
      
      // Сокращаем данные и пробуем снова
      if (Array.isArray(data) && data.length > 50) {
        // Берем только последние 30% элементов в критической ситуации
        const emergencyData = data.slice(-Math.floor(data.length * 0.3));
        console.warn(`Аварийное сокращение данных: ${data.length} -> ${emergencyData.length} элементов`);
        return cacheData(key, emergencyData);
      }
    }
    
    console.error('Ошибка при сохранении в кэш:', e);
    return false;
  }
}

// Функция для управления кэшем (модифицированная)
const manageCache = (forceClean: boolean = false) => {
  if (typeof window === 'undefined') return;
  
  // Получаем все ключи localStorage, связанные с кэшем
  const totalKeys = Object.keys(localStorage).filter(key => key.startsWith('spread-data-') && !key.endsWith('-meta'));
  
  // Если кэшированных данных больше допустимого количества или принудительная очистка
  const MAX_CACHE_ITEMS = 5; // Уменьшаем до 5 (было 10)
  if (forceClean || totalKeys.length > MAX_CACHE_ITEMS) {
    // Получаем время последнего доступа для каждого ключа из метаданных
    const cacheMetadata: Record<string, { lastAccess: number, size?: number }> = {};
    
    for (const key of totalKeys) {
      try {
        const metadata = localStorage.getItem(`${key}-meta`);
        if (metadata) {
          cacheMetadata[key] = JSON.parse(metadata);
        } else {
          // Если метаданных нет, создаем их с текущим временем
          cacheMetadata[key] = { lastAccess: Date.now() - 86400000 }; // -1 день, чтобы этот элемент был удален первым
        }
      } catch (e) {
        console.error('Ошибка при чтении метаданных кэша:', e);
        // Устанавливаем дефолтное значение
        cacheMetadata[key] = { lastAccess: Date.now() - 86400000 };
      }
    }
    
    // Сортируем ключи по времени последнего доступа (от старых к новым)
    const sortedKeys = totalKeys.sort((a, b) => 
      (cacheMetadata[a]?.lastAccess || 0) - (cacheMetadata[b]?.lastAccess || 0)
    );
    
    // При принудительной очистке удаляем больше элементов
    const keysToKeep = forceClean ? 2 : MAX_CACHE_ITEMS;
    
    // Удаляем самые старые ключи, оставляя только последние
    for (let i = 0; i < sortedKeys.length - keysToKeep; i++) {
      localStorage.removeItem(sortedKeys[i]);
      localStorage.removeItem(`${sortedKeys[i]}-meta`);
      console.log(`Удален старый кэш: ${sortedKeys[i]}`);
    }
  }
}

// Функция для обновления метаданных кэша (обновленная)
const updateCacheMetadata = (key: string) => {
  cacheData(key, null, true); // Флаг metaOnly=true означает, что мы обновляем только метаданные
}

// Функция для экспорта данных в CSV
const exportToCSV = (data: SpreadData[], filename: string): void => {
  const csvHeader = ["Время", "Спред (%)", "Биржа1", "Биржа2", "Цена1", "Цена2"];
  
  // Сортируем данные по времени
  const sortedData = [...data].sort((a, b) => a.created - b.created);
  
  const csvRows = sortedData.map(item => [
    new Date(item.created).toISOString(),
    item.difference.toFixed(6),
    item.formatted_exchange1 || item.exchange1,
    item.formatted_exchange2 || item.exchange2,
    item.buy_price?.toFixed(6) || "N/A",
    item.sell_price?.toFixed(6) || "N/A"
  ]);
  
  // Добавляем заголовок
  csvRows.unshift(csvHeader);
  
  // Преобразуем в CSV формат
  const csvContent = csvRows.map(row => row.join(",")).join("\n");
  
  // Создаем blob и ссылку для скачивания
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  
  // Создаем ссылку для скачивания
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  link.style.visibility = 'hidden';
  
  // Добавляем ссылку в DOM и вызываем клик
  document.body.appendChild(link);
  link.click();
  
  // Удаляем ссылку
  document.body.removeChild(link);
}

// Функция для очистки всего кэша
const clearAllCache = () => {
  if (typeof window === 'undefined') return;
  
  // Получаем все ключи localStorage
  const keys = Object.keys(localStorage);
  
  // Удаляем все ключи, которые относятся к кэшу данных спреда
  for (const key of keys) {
    if (key.startsWith('spread-data-')) {
      localStorage.removeItem(key);
      localStorage.removeItem(`${key}-meta`);
    }
  }
  
  console.log('Кэш полностью очищен');
}

export function SpreadChart({ pair, exchange1, exchange2, timeFrame = "24h", onTimeFrameChange }: SpreadChartProps) {
  const [chartData, setChartData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(false) // Индикатор обновления данных
  const [currentSpread, setCurrentSpread] = useState(0)
  const [maxSpread, setMaxSpread] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const chartRef = useRef<any>(null)
  const [zoomMode, setZoomMode] = useState<"xy" | "x" | "y">("xy")
  const [toolMode, setToolMode] = useState<ToolMode>("cursor")
  const [zoomPluginLoaded, setZoomPluginLoaded] = useState(false)
  const [localTimeFrame, setLocalTimeFrame] = useState<string>(timeFrame)
  const [lastUpdate, setLastUpdate] = useState<number>(Date.now())
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true)
  const [refreshInterval, setRefreshInterval] = useState<number | null>(null)
  const [rawData, setRawData] = useState<SpreadData[]>([])
  const [pointsCount, setPointsCount] = useState(0) // Счетчик точек для отображения
  const [showCacheControls, setShowCacheControls] = useState(false)
  const firstLoadRef = useRef(true) // Отслеживание первой загрузки
  
  // Ключ кэша для текущих параметров
  const cacheKey = createCacheKey(pair, exchange1, exchange2, localTimeFrame);

  // Загрузка данных из кэша при изменении параметров
  useEffect(() => {
    // Проверяем наличие кэшированных данных
    if (typeof window !== 'undefined') {
      try {
        const cachedData = localStorage.getItem(cacheKey);
        if (cachedData) {
          const parsedData = JSON.parse(cachedData);
          if (Array.isArray(parsedData) && parsedData.length > 0) {
            console.log(`Загружено ${parsedData.length} точек из кэша для ${cacheKey}`);
            setRawData(parsedData);
            setPointsCount(parsedData.length);
            
            // Обрабатываем данные для графика
            const processedData = processChartData(parsedData, exchange1, exchange2, localTimeFrame);
            setChartData(processedData);
            
            // Вычисляем текущий и максимальный спред
            const currentSpreadValue = parsedData[parsedData.length - 1]?.difference || 0;
            setCurrentSpread(currentSpreadValue);
            
            const maxSpreadValue = Math.max(...parsedData.map(item => item.difference));
            setMaxSpread(maxSpreadValue);
            
            setLoading(false);
            
            // Обновляем метаданные кэша
            updateCacheMetadata(cacheKey);
            
            return;
          }
        }
      } catch (err) {
        console.error("Ошибка при чтении кэша:", err);
      }
    }
    
    // Если кэша нет, сбрасываем данные
    setRawData([]);
  }, [pair, exchange1, exchange2, localTimeFrame]);

  // Кэширование данных при их обновлении
  useEffect(() => {
    if (rawData.length > 0 && typeof window !== 'undefined') {
      cacheData(cacheKey, rawData);
      console.log(`Запрос на сохранение ${rawData.length} точек в кэш для ${cacheKey}`);
    }
  }, [rawData, cacheKey]);

  // Обновляем локальный timeFrame при изменении props
  useEffect(() => {
    setLocalTimeFrame(timeFrame)
    
    // При изменении временного фрейма не сбрасываем данные автоматически,
    // т.к. теперь мы сначала пытаемся загрузить их из кэша
    
  }, [timeFrame]);

  // Динамический импорт zoom плагина только на клиенте
  useEffect(() => {
    // Импортируем плагины динамически только на клиенте
    Promise.all([
      import('chartjs-plugin-zoom'),
    ]).then(([zoomPlugin]) => {
      // Регистрируем плагины
      ChartJS.register(zoomPlugin.default);
      setZoomPluginLoaded(true);
    });
  }, []);

  // Update chart options based on the current tool mode
  const getChartOptions = (): ChartOptions<"line"> => {
    const options: ChartOptions<"line"> = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "top" as const,
        },
        tooltip: {
          mode: "index",
          intersect: false,
          callbacks: {
            title: (context) => {
              // Форматируем заголовок подсказки в зависимости от временного фрейма
              if (context[0]) {
                const label = context[0].label;
                if (['3h', '6h', '24h'].includes(localTimeFrame)) {
                  // Для долгосрочных фреймов показываем полную дату и время
                  const dataIndex = context[0].dataIndex;
                  const time = aggregateDataByTimeFrame(rawData, localTimeFrame)[dataIndex]?.time;
                  if (time) {
                    const date = new Date(time);
                    return `${date.toLocaleDateString()} ${date.toLocaleTimeString().substring(0, 5)}`;
                  }
                }
                return label;
              }
              return '';
            },
            label: (context) => {
              let label = context.dataset.label || ""
              if (label) {
                label += ": "
              }
              if (context.parsed.y !== null) {
                // Ограничиваем до 4 знаков после запятой
                label += context.parsed.y.toFixed(4) + "%"
              }
              return label
            },
          },
        },
      },
      scales: {
        x: {
          ticks: {
            maxRotation: 0,
            autoSkip: true,
            maxTicksLimit: localTimeFrame === '24h' ? 6 : 10, // Меньше меток для больших интервалов
          },
          grid: {
            display: true,
            color: "rgba(0, 0, 0, 0.05)",
          },
        },
        y: {
          ticks: {
            // Ограничиваем до 4 знаков после запятой
            callback: (value) => typeof value === 'number' ? value.toFixed(4) + "%" : value + "%",
          },
          grid: {
            display: true,
            color: "rgba(0, 0, 0, 0.05)",
          },
        },
      },
      interaction: {
        mode: "nearest",
        axis: "x",
        intersect: false,
      },
    };

    // Добавляем опции zoom плагина только если он загружен
    if (zoomPluginLoaded) {
      // @ts-ignore - Игнорируем ошибку типизации для zoom плагина
      options.plugins.zoom = {
        pan: {
          enabled: toolMode === "hand" || toolMode === "zoom",
          mode: zoomMode,
          modifierKey: toolMode === "zoom" ? "shift" : undefined,
        },
        zoom: {
          wheel: {
            enabled: toolMode === "zoom",
          },
          pinch: {
            enabled: toolMode === "zoom",
          },
          mode: zoomMode,
          drag: {
            enabled: toolMode === "zoom",
            backgroundColor: "rgba(99, 102, 241, 0.1)",
            borderColor: "rgba(99, 102, 241, 0.5)",
            borderWidth: 1,
          },
        },
      };
    }

    return options;
  }

  // Получение данных с API вместо мок-данных
  useEffect(() => {
    const loadData = async () => {
      // Показываем разные индикаторы в зависимости от того, первая ли это загрузка
      if (firstLoadRef.current) {
        setLoading(true);
      } else {
        setUpdating(true);
      }
      setError(null);
      
      try {
        // Определяем время последнего обновления для запроса только новых данных
        const lastTimestamp = rawData.length > 0
          ? Math.max(...rawData.map(item => item.created))
          : null;
        
        // Преобразуем обычную строку пары в формат для API
        const apiSymbol = pair.replace('/', '_').replace('-', '_') + '_PERP';
        const exchangePair = exchange1.toLowerCase() + "_" + exchange2.toLowerCase();
        
        // Вызываем API для получения данных с выбранным временным фреймом
        const apiData = await fetchSpreadData({
          symbol: apiSymbol,
          exchange_pair: exchangePair,
          time_range: localTimeFrame,
          since: lastTimestamp // Запрашиваем только новые данные
        });
        
        // Если у нас первый запрос и нет данных
        if (apiData.length === 0 && rawData.length === 0) {
          setError("Нет данных для этой пары бирж и символа");
          setLoading(false);
          setUpdating(false);
          return;
        }
        
        // Объединяем новые данные с существующими
        let updatedData: SpreadData[];
        
        if (lastTimestamp && rawData.length > 0) {
          // Фильтруем новые данные (только те, которые новее последнего известного timestamp)
          const newData = apiData.filter(item => item.created > lastTimestamp);
          
          // Если есть новые данные, добавляем их к существующим
          if (newData.length > 0) {
            updatedData = [...rawData, ...newData];
            console.log(`Добавлено ${newData.length} новых точек данных`);
          } else {
            updatedData = rawData; // Нет новых данных
          }
        } else {
          // Первый запрос или сброс данных
          updatedData = apiData;
        }
        
        // Ограничиваем количество сохраняемых точек для производительности
        // Для более долгих таймфреймов храним больше точек
        const maxPoints = localTimeFrame === '1m' ? 1000 : 
                          localTimeFrame === '5m' ? 2000 :
                          localTimeFrame === '15m' ? 3000 : 5000;
                          
        // Если точек слишком много, удаляем самые старые
        if (updatedData.length > maxPoints) {
          updatedData = updatedData.slice(-maxPoints);
        }
        
        // Сохраняем количество точек для отображения
        setPointsCount(updatedData.length);
        
        // Сохраняем обновленные данные
        setRawData(updatedData);
        
        // Обрабатываем данные для графика с учетом временного фрейма
        const processedData = processChartData(updatedData, exchange1, exchange2, localTimeFrame);
        setChartData(processedData);
        
        // Вычисляем текущий и максимальный спред
        const currentSpreadValue = updatedData[updatedData.length - 1]?.difference || 0;
        setCurrentSpread(currentSpreadValue);
        
        const maxSpreadValue = Math.max(...updatedData.map(item => item.difference));
        setMaxSpread(maxSpreadValue);
        
        setLastUpdate(Date.now());
        
        if (firstLoadRef.current) {
          setLoading(false);
          firstLoadRef.current = false;
        } else {
          // Небольшая задержка перед скрытием индикатора обновления для лучшего UX
          setTimeout(() => {
            setUpdating(false);
          }, 300);
        }
      } catch (err) {
        console.error("Error loading spread data:", err);
        setError("Ошибка при загрузке данных. Пожалуйста, попробуйте позже.");
        setLoading(false);
        setUpdating(false);
      }
    };
    
    // Загружаем данные при монтировании компонента или если данные еще не загружены
    if (rawData.length === 0 || autoRefresh) {
      loadData();
    }
    
    // Настраиваем интервал обновления в зависимости от временного фрейма
    if (autoRefresh) {
      let interval = 30000; // по умолчанию 30 секунд
      
      if (localTimeFrame === '1m') interval = 10000; // 10 секунд для 1-минутного графика
      else if (localTimeFrame === '5m') interval = 20000; // 20 секунд для 5-минутного графика
      else if (localTimeFrame === '24h') interval = 60000; // 1 минута для дневного графика
      
      // Очищаем предыдущий интервал, если есть
      if (refreshInterval) clearInterval(refreshInterval);
      
      // Устанавливаем новый интервал
      const newInterval = setInterval(loadData, interval);
      setRefreshInterval(newInterval as unknown as number);
      
      return () => {
        if (newInterval) clearInterval(newInterval);
      };
    }
    
    return () => {
      if (refreshInterval) clearInterval(refreshInterval);
    };
  }, [pair, exchange1, exchange2, localTimeFrame, autoRefresh]);

  // Обработчик смены временного фрейма
  const handleTimeFrameChange = (value: string) => {
    setLocalTimeFrame(value);
    
    // Уведомляем родительский компонент о смене фрейма
    if (onTimeFrameChange) {
      onTimeFrameChange(value)
    }
    
    resetZoom();
  }

  // Переключатель автообновления
  const toggleAutoRefresh = () => {
    setAutoRefresh(!autoRefresh);
  }

  // Reset zoom level
  const resetZoom = () => {
    if (chartRef && chartRef.current) {
      chartRef.current.resetZoom()
    }
  }

  // Toggle zoom mode
  const toggleZoomMode = (mode: "xy" | "x" | "y") => {
    setZoomMode(mode)
  }

  // Zoom in and out
  const zoomIn = () => {
    if (chartRef && chartRef.current) {
      chartRef.current.zoom(1.1)
    }
  }

  const zoomOut = () => {
    if (chartRef && chartRef.current) {
      chartRef.current.zoom(0.9)
    }
  }

  // Change tool mode
  const changeTool = (mode: ToolMode) => {
    setToolMode(mode)
  }

  // Функция для обработки экспорта
  const handleExportData = () => {
    if (rawData.length === 0) return;
    
    const filename = `${pair.replace('/', '_')}_${exchange1}_${exchange2}_${localTimeFrame}_${new Date().toISOString().split('T')[0]}.csv`;
    exportToCSV(rawData, filename);
  }

  // Сообщение об ошибке
  if (error) {
    return (
      <div className="w-full p-6 text-center">
        <div className="text-red-500 mb-4">{error}</div>
        <Button onClick={() => window.location.reload()}>Попробовать снова</Button>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="w-full space-y-3">
        <Skeleton className="h-[400px] w-full rounded-xl" />
      </div>
    )
  }

  // Функция для обработки очистки кэша
  const handleClearCache = () => {
    clearAllCache();
    window.location.reload(); // Перезагружаем страницу для отображения изменений
  }
  
  // Функция для переключения отображения контролов кэша
  const toggleCacheControls = () => {
    setShowCacheControls(!showCacheControls);
  }

  return (
    <div className="w-full">
      <div className="flex flex-wrap gap-2 mb-4">
        {zoomPluginLoaded && (
          <>
            <ToggleGroup type="single" value={toolMode} onValueChange={(value) => value && changeTool(value as ToolMode)}>
              <ToggleGroupItem value="cursor" aria-label="Курсор">
                <Move className="h-4 w-4 mr-2" />
                Курсор
              </ToggleGroupItem>
              <ToggleGroupItem value="hand" aria-label="Рука">
                <Hand className="h-4 w-4 mr-2" />
                Рука
              </ToggleGroupItem>
              <ToggleGroupItem value="zoom" aria-label="Масштаб">
                <ZoomIn className="h-4 w-4 mr-2" />
                Масштаб
              </ToggleGroupItem>
            </ToggleGroup>

            <div className="flex items-center gap-2 ml-2 border-l pl-2">
              <Select value={localTimeFrame} onValueChange={handleTimeFrameChange}>
                <SelectTrigger className="w-[140px]">
                  <Clock className="h-4 w-4 mr-2" />
                  <SelectValue placeholder="Выберите фрейм" />
                </SelectTrigger>
                <SelectContent>
                  {TIME_FRAMES.map((frame) => (
                    <SelectItem key={frame.value} value={frame.value}>
                      {frame.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              
              <Button 
                variant={autoRefresh ? "default" : "outline"} 
                size="sm" 
                onClick={toggleAutoRefresh}
                className="flex items-center gap-1"
                disabled={updating}
              >
                <RefreshCw className={`h-4 w-4 ${autoRefresh && !updating ? 'animate-spin' : updating ? 'animate-pulse' : ''}`} />
                {updating ? 'Обновление...' : autoRefresh ? 'Авто' : 'Вручную'}
              </Button>
              
              <Button
                variant="outline"
                size="sm"
                onClick={handleExportData}
                className="flex items-center gap-1"
                disabled={rawData.length === 0}
              >
                <Download className="h-4 w-4" />
                Экспорт
              </Button>
            </div>

            <div className="flex-1"></div>

            <div className="text-xs text-muted-foreground flex items-center">
              {pointsCount > 0 && `${pointsCount} точек | `}
              Обновлено: {new Date(lastUpdate).toLocaleTimeString()}
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={toggleCacheControls} 
                className="ml-2 text-xs h-6"
              >
                Кэш
              </Button>
            </div>

            <Button variant="outline" size="sm" onClick={resetZoom} className="flex items-center gap-1">
              <RefreshCw className="h-4 w-4" />
              Сбросить
            </Button>

            {toolMode === "zoom" && (
              <>
                <Button variant="outline" size="sm" onClick={zoomIn} className="flex items-center gap-1">
                  <ZoomIn className="h-4 w-4" />
                  Приблизить
                </Button>
                <Button variant="outline" size="sm" onClick={zoomOut} className="flex items-center gap-1">
                  <ZoomOut className="h-4 w-4" />
                  Отдалить
                </Button>
                <Button
                  variant={zoomMode === "xy" ? "default" : "outline"}
                  size="sm"
                  onClick={() => toggleZoomMode("xy")}
                  className="flex items-center gap-1"
                >
                  XY
                </Button>
                <Button
                  variant={zoomMode === "x" ? "default" : "outline"}
                  size="sm"
                  onClick={() => toggleZoomMode("x")}
                  className="flex items-center gap-1"
                >
                  X
                </Button>
                <Button
                  variant={zoomMode === "y" ? "default" : "outline"}
                  size="sm"
                  onClick={() => toggleZoomMode("y")}
                  className="flex items-center gap-1"
                >
                  Y
                </Button>
              </>
            )}
          </>
        )}
      </div>
      
      {showCacheControls && (
        <div className="mb-4 p-2 border rounded-md bg-muted/50">
          <div className="flex items-center justify-between">
            <span className="text-sm">Управление кэшем данных</span>
            <Button 
              variant="destructive" 
              size="sm" 
              onClick={handleClearCache}
              className="text-xs"
            >
              Очистить кэш
            </Button>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Кэш позволяет быстрее загружать данные и уменьшает количество запросов к серверу.
            Автоматически удаляются старые данные при превышении лимита.
          </p>
        </div>
      )}

      <div
        className={`h-[400px] w-full mb-6 border rounded-lg p-2 ${toolMode === "hand" && zoomPluginLoaded ? "cursor-grab active:cursor-grabbing" : ""} ${updating ? 'opacity-90' : 'opacity-100 transition-opacity duration-300'}`}
      >
        <Line ref={chartRef} options={getChartOptions()} data={chartData} />
      </div>

      {zoomPluginLoaded && (
        <div className="text-xs text-muted-foreground mb-2">
          {toolMode === "cursor" && "Выберите инструмент «Рука» для перемещения графика или «Масштаб» для увеличения"}
          {toolMode === "hand" &&
            "Перетаскивайте график для перемещения. Используйте инструмент «Масштаб» для увеличения"}
          {toolMode === "zoom" &&
            "Используйте колесо мыши для масштабирования, зажмите Shift и перетаскивайте для перемещения, или выделите область для увеличения"}
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 mt-4">
        <Card>
          <CardContent className="p-4">
            <div className="text-sm font-medium text-muted-foreground">Текущий спред</div>
            <div className="text-2xl font-bold mt-1">
              <motion.span
                key={`current-spread-${lastUpdate}`}
                initial={{ opacity: 0.7 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.5 }}
              >
                {currentSpread.toFixed(4)}%
              </motion.span>
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              {exchange1} ↔ {exchange2}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-sm font-medium text-muted-foreground">{localTimeFrame} макс. спред</div>
            <div className="text-2xl font-bold mt-1">
              <motion.span
                key={`max-spread-${lastUpdate}`}
                initial={{ opacity: 0.7 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.5 }}
              >
                {maxSpread.toFixed(4)}%
              </motion.span>
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              Обновлено: {new Date(lastUpdate).toLocaleTimeString()}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
