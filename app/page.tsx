import Link from 'next/link'

export default function Home() {
  return (
    <div className="space-y-6 md:space-y-8">
      <section className="bg-white rounded-lg shadow-md p-6 md:p-8">
        <h2 className="text-2xl md:text-3xl font-bold mb-3 md:mb-4">ようこそ</h2>
        <p className="text-gray-600 mb-6 text-sm md:text-base">
          このツールは競艇レースの結果を予測し、データ分析に基づいた購入券種を推奨します。
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="border rounded-lg p-5 md:p-6 hover:shadow-lg transition-shadow">
            <h3 className="text-lg md:text-xl font-semibold mb-2 text-blue-600">多角的分析</h3>
            <p className="text-gray-600 text-sm">
              選手成績、モーター性能、天気データなど50以上の特徴量を分析
            </p>
          </div>
          <div className="border rounded-lg p-5 md:p-6 hover:shadow-lg transition-shadow">
            <h3 className="text-lg md:text-xl font-semibold mb-2 text-blue-600">AI予測</h3>
            <p className="text-gray-600 text-sm">
              機械学習（XGBoost）による各艇の着順確率を算出
            </p>
          </div>
          <div className="border rounded-lg p-5 md:p-6 hover:shadow-lg transition-shadow">
            <h3 className="text-lg md:text-xl font-semibold mb-2 text-blue-600">推奨券種</h3>
            <p className="text-gray-600 text-sm">
              単勝、2連単、3連単など推奨購入券種を提案
            </p>
          </div>
        </div>
      </section>

      <section className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-lg shadow-md p-6 md:p-8 text-white">
        <h2 className="text-xl md:text-2xl font-bold mb-3 md:mb-4">データ分析ダッシュボード</h2>
        <p className="mb-6 opacity-90 text-sm md:text-base">
          艇別成績、選手ランキング、コース分析など、詳細なデータ分析を確認できます。
        </p>
        <Link
          href="/analytics"
          className="inline-block bg-white text-blue-600 font-bold py-3 px-6 rounded-lg hover:bg-blue-50 active:bg-blue-100 transition-colors shadow-lg text-sm md:text-base min-h-[44px] flex items-center justify-center w-full sm:w-auto"
        >
          分析ダッシュボードを開く →
        </Link>
      </section>

      <section className="bg-white rounded-lg shadow-md p-6 md:p-8">
        <h2 className="text-xl md:text-2xl font-bold mb-4">機能</h2>
        <ul className="space-y-3">
          <li className="flex items-start">
            <span className="text-blue-600 mr-2 flex-shrink-0">✓</span>
            <span className="text-sm md:text-base">5年分の過去データに基づく高精度予測</span>
          </li>
          <li className="flex items-start">
            <span className="text-blue-600 mr-2 flex-shrink-0">✓</span>
            <span className="text-sm md:text-base">リアルタイムの天気データを考慮</span>
          </li>
          <li className="flex items-start">
            <span className="text-blue-600 mr-2 flex-shrink-0">✓</span>
            <span className="text-sm md:text-base">各艇の1着〜6着確率を表示</span>
          </li>
          <li className="flex items-start">
            <span className="text-blue-600 mr-2 flex-shrink-0">✓</span>
            <span className="text-sm md:text-base">期待値に基づく推奨購入券種の提案</span>
          </li>
          <li className="flex items-start">
            <span className="text-blue-600 mr-2 flex-shrink-0">✓</span>
            <span className="text-sm md:text-base">PC・スマホ対応のレスポンシブデザイン</span>
          </li>
        </ul>
      </section>

      <section className="bg-blue-50 border border-blue-200 rounded-lg p-5 md:p-6">
        <h3 className="text-lg md:text-xl font-semibold mb-2 text-blue-800">注意事項</h3>
        <p className="text-sm text-blue-900">
          このツールはデータ分析に基づく予測を提供しますが、レース結果を保証するものではありません。
          競艇は公営ギャンブルです。自己責任でご利用ください。
        </p>
      </section>
    </div>
  )
}
