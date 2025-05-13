"use client"

import { useEffect, useState, useRef } from "react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { Clock, RefreshCw } from "lucide-react"
import { motion } from "framer-motion"
import { fetchLargestSpreads } from "@/services/api"

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
  date: string
  duration: string
}

export function LargestSpreadsTable() {
  const [spreads, setSpreads] = useState<LargestSpread[]>([])
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [localTimeFrame, setLocalTimeFrame] = useState<string>("24h")
  const [lastUpdate, setLastUpdate] = useState<number>(Date.now())
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true)
  const [refreshInterval, setRefreshInterval] = useState<number | null>(null)
  const firstLoadRef = useRef(true)

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
          const [exchange1, exchange2] = maxPair.split('_').map(e => e.charAt(0).toUpperCase() + e.slice(1))
          
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
          
          return {
            id: index + 1,
            pair,
            exchange1,
            exchange2,
            price1: 0, // у нас нет точных данных о ценах в этом API
            price2: 0,
            spreadAmount: 0, // у нас нет точных данных о суммах
            spreadPercentage: maxSpread,
            date: new Date().toLocaleDateString(),
            duration
          }
        })
        
        // Сортируем по проценту спреда (от высшего к низшему)
        formattedSpreads.sort((a, b) => b.spreadPercentage - a.spreadPercentage)
        
        setSpreads(formattedSpreads)
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
      
      return () => {
        if (newInterval) clearInterval(newInterval);
      }
    }
    
    return () => {
      if (refreshInterval) clearInterval(refreshInterval);
    }
  }, [localTimeFrame, autoRefresh])

  // Обработчик смены временного фрейма
  const handleTimeFrameChange = (value: string) => {
    setLocalTimeFrame(value);
  }

  // Переключатель автообновления
  const toggleAutoRefresh = () => {
    setAutoRefresh(!autoRefresh);
  }

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
            <TableHead>Биржа 1</TableHead>
            <TableHead>Биржа 2</TableHead>
            <TableHead>Спред (%)</TableHead>
            <TableHead>Период</TableHead>
            <TableHead>Дата</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {spreads.map((spread) => (
            <TableRow 
              key={spread.id}
              className={updating ? "opacity-80" : "opacity-100 transition-opacity duration-300"}
            >
              <TableCell>{spread.id}</TableCell>
              <TableCell className="font-medium">{spread.pair}</TableCell>
              <TableCell>{spread.exchange1}</TableCell>
              <TableCell>{spread.exchange2}</TableCell>
              <TableCell>
                <motion.div
                  key={`spread-${spread.id}-${lastUpdate}`}
                  initial={{ opacity: 0.6, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.3 }}
                >
                  <Badge variant={spread.spreadPercentage > 5 ? "destructive" : "secondary"}>
                    {spread.spreadPercentage.toFixed(4)}%
                  </Badge>
                </motion.div>
              </TableCell>
              <TableCell>{spread.duration}</TableCell>
              <TableCell>{spread.date}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
