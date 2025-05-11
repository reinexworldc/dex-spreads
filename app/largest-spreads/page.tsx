import { LargestSpreadsTable } from "@/components/largest-spreads-table"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export default function LargestSpreads() {
  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight">Исторически крупнейшие спреды</h1>
        <p className="text-muted-foreground">Анализ самых больших спредов между DEX биржами за всю историю</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Крупнейшие спреды (в %)</CardTitle>
          <CardDescription>Исторически самые большие спреды в процентном соотношении</CardDescription>
        </CardHeader>
        <CardContent>
          <LargestSpreadsTable />
        </CardContent>
      </Card>
    </div>
  )
}
