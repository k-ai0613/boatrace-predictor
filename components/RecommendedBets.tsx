'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { TrendingUp } from 'lucide-react'
import { Recommendation } from '@/types'

interface RecommendedBetsProps {
  recommendations: Recommendation[]
}

export default function RecommendedBets({
  recommendations
}: RecommendedBetsProps) {
  // 券種ごとにグループ化
  const groupedRecs = recommendations.reduce((acc, rec) => {
    if (!acc[rec.type]) {
      acc[rec.type] = []
    }
    acc[rec.type].push(rec)
    return acc
  }, {} as Record<string, Recommendation[]>)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="w-5 h-5" />
          推奨購入券種
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {Object.entries(groupedRecs).map(([type, recs]) => (
            <div key={type}>
              <h3 className="text-lg font-semibold mb-3">{type}</h3>
              <div className="space-y-2">
                {recs.slice(0, 5).map((rec, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-2xl font-bold text-blue-600">
                        {rec.bet}
                      </span>
                      <Badge variant={getConfidenceBadgeVariant(rec.confidence)}>
                        信頼度: {rec.confidence}
                      </Badge>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-gray-600">確率</p>
                      <p className="text-xl font-bold">
                        {(rec.probability * 100).toFixed(1)}%
                      </p>
                      {rec.expectedValue && (
                        <p className="text-sm text-green-600">
                          期待値: {rec.expectedValue.toFixed(2)}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

function getConfidenceBadgeVariant(confidence: string): "default" | "secondary" | "outline" {
  if (confidence === '高') return 'default'
  if (confidence === '中') return 'secondary'
  return 'outline'
}
