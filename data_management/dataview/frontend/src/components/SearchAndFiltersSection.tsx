'use client'

import { useState, useCallback } from 'react'
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"
import { debounce } from "@/lib/utils"
import { Search, X } from "lucide-react"

interface SearchState {
  search: string
}

interface SearchAndFiltersSectionProps {
  onFiltersChange: (searchState: SearchState) => void
  isLoading?: boolean
}

export function SearchAndFiltersSection({ 
  onFiltersChange, 
  isLoading = false 
}: SearchAndFiltersSectionProps) {
  const [searchState, setSearchState] = useState<SearchState>({
    search: ''
  })

  // 防抖搜索
  const debouncedSearchChange = useCallback(
    debounce((newSearchState: SearchState) => {
      onFiltersChange(newSearchState)
    }, 300),
    [onFiltersChange]
  )

  const updateSearch = (search: string) => {
    const updated = { search }
    setSearchState(updated)
    debouncedSearchChange(updated)
  }

  const clearSearch = () => {
    updateSearch('')
  }

  return (
    <Card className="p-4 mb-6">
      <div className="flex flex-col space-y-4">
        {/* 搜索栏 */}
        <div className="flex items-center space-x-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <Input
              type="text"
              placeholder="搜索币种名称或符号 (如: Bitcoin, BTC, ETH...)"
              value={searchState.search}
              onChange={(e) => updateSearch(e.target.value)}
              className="pl-10 pr-10"
              disabled={isLoading}
            />
            {searchState.search && (
              <button
                onClick={clearSearch}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>

        {/* 搜索状态显示 */}
        {searchState.search && (
          <div className="flex flex-wrap gap-2 text-sm text-gray-600">
            <div className="bg-blue-100 text-blue-800 px-2 py-1 rounded flex items-center space-x-1">
              <span>搜索: "{searchState.search}"</span>
              <button
                onClick={clearSearch}
                className="text-blue-600 hover:text-blue-800"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          </div>
        )}
      </div>
    </Card>
  )
}