"use client"

import { SpreadChart } from "@/components/spread-chart"
import { SpreadTable } from "@/components/spread-table"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useState } from "react"
import { Label } from "@/components/ui/label"

export default function Home() {
  const [exchange1, setExchange1] = useState("Uniswap")
  const [exchange2, setExchange2] = useState("SushiSwap")
  const [selectedPair, setSelectedPair] = useState("ETH/USDT")

  const exchanges = ["Uniswap", "SushiSwap", "PancakeSwap", "Curve", "Balancer"]
  const tokenPairs = ["ETH/USDT", "BTC/USDT", "SOL/USDT", "AVAX/USDT", "MATIC/USDT", "LINK/USDT"]

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
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="space-y-2">
              <Label htmlFor="token-pair">Пара токенов</Label>
              <Select value={selectedPair} onValueChange={setSelectedPair}>
                <SelectTrigger id="token-pair">
                  <SelectValue placeholder="Выберите пару токенов" />
                </SelectTrigger>
                <SelectContent>
                  {tokenPairs.map((pair) => (
                    <SelectItem key={pair} value={pair}>
                      {pair}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="exchange1">Биржа 1</Label>
              <Select value={exchange1} onValueChange={setExchange1}>
                <SelectTrigger id="exchange1">
                  <SelectValue placeholder="Выберите биржу" />
                </SelectTrigger>
                <SelectContent>
                  {exchanges.map((exchange) => (
                    <SelectItem key={exchange} value={exchange} disabled={exchange === exchange2}>
                      {exchange}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="exchange2">Биржа 2</Label>
              <Select value={exchange2} onValueChange={setExchange2}>
                <SelectTrigger id="exchange2">
                  <SelectValue placeholder="Выберите биржу" />
                </SelectTrigger>
                <SelectContent>
                  {exchanges.map((exchange) => (
                    <SelectItem key={exchange} value={exchange} disabled={exchange === exchange1}>
                      {exchange}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
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
          <SpreadChart pair={selectedPair} exchange1={exchange1} exchange2={exchange2} />
        </CardContent>
      </Card>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Текущие спреды</CardTitle>
          <CardDescription>Актуальные спреды между различными DEX биржами</CardDescription>
        </CardHeader>
        <CardContent>
          <SpreadTable highlightExchanges={[exchange1, exchange2]} />
        </CardContent>
      </Card>
    </div>
  )
}
