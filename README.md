# 競艇予測分析ツール

AI予測による競艇レース分析ツール

## 概要

このツールは競艇レースの結果を予測し、データ分析に基づいた購入券種を推奨します。

### 主な機能

- **多角的分析**: 選手成績、モーター性能、天気データなど50以上の特徴量を分析
- **AI予測**: 機械学習（XGBoost）による各艇の着順確率を算出
- **推奨券種**: 単勝、2連単、3連単など推奨購入券種を提案
- **完全無料運用**: GitHub Actions、Supabase、Vercelを活用した0円構成

## 技術スタック

### フロントエンド
- Next.js 14 (App Router)
- React, TypeScript
- Tailwind CSS, shadcn/ui
- Recharts

### バックエンド
- Vercel Serverless Functions
- Supabase (PostgreSQL)

### データ収集
- Python 3.11
- aiohttp, BeautifulSoup4
- GitHub Actions

### 機械学習
- scikit-learn
- XGBoost
- pandas, numpy

## セットアップ

### 1. 依存関係のインストール

```bash
# Node.js依存関係
npm install

# Python依存関係（スクレイパー）
pip install -r scraper/requirements.txt

# Python依存関係（機械学習）
pip install -r ml/requirements.txt
```

### 2. 環境変数の設定

`.env.example`をコピーして`.env`を作成し、以下を設定:

```env
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
DATABASE_URL=your_database_url
```

### 3. データベースのセットアップ

Supabaseプロジェクトを作成し、スキーマを適用:

```bash
# Supabase CLIを使用する場合
supabase db push

# または、Supabaseダッシュボードから直接SQLを実行
# supabase/schema.sql の内容をコピー&実行
```

### 4. 開発サーバーの起動

```bash
npm run dev
```

ブラウザで `http://localhost:3000` を開く

## データ収集

### 手動でデータ収集を実行

```bash
# 日次データ収集
cd scraper
python daily_scraper.py

# 過去データ収集
python historical_scraper.py --phase 1 --max-days 5
```

### GitHub Actionsでの自動収集

リポジトリのSecretsに`DATABASE_URL`を設定後、GitHub Actionsが自動実行されます:

- **日次データ**: 1日3回（7時、14時、20時 JST）
- **過去データ**: 毎日深夜3時に1日分ずつ収集

## プロジェクト構造

```
boatrace-predictor/
├── app/                    # Next.js App Router
│   ├── api/               # APIエンドポイント
│   ├── layout.tsx
│   └── page.tsx
├── components/            # Reactコンポーネント
│   ├── ui/               # shadcn/ui コンポーネント
│   ├── PredictionDisplay.tsx
│   └── RecommendedBets.tsx
├── lib/                   # ユーティリティ
├── types/                 # TypeScript型定義
├── scraper/              # データ収集スクリプト
│   ├── boatrace_scraper.py
│   ├── rate_limiter.py
│   └── requirements.txt
├── ml/                    # 機械学習
│   ├── feature_engineer.py
│   ├── race_predictor.py
│   └── requirements.txt
├── supabase/             # データベーススキーマ
│   └── schema.sql
└── .github/              # GitHub Actions
    └── workflows/
```

## 開発フェーズ

### Phase 1: 環境構築とデータ収集基盤（完了）
- ✅ Supabase プロジェクトセットアップ
- ✅ データベーステーブル作成
- ✅ スクレイピングスクリプト実装
- ✅ GitHub Actions ワークフロー作成

### Phase 2: 過去データ収集と分析準備（進行中）
- ⏳ Phase 1（直近1年）データ収集
- ⏳ データクレンジング
- ⏳ 天気データ収集

### Phase 3: 予測モデル開発（予定）
- ⬜ 特徴量エンジニアリング実装
- ⬜ XGBoost モデル訓練
- ⬜ モデル評価と検証

### Phase 4: フロントエンド開発（一部完了）
- ✅ Next.js プロジェクトセットアップ
- ✅ 基本レイアウト実装
- ⬜ レース選択UI実装
- ⬜ API統合

### Phase 5: テストと改善（予定）
- ⬜ 実データでの検証
- ⬜ モデルチューニング
- ⬜ デプロイ

## 注意事項

- このツールはデータ分析に基づく予測を提供しますが、レース結果を保証するものではありません
- 競艇は公営ギャンブルです。自己責任でご利用ください
- スクレイピングは相手サーバーに負荷をかけないよう、適切なレート制限を設定しています

## ライセンス

MIT License

## 貢献

Issue、Pull Requestを歓迎します。

## お問い合わせ

詳細は設計書（boatrace-predictor-design.md）をご覧ください。
