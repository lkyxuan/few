'use client'

import { useState } from 'react'
import Image from 'next/image'

interface CoinImageProps {
  coinId: string
  coinName: string
  size?: number
  className?: string
}

export function CoinImage({ coinId, coinName, size = 32, className = "" }: CoinImageProps) {
  const [imageLoaded, setImageLoaded] = useState(true)
  const [isLoading, setIsLoading] = useState(true)

  // 如果图片加载失败，隐藏整个图片组件
  if (!imageLoaded) {
    return null
  }

  const imageUrl = `/api/v1/images/coin/${coinId}`

  return (
    <div className={`relative ${className}`} style={{ width: size, height: size }}>
      {isLoading && (
        <div
          className="absolute inset-0 bg-gray-200 rounded-full animate-pulse"
          style={{ width: size, height: size }}
        />
      )}
      <Image
        src={imageUrl}
        alt={coinName}
        width={size}
        height={size}
        className="rounded-full"
        onLoadingComplete={() => setIsLoading(false)}
        onError={() => {
          setIsLoading(false)
          setImageLoaded(false)
        }}
        priority={false}
      />
    </div>
  )
}