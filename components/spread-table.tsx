"use client"

import { useEffect, useState } from "react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { ArrowUpIcon } from "lucide-react"
import { cn } from "@/lib/utils"

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

// Mock data generator
const generateMockSpreadData = (): SpreadData[] => {
  const pairs = ["ETH/USDT", "BTC/USDT", "SOL/USDT", "AVAX/USDT", "MATIC/USDT", "LINK/USDT"]
  const exchanges = ["Uniswap", "SushiSwap", "PancakeSwap", "Curve", "Balancer"]

  return pairs.map((pair, index) => {
    const exchange1 = exchanges[Math.floor(Math.random() * 3)]
    let exchange2
    do {
      exchange2 = exchanges[Math.floor(Math.random() * exchanges.length)]
    } while (exchange2 === exchange1)

    let basePrice = 0
    switch (pair) {
      case "ETH/USDT":
        basePrice = 3500
        break
      case "BTC/USDT":
        basePrice = 65000
        break
      case "SOL/USDT":
        basePrice = 150
        break
      case "AVAX/USDT":
        basePrice = 35
        break
      case "MATIC/USDT":
        basePrice = 0.8
        break
      case "LINK/USDT":
        basePrice = 18
        break
      default:
        basePrice = 10
    }

    const price1 = basePrice * (1 + (Math.random() * 0.01 - 0.005))
    const price2 = basePrice * (1 + (Math.random() * 0.01 - 0.005))
    const spreadAmount = Math.abs(price1 - price2)
    const spreadPercentage = (spreadAmount / Math.min(price1, price2)) * 100

    return {
      id: index + 1,
      pair,
      exchange1,
      exchange2,
      price1,
      price2,
      spreadAmount,
      spreadPercentage,
      timestamp: new Date().toISOString(),
    }
  })
}

interface SpreadTableProps {
  highlightExchanges?: string[]
}

export function SpreadTable({ highlightExchanges = [] }: SpreadTableProps) {
  const [spreads, setSpreads] = useState<SpreadData[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Simulate API call
    setLoading(true)
    setTimeout(() => {
      setSpreads(generateMockSpreadData())
      setLoading(false)
    }, 1000)

    // Update data every 30 seconds
    const interval = setInterval(() => {
      setSpreads(generateMockSpreadData())
    }, 30000)

    return () => clearInterval(interval)
  }, [])

  const isHighlighted = (exchange1: string, exchange2: string) => {
    if (highlightExchanges.length !== 2) return false
    return (
      (exchange1 === highlightExchanges[0] && exchange2 === highlightExchanges[1]) ||
      (exchange1 === highlightExchanges[1] && exchange2 === highlightExchanges[0])
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
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Пара</TableHead>
            <TableHead>Биржа 1</TableHead>
            <TableHead>Цена 1</TableHead>
            <TableHead>Биржа 2</TableHead>
            <TableHead>Цена 2</TableHead>
            <TableHead>Спред (USD)</TableHead>
            <TableHead>Спред (%)</TableHead>
            <TableHead>Арбитраж</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {spreads.map((spread) => (
            <TableRow
              key={spread.id}
              className={cn(isHighlighted(spread.exchange1, spread.exchange2) ? "bg-primary/10" : "")}
            >
              <TableCell className="font-medium">{spread.pair}</TableCell>
              <TableCell>{spread.exchange1}</TableCell>
              <TableCell>${spread.price1.toFixed(4)}</TableCell>
              <TableCell>{spread.exchange2}</TableCell>
              <TableCell>${spread.price2.toFixed(4)}</TableCell>
              <TableCell>${spread.spreadAmount.toFixed(4)}</TableCell>
              <TableCell>{spread.spreadPercentage.toFixed(4)}%</TableCell>
              <TableCell>
                {spread.price1 < spread.price2 ? (
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
