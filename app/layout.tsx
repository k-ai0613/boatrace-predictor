import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Header from '@/components/Header'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  metadataBase: new URL('https://boatrace-predictor.vercel.app'),
  title: {
    default: 'ボートレース予測AI - 競艇レース予測分析ツール',
    template: '%s | ボートレース予測AI',
  },
  description: 'AI機械学習による競艇レース予測サービス。過去5年分のデータを分析し、選手成績・モーター性能・コース特性から的中率の高い予測を提供。無料で今すぐ試せます。',
  keywords: ['競艇', 'ボートレース', '予測', 'AI', '機械学習', '的中', '舟券', 'データ分析'],
  authors: [{ name: 'ボートレース予測AI' }],
  creator: 'ボートレース予測AI',
  publisher: 'ボートレース予測AI',
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  openGraph: {
    type: 'website',
    locale: 'ja_JP',
    url: 'https://boatrace-predictor.vercel.app',
    title: 'ボートレース予測AI - 競艇レース予測分析ツール',
    description: 'AI機械学習による競艇レース予測サービス。過去5年分のデータを分析し、選手成績・モーター性能・コース特性から的中率の高い予測を提供。',
    siteName: 'ボートレース予測AI',
    images: [
      {
        url: 'https://boatrace-predictor.vercel.app/og-image.png',
        width: 1200,
        height: 630,
        alt: 'ボートレース予測AI - 競艇レース予測分析ツール',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'ボートレース予測AI - 競艇レース予測分析ツール',
    description: 'AI機械学習による競艇レース予測サービス。過去5年分のデータを分析し、選手成績・モーター性能・コース特性から的中率の高い予測を提供。',
    images: ['https://boatrace-predictor.vercel.app/og-image.png'],
  },
  alternates: {
    canonical: 'https://boatrace-predictor.vercel.app',
  },
  verification: {
    google: 'I9EXlcVhDYQS_c4IwmXTNFuAmdzEg8GDo5CmPiJBMYY',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ja">
      <body className={inter.className}>
        <div className="min-h-screen bg-gray-50 flex flex-col">
          <Header />
          <main className="container mx-auto px-4 py-4 md:py-6 flex-1">
            {children}
          </main>
          <footer className="bg-gray-800 text-white mt-auto">
            <div className="container mx-auto px-4 py-6">
              <div className="text-center space-y-4">
                <div className="flex flex-col sm:flex-row justify-center items-center gap-4 sm:gap-6 text-sm">
                  <a href="/terms" className="text-gray-400 hover:text-white transition-colors py-2">
                    利用規約
                  </a>
                  <a href="/privacy" className="text-gray-400 hover:text-white transition-colors py-2">
                    プライバシーポリシー
                  </a>
                  <a href="/contact" className="text-gray-400 hover:text-white transition-colors py-2">
                    お問い合わせ
                  </a>
                </div>
                <p className="text-xs sm:text-sm text-gray-400">
                  &copy; 2025 ボートレース予測AI
                </p>
                <p className="text-xs text-gray-500 px-4">
                  ※本サービスの予測は統計的分析に基づくものであり、レース結果を保証するものではありません。
                </p>
              </div>
            </div>
          </footer>
        </div>
      </body>
    </html>
  )
}
