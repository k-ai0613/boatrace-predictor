'use client'

import { useState, useEffect } from 'react'
import { getWeatherData, getPredictions, generateAIComment } from '@/lib/predictions'
import { VENUES, WeatherData } from '@/types'

interface RacePredictionProps {
  venueId: number
  date: string
  raceNumber: number
}

interface PredictionData {
  boatNumber: number
  racerName: string
  racerNumber: number
  grade: string
  motorNumber: string
  winProb: number
  secondProb: number
  thirdProb: number
  fourthProb: number
  fifthProb: number
  sixthProb: number
}

interface Recommendation {
  type: string
  bet: string
  probability: number
  confidence: string
}

export default function RacePrediction({ venueId, date, raceNumber }: RacePredictionProps) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [predictions, setPredictions] = useState<PredictionData[]>([])
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [weather, setWeather] = useState<WeatherData | null>(null)
  const [aiComment, setAiComment] = useState<string>('')

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true)
        setError(null)

        // レースデータ取得（API経由）
        const response = await fetch(`/api/races?venue_id=${venueId}&date=${date}&race_number=${raceNumber}`)
        if (!response.ok) {
          throw new Error('レースデータの取得に失敗しました')
        }
        const race = await response.json()

        if (!race) {
          setError('指定されたレースが見つかりません')
          return
        }

        // 天候データ取得
        const weatherData = await getWeatherData(venueId, date)
        setWeather(weatherData)

        // 予測データ取得
        const predictionResult = await getPredictions(race.id)
        setPredictions(predictionResult.predictions)
        setRecommendations(predictionResult.recommendations || [])

        // AIコメント生成
        const venueName = VENUES[venueId]?.name || ''
        const comment = generateAIComment(weatherData, venueName)
        setAiComment(comment)

      } catch (err) {
        console.error('データ取得エラー:', err)
        setError('データの取得に失敗しました')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [venueId, date, raceNumber])

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-[#3c71dd] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600 text-sm">予測データを読み込み中...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <p className="text-red-700 text-sm">{error}</p>
      </div>
    )
  }

  const sortedPredictions = [...predictions].sort((a, b) => b.winProb - a.winProb)
  const venue = VENUES[venueId]

  // 着順予想計算
  const top3 = sortedPredictions.slice(0, 3)
  const exacta = top3.length >= 2 ? `${top3[0].boatNumber}-${top3[1].boatNumber}` : '-'
  const trifecta = top3.length >= 3 ? `${top3[0].boatNumber}-${top3[1].boatNumber}-${top3[2].boatNumber}` : '-'
  const quinella = top3.length >= 2 ? `${Math.min(top3[0].boatNumber, top3[1].boatNumber)}-${Math.max(top3[0].boatNumber, top3[1].boatNumber)}` : '-'
  const trio = top3.length >= 3 ? [top3[0].boatNumber, top3[1].boatNumber, top3[2].boatNumber].sort((a, b) => a - b).join('-') : '-'

  return (
    <div className="space-y-6">
      {/* レース情報ヘッダー */}
      <div className="bg-white border-b-4 border-[#3c71dd] rounded-lg p-6">
        <h2 className="text-2xl font-bold text-neutral-900 mb-2">
          {venue?.name} {raceNumber}R
        </h2>
        <p className="text-sm text-gray-600">
          {date} / {venue?.prefecture} / {venue?.region}
        </p>
      </div>

      {/* 推奨買い目 */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-bold text-neutral-800 mb-4 border-b pb-2">推奨買い目</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="border rounded-lg p-4">
            <p className="text-xs text-gray-600 mb-1">単勝</p>
            <p className="text-3xl font-bold text-[#3c71dd]">{top3[0]?.boatNumber || '-'}</p>
            <p className="text-xs text-gray-500 mt-1">1着予想</p>
          </div>
          <div className="border rounded-lg p-4">
            <p className="text-xs text-gray-600 mb-1">2連単</p>
            <p className="text-2xl font-bold text-[#3c71dd]">{exacta}</p>
            <p className="text-xs text-gray-500 mt-1">1-2着順</p>
          </div>
          <div className="border rounded-lg p-4">
            <p className="text-xs text-gray-600 mb-1">3連単</p>
            <p className="text-2xl font-bold text-[#3c71dd]">{trifecta}</p>
            <p className="text-xs text-gray-500 mt-1">1-2-3着順</p>
          </div>
          <div className="border rounded-lg p-4">
            <p className="text-xs text-gray-600 mb-1">2連複</p>
            <p className="text-2xl font-bold text-[#3c71dd]">{quinella}</p>
            <p className="text-xs text-gray-500 mt-1">1-2着（順不同）</p>
          </div>
          <div className="border rounded-lg p-4">
            <p className="text-xs text-gray-600 mb-1">3連複</p>
            <p className="text-2xl font-bold text-[#3c71dd]">{trio}</p>
            <p className="text-xs text-gray-500 mt-1">1-2-3着（順不同）</p>
          </div>
        </div>
      </div>

      {/* 天候情報 */}
      {weather && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-bold text-neutral-800 mb-4 border-b pb-2">気象条件</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="border rounded-lg p-3">
              <p className="text-xs text-gray-600 mb-1">気温</p>
              <p className="text-xl font-bold text-neutral-900">{weather.temperature || '-'}°C</p>
            </div>
            <div className="border rounded-lg p-3">
              <p className="text-xs text-gray-600 mb-1">風速</p>
              <p className="text-xl font-bold text-neutral-900">{weather.wind_speed || '-'}m/s</p>
            </div>
            <div className="border rounded-lg p-3">
              <p className="text-xs text-gray-600 mb-1">風向</p>
              <p className="text-xl font-bold text-neutral-900">{weather.wind_direction_text || '-'}</p>
            </div>
            <div className="border rounded-lg p-3">
              <p className="text-xs text-gray-600 mb-1">水温</p>
              <p className="text-xl font-bold text-neutral-900">{weather.water_temperature || '-'}°C</p>
            </div>
          </div>
        </div>
      )}

      {/* 分析コメント */}
      {aiComment && (
        <div className="bg-white border-l-4 border-[#3c71dd] rounded-lg p-6">
          <h3 className="text-lg font-bold text-neutral-800 mb-3">レース分析</h3>
          <p className="text-sm text-gray-700 leading-relaxed">{aiComment}</p>
        </div>
      )}

      {/* 予測結果 */}
      <div className="space-y-4">
        <h3 className="text-lg font-bold text-neutral-800 border-b pb-2">着順確率予測</h3>

        {sortedPredictions.map((pred, index) => (
          <div key={pred.boatNumber} className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-4">
                <div
                  className={`w-14 h-14 rounded-full flex items-center justify-center text-white font-bold text-xl ${
                    pred.boatNumber === 1 ? 'bg-white text-black border-2 border-black' :
                    pred.boatNumber === 2 ? 'bg-black' :
                    pred.boatNumber === 3 ? 'bg-red-600' :
                    pred.boatNumber === 4 ? 'bg-blue-600' :
                    pred.boatNumber === 5 ? 'bg-yellow-500' :
                    'bg-green-600'
                  }`}
                >
                  {pred.boatNumber}
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <p className="text-lg font-bold text-neutral-800">{pred.racerName}</p>
                    <span className={`px-2 py-0.5 rounded text-xs font-bold text-white ${
                      pred.grade === 'A1' ? 'bg-red-600' :
                      pred.grade === 'A2' ? 'bg-orange-500' :
                      pred.grade === 'B1' ? 'bg-blue-500' :
                      'bg-gray-500'
                    }`}>
                      {pred.grade}
                    </span>
                    {index === 0 && <span className="text-yellow-600 font-bold">◎</span>}
                    {index === 1 && <span className="text-gray-600 font-bold">○</span>}
                    {index === 2 && <span className="text-gray-500 font-bold">▲</span>}
                  </div>
                  <p className="text-xs text-gray-600">
                    登録: {pred.racerNumber} / モーター: {pred.motorNumber}
                  </p>
                </div>
              </div>

              <div className="text-right">
                <p className="text-xs text-gray-600 mb-1">1着確率</p>
                <p className="text-3xl font-bold text-[#3c71dd]">
                  {(pred.winProb * 100).toFixed(1)}%
                </p>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-2 text-xs">
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-gray-600">1着</span>
                  <span className="font-semibold">{(pred.winProb * 100).toFixed(1)}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded h-1.5">
                  <div className="bg-blue-500 h-1.5 rounded" style={{ width: `${pred.winProb * 100}%` }}></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-gray-600">2着</span>
                  <span className="font-semibold">{(pred.secondProb * 100).toFixed(1)}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded h-1.5">
                  <div className="bg-red-500 h-1.5 rounded" style={{ width: `${pred.secondProb * 100}%` }}></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-gray-600">3着</span>
                  <span className="font-semibold">{(pred.thirdProb * 100).toFixed(1)}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded h-1.5">
                  <div className="bg-green-500 h-1.5 rounded" style={{ width: `${pred.thirdProb * 100}%` }}></div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
