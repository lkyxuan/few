# DataView 前端展示模块

> 现代化的加密货币数据展示系统

## 🎯 核心功能

- **实时展示**: Next.js 15前端 + FastAPI后端
- **数据可视化**: 实时币种数据展示和搜索
- **高性能API**: 优化数据库查询，支持大规模数据展示
- **响应式设计**: 支持PC和移动端
- **用户交互**: 搜索、分页、排序等交互功能

## 🚀 快速开始

### 前端开发
```bash
cd dataview/frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 启动生产服务器
npm start
```

### 后端开发
```bash
cd dataview/backend

# 安装依赖
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 启动API服务
python run.py

# 或使用uvicorn
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

## 📋 技术栈

### 前端技术
- **Next.js 15**: React框架，支持SSR和SSG
- **TypeScript**: 类型安全的JavaScript
- **Tailwind CSS**: 实用优先的CSS框架
- **TradingView**: 专业图表库
- **React Query**: 数据获取和缓存

### 后端技术
- **FastAPI**: 高性能Python Web框架
- **SQLAlchemy**: Python SQL工具包
- **PostgreSQL**: 关系型数据库
- **Pydantic**: 数据验证和序列化
- **Uvicorn**: ASGI服务器

## 🌐 API接口

### 币种数据接口
```bash
# 获取币种列表
GET /api/coins?page=1&limit=20&search=bitcoin

# 获取币种详情
GET /api/coins/{coin_id}

# 获取币种历史数据
GET /api/coins/{coin_id}/history?timeframe=1d&limit=100

# 获取市场统计
GET /api/market/stats
```

### 指标数据接口
```bash
# 获取技术指标
GET /api/indicators/{coin_id}?indicator=rsi&timeframe=1h

# 获取多个指标
GET /api/indicators/{coin_id}/multiple?indicators=sma,ema,rsi

# 获取指标历史
GET /api/indicators/{coin_id}/history?indicator=macd&limit=50
```

### 图片接口
```bash
# 获取币种图片
GET /api/images/{coin_id}

# 上传币种图片
POST /api/images/{coin_id}
```

## 🎨 页面功能

### 首页 (/)
- 市场概览和统计信息
- 热门币种排行榜
- 实时价格变化
- 市场趋势图表

### 币种详情页 (/coin/[coin_id])
- 币种基本信息
- 实时价格和图表
- 技术指标展示
- 历史数据查询

### 搜索和筛选
- 币种名称和符号搜索
- 价格范围筛选
- 市值排名筛选
- 涨跌幅筛选

## ⚙️ 配置说明

### 前端配置 (next.config.ts)
```typescript
const nextConfig = {
  experimental: {
    appDir: true,
  },
  images: {
    domains: ['assets.coingecko.com'],
  },
  env: {
    API_BASE_URL: process.env.API_BASE_URL || 'http://localhost:8000',
  },
}
```

### 后端配置 (settings.py)
```python
# 数据库配置
DATABASE_URL = "postgresql://datasync:password@localhost:5432/cryptodb"

# API配置
API_V1_STR = "/api"
PROJECT_NAME = "DataView API"

# 跨域配置
BACKEND_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
]

# 图片配置
STATIC_DIR = "static"
IMAGES_DIR = "coin-images"
```

## 🔧 开发指南

### 添加新页面
```typescript
// pages/new-page.tsx
import { GetServerSideProps } from 'next'

export default function NewPage({ data }) {
  return (
    <div>
      <h1>新页面</h1>
      <p>{data.message}</p>
    </div>
  )
}

export const getServerSideProps: GetServerSideProps = async () => {
  return {
    props: {
      data: { message: 'Hello World' }
    }
  }
}
```

### 添加新API接口
```python
# src/api/new_endpoint.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class NewResponse(BaseModel):
    message: str
    data: dict

@router.get("/new-endpoint", response_model=NewResponse)
async def new_endpoint():
    return NewResponse(
        message="Success",
        data={"key": "value"}
    )
```

### 添加新组件
```typescript
// src/components/NewComponent.tsx
import React from 'react'

interface NewComponentProps {
  title: string
  data: any[]
}

export const NewComponent: React.FC<NewComponentProps> = ({ title, data }) => {
  return (
    <div className="p-4 border rounded-lg">
      <h2 className="text-xl font-bold">{title}</h2>
      <div className="mt-2">
        {data.map((item, index) => (
          <div key={index}>{item.name}</div>
        ))}
      </div>
    </div>
  )
}
```

## 📊 性能优化

### 前端优化
- **代码分割**: 按路由分割代码，减少初始加载时间
- **图片优化**: 使用Next.js Image组件，自动优化图片
- **缓存策略**: 使用React Query缓存API数据
- **懒加载**: 组件和图片懒加载，提升用户体验

### 后端优化
- **数据库查询**: 优化SQL查询，使用索引
- **连接池**: 使用数据库连接池，提高并发性能
- **缓存**: 使用Redis缓存热点数据
- **异步处理**: 使用异步IO，提高响应速度

## 🔧 故障排查

### 常见问题
1. **页面加载慢**: 检查网络连接和API响应时间
2. **数据不显示**: 检查API接口和数据库连接
3. **图片不显示**: 检查图片路径和CDN配置
4. **搜索不工作**: 检查搜索API和数据库索引

### 日志查看
```bash
# 查看前端日志
npm run dev  # 开发模式会显示详细日志

# 查看后端日志
tail -f /var/log/databao/dataview.log

# 查看API日志
curl http://localhost:8000/docs  # 访问API文档
```

### 健康检查
```bash
# 检查前端服务
curl http://localhost:3000

# 检查后端API
curl http://localhost:8000/health

# 检查数据库连接
psql -d cryptodb -c "SELECT COUNT(*) FROM coin_data;"
```

## 📚 详细文档

- **[技术实现](IMPLEMENTATION.md)** - 详细的技术实现说明

## 🔗 相关链接

- [系统架构](../../ARCHITECTURE.md)
- [部署指南](../../DEPLOYMENT.md)
- [系统维护](../../system/MAINTENANCE.md)

---

*最后更新: 2025-01-01*  
*维护者: DataBao团队*