'use client'

import { useState } from 'react'

interface BetItem {
  combo?: string
  boat?: number
  prob: number
  confidence: string
}

interface Recommendations {
  tansho: BetItem[]
  nirenpuku: BetItem[]
  nirentan: BetItem[]
  sanrenpuku: BetItem[]
  sanrentan: BetItem[]
}

interface BetRecommendationsProps {
  recommendations: Recommendations
}

type BetType = 'tansho' | 'nirenpuku' | 'nirentan' | 'sanrenpuku' | 'sanrentan'

const BET_TYPE_INFO: Record<BetType, { name: string; description: string; icon: string }> = {
  tansho: { name: '単勝', description: '1着を当てる', icon: '1' },
  nirenpuku: { name: '2連複', description: '1-2着（順不同）', icon: '=' },
  nirentan: { name: '2連単', description: '1-2着（順番通り）', icon: '-' },
  sanrenpuku: { name: '3連複', description: '1-2-3着（順不同）', icon: '=' },
  sanrentan: { name: '3連単', description: '1-2-3着（順番通り）', icon: '-' },
}

export default function BetRecommendations({ recommendations }: BetRecommendationsProps) {
  const [selectedBetType, setSelectedBetType] = useState<BetType>('tansho')
  const [showAll, setShowAll] = useState(false)

  const betTypes: BetType[] = ['tansho', 'nirenpuku', 'nirentan', 'sanrenpuku', 'sanrentan']

  const getConfidenceColor = (confidence: string) => {
    switch (confidence) {
      case '高': return 'bg-red-100 text-red-700 border-red-200'
      case '中': return 'bg-yellow-100 text-yellow-700 border-yellow-200'
      default: return 'bg-gray-100 text-gray-700 border-gray-200'
    }
  }

  const getBoatColor = (boatNum: number) => {
    const colors: Record<number, string> = {
      1: 'bg-white text-black border-2 border-black',
      2: 'bg-black text-white',
      3: 'bg-red-600 text-white',
      4: 'bg-blue-600 text-white',
      5: 'bg-yellow-500 text-black',
      6: 'bg-green-600 text-white',
    }
    return colors[boatNum] || 'bg-gray-500 text-white'
  }

  const renderBetItem = (item: BetItem, index: number) => {
    const prob = item.prob * 100

    if (selectedBetType === 'tansho') {
      return (
        <div
          key={index}
          className="flex items-center justify-between p-3 bg-white rounded-lg border hover:shadow-md transition-shadow"
        >
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${getBoatColor(item.boat || 0)}`}>
              {item.boat}
            </div>
            <span className="text-lg font-bold">{item.boat}号艇</span>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-xl font-bold text-blue-600">{prob.toFixed(1)}%</p>
            </div>
            <span className={`px-2 py-1 text-xs font-bold rounded border ${getConfidenceColor(item.confidence)}`}>
              {item.confidence}
            </span>
          </div>
        </div>
      )
    }

    return (
      <div
        key={index}
        className="flex items-center justify-between p-3 bg-white rounded-lg border hover:shadow-md transition-shadow"
      >
        <div className="flex items-center gap-2">
          <span className="text-lg font-bold text-neutral-800 min-w-[80px]">{item.combo}</span>
          <div className="w-full bg-gray-200 rounded-full h-2 max-w-[100px] hidden sm:block">
            <div
              className="bg-blue-500 h-2 rounded-full"
              style={{ width: `${Math.min(prob * 3, 100)}%` }}
            ></div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className="text-lg font-bold text-blue-600">{prob.toFixed(2)}%</p>
          </div>
          <span className={`px-2 py-1 text-xs font-bold rounded border ${getConfidenceColor(item.confidence)}`}>
            {item.confidence}
          </span>
        </div>
      </div>
    )
  }

  const currentItems = recommendations[selectedBetType] || []
  const displayItems = showAll ? currentItems : currentItems.slice(0, 5)

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden">
      {/* タブ */}
      <div className="flex overflow-x-auto border-b bg-gray-50">
        {betTypes.map((type) => (
          <button
            key={type}
            onClick={() => {
              setSelectedBetType(type)
              setShowAll(false)
            }}
            className={`flex-shrink-0 px-4 py-3 text-sm font-medium transition-colors border-b-2 ${
              selectedBetType === type
                ? 'border-blue-600 text-blue-600 bg-white'
                : 'border-transparent text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            }`}
          >
            {BET_TYPE_INFO[type].name}
          </button>
        ))}
      </div>

      {/* 説明 */}
      <div className="px-4 py-3 bg-blue-50 border-b">
        <p className="text-sm text-blue-700">
          <span className="font-bold">{BET_TYPE_INFO[selectedBetType].name}</span>
          ：{BET_TYPE_INFO[selectedBetType].description}
        </p>
      </div>

      {/* リスト */}
      <div className="p-4 space-y-2">
        {displayItems.length > 0 ? (
          <>
            {displayItems.map((item, index) => renderBetItem(item, index))}

            {currentItems.length > 5 && (
              <button
                onClick={() => setShowAll(!showAll)}
                className="w-full py-2 text-sm text-blue-600 hover:text-blue-800 font-medium"
              >
                {showAll ? '折りたたむ' : `さらに表示 (${currentItems.length - 5}件)`}
              </button>
            )}
          </>
        ) : (
          <p className="text-center text-gray-500 py-4">予測データがありません</p>
        )}
      </div>

      {/* 信頼度の説明 */}
      <div className="px-4 py-3 bg-gray-50 border-t">
        <div className="flex items-center gap-4 text-xs text-gray-600">
          <span>信頼度:</span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded bg-red-200"></span>高
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded bg-yellow-200"></span>中
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded bg-gray-200"></span>低
          </span>
        </div>
      </div>
    </div>
  )
}
