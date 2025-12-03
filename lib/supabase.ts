import { createClient, SupabaseClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

// ビルド時に環境変数が未設定の場合のダミークライアント
const isDummyClient = !supabaseUrl || !supabaseAnonKey ||
  supabaseUrl === 'your_supabase_url' ||
  !supabaseUrl.startsWith('http')

let _supabase: SupabaseClient | null = null

export const supabase: SupabaseClient = isDummyClient
  ? (null as unknown as SupabaseClient)
  : (() => {
      if (!_supabase) {
        _supabase = createClient(supabaseUrl, supabaseAnonKey)
      }
      return _supabase
    })()

// Supabaseクライアントが利用可能かチェック
export function isSupabaseAvailable(): boolean {
  return !isDummyClient && supabase !== null
}

// サーバーサイド用のクライアント作成関数
export function createServerClient(): SupabaseClient | null {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY

  if (!url || !key || url === 'your_supabase_url' || !url.startsWith('http')) {
    return null
  }

  return createClient(url, key)
}

// 遅延初期化用のクライアント取得関数
export function getSupabaseClient(): SupabaseClient | null {
  if (isDummyClient) {
    return null
  }
  return supabase
}
