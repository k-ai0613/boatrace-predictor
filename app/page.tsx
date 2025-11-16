import Link from 'next/link'

export default function Home() {
  return (
    <div className="space-y-8">
      <section className="bg-white rounded-lg shadow-md p-8">
        <h2 className="text-3xl font-bold mb-4">ようこそ</h2>
        <p className="text-gray-600 mb-6">
          このツールは競艇レースの結果を予測し、データ分析に基づいた購入券種を推奨します。
        </p>
        <div className="grid md:grid-cols-3 gap-4">
          <div className="border rounded-lg p-6 hover:shadow-lg transition-shadow">
            <h3 className="text-xl font-semibold mb-2 text-blue-600">多角的分析</h3>
            <p className="text-gray-600 text-sm">
              選手成績、モーター性能、天気データなど50以上の特徴量を分析
            </p>
          </div>
          <div className="border rounded-lg p-6 hover:shadow-lg transition-shadow">
            <h3 className="text-xl font-semibold mb-2 text-blue-600">AI予測</h3>
            <p className="text-gray-600 text-sm">
              機械学習（XGBoost）による各艇の着順確率を算出
            </p>
          </div>
          <div className="border rounded-lg p-6 hover:shadow-lg transition-shadow">
            <h3 className="text-xl font-semibold mb-2 text-blue-600">推奨券種</h3>
            <p className="text-gray-600 text-sm">
              単勝、2連単、3連単など推奨購入券種を提案
            </p>
          </div>
        </div>
      </section>

      <section className="bg-white rounded-lg shadow-md p-8">
        <h2 className="text-2xl font-bold mb-4">機能</h2>
        <ul className="space-y-3">
          <li className="flex items-start">
            <span className="text-blue-600 mr-2">✓</span>
            <span>20年分の過去データに基づく高精度予測</span>
          </li>
          <li className="flex items-start">
            <span className="text-blue-600 mr-2">✓</span>
            <span>リアルタイムの天気データを考慮</span>
          </li>
          <li className="flex items-start">
            <span className="text-blue-600 mr-2">✓</span>
            <span>各艇の1着〜6着確率を表示</span>
          </li>
          <li className="flex items-start">
            <span className="text-blue-600 mr-2">✓</span>
            <span>期待値に基づく推奨購入券種の提案</span>
          </li>
          <li className="flex items-start">
            <span className="text-blue-600 mr-2">✓</span>
            <span>PC・スマホ対応のレスポンシブデザイン</span>
          </li>
        </ul>
      </section>

      <section className="bg-white rounded-lg shadow-md p-8">
        <h2 className="text-2xl font-bold mb-4">利用開始</h2>
        <p className="text-gray-600 mb-4">
          現在、システムは開発中です。以下の手順でセットアップしてください:
        </p>
        <ol className="list-decimal list-inside space-y-2 text-gray-700">
          <li>Supabaseプロジェクトを作成し、データベースをセットアップ</li>
          <li>環境変数を.envファイルに設定</li>
          <li>npm installで依存関係をインストール</li>
          <li>npm run devで開発サーバーを起動</li>
          <li>GitHub Actionsでデータ収集を開始</li>
        </ol>
      </section>

      <section className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-xl font-semibold mb-2 text-blue-800">注意事項</h3>
        <p className="text-sm text-blue-900">
          このツールはデータ分析に基づく予測を提供しますが、レース結果を保証するものではありません。
          競艇は公営ギャンブルです。自己責任でご利用ください。
        </p>
      </section>
    </div>
  )
}
