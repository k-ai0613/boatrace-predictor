// レース基本情報
export interface Race {
  id: number
  race_date: string
  venue_id: number
  race_number: number
  grade?: string
  created_at: string
}

// 選手情報
export interface Racer {
  id: number
  racer_number: number
  name: string
  grade?: string
  branch?: string
  birth_date?: string
  updated_at: string
}

// 出走情報
export interface RaceEntry {
  id: number
  race_id: number
  boat_number: number
  racer_id: number
  motor_number?: number
  start_timing?: number
  course?: number
  result_position?: number
  created_at: string
  racer?: Racer
}

// 選手成績
export interface RacerStats {
  id: number
  racer_id: number
  stats_date: string
  win_rate?: number
  second_rate?: number
  third_rate?: number
  avg_start_timing?: number
  venue_id?: number
  created_at: string
}

// モーター情報
export interface Motor {
  id: number
  venue_id: number
  motor_number: number
  year: number
  second_rate?: number
  third_rate?: number
  created_at: string
}

// 天気データ
export interface WeatherData {
  id: number
  venue_id: number
  record_datetime: string
  temperature?: number
  humidity?: number
  pressure?: number
  wind_speed: number
  wind_direction?: number
  wind_direction_text?: string
  wave_height?: number
  water_temperature?: number
  weather_condition?: string
  source?: string
  is_realtime: boolean
  created_at: string
}

// 予測結果
export interface Prediction {
  id: number
  race_id: number
  boat_number: number
  predicted_win_prob?: number
  predicted_second_prob?: number
  predicted_third_prob?: number
  predicted_fourth_prob?: number
  predicted_fifth_prob?: number
  predicted_sixth_prob?: number
  model_version?: string
  created_at: string
}

// フロントエンド用の予測表示データ
export interface PredictionDisplay {
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

// 推奨券種
export interface Recommendation {
  type: string
  bet: string
  probability: number
  confidence: string
  expectedValue?: number
}

// ボートレース場マスタ
export interface Venue {
  id: number
  name: string
  prefecture: string
  region: string
}

export const VENUES: { [key: number]: Venue } = {
  1: { id: 1, name: '桐生', prefecture: '群馬県', region: '関東' },
  2: { id: 2, name: '戸田', prefecture: '埼玉県', region: '関東' },
  3: { id: 3, name: '江戸川', prefecture: '東京都', region: '関東' },
  4: { id: 4, name: '平和島', prefecture: '東京都', region: '関東' },
  5: { id: 5, name: '多摩川', prefecture: '東京都', region: '関東' },
  6: { id: 6, name: '浜名湖', prefecture: '静岡県', region: '東海' },
  7: { id: 7, name: '蒲郡', prefecture: '愛知県', region: '東海' },
  8: { id: 8, name: '常滑', prefecture: '愛知県', region: '東海' },
  9: { id: 9, name: '津', prefecture: '三重県', region: '東海' },
  10: { id: 10, name: '三国', prefecture: '福井県', region: '近畿' },
  11: { id: 11, name: 'びわこ', prefecture: '滋賀県', region: '近畿' },
  12: { id: 12, name: '住之江', prefecture: '大阪府', region: '近畿' },
  13: { id: 13, name: '尼崎', prefecture: '兵庫県', region: '近畿' },
  14: { id: 14, name: '鳴門', prefecture: '徳島県', region: '四国' },
  15: { id: 15, name: '丸亀', prefecture: '香川県', region: '四国' },
  16: { id: 16, name: '児島', prefecture: '岡山県', region: '中国' },
  17: { id: 17, name: '宮島', prefecture: '広島県', region: '中国' },
  18: { id: 18, name: '徳山', prefecture: '山口県', region: '中国' },
  19: { id: 19, name: '下関', prefecture: '山口県', region: '中国' },
  20: { id: 20, name: '若松', prefecture: '福岡県', region: '九州' },
  21: { id: 21, name: '芦屋', prefecture: '福岡県', region: '九州' },
  22: { id: 22, name: '福岡', prefecture: '福岡県', region: '九州' },
  23: { id: 23, name: '唐津', prefecture: '佐賀県', region: '九州' },
  24: { id: 24, name: '大村', prefecture: '長崎県', region: '九州' },
}
