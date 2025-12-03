'use client'

import { useEffect, useState } from 'react'

interface CourseStat {
  course: number
  totalRaces: number
  firstPlace: number
  winRate: number
}

export default function CourseAnalysis() {
  const [stats, setStats] = useState<CourseStat[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true)
        const response = await fetch('/api/analytics/course')
        if (!response.ok) {
          throw new Error('データの取得に失敗しました')
        }
        const data = await response.json()
        setStats(data)
      } catch (err) {
        console.error('データ取得エラー:', err)
        setError('データの取得に失敗しました')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-[#3c71dd] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600 text-sm">データを読み込み中...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 m-6">
        <h3 className="text-red-800 font-bold mb-2">エラーが発生しました</h3>
        <p className="text-red-700 text-sm mb-4">{error}</p>
        <details className="text-xs text-red-600">
          <summary className="cursor-pointer font-semibold">詳細情報</summary>
          <p className="mt-2">コース別成績データの取得に失敗しました。</p>
        </details>
      </div>
    )
  }

  if (stats.length === 0) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 m-6">
        <h3 className="text-yellow-800 font-bold mb-2">📊 データがありません</h3>
        <p className="text-yellow-700 text-sm mb-4">
          コース別成績データがまだ収集されていません。
        </p>
        <p className="text-yellow-600 text-xs">
          レース結果データを収集してください。
        </p>
      </div>
    )
  }

  const maxRate = Math.max(...stats.map(s => s.winRate))

  return (
    <div className="p-6">
      <h2 className="text-lg font-bold text-neutral-800 mb-6">コース別勝率分析</h2>

      {/* グラフ表示 */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <div className="space-y-4">
          {stats.map((stat) => (
            <div key={stat.course} className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium text-gray-700">
                  {stat.course}コース
                </span>
                <span className="text-gray-600">
                  {stat.firstPlace.toLocaleString()}勝 / {stat.totalRaces.toLocaleString()}走
                </span>
              </div>
              <div className="relative">
                <div className="flex items-center gap-2">
                  <div className="flex-1 bg-gray-200 rounded-full h-8 overflow-hidden">
                    <div
                      className={`h-8 rounded-full transition-all flex items-center justify-end pr-3 text-white font-bold text-sm
                        ${stat.course === 1 ? 'bg-gradient-to-r from-blue-500 to-blue-600' :
                          stat.course === 2 ? 'bg-gradient-to-r from-green-500 to-green-600' :
                          stat.course === 3 ? 'bg-gradient-to-r from-yellow-500 to-yellow-600' :
                          stat.course === 4 ? 'bg-gradient-to-r from-orange-500 to-orange-600' :
                          stat.course === 5 ? 'bg-gradient-to-r from-red-500 to-red-600' :
                          'bg-gradient-to-r from-purple-500 to-purple-600'}`}
                      style={{ width: `${(stat.winRate / maxRate) * 100}%` }}
                    >
                      {stat.winRate > 5 && `${stat.winRate}%`}
                    </div>
                  </div>
                  <span className="text-lg font-bold text-gray-900 w-16 text-right">
                    {stat.winRate}%
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 統計サマリー */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {stats.map((stat) => (
          <div key={`summary-${stat.course}`} className="bg-white rounded-lg shadow-md p-4">
            <div className="text-center">
              <div className={`w-12 h-12 rounded-full mx-auto mb-2 flex items-center justify-center text-white font-bold text-lg
                ${stat.course === 1 ? 'bg-blue-600' :
                  stat.course === 2 ? 'bg-green-600' :
                  stat.course === 3 ? 'bg-yellow-600' :
                  stat.course === 4 ? 'bg-orange-600' :
                  stat.course === 5 ? 'bg-red-600' :
                  'bg-purple-600'}`}>
                {stat.course}
              </div>
              <div className="text-2xl font-bold text-[#3c71dd] mb-1">
                {stat.winRate}%
              </div>
              <div className="text-xs text-gray-600">
                {stat.firstPlace}勝 / {stat.totalRaces}走
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* 分析コメント */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="font-bold text-blue-900 mb-2 text-sm">分析ポイント</h3>
        <ul className="space-y-1 text-xs text-blue-800">
          <li>• 1コースの勝率が最も高い傾向があります</li>
          <li>• インコースほど有利な競艇の特性が反映されています</li>
          <li>• ただし、場によってはアウトコースの勝率が高い場合もあります</li>
        </ul>
      </div>
    </div>
  )
}
