'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { PredictionDisplay as PredictionData } from '@/types'
import { getBoatColor } from '@/lib/utils'

interface PredictionDisplayProps {
  predictions: PredictionData[]
  weather?: {
    temperature: number
    windSpeed: number
    windDirection: string
  }
}

export default function PredictionDisplay({
  predictions,
  weather
}: PredictionDisplayProps) {
  // 1着確率でソート
  const sortedPredictions = [...predictions].sort(
    (a, b) => b.winProb - a.winProb
  )

  return (
    <div className="space-y-6">
      {/* 天気情報 */}
      {weather && (
        <Card>
          <CardHeader>
            <CardTitle>気象条件</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-6">
              <div>
                <p className="text-sm text-gray-600">気温</p>
                <p className="text-2xl font-bold">{weather.temperature}°C</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">風速</p>
                <p className="text-2xl font-bold">{weather.windSpeed}m/s</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">風向き</p>
                <p className="text-2xl font-bold">{weather.windDirection}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 予測結果 */}
      <div className="space-y-4">
        <h2 className="text-2xl font-bold">着順確率予測</h2>

        {sortedPredictions.map((pred, index) => (
          <Card key={pred.boatNumber} className="hover:shadow-lg transition-shadow">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between mb-4">
                {/* 艇番と選手情報 */}
                <div className="flex items-center gap-4">
                  <div
                    className={`
                      text-4xl font-bold w-16 h-16 rounded-full
                      flex items-center justify-center
                      ${getBoatColor(pred.boatNumber)}
                    `}
                  >
                    {pred.boatNumber}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="text-xl font-semibold">{pred.racerName}</p>
                      <Badge variant={getGradeBadgeVariant(pred.grade)}>
                        {pred.grade}
                      </Badge>
                    </div>
                    <p className="text-sm text-gray-600">
                      登録: {pred.racerNumber} / モーター: {pred.motorNumber}
                    </p>
                  </div>
                </div>

                {/* 1着確率 */}
                <div className="text-right">
                  <p className="text-sm text-gray-600">1着確率</p>
                  <p className="text-4xl font-bold text-blue-600">
                    {(pred.winProb * 100).toFixed(1)}%
                  </p>
                  {index === 0 && (
                    <Badge className="mt-2" variant="default">
                      本命
                    </Badge>
                  )}
                </div>
              </div>

              {/* 確率バー */}
              <div className="space-y-2">
                <ProbabilityBar
                  label="1着"
                  probability={pred.winProb}
                  color="blue"
                />
                <ProbabilityBar
                  label="2着"
                  probability={pred.secondProb}
                  color="red"
                />
                <ProbabilityBar
                  label="3着"
                  probability={pred.thirdProb}
                  color="green"
                />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

function ProbabilityBar({
  label,
  probability,
  color
}: {
  label: string
  probability: number
  color: string
}) {
  const percentage = probability * 100

  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-600">{label}</span>
        <span className="font-semibold">{percentage.toFixed(1)}%</span>
      </div>
      <Progress
        value={percentage}
        className={`h-2`}
      />
    </div>
  )
}

function getGradeBadgeVariant(grade: string): "default" | "secondary" | "outline" {
  if (grade === 'A1') return 'default'
  if (grade === 'A2') return 'secondary'
  return 'outline'
}
