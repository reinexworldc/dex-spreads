"use client"

import { useEffect, useState, useRef, useMemo } from "react"
import * as React from "react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { Clock, RefreshCw } from "lucide-react"
import { motion } from "framer-motion"
import { fetchLargestSpreads, fetchSpreadData, DataQueryParams } from "@/services/api"

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

interface LargestSpread {
  id: number
  pair: string
  exchange1: string
  exchange2: string
  price1: number
  price2: number
  spreadAmount: number
  spreadPercentage: number
  currentSpread: number | null // Текущий спред
  minSpread: number | null // Минимальный спред
  exchangePair: string
  originalSymbol: string
  date: string
  duration: string
}

interface LargestSpreadsTableProps {
  onSymbolSelect?: (symbol: string, exchange1: string, exchange2: string) => void
}

export function LargestSpreadsTable({ onSymbolSelect }: LargestSpreadsTableProps) {
  const [spreads, setSpreads] = useState<LargestSpread[]>([])
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [localTimeFrame, setLocalTimeFrame] = useState<string>("24h")
  const [lastUpdate, setLastUpdate] = useState<number>(Date.now())
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true)
  const [refreshInterval, setRefreshInterval] = useState<number | null>(null)
  const [currentSpreadInterval, setCurrentSpreadInterval] = useState<number | null>(null)
  const firstLoadRef = useRef(true)
  const spreadDataRef = useRef<LargestSpread[]>([])
  
  // Добавляем состояние для сортировки
  const [sortConfig, setSortConfig] = useState<{
    key: keyof LargestSpread | null,
    direction: 'ascending' | 'descending'
  }>({
    key: 'currentSpread',
    direction: 'descending'
  });

  // Функция для загрузки текущих спредов
  const fetchCurrentSpreads = async (spreadsToUpdate: LargestSpread[]) => {
    try {
      console.log("Начинаем загрузку текущих спредов для", spreadsToUpdate.length, "пар");
      
      // Создаем копию массива спредов
      const updatedSpreads = [...spreadsToUpdate];
      
      // Ограничим количество обрабатываемых пар до первых 5
      // Это уменьшит нагрузку на API и ускорит отображение
      const pairsToProcess = Math.min(updatedSpreads.length, 25);
      
      // Для каждого спреда получаем текущее значение
      for (let i = 0; i < pairsToProcess; i++) {
        const spread = updatedSpreads[i];
        
        try {
          if (!spread.exchangePair) {
            console.log(`Пропускаем пару ${spread.pair}, нет exchangePair`);
            continue;
          }
          
          console.log(`Загружаем текущий спред для ${spread.pair}, exchangePair: ${spread.exchangePair}`);
          
          // Добавляем небольшую задержку между запросами
          if (i > 0) {
            await new Promise(resolve => setTimeout(resolve, 200));
          }
          
          // Подготавливаем параметры запроса - сначала используем оригинальный формат символа из API
          const queryParams: DataQueryParams = {
            symbol: (spread.originalSymbol || spread.pair.replace('/', '_').toUpperCase().replace(/_+$/, '')) + 'PERP',
            exchange_pair: spread.exchangePair,
            time_range: "1m", // Используем минимальный временной фрейм для актуальных данных
            sort_by: 'created',
            sort_order: 'desc',
            since: Math.floor(Date.now() / 1000) - 60 * 15 // последние 15 минут
          }
          
          // Для отладки: проверим, соответствует ли формат symbolId формату, который ожидает API
          const symbolId = queryParams.symbol;
          console.log(`Подготовленный symbolId для API: ${symbolId}`);
          
          // Проверка формата exchange_pair (убедимся, что это именно строка с подчеркиванием)
          if (queryParams.exchange_pair.includes(" - ")) {
            // Если формат с тире, преобразуем в формат с подчеркиванием
            const [exch1, exch2] = queryParams.exchange_pair.split(" - ");
            queryParams.exchange_pair = `${exch1.toLowerCase()}_${exch2.toLowerCase()}`;
            console.log(`Преобразованный exchange_pair: ${queryParams.exchange_pair}`);
          }
          
          console.log("Параметры запроса:", JSON.stringify(queryParams));
          
          // Получаем данные о текущих спредах с таймаутом
          const fetchWithTimeout = async (params: DataQueryParams) => {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 секунд таймаут
            
            try {
              const data = await fetchSpreadData(params);
              clearTimeout(timeoutId);
              return data;
            } catch (error) {
              clearTimeout(timeoutId);
              throw error;
            }
          };
          
          // Пробуем получить данные с коротким временным диапазоном
          let spreadsData = await fetchWithTimeout(queryParams);
          console.log(`Получено ${spreadsData.length} записей для ${spread.pair}`);
          
          // Если данных нет, пробуем с более длительным временным диапазоном
          if (spreadsData.length === 0) {
            console.log(`Пробуем получить данные с большим временным диапазоном для ${spread.pair}`);
            
            // Используем временной диапазон 1 час и последний час данных
            const secondAttemptParams = {
              ...queryParams,
              time_range: "1h",
              since: Math.floor(Date.now() / 1000) - 60 * 60  // последний час
            };
            
            console.log("Вторая попытка, параметры запроса:", JSON.stringify(secondAttemptParams));
            
            try {
              spreadsData = await fetchWithTimeout(secondAttemptParams);
              console.log(`Вторая попытка: получено ${spreadsData.length} записей для ${spread.pair}`);
            } catch (secondError) {
              console.error(`Ошибка при второй попытке для ${spread.pair}:`, secondError);
            }
            
            // Если всё еще нет данных, пробуем альтернативные форматы символа
            if (spreadsData.length === 0) {
              console.log(`Пробуем альтернативные форматы символа для ${spread.pair}`);
              
              // Пробуем с PERP
              const symbolWithPerp = `${spread.pair.replace('/', '_')}PERP`.toUpperCase();
              const thirdAttemptParams = {
                ...queryParams,
                symbol: symbolWithPerp,
                time_range: "1h"
              };
              
              console.log(`Третья попытка с символом ${symbolWithPerp}:`, JSON.stringify(thirdAttemptParams));
              
              try {
                spreadsData = await fetchWithTimeout(thirdAttemptParams);
                console.log(`Третья попытка: получено ${spreadsData.length} записей для ${spread.pair}`);
              } catch (thirdError) {
                console.error(`Ошибка при третьей попытке для ${spread.pair}:`, thirdError);
              }
            }
          }
          
          // Если есть данные, обновляем текущий спред
          if (spreadsData.length > 0) {
            console.log(`Обновляем текущий спред для ${spread.pair}: ${spreadsData[0].difference}%`);
            
            // Находим текущий и минимальный спреды
            const currentSpread = spreadsData[0].difference;
            
            // Ищем минимальный спред среди всех полученных данных
            let minSpread = currentSpread;
            
            for (const data of spreadsData) {
              if (data.difference < minSpread) {
                minSpread = data.difference;
              }
            }
            
            // Правильный вывод в консоль
            console.log(`Для ${spread.pair}: текущий спред=${currentSpread.toFixed(2)}%, минимальный спред=${minSpread.toFixed(2)}%`);
            
            updatedSpreads[i] = {
              ...spread,
              currentSpread,
              minSpread
            };
          } else {
            console.log(`Нет данных для текущего спреда пары ${spread.pair}`);
          }
        } catch (pairError) {
          console.error(`Ошибка при загрузке текущего спреда для ${spread.pair}:`, pairError);
          // Продолжаем с следующей парой
        }
      }
      
      console.log("Загрузка текущих спредов завершена");
      return updatedSpreads;
    } catch (error) {
      console.error("Ошибка при загрузке текущих спредов:", error);
      return spreadsToUpdate; // Возвращаем исходные данные в случае ошибки
    }
  }

  // Отдельная функция только для обновления текущих спредов 
  const updateCurrentSpreadsOnly = async () => {
    console.log("Запускаем обновление только текущих спредов...");
    
    if (spreadDataRef.current.length === 0) {
      console.log("Нет данных спредов для обновления");
      return;
    }
    
    try {
      const updatedSpreads = await fetchCurrentSpreads(spreadDataRef.current);
      
      // Проверяем, были ли обновлены какие-либо спреды
      const hasCurrentSpreads = updatedSpreads.some(s => s.currentSpread !== null);
      console.log(
        "Только текущие спреды обновлены:", 
        hasCurrentSpreads ? "Успешно" : "Нет данных", 
        "Получены данные для", 
        updatedSpreads.filter(s => s.currentSpread !== null).length,
        "из",
        updatedSpreads.length,
        "пар"
      );
      
      // Обновляем состояние и референс
      setSpreads(updatedSpreads);
      spreadDataRef.current = updatedSpreads;
      setLastUpdate(Date.now());
    } catch (error) {
      console.error("Ошибка при обновлении текущих спредов:", error);
    }
  };

  useEffect(() => {
    const loadLargestSpreadsData = async () => {
      if (firstLoadRef.current) {
        setLoading(true)
      } else {
        setUpdating(true)
      }
      
      setError(null)
      
      try {
        // Получаем данные о крупнейших спредах с выбранным временным фреймом
        const largestSpreadsData = await fetchLargestSpreads(localTimeFrame)
        
        // Преобразуем данные в формат для отображения в таблице
        const formattedSpreads = largestSpreadsData.map((item, index) => {
          // Получаем пару с максимальным спредом
          const maxPair = item.formatted_pair || item.max_pair
          
          // Добавим отладку
          console.log(`Данные о паре: max_pair=${item.max_pair}, formatted_pair=${item.formatted_pair}`);
          
          // Правильно разделяем название пары
          let exchanges: string[]
          
          if (maxPair.includes(" - ")) {
            // Если используется разделитель тире с пробелами (например, "Paradex - Backpack")
            exchanges = maxPair.split(" - ")
          } else if (maxPair.includes("_")) {
            // Если используется разделитель подчеркивание (например, "paradex_backpack")
            exchanges = maxPair.split("_").map(e => e.charAt(0).toUpperCase() + e.slice(1))
          } else {
            // Если нет известного разделителя, просто используем исходную строку
            exchanges = [maxPair, "Unknown"]
          }
          
          const exchange1 = exchanges[0] || "Unknown"
          const exchange2 = exchanges[1] || "Unknown"
          
          // Получаем ID пары бирж для API запросов
          // Используем оригинальный max_pair, если он есть, или строим его из имен бирж
          const exchangePairId = item.max_pair || 
            exchange1.toLowerCase() + "_" + exchange2.toLowerCase();
          
          console.log(`Определили exchangePair: ${exchangePairId} для пары ${item.symbol}`);
          
          // Получаем значения для этой пары
          const pairData = item.pair_spreads[item.max_pair]
          const maxBuySpread = pairData?.largest_buy || 0
          const maxSellSpread = pairData?.largest_sell || 0
          
          // Используем максимальный из buy/sell спредов
          const maxSpread = Math.max(maxBuySpread, maxSellSpread)
          
          // Примерная длительность периода в зависимости от временного фрейма
          let duration
          switch(localTimeFrame) {
            case '1m': duration = "1 минута"; break;
            case '5m': duration = "5 минут"; break;
            case '15m': duration = "15 минут"; break;
            case '30m': duration = "30 минут"; break;
            case '1h': duration = "1 час"; break;
            case '3h': duration = "3 часа"; break;
            case '6h': duration = "6 часов"; break;
            case '24h': duration = "24 часа"; break;
            default: duration = "неизвестно";
          }
          
          // Символ для отображения (форматируем из API)
          const pair = item.symbol.replace('_', '/').replace('PERP', '')
          
          // Сохраняем оригинальный символ из API для использования в запросах
          const originalSymbol = item.symbol;
          
          console.log(`Символ для пары: отображение=${pair}, оригинал API=${originalSymbol}`);
          
          return {
            id: index + 1,
            pair,
            exchange1,
            exchange2,
            price1: 0, // у нас нет точных данных о ценах в этом API
            price2: 0,
            spreadAmount: 0, // у нас нет точных данных о суммах
            spreadPercentage: maxSpread,
            currentSpread: null, // Изначально текущий спред не задан
            minSpread: null,
            exchangePair: exchangePairId, // Используем вычисленный идентификатор пары бирж
            originalSymbol, // Сохраняем оригинальный символ из API
            date: new Date().toLocaleDateString(),
            duration
          }
        })
        
        // Сортируем по проценту спреда (от высшего к низшему)
        formattedSpreads.sort((a, b) => b.spreadPercentage - a.spreadPercentage)
        
        // Загружаем текущие спреды для каждой пары
        const spreadsWithCurrentValues = await fetchCurrentSpreads(formattedSpreads)
        
        // Проверяем результаты обновления
        const hasCurrentSpreads = spreadsWithCurrentValues.some(s => s.currentSpread !== null);
        console.log(
          "Результаты загрузки текущих спредов:", 
          hasCurrentSpreads ? "Успешно" : "Нет данных", 
          "Получены данные для", 
          spreadsWithCurrentValues.filter(s => s.currentSpread !== null).length,
          "из",
          spreadsWithCurrentValues.length,
          "пар"
        );
        
        // Выводим первые несколько записей с текущими спредами для проверки
        const spreadsWithValues = spreadsWithCurrentValues.filter(s => s.currentSpread !== null).slice(0, 3);
        if (spreadsWithValues.length > 0) {
          console.log("Примеры пар с текущими спредами:", spreadsWithValues.map(s => 
            `${s.pair}: ${s.currentSpread?.toFixed(2)}%`
          ));
        }
        
        setSpreads(spreadsWithCurrentValues)
        // Сохраняем данные в референс для последующих обновлений только текущих спредов
        spreadDataRef.current = spreadsWithCurrentValues;
        setLastUpdate(Date.now())
        
        if (firstLoadRef.current) {
          setLoading(false)
          firstLoadRef.current = false
        } else {
          setUpdating(false)
        }
      } catch (err) {
        console.error("Ошибка при загрузке данных о крупнейших спредах:", err)
        setError("Ошибка при загрузке данных. Пожалуйста, попробуйте позже.")
        setLoading(false)
        setUpdating(false)
      }
    }
    
    loadLargestSpreadsData()
    
    // Настраиваем интервал обновления в зависимости от временного фрейма
    if (autoRefresh) {
      let interval = 30000; // по умолчанию 30 секунд
      
      if (localTimeFrame === '1m') interval = 10000; // 10 секунд для 1-минутного графика
      else if (localTimeFrame === '5m') interval = 20000; // 20 секунд для 5-минутного графика
      else if (localTimeFrame === '24h') interval = 60000; // 1 минута для дневного графика
      
      // Очищаем предыдущий интервал, если есть
      if (refreshInterval) clearInterval(refreshInterval);
      
      // Устанавливаем новый интервал
      const newInterval = setInterval(loadLargestSpreadsData, interval);
      setRefreshInterval(newInterval as unknown as number);
      
      // Настраиваем отдельный интервал для обновления только текущих спредов
      // Этот таймер работает чаще, чем основной для перезагрузки всей таблицы
      // Очищаем предыдущий интервал для текущих спредов, если есть
      if (currentSpreadInterval) {
        clearInterval(currentSpreadInterval);
      }
      
      // Устанавливаем новый интервал - обновляем текущие спреды каждые 20 секунд
      const newSpreadInterval = setInterval(updateCurrentSpreadsOnly, 20000);
      setCurrentSpreadInterval(newSpreadInterval as unknown as number);
      
      return () => {
        if (refreshInterval) clearInterval(refreshInterval);
        if (currentSpreadInterval) clearInterval(currentSpreadInterval);
        if (newInterval) clearInterval(newInterval);
        if (newSpreadInterval) clearInterval(newSpreadInterval);
      };
    }
    
    return () => {
      if (refreshInterval) clearInterval(refreshInterval);
      if (currentSpreadInterval) clearInterval(currentSpreadInterval);
    };
  }, [localTimeFrame, autoRefresh])

  // Обработчик смены временного фрейма
  const handleTimeFrameChange = (value: string) => {
    setLocalTimeFrame(value);
  }

  // Переключатель автообновления
  const toggleAutoRefresh = () => {
    setAutoRefresh(!autoRefresh);
  }

  // Обработчик выбора строки таблицы
  const handleRowClick = (spread: LargestSpread) => {
    if (onSymbolSelect) {
      onSymbolSelect(spread.pair, spread.exchange1, spread.exchange2);
    }
  }
  
  // Функция для определения цвета спреда
  const getSpreadColorClass = (spreadValue: number): string => {
    if (spreadValue >= 0.3) return "text-green-600 font-bold bg-green-100 dark:bg-green-950";
    if (spreadValue >= 0.2) return "text-green-600 font-semibold"; 
    if (spreadValue >= 0.15) return "text-green-500";
    if (spreadValue >= 0.1) return "text-yellow-600 font-semibold";
    if (spreadValue >= 0.05) return "text-yellow-500";
    return "text-muted-foreground";
  }

  // В середине компонента добавляем функцию для сортировки данных
  const sortedSpreads = useMemo(() => {
    let sortableSpreads = [...spreads];
    if (sortConfig.key !== null) {
      sortableSpreads.sort((a, b) => {
        const aValue = a[sortConfig.key as keyof LargestSpread];
        const bValue = b[sortConfig.key as keyof LargestSpread];
        
        // Обработка null значений
        if (aValue === null && bValue === null) return 0;
        if (aValue === null) return 1;
        if (bValue === null) return -1;
        
        if (aValue < bValue) {
          return sortConfig.direction === 'ascending' ? -1 : 1;
        }
        if (aValue > bValue) {
          return sortConfig.direction === 'ascending' ? 1 : -1;
        }
        return 0;
      });
    }
    return sortableSpreads;
  }, [spreads, sortConfig]);

  // Функция для изменения сортировки при клике на заголовок
  const requestSort = (key: keyof LargestSpread) => {
    let direction: 'ascending' | 'descending' = 'ascending';
    if (sortConfig.key === key && sortConfig.direction === 'ascending') {
      direction = 'descending';
    }
    setSortConfig({ key, direction });
  };

  if (error) {
    return (
      <div className="w-full p-6 text-center">
        <div className="text-red-500 mb-4">{error}</div>
        <button 
          className="px-4 py-2 bg-primary text-primary-foreground rounded" 
          onClick={() => window.location.reload()}
        >
          Попробовать снова
        </button>
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

  return (
    <div className="w-full overflow-auto">
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-2">
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
            <RefreshCw className={`h-4 w-4 ${autoRefresh || updating ? 'animate-spin' : ''}`} />
            {updating ? 'Обновление...' : autoRefresh ? 'Авто' : 'Вручную'}
          </Button>
        </div>
        
        <div className="text-xs text-muted-foreground">
          Последнее обновление: {new Date(lastUpdate).toLocaleTimeString()}
        </div>
      </div>
      
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>№</TableHead>
            <TableHead>Пара</TableHead>
            <TableHead 
              className="font-medium bg-secondary/10 text-secondary cursor-pointer"
              onClick={() => requestSort('currentSpread')}
            >
              Текущий спред (%) {sortConfig.key === 'currentSpread' && 
                (sortConfig.direction === 'ascending' ? '↑' : '↓')}
            </TableHead>
            <TableHead>Биржа 1</TableHead>
            <TableHead>Биржа 2</TableHead>
            <TableHead className="font-bold bg-primary/10 text-primary">MAX SPREAD (%)</TableHead>
            <TableHead className="font-medium bg-muted/20 text-muted-foreground">Мин. спред (%)</TableHead>
            <TableHead>Дата</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sortedSpreads.map((spread) => (
            <TableRow 
              key={spread.id}
              className={`${updating ? "opacity-80" : "opacity-100 transition-opacity duration-300"} ${onSymbolSelect ? "cursor-pointer hover:bg-accent" : ""}`}
              onClick={() => handleRowClick(spread)}
            >
              <TableCell className="text-center font-medium">{spread.id}</TableCell>
              <TableCell className="font-medium">{spread.pair}</TableCell>
              <TableCell>
                {spread.currentSpread !== null ? (
                  <Badge variant="outline" className={`px-2 py-1 ${getSpreadColorClass(spread.currentSpread)}`}>
                    {spread.currentSpread.toFixed(2)}%
                  </Badge>
                ) : (
                  <Badge variant="outline" className="px-2 py-1 text-muted-foreground">
                    —
                  </Badge>
                )}
              </TableCell>
              <TableCell>{spread.exchange1}</TableCell>
              <TableCell>{spread.exchange2}</TableCell>
              <TableCell>
                <Badge variant="outline" className={`px-2 py-1 ${getSpreadColorClass(spread.spreadPercentage)}`}>
                  {spread.spreadPercentage.toFixed(2)}%
                </Badge>
              </TableCell>
              <TableCell>
                {spread.minSpread !== null ? (
                  <Badge variant="outline" className={`px-2 py-1 ${getSpreadColorClass(spread.minSpread)}`}>
                    {spread.minSpread.toFixed(2)}%
                  </Badge>
                ) : (
                  <Badge variant="outline" className="px-2 py-1 text-muted-foreground">
                    —
                  </Badge>
                )}
              </TableCell>
              <TableCell>{spread.date}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
