import type { Metadata } from 'next'
import { Inter, JetBrains_Mono } from 'next/font/google'
import './globals.css'

const inter = Inter({ 
  subsets: ['latin'],
  variable: '--font-sans'
})

const jetbrainsMono = JetBrains_Mono({ 
  subsets: ['latin'],
  variable: '--font-mono'
})

export const metadata: Metadata = {
  title: 'DataBao - 加密货币数据分析平台',
  description: 'DataBao 提供专业的加密货币数据分析、实时价格监控和技术指标展示',
  keywords: '加密货币, 比特币, 以太坊, 数据分析, 技术指标, 实时价格',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN" className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <body className="min-h-screen bg-gray-50 antialiased">
        <div className="flex min-h-screen flex-col">
          {/* 头部导航 */}
          <header className="sticky top-0 z-50 w-full border-b bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/60">
            <div className="container flex h-16 items-center justify-between">
              <div className="flex items-center space-x-4">
                <a href="/" className="flex items-center space-x-2">
                  <div className="rounded-lg bg-crypto-blue p-2">
                    <span className="text-lg font-bold text-white">DB</span>
                  </div>
                  <span className="text-xl font-bold text-gray-900">DataBao</span>
                </a>
              </div>
              
              <nav className="flex items-center space-x-6">
                <a 
                  href="/" 
                  className="text-sm font-medium text-gray-900 hover:text-crypto-blue transition-colors"
                >
                  市场概览
                </a>
                <a 
                  href="/coin/bitcoin" 
                  className="text-sm font-medium text-gray-600 hover:text-crypto-blue transition-colors"
                >
                  币种分析
                </a>
                <a 
                  href="http://localhost:9527" 
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-medium text-gray-600 hover:text-crypto-blue transition-colors"
                >
                  系统监控
                </a>
              </nav>
            </div>
          </header>

          {/* 主内容区域 */}
          <main className="flex-1">
            {children}
          </main>

          {/* 底部状态栏 */}
          <footer className="border-t bg-white">
            <div className="container flex h-12 items-center justify-between text-sm text-gray-600">
              <div className="flex items-center space-x-4">
                <span>数据来源: DataBao Platform</span>
                <div className="flex items-center space-x-1">
                  <div className="h-2 w-2 rounded-full bg-green-500"></div>
                  <span>实时更新</span>
                </div>
              </div>
              <div className="text-xs">
                © 2024 DataBao Team. All rights reserved.
              </div>
            </div>
          </footer>
        </div>
      </body>
    </html>
  )
}