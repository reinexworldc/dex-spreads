"use client"

import { useEffect, useState } from "react"
import { Line } from "react-chartjs-2"
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  type ChartOptions,
} from "chart.js"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

// Register ChartJS components
ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend)

// Mock data generator
const generateMockData = (pair: string, exchange1: string, exchange2: string) => {
  const now = new Date()
  const labels = Array.from({ length: 24 }, (_, i) => {
    const date = new Date(now)
    date.setHours(now.getHours() - 23 + i)
    return `${date.getHours()}:00`
  })

  // Generate random spread data based on the pair and exchanges
  let baseValue = 0
  let volatility = 1.0

  // Base value depends on the cryptocurrency pair
  switch (pair) {
    case "ETH/USDT":
      baseValue = 0.5
      break
    case "BTC/USDT":
      baseValue = 1.2
      break
    case "SOL/USDT":
      baseValue = 0.3
      break
    default:
      baseValue = 0.4
  }

  // Volatility depends on the exchange pair
  if (exchange1 === "Uniswap" && exchange2 === "SushiSwap") {
    volatility = 0.8 // Lower volatility for similar exchanges
  } else if (exchange1 === "Curve" && exchange2 === "Balancer") {
    volatility = 1.2 // Higher volatility
  } else if (exchange1 === "PancakeSwap") {
    volatility = 1.5 // Even higher volatility
  }

  const data = labels.map(() => {
    return (Math.random() * baseValue * 2 - baseValue) * volatility
  })

  return {
    labels,
    datasets: [
      {
        label: `${pair} Спред между ${exchange1} и ${exchange2} (%)`,
        data,
        borderColor: "rgb(99, 102, 241)",
        backgroundColor: "rgba(99, 102, 241, 0.5)",
        tension: 0.3,
      },
    ],
  }
}

const chartOptions: ChartOptions<"line"> = {
  responsive: true,
  plugins: {
    legend: {
      position: "top" as const,
    },
    tooltip: {
      callbacks: {
        label: (context) => {
          let label = context.dataset.label || ""
          if (label) {
            label += ": "
          }
          if (context.parsed.y !== null) {
            label += context.parsed.y.toFixed(4) + "%"
          }
          return label
        },
      },
    },
  },
  scales: {
    y: {
      ticks: {
        callback: (value) => value + "%",
      },
    },
  },
}

interface SpreadChartProps {
  pair: string
  exchange1: string
  exchange2: string
}

export function SpreadChart({ pair, exchange1, exchange2 }: SpreadChartProps) {
  const [chartData, setChartData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [currentSpread, setCurrentSpread] = useState(0)
  const [maxSpread, setMaxSpread] = useState(0)

  useEffect(() => {
    // Simulate API call
    setLoading(true)
    setTimeout(() => {
      const data = generateMockData(pair, exchange1, exchange2)
      setChartData(data)

      // Calculate current and max spread
      const currentSpreadValue =
        (Math.random() * 0.8 - 0.4) * (exchange1 === "PancakeSwap" || exchange2 === "PancakeSwap" ? 1.5 : 1.0)
      setCurrentSpread(currentSpreadValue)

      const maxSpreadValue = Math.max(...data.datasets[0].data)
      setMaxSpread(maxSpreadValue)

      setLoading(false)
    }, 1000)
  }, [pair, exchange1, exchange2])

  if (loading) {
    return (
      <div className="w-full space-y-3">
        <Skeleton className="h-[300px] w-full rounded-xl" />
      </div>
    )
  }

  return (
    <div className="w-full h-[400px]">
      <Line options={chartOptions} data={chartData} />
      <div className="grid grid-cols-2 gap-4 mt-6">
        <Card>
          <CardContent className="p-4">
            <div className="text-sm font-medium text-muted-foreground">Текущий спред</div>
            <div className="text-2xl font-bold mt-1">{currentSpread.toFixed(4)}%</div>
            <div className="text-xs text-muted-foreground mt-1">
              {exchange1} ↔ {exchange2}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-sm font-medium text-muted-foreground">24ч макс. спред</div>
            <div className="text-2xl font-bold mt-1">{maxSpread.toFixed(4)}%</div>
            <div className="text-xs text-muted-foreground mt-1">
              {exchange1} ↔ {exchange2}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
