export interface SpreadData {
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

export interface LargestSpread {
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
