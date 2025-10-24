'use client'

import { useState, useEffect } from 'react'
import useSWR from 'swr'
import { SearchAndFiltersSection } from '@/components/SearchAndFiltersSection'
import { CoinDataTable } from '@/components/CoinDataTable'
import { getCoins } from '@/lib/api'
import { CoinData } from '@/types/coin'
import { Calendar } from 'lucide-react'

interface SearchState {
  search: string
}

export default function HomePage() {
  const [searchState, setSearchState] = useState<SearchState>({
    search: ''
  })
  
  const [currentPage, setCurrentPage] = useState(1)
  const [sortBy, setSortBy] = useState<keyof CoinData>('market_cap_rank')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')
  
  const limit = 50

  // 构建查询参数
  const queryParams = {
    page: currentPage,
    limit,
    sort: sortBy,
    order: sortOrder,
    ...(searchState.search && { search: searchState.search }),
  }

  // 获取币种数据
  const { data: coinData, error: coinError, isLoading: coinLoading } = useSWR(
    ['/coins', queryParams],
    () => getCoins(queryParams),
    {
      refreshInterval: 30000, // 30秒自动刷新
      revalidateOnFocus: false,
      dedupingInterval: 5000,
    }
  )


  // 直接使用API返回的数据，不再进行前端筛选
  const displayCoins = coinData?.data || []

  const handleSearchChange = (newSearch: SearchState) => {
    setSearchState(newSearch)
    setCurrentPage(1) // 重置到第一页
  }

  const handleSort = (key: keyof CoinData, order: 'asc' | 'desc') => {
    setSortBy(key)
    setSortOrder(order)
    setCurrentPage(1) // 重置到第一页
  }

  const handlePageChange = (page: number) => {
    setCurrentPage(page)
    // 滚动到页面顶部
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  // 错误处理
  if (coinError) {
    return (
      <div className="container mx-auto px-4 py-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <h2 className="text-lg font-semibold text-red-800 mb-2">数据加载失败</h2>
          <p className="text-red-600 mb-4">
            无法加载币种数据，请检查网络连接或稍后重试
          </p>
          <button 
            onClick={() => window.location.reload()}
            className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 transition-colors"
          >
            重新加载
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-6">
      {/* 页面标题和数据时间 */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-3xl font-bold text-gray-900">
            加密货币市场概览
          </h1>

          {/* 数据更新时间显示 */}
          {!coinLoading && displayCoins.length > 0 && (
            <div className="flex items-center space-x-2 text-sm text-gray-600">
              <Calendar className="h-4 w-4" />
              <span className="font-medium">数据时间:</span>
              <span className="font-mono bg-gray-100 px-2 py-1 rounded">
                {new Date(displayCoins[0]?.time || Date.now()).toLocaleString('zh-CN', {
                  year: 'numeric',
                  month: '2-digit',
                  day: '2-digit',
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit'
                })}
              </span>
            </div>
          )}
        </div>

        <p className="text-gray-600">
          实时跟踪数千种加密货币的价格、市值和交易数据
        </p>
      </div>

      {/* 搜索和筛选 */}
      <SearchAndFiltersSection
        onFiltersChange={handleSearchChange}
        isLoading={coinLoading}
      />

      {/* 币种数据表格 */}
      <CoinDataTable
        coins={displayCoins}
        isLoading={coinLoading}
        currentPage={currentPage}
        totalPages={coinData?.pagination.total_pages || 1}
        onPageChange={handlePageChange}
        onSort={handleSort}
      />

      {/* 数据更新提示 */}
      {!coinLoading && coinData && (
        <div className="mt-4 text-center text-sm text-gray-500">
          <div className="flex items-center justify-center space-x-2">
            <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse"></div>
            <span>
              数据每30秒自动更新
            </span>
          </div>
        </div>
      )}
    </div>
  )
}