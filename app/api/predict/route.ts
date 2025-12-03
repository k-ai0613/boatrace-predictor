import { NextRequest, NextResponse } from 'next/server'
import { createServerClient } from '@/lib/supabase'

export async function POST(request: NextRequest) {
  try {
    const { raceId } = await request.json()

    if (!raceId) {
      return NextResponse.json(
        { error: 'Race ID is required' },
        { status: 400 }
      )
    }

    const supabase = createServerClient()

    if (!supabase) {
      return NextResponse.json(
        { error: 'データベース接続が設定されていません' },
        { status: 503 }
      )
    }

    // 1. レースエントリーデータ取得
    const { data: entries, error: entriesError } = await supabase
      .from('race_entries')
      .select('*')
      .eq('race_id', raceId)
      .order('boat_number', { ascending: true })

    if (entriesError) {
      console.error('Race entries fetch error:', entriesError)
      return NextResponse.json(
        { error: 'Failed to fetch race data' },
        { status: 500 }
      )
    }

    if (!entries || entries.length === 0) {
      return NextResponse.json(
        { error: 'Race not found' },
        { status: 404 }
      )
    }

    // 選手データを個別に取得
    const raceData = await Promise.all(
      entries.map(async (entry) => {
        const { data: racer, error: racerError } = await supabase
          .from('racers')
          .select('*')
          .eq('id', entry.racer_id)
          .single()

        if (racerError) {
          console.error('Racer fetch error:', racerError)
          return { ...entry, racers: null }
        }

        return { ...entry, racers: racer }
      })
    )

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

    // 3. 新規予測の場合（Pythonモデルで予測を実行）
    try {
      const { execSync } = require('child_process')
      const pythonCommand = process.platform === 'win32' ? 'python' : 'python3'

      // Pythonスクリプトを実行して予測を生成＆DBに保存
      console.log(`Running Python prediction for race ${raceId}...`)

      execSync(
        `${pythonCommand} ml/predict_race.py ${raceId} --quiet`,
        {
          cwd: process.cwd(),
          encoding: 'utf-8',
          stdio: 'inherit'
        }
      )

      // DBから保存された予測を再取得
      const { data: newPredictions, error: newPredError } = await supabase
        .from('predictions')
        .select('*')
        .eq('race_id', raceId)

      if (newPredError || !newPredictions || newPredictions.length === 0) {
        throw new Error('Failed to retrieve predictions after generation')
      }

      const predictions = newPredictions.map(pred => ({
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
        recommendations,
        modelVersion: newPredictions[0]?.model_version || 'latest'
      })

    } catch (mlError) {
      console.error('ML prediction error:', mlError)

      // MLモデルが使用できない場合のフォールバック
      console.warn('Falling back to dummy predictions')

      const fallbackPredictions = raceData.map(entry => ({
        boatNumber: entry.boat_number,
        racerName: entry.racers?.name || 'Unknown',
        racerNumber: entry.racer_id,
        grade: entry.racers?.grade || 'B2',
        motorNumber: entry.motor_number?.toString() || 'N/A',
        winProb: 1.0 / 6.0,
        secondProb: 1.0 / 6.0,
        thirdProb: 1.0 / 6.0,
        fourthProb: 1.0 / 6.0,
        fifthProb: 1.0 / 6.0,
        sixthProb: 1.0 / 6.0,
      }))

      const recommendations = calculateRecommendations(fallbackPredictions)

      return NextResponse.json({
        predictions: fallbackPredictions,
        recommendations,
        warning: 'ML model unavailable, using uniform probability distribution',
        error: mlError instanceof Error ? mlError.message : 'Unknown error'
      })
    }

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
