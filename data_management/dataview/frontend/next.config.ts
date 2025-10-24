import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  turbopack: {
    resolveAlias: {
      underscore: 'lodash',
      mocha: { browser: 'mocha/browser-entry.js' },
    },
  },
  // 🌐 局域网访问配置 - DataBao服务器固定IP
  // 这个IP地址是DataBao系统的专用局域网地址，不是localhost
  allowedDevOrigins: ['192.168.5.124'],
  images: {
    // 移除外部图片域名配置，只使用本地后端API
    unoptimized: false,
  },
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

export default nextConfig