"use client"

import { useState, useEffect } from "react"
import { LargestSpreadsTable } from "@/components/largest-spreads-table"
import { LiquidityIndicator } from "@/components/liquidity-indicator"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { fetchSymbols, SymbolData } from "@/services/api"

export default function LargestSpreads() {
  // Состояние для хранения выбранной пары и бирж для отображения ликвидности
  const [selectedSymbol, setSelectedSymbol] = useState<string>("ETH/USDC")
  const [selectedExchanges, setSelectedExchanges] = useState<string[]>(["Paradex", "Backpack", "Hyperliquid"])
  const [availableSymbols, setAvailableSymbols] = useState<SymbolData[]>([])
  const [isLoadingSymbols, setIsLoadingSymbols] = useState<boolean>(true)

  // Загрузка доступных символов
  useEffect(() => {
    const loadSymbols = async () => {
      try {
        setIsLoadingSymbols(true)
        const symbols = await fetchSymbols()
        
        // Отсортируем символы для более удобного отображения
        symbols.sort((a, b) => {
          const aSymbol = a.symbol;
          const bSymbol = b.symbol;
          
          // Выносим наиболее популярные криптовалюты вверх
          const popularCoins = ["BTC", "ETH", "SOL", "AVAX", "ARB"];
          
          const getPopularityIndex = (sym: string) => {
            for (let i = 0; i < popularCoins.length; i++) {
              if (sym.includes(popularCoins[i])) {
                return i;
              }
            }
            return 999; // Не популярная монета
          };
          
          const aPopularity = getPopularityIndex(aSymbol);
          const bPopularity = getPopularityIndex(bSymbol);
          
          // Сначала сортируем по популярности
          if (aPopularity !== bPopularity) {
            return aPopularity - bPopularity;
          }
          
          // Затем по алфавиту
          return aSymbol.localeCompare(bSymbol);
        });
        
        setAvailableSymbols(symbols)
      } catch (error) {
        console.error("Ошибка при загрузке символов:", error)
      } finally {
        setIsLoadingSymbols(false)
      }
    }
    
    loadSymbols()
  }, [])

  // Обработчик выбора пары из таблицы (будет передан в LargestSpreadsTable)
  const handleSymbolSelect = (symbol: string, exchange1: string, exchange2: string) => {
    setSelectedSymbol(symbol)
    // Убедимся, что Hyperliquid всегда добавлен к выбранным биржам
    const exchanges = [exchange1, exchange2]
    if (!exchanges.includes("Hyperliquid")) {
      exchanges.push("Hyperliquid")
    }
    setSelectedExchanges(exchanges)
  }

  // Обработчик выбора символа из селектора
  const handleSymbolChange = (value: string) => {
    setSelectedSymbol(value)
  }

  return (
    <div className="p-6">
      <div className="flex flex-col gap-2 mb-6">
        <h1 className="text-3xl font-bold tracking-tight">Исторически крупнейшие спреды</h1>
        <p className="text-muted-foreground">Анализ самых больших спредов между DEX биржами за всю историю</p>
      </div>

      <div className="flex flex-col md:flex-row gap-6">
        {/* Основная таблица (левая колонка) */}
        <div className="flex-1">
      <Card>
        <CardHeader>
          <CardTitle>Крупнейшие спреды (в %)</CardTitle>
          <CardDescription>Исторически самые большие спреды в процентном соотношении</CardDescription>
        </CardHeader>
        <CardContent>
              <LargestSpreadsTable onSymbolSelect={handleSymbolSelect} />
        </CardContent>
      </Card>
        </div>
        
        {/* Правая колонка - индикаторы ликвидности */}
        <div className="w-full md:w-96 lg:w-[400px] flex flex-col gap-6">
          {/* Селектор символов */}
          <Card>
            <CardHeader className="p-4">
              <div className="flex flex-col gap-2">
                <CardTitle className="text-base">Ликвидность</CardTitle>
                <CardDescription>Выберите торговую пару для анализа ликвидности</CardDescription>
                <Select 
                  value={selectedSymbol} 
                  onValueChange={handleSymbolChange}
                  disabled={isLoadingSymbols}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder={isLoadingSymbols ? "Загрузка символов..." : "Выберите символ"} />
                  </SelectTrigger>
                  <SelectContent>
                    {availableSymbols.map((item) => {
                      // Преобразуем формат символа для отображения
                      let displaySymbol = item.symbol;
                      if (displaySymbol.includes('_PERP')) {
                        displaySymbol = displaySymbol.replace('_PERP', '').replace('_', '/');
                      }
                      
                      return (
                        <SelectItem key={item.symbol} value={displaySymbol}>
                          {displaySymbol}
                        </SelectItem>
                      );
                    })}
                  </SelectContent>
                </Select>
              </div>
            </CardHeader>
          </Card>
          
          {/* Индикаторы ликвидности (если выбраны биржи) */}
          {selectedExchanges.length > 0 && (
            <>
              <Card>
                <CardHeader className="p-4">
                  <CardTitle className="text-base">Ликвидность для {selectedSymbol}</CardTitle>
                  <CardDescription>Данные стакана ордеров и спреда</CardDescription>
                </CardHeader>
              </Card>
              {selectedExchanges.map((exchange) => (
                <LiquidityIndicator 
                  key={exchange} 
                  exchange={exchange} 
                  symbol={selectedSymbol} 
                  refreshInterval={15000}
                />
              ))}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
