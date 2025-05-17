"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { fetchOrderbookData } from "@/services/api"
import { AlertTriangle } from "lucide-react"

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
  timestamp?: number
}

export function LiquidityIndicator({ exchange, symbol, refreshInterval = 15000 }: LiquidityProps) {
  const [liquidity, setLiquidity] = useState<LiquidityData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdate, setLastUpdate] = useState<number>(Date.now())
  const [updateTimer, setUpdateTimer] = useState<number | null>(null)
  const [retryCount, setRetryCount] = useState(0)

  useEffect(() => {
    // Сбрасываем состояние при изменении символа или биржи
    setLoading(true)
    setLiquidity(null)
    setError(null)
    setRetryCount(0)
    
    const fetchLiquidity = async () => {
      try {
        setLoading(prevLoading => prevLoading ? true : false)
        
        // Используем реальный API-вызов
        const orderbookData = await fetchOrderbookData(exchange.toLowerCase(), symbol)
        
        // Проверяем, являются ли данные сгенерированными
        const isGenerated = orderbookData.isFake === true
        
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
          isGenerated,
          timestamp: orderbookData.timestamp
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
        
        // Генерируем локально фейковые данные в случае ошибки, чтобы пользователь видел хоть что-то
        generateLocalFakeData()
        setLoading(false)
      }
    }
    
    // Функция для генерации фейковых данных на стороне клиента в случае ошибки
    const generateLocalFakeData = () => {
      // Базовые цены в зависимости от символа
      let basePrice = 100
      
      if (symbol.includes('BTC')) {
        basePrice = 70000 + Math.random() * 2000 - 1000
      } else if (symbol.includes('ETH')) {
        basePrice = 3500 + Math.random() * 200 - 100
      } else if (symbol.includes('SOL')) {
        basePrice = 150 + Math.random() * 10 - 5
      } else if (symbol.includes('AVAX')) {
        basePrice = 30 + Math.random() * 4 - 2
      } else if (symbol.includes('ARB')) {
        basePrice = 1.2 + Math.random() * 0.1 - 0.05
      }
      
      // Спред в пределах 0.1-0.2%
      const spread = 0.1 + Math.random() * 0.1
      
      // Создаем уровни стакана
      const bidLevels: OrderLevel[] = []
      const askLevels: OrderLevel[] = []
      
      // Базовый объем зависит от цены
      const baseVolume = basePrice * 1000
      
      // Bid и ask цены
      const bidPrice = basePrice * (1 - spread/200)
      const askPrice = basePrice * (1 + spread/200)
      
      // Объемы
      let totalBidVolume = 0
      let totalAskVolume = 0
      
      // Генерируем 5 уровней стакана
      for (let i = 0; i < 5; i++) {
        // Для ордеров на покупку: чем ниже цена, тем больше объем
        const bidPriceLevel = bidPrice * (1 - 0.0005 * (i + 1))
        const bidVolumeLevel = baseVolume * (1 - 0.15 * i) * (1 + Math.random() * 0.1 - 0.05)
        
        // Для ордеров на продажу: чем выше цена, тем больше объем
        const askPriceLevel = askPrice * (1 + 0.0005 * (i + 1))
        const askVolumeLevel = baseVolume * (1 - 0.15 * i) * (1 + Math.random() * 0.1 - 0.05)
        
        bidLevels.push({ price: bidPriceLevel, volume: bidVolumeLevel })
        askLevels.push({ price: askPriceLevel, volume: askVolumeLevel })
        
        totalBidVolume += bidVolumeLevel
        totalAskVolume += askVolumeLevel
      }
      
      setLiquidity({
        bidLevels,
        askLevels,
        totalBidVolume,
        totalAskVolume,
        totalVolume: totalBidVolume + totalAskVolume,
        spread,
        isGenerated: true
      })
    }
    
    // Загружаем данные при монтировании
    fetchLiquidity()
    
    // Настраиваем интервал обновления
    const interval = setInterval(fetchLiquidity, refreshInterval)
    setUpdateTimer(interval as unknown as number)
    
    return () => {
      if (updateTimer) clearInterval(updateTimer)
    }
  }, [exchange, symbol, refreshInterval, retryCount])

  // Функция для определения цвета спреда
  const getSpreadColorClass = (spreadValue: number): string => {
    if (spreadValue >= 0.3) return "text-green-600 font-bold bg-green-100 dark:bg-green-950";
    if (spreadValue >= 0.2) return "text-green-600 font-semibold"; 
    if (spreadValue >= 0.15) return "text-green-500";
    if (spreadValue >= 0.1) return "text-yellow-600 font-semibold";
    if (spreadValue >= 0.05) return "text-yellow-500";
    return "text-muted-foreground";
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
    <Card className={liquidity?.isGenerated ? "border-yellow-500 dark:border-yellow-800" : ""}>
      <CardHeader className="p-4">
        <div className="flex justify-between items-center">
          <CardTitle className="text-base font-medium">
            Ликвидность {exchange}
          </CardTitle>
          {liquidity?.isGenerated && (
            <Badge variant="outline" className="bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300">
              <AlertTriangle className="h-3 w-3 mr-1" />
              Оценка
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="p-4 pt-0">
        {error && !liquidity && (
          <div className="text-red-500 text-sm bg-red-50 dark:bg-red-900/20 p-2 mb-2 rounded">
            <p>{error}</p>
            <p className="text-xs mt-1">Показаны приблизительные данные</p>
          </div>
        )}

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
            
            <div className="text-xs text-muted-foreground text-right pt-2 flex justify-between items-center">
              <span className={liquidity?.isGenerated ? "text-yellow-500" : ""}>
                {liquidity?.isGenerated && "* Приблизительные данные"}
              </span>
              <span>Обновлено: {new Date(lastUpdate).toLocaleTimeString()}</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
} 