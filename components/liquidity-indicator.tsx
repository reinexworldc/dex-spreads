"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { fetchOrderbookData } from "@/services/api"

interface LiquidityProps {
  exchange: string
  symbol: string
  refreshInterval?: number
}

interface OrderLevel {
  price: number
  volume: number
}

interface LiquidityData {
  bidLevels: OrderLevel[]
  askLevels: OrderLevel[]
  totalBidVolume: number
  totalAskVolume: number
  totalVolume: number
  spread: number
  isGenerated?: boolean
}

export function LiquidityIndicator({ exchange, symbol, refreshInterval = 15000 }: LiquidityProps) {
  const [liquidity, setLiquidity] = useState<LiquidityData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdate, setLastUpdate] = useState<number>(Date.now())
  const [updateTimer, setUpdateTimer] = useState<number | null>(null)
  const [retryCount, setRetryCount] = useState(0)

  useEffect(() => {
    const fetchLiquidity = async () => {
      try {
        setLoading(prevLoading => prevLoading ? true : false)
        
        // Используем реальный API-вызов
        const orderbookData = await fetchOrderbookData(exchange.toLowerCase(), symbol)
        
        // Проверяем, являются ли данные сгенерированными
        const isGenerated = orderbookData.is_generated === true
        
        // Собираем уровни стакана и вычисляем общие объемы
        const bidLevels = Array.isArray(orderbookData.bids) ? orderbookData.bids : [orderbookData.bids]
        const askLevels = Array.isArray(orderbookData.asks) ? orderbookData.asks : [orderbookData.asks]
        
        // Подсчитываем общие объемы
        const totalBidVolume = bidLevels.reduce((sum, level) => sum + level.volume, 0)
        const totalAskVolume = askLevels.reduce((sum, level) => sum + level.volume, 0)
        const calculatedTotalVolume = totalBidVolume + totalAskVolume
        
        setLiquidity({
          bidLevels,
          askLevels,
          totalBidVolume,
          totalAskVolume,
          totalVolume: calculatedTotalVolume,  // Всегда используем вычисленный объем
          spread: orderbookData.spread,
          isGenerated
        })
        
        setLastUpdate(Date.now())
        setLoading(false)
        
        // Сбрасываем счетчик повторных попыток при успешном получении данных
        if (retryCount > 0) setRetryCount(0)
        
        // Сбрасываем ошибку, если она была
        if (error) setError(null)
      } catch (err: any) {
        console.error(`Ошибка при загрузке ликвидности для ${exchange} ${symbol}:`, err)
        
        // Увеличиваем счетчик попыток
        setRetryCount(prev => prev + 1)
        
        // Получаем детали ошибки из ответа API, если они есть
        let errorMessage = "Ошибка загрузки данных";
        
        if (err.message) {
          if (err.message.includes("404")) {
            errorMessage = `Данные о ликвидности для ${symbol} на бирже ${exchange} отсутствуют`;
          } else if (err.message.includes("500")) {
            errorMessage = `Внутренняя ошибка сервера при получении данных о ликвидности`;
          } else {
            errorMessage = err.message;
          }
        }
        
        // Разные сообщения об ошибке в зависимости от количества попыток
        if (retryCount > 3) {
          setError(`${errorMessage}. Возможно, биржа ${exchange} не поддерживается для ${symbol} или данные временно недоступны.`);
        } else {
          setError(`${errorMessage}`);
        }
        
        setLoading(false)
      }
    }
    
    // Загружаем данные при монтировании
    fetchLiquidity()
    
    // Настраиваем интервал обновления
    const interval = setInterval(fetchLiquidity, refreshInterval)
    setUpdateTimer(interval as unknown as number)
    
    return () => {
      if (updateTimer) clearInterval(updateTimer)
    }
  }, [exchange, symbol, refreshInterval, retryCount, error])

  // Функция для определения цвета спреда
  const getSpreadColorClass = (spreadValue: number): string => {
    if (spreadValue >= 0.3) return "text-green-600 font-bold bg-green-100 dark:bg-green-950";
    if (spreadValue >= 0.2) return "text-green-600 font-semibold"; 
    if (spreadValue >= 0.15) return "text-green-500";
    if (spreadValue >= 0.1) return "text-yellow-600 font-semibold";
    if (spreadValue >= 0.05) return "text-yellow-500";
    return "text-muted-foreground";
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-medium">Ликвидность {exchange}</CardTitle>
        </CardHeader>
        <CardContent className="text-red-500 text-sm">{error}</CardContent>
      </Card>
    )
  }

  // Функция форматирования объема в читаемый вид
  const formatVolume = (volume: number) => {
    if (volume >= 1000000) {
      return `${(volume / 1000000).toFixed(2)}M`
    } else if (volume >= 1000) {
      return `${(volume / 1000).toFixed(2)}K`
    }
    return volume.toFixed(2)
  }

  return (
    <Card>
      <CardHeader className="p-4">
        <CardTitle className="text-base font-medium">
          Ликвидность {exchange}
          {liquidity?.isGenerated && (
            <span className="text-xs text-yellow-500 ml-2">(оценка)</span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="p-4 pt-0">
        {loading && !liquidity ? (
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </div>
        ) : (
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Покупка (Bid)</span>
              <span className="font-medium">{liquidity ? formatVolume(liquidity.totalBidVolume) : "0"}</span>
            </div>
            <Progress 
              value={liquidity ? (liquidity.totalBidVolume / (liquidity.totalVolume || 1)) * 100 : 0} 
              className="h-2" 
            />
            
            {/* Уровни стакана bid */}
            {liquidity && liquidity.bidLevels.length > 1 && (
              <div className="space-y-1 mt-1 text-xs text-muted-foreground">
                {liquidity.bidLevels.slice(0, 5).map((level, index) => (
                  <div key={`bid-${index}`} className="flex justify-between">
                    <span>Уровень {index + 1}</span>
                    <div className="flex gap-1">
                      <span>{formatVolume(level.volume)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
            
            <div className="flex justify-between text-sm pt-2">
              <span>Продажа (Ask)</span>
              <span className="font-medium">{liquidity ? formatVolume(liquidity.totalAskVolume) : "0"}</span>
            </div>
            <Progress 
              value={liquidity ? (liquidity.totalAskVolume / (liquidity.totalVolume || 1)) * 100 : 0} 
              className="h-2" 
            />
            
            {/* Уровни стакана ask */}
            {liquidity && liquidity.askLevels.length > 1 && (
              <div className="space-y-1 mt-1 text-xs text-muted-foreground">
                {liquidity.askLevels.slice(0, 5).map((level, index) => (
                  <div key={`ask-${index}`} className="flex justify-between">
                    <span>Уровень {index + 1}</span>
                    <div className="flex gap-1">
                      <span>{formatVolume(level.volume)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
            
            <div className="flex justify-between text-sm pt-2">
              <span>Общий объем</span>
              <span className="font-medium">{liquidity ? formatVolume(liquidity.totalVolume) : "0"}</span>
            </div>
            
            <div className="flex justify-between text-sm pt-2">
              <span>Текущий спред</span>
              {liquidity ? (
                <Badge variant="outline" className={`px-2 py-0 ${getSpreadColorClass(liquidity.spread)}`}>
                  {liquidity.spread.toFixed(2)}%
                </Badge>
              ) : (
                <span className="font-medium">0%</span>
              )}
            </div>
            
            <div className="text-xs text-muted-foreground text-right pt-2">
              Обновлено: {new Date(lastUpdate).toLocaleTimeString()}
              {liquidity?.isGenerated && (
                <span className="text-yellow-500 ml-1">*</span>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
} 