# DataView 网络配置说明

## 🌐 局域网访问配置

DataView服务配置为支持局域网访问，使用固定IP地址 **192.168.5.124**。

### 网络架构

```
局域网设备 → 192.168.5.124:3000 → Next.js前端
                ↓
       192.168.5.124:8080 → FastAPI后端 → PostgreSQL数据库
```

### 配置文件

#### 1. Next.js配置 (`frontend/next.config.ts`)

```typescript
const nextConfig: NextConfig = {
  // 🌐 局域网访问配置 - DataBao服务器固定IP
  // 这个IP地址是DataBao系统的专用局域网地址，不是localhost
  allowedDevOrigins: ['192.168.5.124'],

  async rewrites() {
    return [
      {
        source: '/api/:path*',
        // 🔗 API代理指向DataBao服务器局域网地址，不是localhost
        destination: 'http://192.168.5.124:8080/api/:path*',
      },
    ]
  },
}
```

#### 2. 服务启动配置

```bash
# 后端API (绑定所有网络接口)
uvicorn src.main:app --host 0.0.0.0 --port 8080

# 前端Web (绑定所有网络接口)
npm run dev -- --hostname 0.0.0.0
```

### 访问地址

| 服务 | 本地访问 | 局域网访问 | 说明 |
|------|----------|------------|------|
| 前端界面 | http://localhost:3000 | **http://192.168.5.124:3000** | 推荐使用局域网地址 |
| API文档 | http://localhost:8080/docs | **http://192.168.5.124:8080/docs** | FastAPI Swagger文档 |
| API端点 | http://localhost:8080/api/v1 | **http://192.168.5.124:8080/api/v1** | REST API |

### 重要特性

1. **跨域支持**: Next.js配置了`allowedDevOrigins`支持从192.168.5.124访问
2. **API代理**: 前端请求自动代理到192.168.5.124:8080
3. **网络绑定**: 所有服务使用`--host 0.0.0.0`绑定所有网络接口
4. **图片服务**: 智能图片组件支持后端图片API

### 测试连接

```bash
# 测试后端API
curl http://192.168.5.124:8080/api/v1/coins/bitcoin

# 测试前端访问
curl -w "响应时间: %{time_total}s\n" http://192.168.5.124:3000
```

### 故障排除

如果无法访问192.168.5.124地址：

1. **检查IP地址**: 确认服务器实际IP是否为192.168.5.124
2. **防火墙设置**: 确保端口3000和8080开放
3. **服务绑定**: 确认服务使用`--host 0.0.0.0`启动
4. **网络连接**: 确认客户端和服务器在同一局域网

### 配置修改

如需修改IP地址，需要更新：
- `frontend/next.config.ts`: 更新`allowedDevOrigins`和`destination`
- `/databao/CLAUDE.md`: 更新文档中的IP地址
- 启动脚本中的hostname参数

---
*配置日期: 2025-09-20*
*说明: 此配置专门为局域网访问优化，不是标准的localhost配置*