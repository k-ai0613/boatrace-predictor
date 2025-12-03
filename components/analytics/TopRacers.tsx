'use client'

import { useEffect, useState } from 'react'

interface TopRacer {
  racer_id: number
  win_rate: number
  second_rate: number
  third_rate: number
  racers: {
    racer_number: number
    name: string
    grade: string
    branch: string
  }
}

export default function TopRacers() {
  const [racers, setRacers] = useState<TopRacer[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true)
        const response = await fetch('/api/analytics/top-racers?limit=20')
        if (!response.ok) {
          throw new Error('データの取得に失敗しました')
        }
        const data = await response.json()
        setRacers(data as TopRacer[])
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
          <p className="mt-2">選手成績データの取得に失敗しました。</p>
          <ul className="list-disc list-inside mt-2 space-y-1">
            <li>racer_statsテーブルにデータが存在するか確認してください</li>
            <li>racersテーブルとの結合が正しく行われているか確認してください</li>
          </ul>
        </details>
      </div>
    )
  }

  if (racers.length === 0) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 m-6">
        <h3 className="text-yellow-800 font-bold mb-2">📊 データがありません</h3>
        <p className="text-yellow-700 text-sm mb-4">
          選手成績データがまだ収集されていません。
        </p>
        <p className="text-yellow-600 text-xs">
          データ収集スクリプトを実行してください。
        </p>
      </div>
    )
  }

  return (
    <div className="p-6">
      <h2 className="text-lg font-bold text-neutral-800 mb-6">選手ランキング（勝率順）</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {racers.map((racer, index) => (
          <div
            key={racer.racer_id}
            className="bg-white rounded-lg shadow-md p-4 hover:shadow-lg transition-shadow"
          >
            <div className="flex items-center gap-4">
              {/* ランキング番号 */}
              <div className={`w-12 h-12 rounded-full flex items-center justify-center font-bold text-lg
                ${index < 3 ? 'bg-gradient-to-br from-yellow-400 to-yellow-600 text-white' : 'bg-gray-200 text-gray-700'}`}>
                {index + 1}
              </div>

              {/* 選手情報 */}
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-bold text-base text-neutral-800">{racer.racers.name}</span>
                  <span className={`px-2 py-0.5 rounded text-xs font-bold text-white
                    ${racer.racers.grade === 'A1' ? 'bg-red-600' :
                      racer.racers.grade === 'A2' ? 'bg-orange-500' :
                      racer.racers.grade === 'B1' ? 'bg-blue-500' :
                      'bg-gray-500'}`}>
                    {racer.racers.grade}
                  </span>
                </div>
                <div className="flex items-center gap-3 text-xs text-gray-600">
                  <span>登録番号: {racer.racers.racer_number}</span>
                  <span>{racer.racers.branch}</span>
                </div>
              </div>

              {/* 成績 */}
              <div className="text-right">
                <div className="text-2xl font-bold text-[#3c71dd]">
                  {racer.win_rate?.toFixed(2) ?? '-'}%
                </div>
                <div className="text-xs text-gray-500">勝率</div>
              </div>
            </div>

            {/* 詳細成績 */}
            <div className="mt-3 pt-3 border-t border-gray-200 flex gap-4 text-xs">
              <div className="flex-1 text-center">
                <div className="text-gray-500 mb-1">2連対率</div>
                <div className="font-bold text-gray-900">{racer.second_rate?.toFixed(2) ?? '-'}%</div>
              </div>
              <div className="flex-1 text-center">
                <div className="text-gray-500 mb-1">3連対率</div>
                <div className="font-bold text-gray-900">{racer.third_rate?.toFixed(2) ?? '-'}%</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
