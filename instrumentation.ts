import * as Sentry from '@sentry/nextjs'

export async function register() {
  if (process.env.NEXT_RUNTIME === 'nodejs') {
    Sentry.init({
      dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,

      // パフォーマンス監視のサンプルレート
      tracesSampleRate: process.env.NODE_ENV === 'production' ? 0.1 : 1.0,

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
    })
  }

  if (process.env.NEXT_RUNTIME === 'edge') {
    Sentry.init({
      dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,

      // パフォーマンス監視のサンプルレート
      tracesSampleRate: process.env.NODE_ENV === 'production' ? 0.1 : 1.0,

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
    })
  }
}
