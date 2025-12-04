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

      // 強化版Pythonスクリプトを実行して予測を生成＆DBに保存
      console.log(`Running enhanced Python prediction for race ${raceId}...`)

      execSync(
        `${pythonCommand} ml/predict_race_enhanced.py ${raceId} --quiet`,
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

function calculateRecommendations(predictions: any[]): any {
  const recommendations: any = {
    tansho: [],      // 単勝
    nirenpuku: [],   // 2連複
    nirentan: [],    // 2連単
    sanrenpuku: [],  // 3連複
    sanrentan: []    // 3連単
  }

  // 単勝（全艇）
  const sortedByWin = [...predictions].sort((a, b) => b.winProb - a.winProb)
  for (const pred of sortedByWin) {
    recommendations.tansho.push({
      boat: pred.boatNumber,
      prob: pred.winProb,
      confidence: pred.winProb > 0.4 ? '高' : pred.winProb > 0.3 ? '中' : '低'
    })
  }

  // 2連単（上位組み合わせ）
  const nirentanList: any[] = []
  for (let i = 0; i < 6; i++) {
    for (let j = 0; j < 6; j++) {
      if (i !== j) {
        const prob = predictions[i].winProb * predictions[j].secondProb
        nirentanList.push({
          combo: `${predictions[i].boatNumber}-${predictions[j].boatNumber}`,
          prob: prob,
          confidence: prob > 0.12 ? '高' : prob > 0.08 ? '中' : '低'
        })
      }
    }
  }
  nirentanList.sort((a, b) => b.prob - a.prob)
  recommendations.nirentan = nirentanList.slice(0, 10)

  // 2連複（上位組み合わせ）
  const nirenpukuList: any[] = []
  for (let i = 0; i < 6; i++) {
    for (let j = i + 1; j < 6; j++) {
      const prob = predictions[i].winProb * predictions[j].secondProb +
                   predictions[j].winProb * predictions[i].secondProb
      nirenpukuList.push({
        combo: `${Math.min(predictions[i].boatNumber, predictions[j].boatNumber)}=${Math.max(predictions[i].boatNumber, predictions[j].boatNumber)}`,
        prob: prob,
        confidence: prob > 0.15 ? '高' : prob > 0.10 ? '中' : '低'
      })
    }
  }
  nirenpukuList.sort((a, b) => b.prob - a.prob)
  recommendations.nirenpuku = nirenpukuList.slice(0, 10)

  // 3連単（上位組み合わせ）
  const sanrentanList: any[] = []
  for (let i = 0; i < 6; i++) {
    for (let j = 0; j < 6; j++) {
      if (j === i) continue
      for (let k = 0; k < 6; k++) {
        if (k === i || k === j) continue
        const prob = predictions[i].winProb * predictions[j].secondProb * predictions[k].thirdProb
        sanrentanList.push({
          combo: `${predictions[i].boatNumber}-${predictions[j].boatNumber}-${predictions[k].boatNumber}`,
          prob: prob,
          confidence: prob > 0.05 ? '高' : prob > 0.02 ? '中' : '低'
        })
      }
    }
  }
  sanrentanList.sort((a, b) => b.prob - a.prob)
  recommendations.sanrentan = sanrentanList.slice(0, 10)

  // 3連複（上位組み合わせ）
  const sanrenpukuList: any[] = []
  for (let i = 0; i < 6; i++) {
    for (let j = i + 1; j < 6; j++) {
      for (let k = j + 1; k < 6; k++) {
        // 全順列の確率合計
        let prob = 0
        const boats = [predictions[i], predictions[j], predictions[k]]
        const perms = [[0,1,2], [0,2,1], [1,0,2], [1,2,0], [2,0,1], [2,1,0]]
        for (const perm of perms) {
          prob += boats[perm[0]].winProb * boats[perm[1]].secondProb * boats[perm[2]].thirdProb
        }
        const sortedBoats = [predictions[i].boatNumber, predictions[j].boatNumber, predictions[k].boatNumber].sort((a,b) => a-b)
        sanrenpukuList.push({
          combo: `${sortedBoats[0]}=${sortedBoats[1]}=${sortedBoats[2]}`,
          prob: prob,
          confidence: prob > 0.08 ? '高' : prob > 0.04 ? '中' : '低'
        })
      }
    }
  }
  sanrenpukuList.sort((a, b) => b.prob - a.prob)
  recommendations.sanrenpuku = sanrenpukuList.slice(0, 10)

  return recommendations
}
