"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { LineChart, BarChart3, HelpCircle } from "lucide-react"

export function MainNav() {
  const pathname = usePathname()

  return (
    <div className="mr-4 flex">
      <Link href="/" className="mr-6 flex items-center space-x-2">
        <LineChart className="h-6 w-6" />
        <span className="hidden font-bold sm:inline-block">DEX Spread Monitor</span>
      </Link>
      <nav className="flex items-center space-x-6 text-sm font-medium">
        <Link
          href="/"
          className={cn(
            "transition-colors hover:text-foreground/80",
            pathname === "/" ? "text-foreground" : "text-foreground/60",
          )}
        >
          <div className="flex items-center gap-1">
            <LineChart className="h-4 w-4" />
            <span>Главная</span>
          </div>
        </Link>
        <Link
          href="/largest-spreads"
          className={cn(
            "transition-colors hover:text-foreground/80",
            pathname?.startsWith("/largest-spreads") ? "text-foreground" : "text-foreground/60",
          )}
        >
          <div className="flex items-center gap-1">
            <BarChart3 className="h-4 w-4" />
            <span>Крупнейшие спреды</span>
          </div>
        </Link>
        <Link
          href="/help"
          className={cn(
            "transition-colors hover:text-foreground/80",
            pathname?.startsWith("/help") ? "text-foreground" : "text-foreground/60",
          )}
        >
          <div className="flex items-center gap-1">
            <HelpCircle className="h-4 w-4" />
            <span>Справка</span>
          </div>
        </Link>
      </nav>
    </div>
  )
}
