"use client"

import { useState } from "react"
import { LargestSpreadsTable } from "@/components/largest-spreads-table"
import { LiquidityIndicator } from "@/components/liquidity-indicator"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export default function LargestSpreads() {
  // Состояние для хранения выбранной пары и бирж для отображения ликвидности
  const [selectedSymbol, setSelectedSymbol] = useState<string>("ETH/USDC")
  const [selectedExchanges, setSelectedExchanges] = useState<string[]>(["Paradex", "Backpack", "Hyperliquid"])

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
