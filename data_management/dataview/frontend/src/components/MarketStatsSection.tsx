'use client'

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatCurrency, formatNumber, formatPercentage, getPriceChangeColor } from "@/lib/utils"
import { MarketStats } from "@/types/coin"
import { TrendingUp, TrendingDown, DollarSign, Activity } from "lucide-react"

interface MarketStatsSectionProps {
  stats: MarketStats | undefined
  isLoading: boolean
}

export function MarketStatsSection({ stats, isLoading }: MarketStatsSectionProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                <div className="h-4 bg-gray-200 rounded animate-pulse"></div>
              </CardTitle>
              <div className="h-4 w-4 bg-gray-200 rounded animate-pulse"></div>
            </CardHeader>
            <CardContent>
              <div className="h-8 bg-gray-200 rounded animate-pulse mb-2"></div>
              <div className="h-3 bg-gray-200 rounded animate-pulse w-16"></div>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  if (!stats) return null

  const marketCapChange = stats.market_cap_change_percentage_24h
  const btcDominance = stats.market_cap_percentage.bitcoin

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {/* 总市值 */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            总市值
          </CardTitle>
          <DollarSign className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold font-mono">
            {formatCurrency(stats.total_market_cap, 'USD', 0, 0)}
          </div>
          <div className={`text-xs ${getPriceChangeColor(marketCapChange)} flex items-center mt-1`}>
            {marketCapChange > 0 ? (
              <TrendingUp className="h-3 w-3 mr-1" />
            ) : (
              <TrendingDown className="h-3 w-3 mr-1" />
            )}
            {formatPercentage(marketCapChange)} 24h
          </div>
        </CardContent>
      </Card>

      {/* 24小时交易量 */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            24h 交易量
          </CardTitle>
          <Activity className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold font-mono">
            {formatCurrency(stats.total_volume_24h, 'USD', 0, 0)}
          </div>
          <div className="text-xs text-muted-foreground mt-1">
            全市场交易活跃度
          </div>
        </CardContent>
      </Card>

      {/* BTC 市值占比 */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            BTC 占比
          </CardTitle>
          <div className="h-4 w-4 rounded-full bg-orange-500"></div>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold font-mono">
            {btcDominance.toFixed(1)}%
          </div>
          <div className="text-xs text-muted-foreground mt-1">
            比特币市值占比
          </div>
        </CardContent>
      </Card>

      {/* 活跃币种数 */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            活跃币种
          </CardTitle>
          <div className="h-4 w-4 rounded bg-blue-500"></div>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold font-mono">
            {formatNumber(stats.active_cryptocurrencies)}
          </div>
          <div className="text-xs text-muted-foreground mt-1">
            正在交易的币种
          </div>
        </CardContent>
      </Card>
    </div>
  )
}