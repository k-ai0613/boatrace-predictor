import { supabase, isSupabaseAvailable } from './supabase'
import { Racer, RacerStats, Race, RaceEntry, Prediction } from '@/types'

// Supabaseが利用不可の場合のエラー
function checkSupabase() {
  if (!isSupabaseAvailable()) {
    throw new Error('データベース接続が設定されていません')
  }
}

// 選手データの取得
export async function getRacers(limit: number = 50) {
  checkSupabase()
  const { data, error } = await supabase
    .from('racers')
    .select('*')
    .order('racer_number', { ascending: true })
    .limit(limit)

  if (error) throw error
  return data as Racer[]
}

// 選手成績データの取得
export async function getRacerStats(racerId?: number) {
  checkSupabase()
  let query = supabase
    .from('racer_stats')
    .select('*, racers!racer_id(*)')
    .order('stats_date', { ascending: false })

  if (racerId) {
    query = query.eq('racer_id', racerId)
  }

  const { data, error } = await query.limit(100)

  if (error) throw error
  return data
}

// レースデータの取得
export async function getRecentRaces(limit: number = 20) {
  checkSupabase()
  const { data, error } = await supabase
    .from('races')
    .select(`
      *,
      race_entries(
        *,
        racers!racer_id(*)
      )
    `)
    .order('race_date', { ascending: false })
    .limit(limit)

  if (error) throw error
  return data as (Race & { race_entries: (RaceEntry & { racer: Racer })[] })[]
}

// 予測データの取得
export async function getPredictionsByRaceId(raceId: number) {
  checkSupabase()
  const { data, error } = await supabase
    .from('predictions')
    .select('*')
    .eq('race_id', raceId)
    .order('boat_number', { ascending: true })

  if (error) throw error
  return data as Prediction[]
}

// コース別成績の集計
export async function getCourseStatistics() {
  checkSupabase()
  const { data, error } = await supabase
    .from('race_entries')
    .select('course, result_position')
    .not('course', 'is', null)
    .not('result_position', 'is', null)

  if (error) {
    console.error('コース別成績取得エラー:', error)
    throw new Error(`コース別成績の取得に失敗しました: ${error.message}`)
  }

  if (!data || data.length === 0) {
    console.warn('コース別成績データが存在しません')
    return []
  }

  // コース別の1着率を計算
  const courseStats = [1, 2, 3, 4, 5, 6].map(course => {
    const courseData = data.filter(entry => entry.course === course)
    const firstPlace = courseData.filter(entry => entry.result_position === 1).length
    const winRate = courseData.length > 0 ? (firstPlace / courseData.length) * 100 : 0

    return {
      course,
      totalRaces: courseData.length,
      firstPlace,
      winRate: Math.round(winRate * 10) / 10
    }
  })

  return courseStats
}

// 艇別成績の集計
export async function getBoatStatistics() {
  checkSupabase()
  const { data, error } = await supabase
    .from('race_entries')
    .select('boat_number, result_position')
    .not('boat_number', 'is', null)
    .not('result_position', 'is', null)

  if (error) {
    console.error('艇別成績取得エラー:', error)
    throw new Error(`艇別成績の取得に失敗しました: ${error.message}`)
  }

  if (!data || data.length === 0) {
    console.warn('艇別成績データが存在しません')
    return []
  }

  // 艇番別の1着率を計算
  const boatStats = [1, 2, 3, 4, 5, 6].map(boat => {
    const boatData = data.filter(entry => entry.boat_number === boat)
    const firstPlace = boatData.filter(entry => entry.result_position === 1).length
    const secondPlace = boatData.filter(entry => entry.result_position === 2).length
    const thirdPlace = boatData.filter(entry => entry.result_position === 3).length
    const winRate = boatData.length > 0 ? (firstPlace / boatData.length) * 100 : 0
    const placeRate = boatData.length > 0 ? ((firstPlace + secondPlace + thirdPlace) / boatData.length) * 100 : 0

    return {
      boatNumber: boat,
      totalRaces: boatData.length,
      firstPlace,
      secondPlace,
      thirdPlace,
      winRate: Math.round(winRate * 10) / 10,
      placeRate: Math.round(placeRate * 10) / 10
    }
  })

  return boatStats
}

// トップ選手の取得
export async function getTopRacers(limit: number = 10) {
  checkSupabase()
  const { data, error } = await supabase
    .from('racer_stats')
    .select('*, racers!racer_id(*)')
    .not('win_rate', 'is', null)
    .order('win_rate', { ascending: false })
    .limit(limit)

  if (error) throw error
  return data
}
