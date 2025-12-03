'use client'

import { useEffect, useState } from 'react'

interface Recommendation {
  type: string
  bet: string
  probability: number
  confidence: string
  expectedValue?: number
}

interface RecommendedBetsDisplayProps {
  raceId: number
}

export default function RecommendedBetsDisplay({ raceId }: RecommendedBetsDisplayProps) {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchRecommendations() {
      try {
        setLoading(true)
        const response = await fetch('/api/predict', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ raceId })
        })

        const data = await response.json()
        setRecommendations(data.recommendations || [])
      } catch (error) {
        console.error('推奨券種取得エラー:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchRecommendations()
  }, [raceId])

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-gray-200 rounded w-1/4"></div>
          <div className="h-10 bg-gray-200 rounded"></div>
          <div className="h-10 bg-gray-200 rounded"></div>
          <div className="h-10 bg-gray-200 rounded"></div>
        </div>
      </div>
    )
  }

  if (recommendations.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-bold text-neutral-800 mb-4">📊 推奨購入券種</h3>
        <p className="text-gray-600 text-sm">推奨券種データがありません</p>
      </div>
    )
  }

  const getConfidenceBadge = (confidence: string) => {
    switch (confidence) {
      case '高':
        return 'bg-red-100 text-red-800 border-red-300'
      case '中':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300'
      case '低':
        return 'bg-blue-100 text-blue-800 border-blue-300'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300'
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h3 className="text-lg font-bold text-neutral-800 mb-4 flex items-center gap-2">
        📊 推奨購入券種
      </h3>

      <div className="space-y-3">
        {recommendations.map((rec, index) => (
          <div
            key={index}
            className="border border-gray-200 rounded-lg p-4 hover:border-[#3c71dd] hover:shadow-md transition-all"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {/* ランキング */}
                <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${
                  index === 0 ? 'bg-yellow-400 text-yellow-900' :
                  index === 1 ? 'bg-gray-300 text-gray-800' :
                  index === 2 ? 'bg-orange-300 text-orange-900' :
                  'bg-gray-200 text-gray-700'
                }`}>
                  {index + 1}
                </div>

                {/* 券種と買い目 */}
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="px-2 py-1 bg-[#3c71dd] text-white rounded text-xs font-bold">
                      {rec.type}
                    </span>
                    <span className="text-lg font-bold text-neutral-800">
                      {rec.bet}
                    </span>
                  </div>
                  <p className="text-xs text-gray-600">
                    的中確率: {(rec.probability * 100).toFixed(1)}%
                  </p>
                </div>
              </div>

              {/* 信頼度 */}
              <div className="text-right">
                <span className={`inline-block px-3 py-1 rounded-full text-xs font-bold border ${getConfidenceBadge(rec.confidence)}`}>
                  信頼度: {rec.confidence}
                </span>
              </div>
            </div>

            {/* プログレスバー */}
            <div className="mt-3">
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-gradient-to-r from-[#3c71dd] to-[#2d5dbd] h-2 rounded-full transition-all"
                  style={{ width: `${Math.min(rec.probability * 100, 100)}%` }}
                ></div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* 注意事項 */}
      <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
        <p className="text-xs text-yellow-900">
          <span className="font-bold">⚠️ 注意:</span> これらは統計的な予測であり、実際のレース結果を保証するものではありません。自己責任でご利用ください。
        </p>
      </div>
    </div>
  )
}
