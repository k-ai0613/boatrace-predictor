import * as Sentry from '@sentry/nextjs'

// ナビゲーショントランジションの計測
export const onRouterTransitionStart = Sentry.captureRouterTransitionStart

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,

  // パフォーマンス監視のサンプルレート（本番では0.1程度に下げる）
  tracesSampleRate: process.env.NODE_ENV === 'production' ? 0.1 : 1.0,

  // セッションリプレイのサンプルレート
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,

  // 開発環境ではデバッグモードを有効化
  debug: process.env.NODE_ENV === 'development',

  // エラーフィルタリング
  beforeSend(event) {
    // 開発環境ではSentryに送信しない
    if (process.env.NODE_ENV === 'development') {
      return null
    }
    return event
  },

  // 無視するエラー
  ignoreErrors: [
    // ネットワークエラー
    'Network request failed',
    'Failed to fetch',
    'NetworkError',
    // ユーザーによるキャンセル
    'AbortError',
    // ブラウザ拡張機能のエラー
    /^chrome-extension:\/\//,
    /^moz-extension:\/\//,
  ],
})
