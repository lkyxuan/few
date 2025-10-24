'use client'

import { useState, useMemo, useEffect } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts'

interface IndicatorData {
  time: string
  indicator_name: string
  indicator_value: number
}

interface IndicatorTimelineChartProps {
  data: IndicatorData[]
  height?: number
  coinName?: string
  coinSymbol?: string
}

// 优化的现代化配色方案 - 使用专业的金融图表配色
const PERCENTAGE_INDICATORS = {
  'PRICE_CHANGE_24H': {
    color: '#3b82f6',
    gradient: 'from-blue-400 to-blue-600',
    name: '24小时价格变化',
    category: '价格'
  },
  'PRICE_CHANGE_3M': {
    color: '#10b981',
    gradient: 'from-emerald-400 to-emerald-600',
    name: '3分钟价格变化',
    category: '价格'
  },
  'PRICE_CHANGE_6M': {
    color: '#f59e0b',
    gradient: 'from-amber-400 to-amber-600',
    name: '6分钟价格变化',
    category: '价格'
  },
  'PRICE_CHANGE_12M': {
    color: '#ef4444',
    gradient: 'from-red-400 to-red-600',
    name: '12分钟价格变化',
    category: '价格'
  },
  'VOLUME_CHANGE_1H': {
    color: '#8b5cf6',
    gradient: 'from-violet-400 to-violet-600',
    name: '1小时交易量变化',
    category: '交易量'
  },
  'VOLUME_CHANGE_3H': {
    color: '#06b6d4',
    gradient: 'from-cyan-400 to-cyan-600',
    name: '3小时交易量变化',
    category: '交易量'
  },
  'VOLUME_CHANGE_8H': {
    color: '#84cc16',
    gradient: 'from-lime-400 to-lime-600',
    name: '8小时交易量变化',
    category: '交易量'
  },
  'VOLUME_CHANGE_24H': {
    color: '#ec4899',
    gradient: 'from-pink-400 to-pink-600',
    name: '24小时交易量变化',
    category: '交易量'
  },
  'VOLUME_CHANGE_3M': {
    color: '#f97316',
    gradient: 'from-orange-400 to-orange-600',
    name: '3分钟交易量变化',
    category: '交易量'
  },
  'VOLUME_CHANGE_6M': {
    color: '#14b8a6',
    gradient: 'from-teal-400 to-teal-600',
    name: '6分钟交易量变化',
    category: '交易量'
  },
  'VOLUME_CHANGE_9M': {
    color: '#f43f5e',
    gradient: 'from-rose-400 to-rose-600',
    name: '9分钟交易量变化',
    category: '交易量'
  },
  'VOLUME_CHANGE_RATIO_3M': {
    color: '#6366f1',
    gradient: 'from-indigo-400 to-indigo-600',
    name: '3分钟交易量比率',
    category: '比率'
  }
}

const ABSOLUTE_INDICATORS = {
  'CAPITAL_INFLOW_INTENSITY_3M': {
    color: '#eab308',
    gradient: 'from-yellow-400 to-yellow-600',
    name: '3分钟资金流入强度',
    category: '资金流'
  },
  'AVG_VOLUME_3M_24H': {
    color: '#a855f7',
    gradient: 'from-purple-400 to-purple-600',
    name: '3分钟24小时平均交易量',
    category: '平均量'
  }
}

// 单个图表组件
function SingleChart({
  chartData,
  indicators,
  visibleIndicators,
  onToggleIndicator,
  onToggleAll,
  title,
  yAxisLabel,
  formatValue,
  coinName,
  coinSymbol,
  height
}: {
  chartData: any[]
  indicators: string[]
  visibleIndicators: Set<string>
  onToggleIndicator: (indicator: string) => void
  onToggleAll: () => void
  title: string
  yAxisLabel: string
  formatValue: (value: number) => string
  coinName: string
  coinSymbol: string
  height: number
}) {
  // 自定义时间格式化
  const formatTime = (timeStr: string) => {
    const date = new Date(timeStr)
    return date.toLocaleDateString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  // 自定义Tooltip - 针对加密货币数据优化
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const filteredPayload = payload.filter((entry: any) =>
        visibleIndicators.has(entry.dataKey)
      )

      return (
        <div className="bg-white/95 backdrop-blur-sm border border-gray-200 rounded-xl p-4 shadow-xl max-w-xs">
          {/* 时间标题 */}
          <div className="flex items-center mb-3 pb-2 border-b border-gray-100">
            <div className="w-2 h-2 rounded-full bg-blue-500 mr-2 animate-pulse"></div>
            <p className="font-bold text-gray-800 text-sm">
              {formatTime(label)}
            </p>
          </div>

          {/* 指标数据 */}
          <div className="space-y-2">
            {filteredPayload.map((entry: any, index: number) => {
              const config = { ...PERCENTAGE_INDICATORS, ...ABSOLUTE_INDICATORS }[entry.dataKey]
              const isPercentage = entry.dataKey in PERCENTAGE_INDICATORS

              return (
                <div key={index} className="flex items-center justify-between py-1">
                  <div className="flex items-center">
                    <div
                      className="w-3 h-3 rounded-full mr-2 shadow-sm"
                      style={{ backgroundColor: entry.color }}
                    />
                    <span className="text-xs text-gray-600 truncate max-w-[120px]">
                      {config?.name || entry.dataKey}
                    </span>
                  </div>
                  <span
                    className="font-mono text-xs font-bold ml-2"
                    style={{ color: entry.color }}
                  >
                    {isPercentage
                      ? `${(entry.value * 100).toFixed(2)}%`
                      : formatValue(entry.value)
                    }
                  </span>
                </div>
              )
            })}
          </div>

          {/* 底部标识 */}
          {filteredPayload.length > 0 && (
            <div className="mt-3 pt-2 border-t border-gray-100">
              <p className="text-xs text-gray-400 text-center">
                {filteredPayload.length} 个指标
              </p>
            </div>
          )}
        </div>
      )
    }
    return null
  }

  if (indicators.length === 0 || chartData.length === 0) {
    return (
      <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl p-8 shadow-sm">
        <h4 className="text-xl font-bold text-gray-700 mb-2 flex items-center">
          <div className="w-4 h-4 bg-gray-400 rounded-full mr-3"></div>
          {title}
        </h4>
        <div className="flex items-center justify-center h-48">
          <div className="text-center">
            <div className="w-16 h-16 bg-gray-300 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <p className="text-gray-500 font-medium">暂无{title.toLowerCase()}数据</p>
            <p className="text-gray-400 text-sm mt-1">请选择其他时间范围或币种</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl shadow-lg border border-gray-100 overflow-hidden">
      {/* 图表标题 - 使用渐变背景 */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 px-6 py-4 border-b border-gray-100">
        <div className="flex justify-between items-center">
          <h4 className="text-xl font-bold text-gray-800 flex items-center">
            <div className="w-2 h-8 bg-gradient-to-b from-blue-400 to-blue-600 rounded-full mr-3"></div>
            {coinName} {coinSymbol && `(${coinSymbol.toUpperCase()})`}
            <span className="ml-2 px-3 py-1 bg-white rounded-full text-sm font-medium text-gray-600 shadow-sm">
              {title}
            </span>
          </h4>
          <div className="text-sm text-gray-500 bg-white px-3 py-1 rounded-full shadow-sm">
            <span className="font-medium text-blue-600">{visibleIndicators.size}</span>
            <span className="text-gray-400 mx-1">/</span>
            <span className="text-gray-600">{indicators.length}</span>
            <span className="ml-1 text-gray-400">个指标</span>
          </div>
        </div>
      </div>

      {/* 指标开关面板 - 现代化设计 */}
      <div className="bg-gradient-to-br from-slate-50 to-gray-100 p-5 border-b border-gray-100">
        <div className="flex justify-between items-center mb-4">
          <h5 className="text-base font-bold text-gray-800 flex items-center">
            <div className="w-1.5 h-6 bg-gradient-to-b from-violet-400 to-purple-600 rounded-full mr-2"></div>
            指标控制面板
          </h5>
          <button
            onClick={onToggleAll}
            className="text-sm px-4 py-2 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-lg
                     hover:from-blue-600 hover:to-blue-700 transition-all duration-200 shadow-md hover:shadow-lg
                     font-medium flex items-center space-x-1"
          >
            <span>{visibleIndicators.size === indicators.length ? '取消全选' : '全选'}</span>
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {indicators.map(indicator => {
            const config = { ...PERCENTAGE_INDICATORS, ...ABSOLUTE_INDICATORS }[indicator]
            const isVisible = visibleIndicators.has(indicator)

            return (
              <label
                key={indicator}
                className={`flex items-center space-x-3 p-3 rounded-xl cursor-pointer transition-all duration-200
                          transform hover:scale-[1.02] ${
                  isVisible
                    ? 'bg-white shadow-md border-2 ring-1 ring-opacity-20'
                    : 'bg-white/70 hover:bg-white hover:shadow-sm border border-gray-200'
                }`}
                style={{
                  borderColor: isVisible ? config?.color : 'transparent',
                  ringColor: isVisible ? config?.color : 'transparent'
                }}
              >
                <input
                  type="checkbox"
                  checked={isVisible}
                  onChange={() => onToggleIndicator(indicator)}
                  className="sr-only"
                />
                <div className="relative">
                  <div
                    className={`w-4 h-4 rounded-full transition-all duration-200 ${
                      isVisible ? 'shadow-md scale-110' : 'opacity-70'
                    }`}
                    style={{
                      backgroundColor: config?.color || '#666',
                      boxShadow: isVisible ? `0 2px 8px ${config?.color}40` : 'none'
                    }}
                  />
                  {isVisible && (
                    <div className="absolute -inset-1 rounded-full animate-ping opacity-20"
                         style={{ backgroundColor: config?.color }} />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <span className={`text-sm font-medium truncate block ${
                    isVisible ? 'text-gray-800' : 'text-gray-600'
                  }`}>
                    {config?.name || indicator}
                  </span>
                  {config?.category && (
                    <span className="text-xs text-gray-400 font-normal">
                      {config.category}
                    </span>
                  )}
                </div>
                {isVisible && (
                  <div className="flex-shrink-0">
                    <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse"></div>
                  </div>
                )}
              </label>
            )
          })}
        </div>
      </div>

      {/* 图表区域 - 现代化数据可视化 */}
      <div className="bg-gradient-to-b from-white to-slate-50 p-6 rounded-b-xl">
        <ResponsiveContainer width="100%" height={height}>
          <LineChart
            data={chartData}
            margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
          >
            {/* 高级网格线 */}
            <CartesianGrid
              strokeDasharray="2 4"
              stroke="#e2e8f0"
              opacity={0.6}
              horizontal={true}
              vertical={false}
            />

            {/* 时间轴 - 针对3分钟数据间隔优化 */}
            <XAxis
              dataKey="time"
              tickFormatter={formatTime}
              tick={{
                fontSize: 11,
                fill: '#64748b',
                fontWeight: 500
              }}
              stroke="#cbd5e1"
              strokeWidth={1}
              axisLine={{ stroke: '#e2e8f0' }}
              tickLine={{ stroke: '#cbd5e1' }}
              interval="preserveStartEnd"
              minTickGap={50}
            />

            {/* Y轴 - 智能格式化数值 */}
            <YAxis
              tick={{
                fontSize: 11,
                fill: '#64748b',
                fontWeight: 500
              }}
              stroke="#cbd5e1"
              strokeWidth={1}
              axisLine={{ stroke: '#e2e8f0' }}
              tickLine={{ stroke: '#cbd5e1' }}
              tickFormatter={(value) => {
                // 智能数值格式化
                if (Math.abs(value) >= 1000000) {
                  return `${(value / 1000000).toFixed(1)}M`
                } else if (Math.abs(value) >= 1000) {
                  return `${(value / 1000).toFixed(1)}K`
                } else if (Math.abs(value) < 1 && Math.abs(value) > 0) {
                  return `${(value * 100).toFixed(2)}%`
                }
                return value.toFixed(2)
              }}
              domain={['auto', 'auto']}
            />

            {/* 增强悬浮提示 */}
            <Tooltip
              content={<CustomTooltip />}
              cursor={{
                stroke: '#6366f1',
                strokeWidth: 1,
                strokeDasharray: '4 4',
                opacity: 0.7
              }}
              wrapperStyle={{
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                border: '1px solid #e5e7eb',
                borderRadius: '12px',
                boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)'
              }}
            />

            {/* 现代化图例 */}
            <Legend
              wrapperStyle={{
                paddingTop: '20px',
                paddingBottom: '10px'
              }}
              iconType="line"
              formatter={(value) => {
                const config = { ...PERCENTAGE_INDICATORS, ...ABSOLUTE_INDICATORS }[value]
                return (
                  <span className="text-sm font-medium text-gray-700">
                    {config?.name || value}
                  </span>
                )
              }}
            />

            {/* 渲染所有可见的指标线 - 高级视觉效果 */}
            {indicators.map(indicator => {
              if (!visibleIndicators.has(indicator)) return null

              const config = { ...PERCENTAGE_INDICATORS, ...ABSOLUTE_INDICATORS }[indicator]

              return (
                <Line
                  key={indicator}
                  type="monotone"
                  dataKey={indicator}
                  stroke={config?.color || '#666'}
                  strokeWidth={2.5}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  dot={{
                    fill: config?.color,
                    stroke: 'white',
                    strokeWidth: 2,
                    r: 1.5,
                    style: {
                      filter: `drop-shadow(0px 1px 2px rgba(0,0,0,0.1))`
                    }
                  }}
                  activeDot={{
                    r: 5,
                    fill: config?.color,
                    stroke: 'white',
                    strokeWidth: 3,
                    style: {
                      filter: `drop-shadow(0px 2px 4px ${config?.color}40)`
                    }
                  }}
                  connectNulls={false}
                  style={{
                    filter: `drop-shadow(0px 1px 2px rgba(0,0,0,0.05))`
                  }}
                />
              )
            })}
          </LineChart>
        </ResponsiveContainer>

        {/* 数据统计 */}
        <div className="text-center text-xs text-gray-500 mt-2">
          数据点: {chartData.length} 个时间点
        </div>
      </div>
    </div>
  )
}

export function IndicatorTimelineChart({
  data,
  height = 350,
  coinName = "加密货币",
  coinSymbol = ""
}: IndicatorTimelineChartProps) {
  // 根据指标类型分组
  const { percentageIndicators, absoluteIndicators } = useMemo(() => {
    if (!data || data.length === 0) return { percentageIndicators: [], absoluteIndicators: [] }

    const allIndicators = [...new Set(data.map(item => item.indicator_name))]
    const percentageIndicators = allIndicators.filter(indicator =>
      indicator in PERCENTAGE_INDICATORS
    ).sort()
    const absoluteIndicators = allIndicators.filter(indicator =>
      indicator in ABSOLUTE_INDICATORS
    ).sort()

    return { percentageIndicators, absoluteIndicators }
  }, [data])

  // 分别管理两个图表的可见指标
  const [visiblePercentageIndicators, setVisiblePercentageIndicators] = useState<Set<string>>(new Set())
  const [visibleAbsoluteIndicators, setVisibleAbsoluteIndicators] = useState<Set<string>>(new Set())

  // 初始化可见指标
  useEffect(() => {
    if (percentageIndicators.length > 0) {
      setVisiblePercentageIndicators(new Set(percentageIndicators.slice(0, 3)))
    }
    if (absoluteIndicators.length > 0) {
      setVisibleAbsoluteIndicators(new Set(absoluteIndicators))
    }
  }, [percentageIndicators, absoluteIndicators])

  // 转换数据格式为Recharts需要的时间序列格式
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return []

    // 按时间分组数据
    const timeGroups: Record<string, Record<string, number>> = {}

    data.forEach(item => {
      const timeKey = new Date(item.time).toISOString()
      if (!timeGroups[timeKey]) {
        timeGroups[timeKey] = { time: timeKey }
      }
      timeGroups[timeKey][item.indicator_name] = item.indicator_value
    })

    // 转换为数组并排序
    return Object.values(timeGroups)
      .sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime())
  }, [data])

  // 百分比指标切换函数
  const togglePercentageIndicator = (indicator: string) => {
    const newVisible = new Set(visiblePercentageIndicators)
    if (newVisible.has(indicator)) {
      newVisible.delete(indicator)
    } else {
      newVisible.add(indicator)
    }
    setVisiblePercentageIndicators(newVisible)
  }

  const toggleAllPercentage = () => {
    if (visiblePercentageIndicators.size === percentageIndicators.length) {
      setVisiblePercentageIndicators(new Set())
    } else {
      setVisiblePercentageIndicators(new Set(percentageIndicators))
    }
  }

  // 绝对值指标切换函数
  const toggleAbsoluteIndicator = (indicator: string) => {
    const newVisible = new Set(visibleAbsoluteIndicators)
    if (newVisible.has(indicator)) {
      newVisible.delete(indicator)
    } else {
      newVisible.add(indicator)
    }
    setVisibleAbsoluteIndicators(newVisible)
  }

  const toggleAllAbsolute = () => {
    if (visibleAbsoluteIndicators.size === absoluteIndicators.length) {
      setVisibleAbsoluteIndicators(new Set())
    } else {
      setVisibleAbsoluteIndicators(new Set(absoluteIndicators))
    }
  }

  if (!data || data.length === 0) {
    return (
      <div
        style={{ height: `${height * 2 + 50}px` }}
        className="flex items-center justify-center bg-gray-50 rounded border"
      >
        <div className="text-center text-gray-500">
          <p className="text-lg font-medium mb-1">暂无指标数据</p>
          <p className="text-sm">请选择其他时间范围或币种</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 百分比指标图表 */}
      <SingleChart
        chartData={chartData}
        indicators={percentageIndicators}
        visibleIndicators={visiblePercentageIndicators}
        onToggleIndicator={togglePercentageIndicator}
        onToggleAll={toggleAllPercentage}
        title="变化率指标"
        yAxisLabel="变化率 (%)"
        formatValue={(value) => `${typeof value === 'number' ? value.toFixed(2) : value}%`}
        coinName={coinName}
        coinSymbol={coinSymbol}
        height={height}
      />

      {/* 绝对值指标图表 */}
      {absoluteIndicators.length > 0 && (
        <SingleChart
          chartData={chartData}
          indicators={absoluteIndicators}
          visibleIndicators={visibleAbsoluteIndicators}
          onToggleIndicator={toggleAbsoluteIndicator}
          onToggleAll={toggleAllAbsolute}
          title="绝对值指标"
          yAxisLabel="数值"
          formatValue={(value) => typeof value === 'number' ? value.toLocaleString() : value.toString()}
          coinName={coinName}
          coinSymbol={coinSymbol}
          height={height}
        />
      )}

      {/* 总体数据统计 */}
      <div className="text-center text-sm text-gray-500 bg-gray-50 p-3 rounded">
        <span>总共 {percentageIndicators.length + absoluteIndicators.length} 个指标</span>
        <span className="mx-2">•</span>
        <span>时间范围: {chartData.length > 0 && new Date(chartData[0].time).toLocaleDateString('zh-CN')} - {chartData.length > 0 && new Date(chartData[chartData.length - 1].time).toLocaleDateString('zh-CN')}</span>
      </div>
    </div>
  )
}