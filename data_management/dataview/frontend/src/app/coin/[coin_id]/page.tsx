'use client'

import { useParams } from 'next/navigation'
import { useState, useMemo } from 'react'
import useSWR from 'swr'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { getCoin, getCoinHistory, getCoinIndicatorTimeline } from '@/lib/api'
import { formatCurrency, formatNumber, formatPercentage, getPriceChangeColor, formatTime } from '@/lib/utils'
import { ArrowLeft, TrendingUp, TrendingDown, Calendar, DollarSign, BarChart3 } from 'lucide-react'
import { CoinImage } from '@/components/CoinImage'
import { TradingViewChart } from '@/components/TradingViewChart'
import { IndicatorTimelineChart } from '@/components/IndicatorTimelineChart'

export default function CoinDetailPage() {
  const params = useParams()
  const coinId = params.coin_id as string
  
  const [timeframe, setTimeframe] = useState('7d')
  
  // 获取币种基础信息
  const { data: coin, error: coinError, isLoading: coinLoading } = useSWR(
    coinId ? `/coin/${coinId}` : null,
    () => getCoin(coinId),
    { 
      refreshInterval: 30000,
      revalidateOnFocus: false,
    }
  )
  
  // 获取历史数据 - 使用静态时间范围避免无限循环
  const historyParams = useMemo(() => {
    const dataStartDate = '2025-08-09T00:00:00Z'
    const staticEndTime = '2025-09-19T23:59:59Z' // 使用固定结束时间
    let start: string
    let interval: string

    switch (timeframe) {
      case '24h':
        start = '2025-09-18T00:00:00Z'
        interval = '1h'
        break
      case '7d':
        start = '2025-09-12T00:00:00Z'
        interval = '4h'
        break
      case '30d':
        start = '2025-08-20T00:00:00Z'
        interval = '1d'
        break
      case '90d':
        start = dataStartDate
        interval = '1d'
        break
      default:
        start = '2025-09-12T00:00:00Z'
        interval = '4h'
        break
    }

    return { start, end: staticEndTime, interval }
  }, [timeframe])
  const { data: historyData, isLoading: historyLoading } = useSWR(
    coinId ? ['coin-history', coinId, historyParams.start, historyParams.end, historyParams.interval] : null,
    () => getCoinHistory(coinId, historyParams),
    {
      refreshInterval: 60000,
      revalidateOnFocus: false,
    }
  )

  // 获取指标时间线数据 - 使用静态时间范围避免无限循环
  const indicatorParams = useMemo(() => {
    const dataStartDate = '2025-08-09T00:00:00Z'
    const staticEndTime = '2025-09-19T23:59:59Z' // 使用固定结束时间
    let start: string

    // 根据选择的时间框架决定指标数据范围
    switch (timeframe) {
      case '24h':
        start = '2025-09-12T00:00:00Z' // 7天指标数据
        break
      case '7d':
        start = '2025-09-05T00:00:00Z' // 14天指标数据
        break
      case '30d':
        start = '2025-08-20T00:00:00Z' // 30天指标数据
        break
      case '90d':
        start = dataStartDate // 全部数据
        break
      default:
        start = '2025-09-05T00:00:00Z' // 14天指标数据
        break
    }

    return { start, end: staticEndTime }
  }, [timeframe])

  const { data: indicatorData, isLoading: indicatorLoading, error: indicatorError } = useSWR(
    coinId ? ['coin-indicators', coinId, indicatorParams.start, indicatorParams.end] : null,
    () => getCoinIndicatorTimeline(coinId, indicatorParams),
    {
      refreshInterval: 120000, // 2分钟刷新
      revalidateOnFocus: false,
    }
  )

  if (coinError) {
    return (
      <div className="container mx-auto px-4 py-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <h2 className="text-lg font-semibold text-red-800 mb-2">加载失败</h2>
          <p className="text-red-600 mb-4">
            无法加载币种数据：{coinError.message}
          </p>
          <Button 
            onClick={() => window.history.back()}
            className="bg-red-600 text-white hover:bg-red-700"
          >
            返回列表
          </Button>
        </div>
      </div>
    )
  }

  if (coinLoading) {
    return (
      <div className="container mx-auto px-4 py-6">
        <div className="space-y-6">
          {/* 加载骨架屏 */}
          <div className="flex items-center space-x-4 mb-6">
            <div className="h-8 w-8 bg-gray-200 rounded animate-pulse"></div>
            <div className="h-8 bg-gray-200 rounded animate-pulse w-32"></div>
          </div>
          
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <div className="h-96 bg-gray-200 rounded-lg animate-pulse"></div>
            </div>
            <div className="space-y-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-24 bg-gray-200 rounded-lg animate-pulse"></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (!coin) {
    return (
      <div className="container mx-auto px-4 py-6">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
          <h2 className="text-lg font-semibold text-yellow-800 mb-2">币种不存在</h2>
          <p className="text-yellow-600 mb-4">
            找不到币种 "{coinId}"
          </p>
          <Button 
            onClick={() => window.history.back()}
            className="bg-yellow-600 text-white hover:bg-yellow-700"
          >
            返回列表
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-6">
      {/* 返回按钮和币种标题 */}
      <div className="flex items-center space-x-4 mb-6">
        <Button
          variant="outline"
          onClick={() => window.history.back()}
          className="flex items-center space-x-2"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>返回</span>
        </Button>
        
        <div className="flex items-center space-x-3">
          <CoinImage
            coinId={coin.coin_id}
            coinName={coin.name}
            size={40}
          />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{coin.name}</h1>
            <p className="text-gray-500 uppercase">{coin.symbol}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 主要图表区域 */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle>价格走势</CardTitle>
                <div className="flex space-x-1">
                  {['24h', '7d', '30d', '90d'].map((period) => (
                    <Button
                      key={period}
                      variant={timeframe === period ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setTimeframe(period)}
                    >
                      {period}
                    </Button>
                  ))}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <TradingViewChart
                data={historyData?.data || []}
                height={400}
                coinName={coin?.name}
                coinSymbol={coin?.symbol}
              />
            </CardContent>
          </Card>

          {/* 指标时间线图表 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <BarChart3 className="h-5 w-5" />
                <span>指标时间线</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <IndicatorTimelineChart
                data={indicatorData?.data || []}
                height={500}
                coinName={coin?.name}
                coinSymbol={coin?.symbol}
              />
              {indicatorLoading && (
                <div className="flex items-center justify-center h-96">
                  <div className="text-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
                    <p className="text-gray-600">正在加载指标数据...</p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* 币种信息卡片 */}
        <div className="space-y-4">
          {/* 价格信息 */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-gray-500">当前价格</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="text-3xl font-bold font-mono">
                  {formatCurrency(coin.current_price)}
                </div>
                <div className={`flex items-center space-x-2 ${getPriceChangeColor(coin.price_change_percentage_24h)}`}>
                  {coin.price_change_percentage_24h > 0 ? (
                    <TrendingUp className="h-4 w-4" />
                  ) : (
                    <TrendingDown className="h-4 w-4" />
                  )}
                  <span className="font-semibold">
                    {formatPercentage(coin.price_change_percentage_24h)} (24h)
                  </span>
                </div>
                <div className={`text-sm font-mono ${getPriceChangeColor(coin.price_change_24h)}`}>
                  {coin.price_change_24h > 0 ? '+' : ''}{formatCurrency(coin.price_change_24h)}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 市场数据 */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-gray-500">市场数据</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-600">市值</span>
                <span className="font-mono font-semibold">
                  {formatCurrency(coin.market_cap, 'USD', 0, 0)}
                </span>
              </div>
              
              <div className="flex justify-between">
                <span className="text-gray-600">市值排名</span>
                <span className="font-mono">
                  #{coin.market_cap_rank || '--'}
                </span>
              </div>
              
              <div className="flex justify-between">
                <span className="text-gray-600">24h交易量</span>
                <span className="font-mono">
                  {formatCurrency(coin.total_volume, 'USD', 0, 0)}
                </span>
              </div>
              
              {coin.fully_diluted_valuation && (
                <div className="flex justify-between">
                  <span className="text-gray-600">完全稀释估值</span>
                  <span className="font-mono">
                    {formatCurrency(coin.fully_diluted_valuation, 'USD', 0, 0)}
                  </span>
                </div>
              )}
            </CardContent>
          </Card>

          {/* 供应量信息 */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-gray-500">供应量信息</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-600">流通量</span>
                <span className="font-mono">
                  {formatNumber(coin.circulating_supply)}
                </span>
              </div>
              
              {coin.max_supply && (
                <div className="flex justify-between">
                  <span className="text-gray-600">最大供应量</span>
                  <span className="font-mono">
                    {formatNumber(coin.max_supply)}
                  </span>
                </div>
              )}
              
              {coin.max_supply && coin.circulating_supply && (
                <div className="pt-2">
                  <div className="flex justify-between text-sm text-gray-600 mb-1">
                    <span>流通率</span>
                    <span>{((coin.circulating_supply / coin.max_supply) * 100).toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-blue-600 h-2 rounded-full" 
                      style={{ width: `${(coin.circulating_supply / coin.max_supply) * 100}%` }}
                    />
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* 历史高低点 */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-gray-500">历史价格</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {coin.ath && (
                <div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">历史最高 (ATH)</span>
                    <span className="font-mono font-semibold">
                      {formatCurrency(coin.ath)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-red-600">
                      {formatPercentage(coin.ath_change_percentage)}
                    </span>
                    <span className="text-gray-500">
                      {coin.ath_date ? formatTime(coin.ath_date.toString()) : '--'}
                    </span>
                  </div>
                </div>
              )}
              
              {coin.atl && (
                <div className="pt-2 border-t">
                  <div className="flex justify-between">
                    <span className="text-gray-600">历史最低 (ATL)</span>
                    <span className="font-mono font-semibold">
                      {formatCurrency(coin.atl)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-green-600">
                      +{formatPercentage(Math.abs(coin.atl_change_percentage))}
                    </span>
                    <span className="text-gray-500">
                      {coin.atl_date ? formatTime(coin.atl_date.toString()) : '--'}
                    </span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* 交易量变化指标 */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-gray-500">交易量变化</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-2">
                {coin.volume_change_1h !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">1小时</span>
                    <span className={`font-mono ${getPriceChangeColor(coin.volume_change_1h)}`}>
                      {formatPercentage(coin.volume_change_1h)}
                    </span>
                  </div>
                )}
                {coin.volume_change_3h !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">3小时</span>
                    <span className={`font-mono ${getPriceChangeColor(coin.volume_change_3h)}`}>
                      {formatPercentage(coin.volume_change_3h)}
                    </span>
                  </div>
                )}
                {coin.volume_change_24h !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">24小时</span>
                    <span className={`font-mono ${getPriceChangeColor(coin.volume_change_24h)}`}>
                      {formatPercentage(coin.volume_change_24h)}
                    </span>
                  </div>
                )}
                {coin.volume_change_8h !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">8小时</span>
                    <span className={`font-mono ${getPriceChangeColor(coin.volume_change_8h)}`}>
                      {formatPercentage(coin.volume_change_8h)}
                    </span>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* 长期价格趋势 */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-gray-500">长期价格趋势</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-2">
                {coin.price_change_3m !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">3个月</span>
                    <span className={`font-mono ${getPriceChangeColor(coin.price_change_3m)}`}>
                      {formatPercentage(coin.price_change_3m)}
                    </span>
                  </div>
                )}
                {coin.price_change_6m !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">6个月</span>
                    <span className={`font-mono ${getPriceChangeColor(coin.price_change_6m)}`}>
                      {formatPercentage(coin.price_change_6m)}
                    </span>
                  </div>
                )}
                {coin.price_change_12m !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">12个月</span>
                    <span className={`font-mono ${getPriceChangeColor(coin.price_change_12m)}`}>
                      {formatPercentage(coin.price_change_12m)}
                    </span>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* 长期交易量趋势 */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-gray-500">长期交易量趋势</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-2">
                {coin.volume_change_3m !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">3个月</span>
                    <span className={`font-mono ${getPriceChangeColor(coin.volume_change_3m)}`}>
                      {formatPercentage(coin.volume_change_3m)}
                    </span>
                  </div>
                )}
                {coin.volume_change_6m !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">6个月</span>
                    <span className={`font-mono ${getPriceChangeColor(coin.volume_change_6m)}`}>
                      {formatPercentage(coin.volume_change_6m)}
                    </span>
                  </div>
                )}
                {coin.volume_change_9m !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">9个月</span>
                    <span className={`font-mono ${getPriceChangeColor(coin.volume_change_9m)}`}>
                      {formatPercentage(coin.volume_change_9m)}
                    </span>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* 数据更新时间 */}
      <div className="mt-6 text-center text-sm text-gray-500">
        <div className="flex items-center justify-center space-x-2">
          <Calendar className="h-4 w-4" />
          <span>
            最后更新: {coin.last_updated ? formatTime(coin.last_updated.toString()) : '--'}
          </span>
        </div>
      </div>
    </div>
  )
}