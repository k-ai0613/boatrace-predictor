import { NextRequest, NextResponse } from 'next/server'
import { supabase } from '@/lib/supabase'

export async function POST(request: NextRequest) {
  try {
    const { raceId } = await request.json()

    if (!raceId) {
      return NextResponse.json(
        { error: 'Race ID is required' },
        { status: 400 }
      )
    }

    // 1. レースデータ取得
    const { data: raceData, error: raceError } = await supabase
      .from('race_entries')
      .select(`
        *,
        races(*),
        racers(*)
      `)
      .eq('race_id', raceId)

    if (raceError) {
      console.error('Race data fetch error:', raceError)
      return NextResponse.json(
        { error: 'Failed to fetch race data' },
        { status: 500 }
      )
    }

    if (!raceData || raceData.length === 0) {
      return NextResponse.json(
        { error: 'Race not found' },
        { status: 404 }
      )
    }

    // 2. 既存の予測結果をチェック
    const { data: existingPredictions, error: predError } = await supabase
      .from('predictions')
      .select('*')
      .eq('race_id', raceId)

    if (predError) {
      console.error('Prediction fetch error:', predError)
    }

    // 既存の予測がある場合はそれを返す
    if (existingPredictions && existingPredictions.length > 0) {
      const predictions = existingPredictions.map(pred => ({
        boatNumber: pred.boat_number,
        racerName: raceData.find(r => r.boat_number === pred.boat_number)?.racers?.name || 'Unknown',
        racerNumber: raceData.find(r => r.boat_number === pred.boat_number)?.racer_id || 0,
        grade: raceData.find(r => r.boat_number === pred.boat_number)?.racers?.grade || 'B2',
        motorNumber: raceData.find(r => r.boat_number === pred.boat_number)?.motor_number?.toString() || 'N/A',
        winProb: pred.predicted_win_prob || 0,
        secondProb: pred.predicted_second_prob || 0,
        thirdProb: pred.predicted_third_prob || 0,
        fourthProb: pred.predicted_fourth_prob || 0,
        fifthProb: pred.predicted_fifth_prob || 0,
        sixthProb: pred.predicted_sixth_prob || 0,
      }))

      const recommendations = calculateRecommendations(predictions)

      return NextResponse.json({
        predictions,
        recommendations
      })
    }

    // 3. 新規予測の場合（実際の機械学習モデルが必要）
    // ここでは簡易的なダミーデータを返す
    const dummyPredictions = raceData.map(entry => {
      // 簡易的な確率計算（実際はMLモデルを使用）
      const baseProb = Math.random() * 0.3
      const winProb = entry.boat_number === 1 ? 0.4 + baseProb : 0.1 + baseProb * 0.5

      return {
        boatNumber: entry.boat_number,
        racerName: entry.racers?.name || 'Unknown',
        racerNumber: entry.racer_id,
        grade: entry.racers?.grade || 'B2',
        motorNumber: entry.motor_number?.toString() || 'N/A',
        winProb: winProb,
        secondProb: 0.15 + Math.random() * 0.1,
        thirdProb: 0.15 + Math.random() * 0.1,
        fourthProb: 0.15 + Math.random() * 0.1,
        fifthProb: 0.10 + Math.random() * 0.1,
        sixthProb: 0.05 + Math.random() * 0.1,
      }
    })

    const recommendations = calculateRecommendations(dummyPredictions)

    return NextResponse.json({
      predictions: dummyPredictions,
      recommendations,
      note: 'This is dummy prediction data. ML model integration required.'
    })

  } catch (error) {
    console.error('Prediction error:', error)
    return NextResponse.json(
      { error: 'Prediction failed' },
      { status: 500 }
    )
  }
}

function calculateRecommendations(predictions: any[]): any[] {
  const recommendations = []

  // 単勝推奨
  for (const pred of predictions) {
    if (pred.winProb > 0.25) {
      recommendations.push({
        type: '単勝',
        bet: `${pred.boatNumber}`,
        probability: pred.winProb,
        confidence: pred.winProb > 0.4 ? '高' : pred.winProb > 0.3 ? '中' : '低'
      })
    }
  }

  // 2連単推奨（上位2艇の組み合わせ）
  const sortedByWin = [...predictions].sort((a, b) => b.winProb - a.winProb)
  for (let i = 0; i < Math.min(2, sortedByWin.length); i++) {
    for (let j = 0; j < Math.min(3, sortedByWin.length); j++) {
      if (i !== j) {
        const prob = sortedByWin[i].winProb * sortedByWin[j].secondProb
        if (prob > 0.08) {
          recommendations.push({
            type: '2連単',
            bet: `${sortedByWin[i].boatNumber}-${sortedByWin[j].boatNumber}`,
            probability: prob,
            confidence: prob > 0.15 ? '高' : prob > 0.10 ? '中' : '低'
          })
        }
      }
    }
  }

  // 確率でソート
  recommendations.sort((a, b) => b.probability - a.probability)

  return recommendations.slice(0, 10)
}
