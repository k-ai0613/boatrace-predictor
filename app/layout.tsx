import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: '競艇予測分析ツール',
  description: 'AI予測による競艇レース分析ツール',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ja">
      <body className={inter.className}>
        <div className="min-h-screen bg-gray-50">
          <header className="bg-blue-600 text-white shadow-md">
            <div className="container mx-auto px-4 py-4">
              <h1 className="text-2xl font-bold">競艇予測分析ツール</h1>
              <p className="text-sm text-blue-100">AIによるレース結果予測</p>
            </div>
          </header>
          <main className="container mx-auto px-4 py-6">
            {children}
          </main>
          <footer className="bg-gray-800 text-white mt-12">
            <div className="container mx-auto px-4 py-6">
              <p className="text-sm text-gray-400 text-center">
                &copy; 2024 競艇予測分析ツール - データ分析による予測支援
              </p>
            </div>
          </footer>
        </div>
      </body>
    </html>
  )
}
