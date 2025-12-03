'use client'

import { useEffect, useState } from 'react'

interface BoatStat {
  boatNumber: number
  totalRaces: number
  firstPlace: number
  secondPlace: number
  thirdPlace: number
  winRate: number
  placeRate: number
}

export default function BoatStatistics() {
  const [stats, setStats] = useState<BoatStat[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true)
        const response = await fetch('/api/analytics/boats')
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
          <p className="mt-2">データベースに接続できないか、データが存在しない可能性があります。</p>
          <ul className="list-disc list-inside mt-2 space-y-1">
            <li>Supabaseの接続設定を確認してください</li>
            <li>race_entriesテーブルにデータが存在するか確認してください</li>
            <li>GitHub Actionsでデータ収集が実行されているか確認してください</li>
          </ul>
        </details>
      </div>
    )
  }

  if (stats.length === 0) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 m-6">
        <h3 className="text-yellow-800 font-bold mb-2">📊 データがありません</h3>
        <p className="text-yellow-700 text-sm mb-4">
          艇別成績データがまだ収集されていません。
        </p>
        <p className="text-yellow-600 text-xs">
          データ収集スクリプトを実行するか、GitHub Actionsが正常に動作しているか確認してください。
        </p>
      </div>
    )
  }

  return (
    <div className="p-6">
      <h2 className="text-lg font-bold text-neutral-800 mb-6">艇別成績統計</h2>

      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                艇番
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                総レース数
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                1着回数
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                2着回数
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                3着回数
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                勝率
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                連対率
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {stats.map((stat) => (
              <tr key={stat.boatNumber} className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white font-bold text-sm
                      ${stat.boatNumber === 1 ? 'bg-white text-black border-2 border-black' :
                        stat.boatNumber === 2 ? 'bg-black' :
                        stat.boatNumber === 3 ? 'bg-red-600' :
                        stat.boatNumber === 4 ? 'bg-blue-600' :
                        stat.boatNumber === 5 ? 'bg-yellow-500' :
                        'bg-green-600'}`}>
                      {stat.boatNumber}
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {stat.totalRaces.toLocaleString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {stat.firstPlace.toLocaleString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {stat.secondPlace.toLocaleString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {stat.thirdPlace.toLocaleString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center gap-2">
                    <div className="flex-1 bg-gray-200 rounded-full h-2 max-w-[100px]">
                      <div
                        className="bg-[#3c71dd] h-2 rounded-full transition-all"
                        style={{ width: `${Math.min(stat.winRate, 100)}%` }}
                      ></div>
                    </div>
                    <span className="text-sm font-medium text-gray-900 w-12 text-right">
                      {stat.winRate}%
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center gap-2">
                    <div className="flex-1 bg-gray-200 rounded-full h-2 max-w-[100px]">
                      <div
                        className="bg-green-500 h-2 rounded-full transition-all"
                        style={{ width: `${Math.min(stat.placeRate, 100)}%` }}
                      ></div>
                    </div>
                    <span className="text-sm font-medium text-gray-900 w-12 text-right">
                      {stat.placeRate}%
                    </span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
