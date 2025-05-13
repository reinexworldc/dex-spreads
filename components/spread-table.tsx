"use client"

import { useEffect, useState, useRef } from "react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { ArrowUpIcon, Clock, RefreshCw } from "lucide-react"
import { cn } from "@/lib/utils"
import { fetchSummary } from "@/services/api"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { motion } from "framer-motion"

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

interface SpreadData {
  id: number
  pair: string
  exchange1: string
  exchange2: string
  price1: number
  price2: number
  spreadAmount: number
  spreadPercentage: number
  timestamp: string
}

interface SpreadTableProps {
  highlightExchanges?: string[]
  timeFrame?: string
  onTimeFrameChange?: (timeFrame: string) => void
}

export function SpreadTable({ highlightExchanges = [], timeFrame = "24h", onTimeFrameChange }: SpreadTableProps) {
  const [spreads, setSpreads] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [localTimeFrame, setLocalTimeFrame] = useState<string>(timeFrame)
  const [lastUpdate, setLastUpdate] = useState<number>(Date.now())
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true)
  const [refreshInterval, setRefreshInterval] = useState<number | null>(null)
  const firstLoadRef = useRef(true)

  // Обновляем локальный timeFrame при изменении props
  useEffect(() => {
    setLocalTimeFrame(timeFrame)
  }, [timeFrame])

  useEffect(() => {
    const loadSummaryData = async () => {
      if (firstLoadRef.current) {
        setLoading(true)
      } else {
        setUpdating(true)
      }
      
      setError(null)
      
      try {
        // Получаем данные из API summary с выбранным временным фреймом
        const summaryData = await fetchSummary(localTimeFrame)
        
        // Преобразуем данные в формат для отображения в таблице
        const spreadRows = Object.entries(summaryData).map(([exchangePair, data]: [string, any], index) => {
          const [exchange1, exchange2] = exchangePair.split('_')
          
          // Вычисляем среднюю цену на каждой бирже (эти данные на самом деле в API нет, это для примера)
          const avgPrice1 = 1000 + Math.random() * 100 // фиктивные данные
          const avgPrice2 = avgPrice1 * (1 + data.avg_buy_spread / 100)
          
          return {
            id: index + 1,
            pair: "ETH/USDT", // Это поле нужно будет получать из API в будущем
            exchange1: data.formatted_exchange1 || exchange1,
            exchange2: data.formatted_exchange2 || exchange2,
            price1: avgPrice1,
            price2: avgPrice2,
            spreadAmount: Math.abs(avgPrice2 - avgPrice1),
            spreadPercentage: data.avg_buy_spread || 0,
            buySpread: data.avg_buy_spread || 0,
            sellSpread: data.avg_sell_spread || 0,
            maxBuySpread: data.max_buy_spread || 0,
            maxSellSpread: data.max_sell_spread || 0,
            timestamp: new Date().toISOString(),
            exchange_pair: exchangePair
          }
        })
        
        setSpreads(spreadRows)
        setLastUpdate(Date.now())
        
        if (firstLoadRef.current) {
          setLoading(false)
          firstLoadRef.current = false
        } else {
          setUpdating(false)
        }
      } catch (err) {
        console.error("Error loading summary data:", err)
        setError("Ошибка при загрузке данных. Пожалуйста, попробуйте позже.")
        setLoading(false)
        setUpdating(false)
      }
    }
    
    loadSummaryData()
    
    // Настраиваем интервал обновления в зависимости от временного фрейма
    // Для маленьких фреймов (1m, 5m) обновляем чаще, для больших (24h) - реже
    if (autoRefresh) {
      let interval = 30000; // по умолчанию 30 секунд
      
      if (localTimeFrame === '1m') interval = 10000; // 10 секунд для 1-минутного графика
      else if (localTimeFrame === '5m') interval = 20000; // 20 секунд для 5-минутного графика
      else if (localTimeFrame === '24h') interval = 60000; // 1 минута для дневного графика
      
      // Очищаем предыдущий интервал, если есть
      if (refreshInterval) clearInterval(refreshInterval);
      
      // Устанавливаем новый интервал
      const newInterval = setInterval(loadSummaryData, interval);
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
    
    // Уведомляем родительский компонент о смене фрейма
    if (onTimeFrameChange) {
      onTimeFrameChange(value);
    }
  }

  // Переключатель автообновления
  const toggleAutoRefresh = () => {
    setAutoRefresh(!autoRefresh);
  }

  const isHighlighted = (exchange1: string, exchange2: string) => {
    if (highlightExchanges.length !== 2) return false
    return (
      (exchange1.toLowerCase().includes(highlightExchanges[0].toLowerCase()) && 
      exchange2.toLowerCase().includes(highlightExchanges[1].toLowerCase())) ||
      (exchange1.toLowerCase().includes(highlightExchanges[1].toLowerCase()) && 
      exchange2.toLowerCase().includes(highlightExchanges[0].toLowerCase()))
    )
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
            <TableHead>Пара</TableHead>
            <TableHead>Биржа 1</TableHead>
            <TableHead>Биржа 2</TableHead>
            <TableHead>Спред (BUY)</TableHead>
            <TableHead>Спред (SELL)</TableHead>
            <TableHead>Макс. спред</TableHead>
            <TableHead>Арбитраж</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {spreads.map((spread) => (
            <TableRow
              key={spread.id}
              className={cn(
                isHighlighted(spread.exchange1, spread.exchange2) ? "bg-primary/10" : "",
                updating ? "opacity-80" : "opacity-100 transition-opacity duration-300"
              )}
            >
              <TableCell className="font-medium">{spread.pair}</TableCell>
              <TableCell>{spread.exchange1}</TableCell>
              <TableCell>{spread.exchange2}</TableCell>
              
              <TableCell>
                <motion.span
                  key={`buy-${spread.id}-${lastUpdate}`}
                  initial={{ opacity: 0.6, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.3 }}
                >
                  {spread.buySpread.toFixed(4)}%
                </motion.span>
              </TableCell>
              
              <TableCell>
                <motion.span
                  key={`sell-${spread.id}-${lastUpdate}`}
                  initial={{ opacity: 0.6, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.3 }}
                >
                  {spread.sellSpread.toFixed(4)}%
                </motion.span>
              </TableCell>
              
              <TableCell>
                <motion.span
                  key={`max-${spread.id}-${lastUpdate}`}
                  initial={{ opacity: 0.6, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.3 }}
                >
                  {Math.max(spread.maxBuySpread, spread.maxSellSpread).toFixed(4)}%
                </motion.span>
              </TableCell>
              
              <TableCell>
                {spread.buySpread > spread.sellSpread ? (
                  <Badge className="flex items-center gap-1 bg-green-500">
                    <ArrowUpIcon className="h-3 w-3" />
                    Покупка на {spread.exchange1}
                  </Badge>
                ) : (
                  <Badge className="flex items-center gap-1 bg-green-500">
                    <ArrowUpIcon className="h-3 w-3" />
                    Покупка на {spread.exchange2}
                  </Badge>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
