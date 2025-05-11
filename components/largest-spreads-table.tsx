"use client"

import { useEffect, useState } from "react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"

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

// Mock data generator
const generateMockLargestSpreads = (): LargestSpread[] => {
  const pairs = ["ETH/USDT", "BTC/USDT", "SOL/USDT", "AVAX/USDT", "MATIC/USDT", "LINK/USDT"]
  const exchanges = ["Uniswap", "SushiSwap", "PancakeSwap", "Curve", "Balancer"]
  const dates = ["2023-05-12", "2023-07-23", "2023-09-05", "2023-11-18", "2024-01-07", "2024-03-22", "2024-04-15"]
  const durations = ["5 минут", "12 минут", "3 минуты", "8 минут", "15 минут", "7 минут"]

  const data: LargestSpread[] = []

  for (let i = 0; i < 10; i++) {
    const pair = pairs[Math.floor(Math.random() * pairs.length)]
    const exchange1 = exchanges[Math.floor(Math.random() * exchanges.length)]
    let exchange2
    do {
      exchange2 = exchanges[Math.floor(Math.random() * exchanges.length)]
    } while (exchange2 === exchange1)

    let basePrice = 0
    let spreadMultiplier = 0

    switch (pair) {
      case "ETH/USDT":
        basePrice = 3500
        spreadMultiplier = 0.15
        break
      case "BTC/USDT":
        basePrice = 65000
        spreadMultiplier = 0.08
        break
      case "SOL/USDT":
        basePrice = 150
        spreadMultiplier = 0.2
        break
      default:
        basePrice = 100
        spreadMultiplier = 0.1
    }

    const price1 = basePrice
    const price2 = basePrice * (1 + (spreadMultiplier * (10 - i)) / 5)
    const spreadAmount = Math.abs(price1 - price2)
    const spreadPercentage = (spreadAmount / Math.min(price1, price2)) * 100

    data.push({
      id: i + 1,
      pair,
      exchange1,
      exchange2,
      price1,
      price2,
      spreadAmount,
      spreadPercentage,
      date: dates[Math.floor(Math.random() * dates.length)],
      duration: durations[Math.floor(Math.random() * durations.length)],
    })
  }

  // Sort by percentage
  data.sort((a, b) => b.spreadPercentage - a.spreadPercentage)

  return data
}

export function LargestSpreadsTable() {
  const [spreads, setSpreads] = useState<LargestSpread[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Simulate API call
    setLoading(true)
    setTimeout(() => {
      setSpreads(generateMockLargestSpreads())
      setLoading(false)
    }, 1000)
  }, [])

  if (loading) {
    return (
      <div className="w-full space-y-3">
        <Skeleton className="h-[400px] w-full rounded-xl" />
      </div>
    )
  }

  return (
    <div className="w-full overflow-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>№</TableHead>
            <TableHead>Пара</TableHead>
            <TableHead>Биржа 1</TableHead>
            <TableHead>Биржа 2</TableHead>
            <TableHead>Спред (USD)</TableHead>
            <TableHead>Спред (%)</TableHead>
            <TableHead>Дата</TableHead>
            <TableHead>Длительность</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {spreads.map((spread) => (
            <TableRow key={spread.id}>
              <TableCell>{spread.id}</TableCell>
              <TableCell className="font-medium">{spread.pair}</TableCell>
              <TableCell>{spread.exchange1}</TableCell>
              <TableCell>{spread.exchange2}</TableCell>
              <TableCell>${spread.spreadAmount.toFixed(2)}</TableCell>
              <TableCell>
                <Badge variant={spread.spreadPercentage > 5 ? "destructive" : "secondary"}>
                  {spread.spreadPercentage.toFixed(2)}%
                </Badge>
              </TableCell>
              <TableCell>{spread.date}</TableCell>
              <TableCell>{spread.duration}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
