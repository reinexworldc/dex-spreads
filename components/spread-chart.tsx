"use client"

import { useEffect, useState, useRef } from "react"
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
  type ChartType,
} from "chart.js"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import { ZoomIn, ZoomOut, RefreshCw, Hand, Move } from "lucide-react"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"

// Register ChartJS components без zoom плагина (добавим его динамически)
ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend)

// Mock data generator
const generateMockData = (pair: string, exchange1: string, exchange2: string) => {
  const now = new Date()
  const labels = Array.from({ length: 96 }, (_, i) => {
    const date = new Date(now)
    date.setHours(now.getHours() - 95 + i)
    return `${date.getHours()}:${date.getMinutes().toString().padStart(2, "0")}`
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

  // Generate more realistic data with trends
  let lastValue = 0
  const data = labels.map((_, index) => {
    // Add some trend to make the data look more realistic
    if (index === 0) {
      // Начинаем с более реалистичного значения
      lastValue = (Math.random() * baseValue - baseValue / 2) * volatility
    } else {
      // Add some randomness but keep a trend
      const change = ((Math.random() * baseValue) / 10 - baseValue / 20) * volatility
      lastValue = Math.max(-baseValue, Math.min(baseValue, lastValue + change))
    }
    // Округляем до 4 знаков после запятой для более чистых значений
    return Number.parseFloat(lastValue.toFixed(4))
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
        pointRadius: 0, // Hide points for cleaner look
        pointHoverRadius: 5, // Show points on hover
      },
    ],
  }
}

interface SpreadChartProps {
  pair: string
  exchange1: string
  exchange2: string
}

type ToolMode = "cursor" | "hand" | "zoom"

export function SpreadChart({ pair, exchange1, exchange2 }: SpreadChartProps) {
  const [chartData, setChartData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [currentSpread, setCurrentSpread] = useState(0)
  const [maxSpread, setMaxSpread] = useState(0)
  const chartRef = useRef<any>(null)
  const [zoomMode, setZoomMode] = useState<"xy" | "x" | "y">("xy")
  const [toolMode, setToolMode] = useState<ToolMode>("cursor")
  const [zoomPluginLoaded, setZoomPluginLoaded] = useState(false)

  // Динамический импорт zoom плагина только на клиенте
  useEffect(() => {
    // Импортируем плагин динамически только на клиенте
    import('chartjs-plugin-zoom').then((zoomPlugin) => {
      // Регистрируем плагин
      ChartJS.register(zoomPlugin.default)
      setZoomPluginLoaded(true)
    })
  }, [])

  // Update chart options based on the current tool mode
  const getChartOptions = (): ChartOptions<"line"> => {
    const options: ChartOptions<"line"> = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "top" as const,
        },
        tooltip: {
          mode: "index",
          intersect: false,
          callbacks: {
            label: (context) => {
              let label = context.dataset.label || ""
              if (label) {
                label += ": "
              }
              if (context.parsed.y !== null) {
                // Ограничиваем до 4 знаков после запятой
                label += context.parsed.y.toFixed(4) + "%"
              }
              return label
            },
          },
        },
      },
      scales: {
        x: {
          ticks: {
            maxRotation: 0,
            autoSkip: true,
            maxTicksLimit: 10,
          },
          grid: {
            display: true,
            color: "rgba(0, 0, 0, 0.05)",
          },
        },
        y: {
          ticks: {
            // Ограничиваем до 4 знаков после запятой
            callback: (value) => typeof value === 'number' ? value.toFixed(4) + "%" : value + "%",
          },
          grid: {
            display: true,
            color: "rgba(0, 0, 0, 0.05)",
          },
        },
      },
      interaction: {
        mode: "nearest",
        axis: "x",
        intersect: false,
      },
    };

    // Добавляем опции zoom плагина только если он загружен
    if (zoomPluginLoaded) {
      // @ts-ignore - Игнорируем ошибку типизации для zoom плагина
      options.plugins.zoom = {
        pan: {
          enabled: toolMode === "hand" || toolMode === "zoom",
          mode: zoomMode,
          modifierKey: toolMode === "zoom" ? "shift" : undefined,
        },
        zoom: {
          wheel: {
            enabled: toolMode === "zoom",
          },
          pinch: {
            enabled: toolMode === "zoom",
          },
          mode: zoomMode,
          drag: {
            enabled: toolMode === "zoom",
            backgroundColor: "rgba(99, 102, 241, 0.1)",
            borderColor: "rgba(99, 102, 241, 0.5)",
            borderWidth: 1,
          },
        },
      };
    }

    return options;
  }

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

  // Reset zoom level
  const resetZoom = () => {
    if (chartRef && chartRef.current) {
      chartRef.current.resetZoom()
    }
  }

  // Toggle zoom mode
  const toggleZoomMode = (mode: "xy" | "x" | "y") => {
    setZoomMode(mode)
  }

  // Zoom in and out
  const zoomIn = () => {
    if (chartRef && chartRef.current) {
      chartRef.current.zoom(1.1)
    }
  }

  const zoomOut = () => {
    if (chartRef && chartRef.current) {
      chartRef.current.zoom(0.9)
    }
  }

  // Change tool mode
  const changeTool = (mode: ToolMode) => {
    setToolMode(mode)
  }

  if (loading) {
    return (
      <div className="w-full space-y-3">
        <Skeleton className="h-[400px] w-full rounded-xl" />
      </div>
    )
  }

  return (
    <div className="w-full">
      <div className="flex flex-wrap gap-2 mb-4">
        {zoomPluginLoaded && (
          <>
            <ToggleGroup type="single" value={toolMode} onValueChange={(value) => value && changeTool(value as ToolMode)}>
              <ToggleGroupItem value="cursor" aria-label="Курсор">
                <Move className="h-4 w-4 mr-2" />
                Курсор
              </ToggleGroupItem>
              <ToggleGroupItem value="hand" aria-label="Рука">
                <Hand className="h-4 w-4 mr-2" />
                Рука
              </ToggleGroupItem>
              <ToggleGroupItem value="zoom" aria-label="Масштаб">
                <ZoomIn className="h-4 w-4 mr-2" />
                Масштаб
              </ToggleGroupItem>
            </ToggleGroup>

            <div className="flex-1"></div>

            <Button variant="outline" size="sm" onClick={resetZoom} className="flex items-center gap-1">
              <RefreshCw className="h-4 w-4" />
              Сбросить
            </Button>

            {toolMode === "zoom" && (
              <>
                <Button variant="outline" size="sm" onClick={zoomIn} className="flex items-center gap-1">
                  <ZoomIn className="h-4 w-4" />
                  Приблизить
                </Button>
                <Button variant="outline" size="sm" onClick={zoomOut} className="flex items-center gap-1">
                  <ZoomOut className="h-4 w-4" />
                  Отдалить
                </Button>
                <Button
                  variant={zoomMode === "xy" ? "default" : "outline"}
                  size="sm"
                  onClick={() => toggleZoomMode("xy")}
                  className="flex items-center gap-1"
                >
                  XY
                </Button>
                <Button
                  variant={zoomMode === "x" ? "default" : "outline"}
                  size="sm"
                  onClick={() => toggleZoomMode("x")}
                  className="flex items-center gap-1"
                >
                  X
                </Button>
                <Button
                  variant={zoomMode === "y" ? "default" : "outline"}
                  size="sm"
                  onClick={() => toggleZoomMode("y")}
                  className="flex items-center gap-1"
                >
                  Y
                </Button>
              </>
            )}
          </>
        )}
      </div>

      <div
        className={`h-[400px] w-full mb-6 border rounded-lg p-2 ${toolMode === "hand" && zoomPluginLoaded ? "cursor-grab active:cursor-grabbing" : ""}`}
      >
        <Line ref={chartRef} options={getChartOptions()} data={chartData} />
      </div>

      {zoomPluginLoaded && (
        <div className="text-xs text-muted-foreground mb-2">
          {toolMode === "cursor" && "Выберите инструмент «Рука» для перемещения графика или «Масштаб» для увеличения"}
          {toolMode === "hand" &&
            "Перетаскивайте график для перемещения. Используйте инструмент «Масштаб» для увеличения"}
          {toolMode === "zoom" &&
            "Используйте колесо мыши для масштабирования, зажмите Shift и перетаскивайте для перемещения, или выделите область для увеличения"}
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 mt-4">
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
