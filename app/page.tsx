"use client"

import { SpreadChart } from "@/components/spread-chart"
import { SpreadTable } from "@/components/spread-table"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useState, useEffect } from "react"
import { Label } from "@/components/ui/label"
import { fetchExchangePairs, fetchSymbols, type ExchangePair } from "@/services/api"
import { Skeleton } from "@/components/ui/skeleton"
import { Clock, Save } from "lucide-react"
import { Button } from "@/components/ui/button"

// Интерфейс для данных символа
interface SymbolData {
  symbol: string;
}

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

// Ключ для хранения настроек пользователя
const USER_SETTINGS_KEY = "dex-spread-monitor-settings";

// Интерфейс для настроек пользователя
interface UserSettings {
  selectedPair: string;
  exchange1: string;
  exchange2: string;
  timeFrame: string;
}

export default function Home() {
  const [exchange1, setExchange1] = useState("Paradex")
  const [exchange2, setExchange2] = useState("Backpack")
  const [selectedPair, setSelectedPair] = useState("ETH/USDT")
  const [exchangePairs, setExchangePairs] = useState<ExchangePair[]>([])
  const [symbols, setSymbols] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [timeFrame, setTimeFrame] = useState<string>("24h")
  const [settingsSaved, setSettingsSaved] = useState(false)
  
  // Загрузка сохраненных настроек при запуске
  useEffect(() => {
    if (typeof window !== 'undefined') {
      try {
        const savedSettings = localStorage.getItem(USER_SETTINGS_KEY);
        if (savedSettings) {
          const settings: UserSettings = JSON.parse(savedSettings);
          if (settings.selectedPair) setSelectedPair(settings.selectedPair);
          if (settings.exchange1) setExchange1(settings.exchange1);
          if (settings.exchange2) setExchange2(settings.exchange2);
          if (settings.timeFrame) setTimeFrame(settings.timeFrame);
        }
      } catch (err) {
        console.error("Ошибка при загрузке настроек:", err);
      }
    }
  }, []);
  
  // Сохранение настроек пользователя
  const saveUserSettings = () => {
    if (typeof window !== 'undefined') {
      try {
        const settings: UserSettings = {
          selectedPair,
          exchange1,
          exchange2,
          timeFrame
        };
        
        localStorage.setItem(USER_SETTINGS_KEY, JSON.stringify(settings));
        setSettingsSaved(true);
        
        // Скрываем уведомление через 2 секунды
        setTimeout(() => {
          setSettingsSaved(false);
        }, 2000);
      } catch (err) {
        console.error("Ошибка при сохранении настроек:", err);
      }
    }
  };
  
  // Получаем список пар бирж и символов при загрузке страницы
  useEffect(() => {
    const loadExchangeData = async () => {
      setLoading(true)
      setError(null)
      
      try {
        // Загружаем список пар бирж
        const pairs = await fetchExchangePairs()
        setExchangePairs(pairs)
        
        // Если есть пары бирж, устанавливаем первую как выбранную
        if (pairs.length > 0) {
          const firstExchangePair = pairs[0].id.split('_')
          if (firstExchangePair.length === 2) {
            setExchange1(firstExchangePair[0].charAt(0).toUpperCase() + firstExchangePair[0].slice(1))
            setExchange2(firstExchangePair[1].charAt(0).toUpperCase() + firstExchangePair[1].slice(1))
          }
        }
        
        // Загружаем список символов
        try {
          const symbolsData = await fetchSymbols()
          // Преобразуем символы из формата API в пользовательский формат
          const formattedSymbols = symbolsData.map((item: SymbolData) => {
            const symbol = item.symbol
            if (symbol.includes('_PERP')) {
              // Формат ETH_USDT_PERP -> ETH/USDT
              return symbol.replace('_PERP', '').replace('_', '/')
            }
            return symbol
          })
          
          setSymbols(formattedSymbols)
          
          // Устанавливаем первый символ как выбранный, если он есть
          if (formattedSymbols.length > 0) {
            setSelectedPair(formattedSymbols[0])
          }
          
        } catch (err) {
          console.error("Ошибка при загрузке символов:", err)
          // Используем дефолтные символы в случае ошибки
          setSymbols(["ETH/USDT", "BTC/USDT", "SOL/USDT", "AVAX/USDT", "MATIC/USDT", "LINK/USDT"])
        }
        
        setLoading(false)
      } catch (err) {
        console.error("Ошибка при загрузке данных бирж:", err)
        setError("Ошибка при загрузке данных. Пожалуйста, попробуйте позже.")
        
        // Используем дефолтные значения в случае ошибки
        setExchangePairs([
          { id: "paradex_backpack", name: "Paradex - Backpack" },
          { id: "paradex_hyperliquid", name: "Paradex - Hyperliquid" },
          { id: "backpack_hyperliquid", name: "Backpack - Hyperliquid" }
        ])
        
        setLoading(false)
      }
    }
    
    loadExchangeData()
  }, [])
  
  // Разделяем название пары бирж на отдельные биржи
  const getExchangesFromPair = (exchangePairId: string): string[] => {
    if (!exchangePairId || !exchangePairId.includes('_')) return [exchange1, exchange2]
    
    const [first, second] = exchangePairId.split('_')
    return [
      first.charAt(0).toUpperCase() + first.slice(1),
      second.charAt(0).toUpperCase() + second.slice(1)
    ]
  }
  
  // Обработчик выбора пары бирж
  const handleExchangePairChange = (value: string) => {
    const [first, second] = getExchangesFromPair(value)
    setExchange1(first)
    setExchange2(second)
  }
  
  // Обработчик выбора временного фрейма
  const handleTimeFrameChange = (value: string) => {
    setTimeFrame(value)
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen p-6">
        <div className="text-red-500 mb-4 text-xl">{error}</div>
        <button 
          className="px-4 py-2 bg-primary text-primary-foreground rounded" 
          onClick={() => window.location.reload()}
        >
          Попробовать снова
        </button>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight">DEX Spread Monitor</h1>
        <p className="text-muted-foreground">
          Отслеживайте спреды между различными парами на DEX биржах в реальном времени
        </p>
      </div>

      <Card className="mb-2">
        <CardHeader>
          <CardTitle>Настройки мониторинга</CardTitle>
          <CardDescription>Выберите пару токенов и биржи для сравнения спредов</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <Skeleton className="h-[40px] w-full" />
              <Skeleton className="h-[40px] w-full" />
              <Skeleton className="h-[40px] w-full" />
            </div>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="token-pair">Пара токенов</Label>
                  <Select value={selectedPair} onValueChange={setSelectedPair}>
                    <SelectTrigger id="token-pair">
                      <SelectValue placeholder="Выберите пару токенов" />
                    </SelectTrigger>
                    <SelectContent>
                      {symbols.map((pair) => (
                        <SelectItem key={pair} value={pair}>
                          {pair}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="exchange-pair">Пара бирж</Label>
                  <Select 
                    value={`${exchange1.toLowerCase()}_${exchange2.toLowerCase()}`} 
                    onValueChange={handleExchangePairChange}
                  >
                    <SelectTrigger id="exchange-pair">
                      <SelectValue placeholder="Выберите пару бирж" />
                    </SelectTrigger>
                    <SelectContent>
                      {exchangePairs.map((pair) => (
                        <SelectItem key={pair.id} value={pair.id}>
                          {pair.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="time-frame">Временной фрейм</Label>
                  <Select value={timeFrame} onValueChange={handleTimeFrameChange}>
                    <SelectTrigger id="time-frame">
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
                </div>
              </div>
              
              <div className="flex justify-end">
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={saveUserSettings}
                  className="flex items-center gap-1"
                >
                  <Save className="h-4 w-4" />
                  {settingsSaved ? "Сохранено!" : "Сохранить настройки"}
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{selectedPair} Спред</CardTitle>
          <CardDescription>
            Спред между {exchange1} и {exchange2} для пары {selectedPair}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <SpreadChart 
            pair={selectedPair} 
            exchange1={exchange1} 
            exchange2={exchange2} 
            timeFrame={timeFrame} 
            onTimeFrameChange={handleTimeFrameChange}
          />
        </CardContent>
      </Card>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Текущие спреды</CardTitle>
          <CardDescription>Актуальные спреды между различными DEX биржами</CardDescription>
        </CardHeader>
        <CardContent>
          <SpreadTable 
            highlightExchanges={[exchange1, exchange2]} 
            timeFrame={timeFrame} 
            onTimeFrameChange={handleTimeFrameChange}
          />
        </CardContent>
      </Card>
    </div>
  )
}
