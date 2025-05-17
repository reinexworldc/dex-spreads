"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { fetchLargestSpreads } from "@/services/api"
import { Skeleton } from "@/components/ui/skeleton"
import { ButtonGroup, ButtonGroupItem } from "@/components/ui/button-group"

const TIME_FRAMES = [
  { value: "8h", label: "8h" },
  { value: "1d", label: "1d" },
  { value: "3d", label: "3d" },
  { value: "7d", label: "7d" },
  { value: "14d", label: "14d" }
]

export function MaxSpreadCard() {
  const [maxSpread, setMaxSpread] = useState<number | null>(null)
  const [timeFrame, setTimeFrame] = useState<string>("1d")
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdate, setLastUpdate] = useState<number>(Date.now())
  const [refreshInterval, setRefreshInterval] = useState<number | null>(null)

  useEffect(() => {
    const fetchMaxSpread = async () => {
      try {
        if (loading) {
          setLoading(true)
        } else {
          setUpdating(true)
        }
        
        // Преобразуем наши таймфреймы в формат API
        let apiTimeFrame: string;
        switch(timeFrame) {
          case "8h": apiTimeFrame = "8h"; break;
          case "1d": apiTimeFrame = "24h"; break;
          case "3d": apiTimeFrame = "72h"; break;
          case "7d": apiTimeFrame = "168h"; break;
          case "14d": apiTimeFrame = "336h"; break;
          default: apiTimeFrame = "24h";
        }
        
        // Получаем данные о крупнейших спредах
        const largestSpreadsData = await fetchLargestSpreads(apiTimeFrame)
        
        // Если есть данные, находим максимальный спред
        if (largestSpreadsData && largestSpreadsData.length > 0) {
          // Находим максимальный спред среди всех пар
          const highestSpread = largestSpreadsData.reduce((max, current) => {
            return current.max_spread > max ? current.max_spread : max
          }, 0)
          
          setMaxSpread(highestSpread)
        } else {
          setMaxSpread(0)
        }
        
        setLastUpdate(Date.now())
        setLoading(false)
        setUpdating(false)
        
      } catch (err) {
        console.error("Ошибка при загрузке максимального спреда:", err)
        setError("Ошибка при загрузке данных")
        setLoading(false)
        setUpdating(false)
      }
    }
    
    // Загружаем данные при монтировании и при смене таймфрейма
    fetchMaxSpread()
    
    // Настраиваем интервал обновления (каждые 30 секунд)
    const interval = setInterval(fetchMaxSpread, 30000) 
    setRefreshInterval(interval as unknown as number)
    
    return () => {
      if (refreshInterval) clearInterval(refreshInterval)
    }
  }, [timeFrame])

  // Обработчик смены временного фрейма
  const handleTimeFrameChange = (value: string) => {
    setTimeFrame(value)
  }

  if (error) {
    return (
      <Card className="h-auto">
        <CardHeader className="pb-2">
          <CardTitle className="text-center">MAX SPREAD</CardTitle>
        </CardHeader>
        <CardContent className="text-center text-red-500">
          {error}
        </CardContent>
      </Card>
    )
  }

  // Вычисляем цвет в зависимости от значения спреда
  const getSpreadColor = () => {
    if (!maxSpread) return "text-muted-foreground";
    if (maxSpread > 0.2) return "text-green-500";
    if (maxSpread > 0.1) return "text-yellow-500";
    return "text-muted-foreground";
  }

  return (
    <Card className="h-auto">
      <CardHeader className="pb-2">
        <CardTitle className="text-center text-xl">MAX SPREAD</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="flex flex-col">
          <ButtonGroup value={timeFrame} onValueChange={handleTimeFrameChange} className="mb-0 rounded-none">
            {TIME_FRAMES.map((frame) => (
              <ButtonGroupItem key={frame.value} value={frame.value} className="py-1">
                {frame.label}
              </ButtonGroupItem>
            ))}
          </ButtonGroup>
          
          <div className="flex items-center justify-center border-t p-6">
            {loading ? (
              <Skeleton className="h-16 w-40" />
            ) : (
              <div className="text-center">
                <div className={`text-5xl font-bold ${getSpreadColor()}`}>
                  {maxSpread !== null ? `${maxSpread.toFixed(4)}%` : "—"}
                </div>
                <div className="text-xs text-muted-foreground mt-2">
                  Обновлено: {new Date(lastUpdate).toLocaleTimeString()}
                </div>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
} 