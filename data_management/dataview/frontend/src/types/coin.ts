// 币种数据类型定义
export interface CoinData {
  coin_id: string;
  symbol: string;
  name: string;
  image: string;
  current_price: number;
  market_cap: number;
  market_cap_rank: number;
  fully_diluted_valuation?: number;
  total_volume: number;
  circulating_supply: number;
  max_supply?: number;
  price_change_24h: number;
  price_change_percentage_24h: number;
  market_cap_change_24h: number;
  market_cap_change_percentage_24h: number;
  ath: number;
  ath_change_percentage: number;
  ath_date: string;
  atl: number;
  atl_change_percentage: number;
  atl_date: string;
  last_updated: string;
  time: string;  // 数据采集时间点（3分钟间隔）

  // 指标数据 - 交易量变化指标
  volume_change_1h?: number;
  volume_change_3h?: number;
  volume_change_24h?: number;
  volume_change_8h?: number;
  volume_change_3m?: number;
  volume_change_6m?: number;
  volume_change_9m?: number;
  
  // 价格变化指标
  price_change_3m?: number;
  price_change_6m?: number;
  price_change_12m?: number;
  
  // 平均指标
  avg_btc_eth?: number;
  avg_btc_eth_sol?: number;
  weighted_avg_btc_eth?: number;
  weighted_avg_btc_eth_sol?: number;
  weighted_avg_sol_eth_bnb?: number;

  // 核心自定义指标
  capital_inflow_intensity_3m?: number;
  volume_change_ratio_3m?: number;
  avg_volume_3m_24h?: number;
}

// 历史价格数据
export interface HistoricalData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

// 市场统计数据
export interface MarketStats {
  total_market_cap: number;
  total_volume_24h: number;
  market_cap_change_percentage_24h: number;
  active_cryptocurrencies: number;
  market_cap_percentage: {
    bitcoin: number;
    ethereum: number;
    others: number;
  };
  last_updated: string;
}

// API 响应分页信息
export interface Pagination {
  page: number;
  limit: number;
  total: number;
  total_pages: number;
}

// 币种列表 API 响应
export interface CoinListResponse {
  data: CoinData[];
  pagination: Pagination;
  meta: MarketStats;
}

// 搜索和筛选参数
export interface FilterParams {
  search: string;
  sortBy: keyof CoinData;
  sortOrder: 'asc' | 'desc';
  priceRange: [number, number];
  marketCapRankRange: [number, number];
  page: number;
  limit: number;
}

// 技术指标数据
export interface IndicatorData {
  time: string;
  coin_id: string;
  indicator_name: string;
  timeframe: string;
  indicator_value: number;
}

// 指标列表
export interface Indicator {
  name: string;
  display_name: string;
  description: string;
  timeframes: string[];
}

// 错误响应类型
export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: any;
  };
}