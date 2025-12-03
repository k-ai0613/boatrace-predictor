import { supabase, isSupabaseAvailable } from './supabase'
import { Race, RaceEntry, Racer, WeatherData, Prediction } from '@/types'

// Supabaseが利用不可の場合のエラー
function checkSupabase() {
  if (!isSupabaseAvailable()) {
    throw new Error('データベース接続が設定されていません')
  }
}

// 未来のレース取得
export async function getUpcomingRaces(venueId?: number, date?: string) {
  checkSupabase()
  let query = supabase
    .from('races')
    .select(`
      *,
      race_entries(
        *,
        racers!racer_id(*)
      )
    `)
    .order('race_date', { ascending: true })
    .order('race_number', { ascending: true })

  if (venueId) {
    query = query.eq('venue_id', venueId)
  }

  if (date) {
    const startDate = new Date(date)
    const endDate = new Date(date)
    endDate.setDate(endDate.getDate() + 1)

    query = query
      .gte('race_date', startDate.toISOString().split('T')[0])
      .lt('race_date', endDate.toISOString().split('T')[0])
  } else {
    // 今日以降のレース
    const today = new Date().toISOString().split('T')[0]
    query = query.gte('race_date', today)
  }

  const { data, error } = await query.limit(50)

  if (error) throw error
  return data as (Race & { race_entries: (RaceEntry & { racer: Racer })[] })[]
}

// 特定のレース取得
export async function getRaceById(raceId: number) {
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
    .eq('id', raceId)
    .single()

  if (error) throw error
  return data as Race & { race_entries: (RaceEntry & { racer: Racer })[] }
}

// 開催場と日付からレース取得
export async function getRacesByVenueAndDate(venueId: number, date: string, raceNumber?: number) {
  checkSupabase()
  let query = supabase
    .from('races')
    .select(`
      *,
      race_entries(
        *,
        racers!racer_id(*)
      )
    `)
    .eq('venue_id', venueId)
    .eq('race_date', date)
    .order('race_number', { ascending: true })

  if (raceNumber) {
    query = query.eq('race_number', raceNumber)
  }

  const { data, error } = await query

  if (error) throw error

  if (raceNumber) {
    return data?.[0] as (Race & { race_entries: (RaceEntry & { racer: Racer })[] }) | null
  }

  return data as (Race & { race_entries: (RaceEntry & { racer: Racer })[] })[]
}

// 天候データ取得
export async function getWeatherData(venueId: number, date?: string) {
  checkSupabase()
  let query = supabase
    .from('weather_data')
    .select('*')
    .eq('venue_id', venueId)
    .order('record_datetime', { ascending: false })

  if (date) {
    const startDate = new Date(date)
    const endDate = new Date(date)
    endDate.setDate(endDate.getDate() + 1)

    query = query
      .gte('record_datetime', startDate.toISOString())
      .lt('record_datetime', endDate.toISOString())
  }

  const { data, error } = await query.limit(1)

  if (error) throw error
  return data?.[0] as WeatherData | null
}

// 予測データ取得（API経由）
export async function getPredictions(raceId: number) {
  const response = await fetch('/api/predict', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ raceId }),
  })

  if (!response.ok) {
    throw new Error('予測データの取得に失敗しました')
  }

  return await response.json()
}

// AIコメント生成
export function generateAIComment(
  weatherData: WeatherData | null,
  venueName: string
): string {
  const comments = []

  if (weatherData) {
    // 風速による影響
    if (weatherData.wind_speed > 5) {
      comments.push(`風速${weatherData.wind_speed}m/sの強風により、スタート展示との差が出やすい状況です。`)
    } else if (weatherData.wind_speed < 2) {
      comments.push(`風が穏やかで、選手の実力が出やすいコンディションです。`)
    }

    // 波高による影響
    if (weatherData.wave_height && weatherData.wave_height > 5) {
      comments.push(`波高${weatherData.wave_height}cmの荒れた水面で、艇の操縦技術が重要になります。`)
    }

    // 水温による影響
    if (weatherData.water_temperature) {
      if (weatherData.water_temperature < 15) {
        comments.push(`水温${weatherData.water_temperature}°Cと低く、モーター性能の差が出やすい状況です。`)
      } else if (weatherData.water_temperature > 25) {
        comments.push(`水温${weatherData.water_temperature}°Cと高く、パワーのある選手が有利です。`)
      }
    }
  }

  // 開催場別のコメント
  if (venueName.includes('江戸川') || venueName.includes('戸田')) {
    comments.push(`${venueName}は荒れやすい水面特性があります。`)
  } else if (venueName.includes('平和島') || venueName.includes('多摩川')) {
    comments.push(`${venueName}はインコース有利な傾向があります。`)
  }

  if (comments.length === 0) {
    return '標準的なレースコンディションです。各選手の実力通りの展開が予想されます。'
  }

  return comments.join(' ')
}
