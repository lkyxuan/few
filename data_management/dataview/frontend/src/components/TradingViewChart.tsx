'use client'

import { useEffect, useRef, useState } from 'react'
import { HistoricalData } from '@/types/coin'

interface TradingViewChartProps {
  data: HistoricalData[]
  height?: number
  coinName?: string
  coinSymbol?: string
}

export function TradingViewChart({
  data,
  height = 400,
  coinName = "加密货币",
  coinSymbol = ""
}: TradingViewChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [chartModule, setChartModule] = useState<any>(null)

  // 动态加载图表库
  useEffect(() => {
    if (typeof window === 'undefined') return

    import('lightweight-charts')
      .then((module) => {
        setChartModule(module)
        setIsLoading(false)
      })
      .catch((error) => {
        console.error('Failed to load lightweight-charts:', error)
        setIsLoading(false)
      })
  }, [])

  // 初始化图表
  useEffect(() => {
    if (!chartContainerRef.current || !chartModule || isLoading) return

    try {
      // 创建图表
      chartRef.current = chartModule.createChart(chartContainerRef.current, {
        layout: {
          background: { type: chartModule.ColorType.Solid, color: '#ffffff' },
          textColor: '#333333',
        },
        width: chartContainerRef.current.clientWidth,
        height: height,
        grid: {
          vertLines: { color: '#f0f0f0' },
          horzLines: { color: '#f0f0f0' },
        },
        crosshair: { mode: 1 },
        rightPriceScale: {
          borderColor: '#cccccc',
          scaleMargins: { top: 0.1, bottom: 0.1 },
        },
        timeScale: {
          borderColor: '#cccccc',
          timeVisible: true,
          secondsVisible: false,
        },
      })

      // 创建蜡烛图系列
      const candleSeries = chartRef.current.addCandlestickSeries({
        upColor: '#00d4aa',
        downColor: '#ff6b6b',
        borderVisible: false,
        wickUpColor: '#00d4aa',
        wickDownColor: '#ff6b6b',
      })

      // 转换数据格式
      const formattedData = data.map((item) => ({
        time: item.time as any,
        open: item.open,
        high: item.high,
        low: item.low,
        close: item.close,
      }))

      candleSeries.setData(formattedData)

      // 自适应内容
      chartRef.current.timeScale().fitContent()

    } catch (error) {
      console.error('Failed to create chart:', error)
    }

    // 清理函数
    return () => {
      if (chartRef.current) {
        chartRef.current.remove()
        chartRef.current = null
      }
    }
  }, [chartModule, isLoading, data, height])

  // 窗口大小调整处理
  useEffect(() => {
    if (!chartRef.current || !chartContainerRef.current) return

    const handleResize = () => {
      if (chartContainerRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        })
      }
    }

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [chartModule])

  if (typeof window === 'undefined') {
    // 服务端渲染时显示占位符
    return (
      <div
        className="flex items-center justify-center bg-gray-50 rounded"
        style={{ height: `${height}px` }}
      >
        <div className="text-center text-gray-500">
          <p className="text-lg font-medium mb-1">价格走势图表</p>
          <p className="text-sm">Loading chart...</p>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div
        className="flex items-center justify-center bg-gray-50 rounded"
        style={{ height: `${height}px` }}
      >
        <div className="text-center text-gray-500">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
          <p className="text-sm">正在加载图表组件...</p>
        </div>
      </div>
    )
  }

  if (!data || data.length === 0) {
    return (
      <div
        className="flex items-center justify-center bg-gray-50 rounded"
        style={{ height: `${height}px` }}
      >
        <div className="text-center text-gray-500">
          <p className="text-lg font-medium mb-1">暂无价格数据</p>
          <p className="text-sm">请选择其他时间范围</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center text-sm text-gray-600">
        <span>
          {coinName} {coinSymbol && `(${coinSymbol.toUpperCase()})`} 价格走势
        </span>
        <span>数据点: {data.length}</span>
      </div>
      <div
        ref={chartContainerRef}
        className="w-full rounded border bg-white"
        style={{ height: `${height}px` }}
      />
    </div>
  )
}