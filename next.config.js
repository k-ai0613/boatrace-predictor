const { withSentryConfig } = require('@sentry/nextjs')

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  experimental: {
    instrumentationHook: true,
  },
}

// Sentry設定
const sentryWebpackPluginOptions = {
  // ソースマップのアップロードを無効化（無料プランでは不要）
  silent: true,

  // 本番環境でのみソースマップをアップロード
  disableServerWebpackPlugin: process.env.NODE_ENV !== 'production',
  disableClientWebpackPlugin: process.env.NODE_ENV !== 'production',

  // ソースマップを公開しない
  hideSourceMaps: true,
}

// Sentry DSNが設定されている場合のみSentryを有効化
module.exports = process.env.NEXT_PUBLIC_SENTRY_DSN
  ? withSentryConfig(nextConfig, sentryWebpackPluginOptions)
  : nextConfig
