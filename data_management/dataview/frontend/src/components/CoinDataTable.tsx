'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { CoinImage } from './CoinImage'
import {
  formatCurrency,
  formatNumber,
  formatPercentage,
  getPriceChangeColor,
  getPriceChangeBgColor
} from "@/lib/utils"
import { CoinData } from "@/types/coin"
import { ChevronUp, ChevronDown, TrendingUp, TrendingDown } from "lucide-react"

interface CoinDataTableProps {
  coins: CoinData[]
  isLoading: boolean
  currentPage: number
  totalPages: number
  onPageChange: (page: number) => void
  onSort: (sortBy: keyof CoinData, order: 'asc' | 'desc') => void
}

interface SortConfig {
  key: keyof CoinData | null
  direction: 'asc' | 'desc'
}

export function CoinDataTable({ 
  coins, 
  isLoading, 
  currentPage, 
  totalPages,
  onPageChange,
  onSort 
}: CoinDataTableProps) {
  const router = useRouter()
  const [sortConfig, setSortConfig] = useState<SortConfig>({ 
    key: 'market_cap_rank', 
    direction: 'asc' 
  })

  const handleSort = (key: keyof CoinData) => {
    const direction = sortConfig.key === key && sortConfig.direction === 'asc' ? 'desc' : 'asc'
    setSortConfig({ key, direction })
    onSort(key, direction)
  }

  const getSortIcon = (key: keyof CoinData) => {
    if (sortConfig.key !== key) {
      return <div className="w-4 h-4" />
    }
    return sortConfig.direction === 'asc' ? 
      <ChevronUp className="w-4 h-4" /> : 
      <ChevronDown className="w-4 h-4" />
  }

  const handleRowClick = (coin: CoinData) => {
    router.push(`/coin/${coin.coin_id}`)
  }

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="p-6">
          <div className="space-y-3">
            {Array.from({ length: 10 }).map((_, i) => (
              <div key={i} className="flex items-center space-x-4">
                <div className="h-8 w-8 bg-gray-200 rounded-full animate-pulse"></div>
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-gray-200 rounded animate-pulse"></div>
                  <div className="h-3 bg-gray-200 rounded animate-pulse w-1/3"></div>
                </div>
                <div className="h-4 bg-gray-200 rounded animate-pulse w-20"></div>
                <div className="h-4 bg-gray-200 rounded animate-pulse w-16"></div>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full table-auto">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th
                className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => handleSort('market_cap_rank')}
                style={{ width: '80px' }}
              >
                <div className="flex items-center space-x-1">
                  <span>排名</span>
                  {getSortIcon('market_cap_rank')}
                </div>
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider" style={{ width: '200px' }}>
                币种
              </th>
              <th
                className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => handleSort('current_price')}
                style={{ minWidth: '100px' }}
              >
                <div className="flex items-center justify-end space-x-1">
                  <span>价格</span>
                  {getSortIcon('current_price')}
                </div>
              </th>
              <th
                className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => handleSort('price_change_percentage_24h')}
                style={{ minWidth: '120px' }}
              >
                <div className="flex items-center justify-end space-x-1">
                  <span>24h 变化</span>
                  {getSortIcon('price_change_percentage_24h')}
                </div>
              </th>
              <th
                className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => handleSort('market_cap')}
                style={{ minWidth: '140px' }}
              >
                <div className="flex items-center justify-end space-x-1">
                  <span>市值</span>
                  {getSortIcon('market_cap')}
                </div>
              </th>
              <th
                className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => handleSort('total_volume')}
                style={{ minWidth: '140px' }}
              >
                <div className="flex items-center justify-end space-x-1">
                  <span>24h 交易量</span>
                  {getSortIcon('total_volume')}
                </div>
              </th>
              {/* 资本流入强度 */}
              <th
                className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => handleSort('capital_inflow_intensity_3m')}
                style={{ minWidth: '100px' }}
              >
                <div className="flex items-center justify-end space-x-1">
                  <span>资本流入</span>
                  {getSortIcon('capital_inflow_intensity_3m')}
                </div>
              </th>
              {/* 交易量变化比率 */}
              <th
                className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => handleSort('volume_change_ratio_3m')}
                style={{ minWidth: '100px' }}
              >
                <div className="flex items-center justify-end space-x-1">
                  <span>量变比率</span>
                  {getSortIcon('volume_change_ratio_3m')}
                </div>
              </th>
              {/* 平均交易量 */}
              <th
                className="px-3 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => handleSort('avg_volume_3m_24h')}
                style={{ minWidth: '120px' }}
              >
                <div className="flex items-center justify-end space-x-1">
                  <span>平均量</span>
                  {getSortIcon('avg_volume_3m_24h')}
                </div>
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {coins.map((coin) => (
              <tr 
                key={coin.coin_id}
                className="hover:bg-gray-50 cursor-pointer transition-colors"
                onClick={() => handleRowClick(coin)}
              >
                {/* 排名 */}
                <td className="px-3 py-3 whitespace-nowrap">
                  <span className="font-mono text-sm text-gray-500">
                    #{coin.market_cap_rank || '--'}
                  </span>
                </td>

                {/* 币种信息 */}
                <td className="px-4 py-3 whitespace-nowrap">
                  <div className="flex items-center space-x-3">
                    <CoinImage
                      coinId={coin.coin_id}
                      coinName={coin.name}
                      size={32}
                    />
                    <div>
                      <div className="font-semibold text-gray-900 text-sm">
                        {coin.name}
                      </div>
                      <div className="text-xs text-gray-500 uppercase">
                        {coin.symbol}
                      </div>
                    </div>
                  </div>
                </td>

                {/* 价格 */}
                <td className="px-3 py-3 whitespace-nowrap text-right">
                  <span className="font-mono font-semibold text-gray-900 text-sm">
                    {formatCurrency(coin.current_price)}
                  </span>
                </td>

                {/* 24小时变化 */}
                <td className="px-3 py-3 whitespace-nowrap text-right">
                  <div className="flex flex-col items-end space-y-1">
                    <span className={`font-mono font-semibold text-sm ${getPriceChangeColor(coin.price_change_percentage_24h)}`}>
                      {formatPercentage(coin.price_change_percentage_24h)}
                    </span>
                    <span className={`text-xs font-mono ${getPriceChangeColor(coin.price_change_24h)}`}>
                      {coin.price_change_24h > 0 ? '+' : ''}{formatCurrency(coin.price_change_24h)}
                    </span>
                  </div>
                </td>

                {/* 市值 */}
                <td className="px-3 py-3 whitespace-nowrap text-right">
                  <span className="font-mono text-gray-900 text-sm">
                    {formatCurrency(coin.market_cap, 'USD', 0, 0)}
                  </span>
                </td>

                {/* 24小时交易量 */}
                <td className="px-3 py-3 whitespace-nowrap text-right">
                  <span className="font-mono text-gray-900 text-sm">
                    {formatCurrency(coin.total_volume, 'USD', 0, 0)}
                  </span>
                </td>

                {/* 资本流入强度 3个月 */}
                <td className="px-3 py-3 whitespace-nowrap text-right">
                  <span className={`font-mono font-semibold text-sm ${getPriceChangeColor(coin.capital_inflow_intensity_3m)}`}>
                    {coin.capital_inflow_intensity_3m !== undefined && coin.capital_inflow_intensity_3m !== null
                      ? formatPercentage(coin.capital_inflow_intensity_3m)
                      : '--'}
                  </span>
                </td>

                {/* 交易量变化比率 3个月 */}
                <td className="px-3 py-3 whitespace-nowrap text-right">
                  <span className={`font-mono font-semibold text-sm ${getPriceChangeColor(coin.volume_change_ratio_3m)}`}>
                    {coin.volume_change_ratio_3m !== undefined && coin.volume_change_ratio_3m !== null
                      ? formatPercentage(coin.volume_change_ratio_3m)
                      : '--'}
                  </span>
                </td>

                {/* 平均交易量 3个月-24小时 */}
                <td className="px-3 py-3 whitespace-nowrap text-right">
                  <span className="font-mono text-gray-900 text-sm">
                    {coin.avg_volume_3m_24h !== undefined && coin.avg_volume_3m_24h !== null
                      ? formatCurrency(coin.avg_volume_3m_24h, 'USD', 0, 0)
                      : '--'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 分页控件和时间脚标 */}
      <div className="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200">
        <div className="flex-1 flex justify-between items-center">
          <button
            onClick={() => onPageChange(Math.max(1, currentPage - 1))}
            disabled={currentPage <= 1}
            className="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            上一页
          </button>

          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-700">
              第 {currentPage} 页，共 {totalPages} 页
            </span>
          </div>

          <button
            onClick={() => onPageChange(Math.min(totalPages, currentPage + 1))}
            disabled={currentPage >= totalPages}
            className="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            下一页
          </button>
        </div>

      </div>
    </div>
  )
}