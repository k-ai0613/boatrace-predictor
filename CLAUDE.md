# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## プロジェクト概要

競艇予測分析ツール - AI予測による競艇レース分析システム

- **目的**: 機械学習を使用して競艇レースの着順確率を予測し、推奨買い目を提案
- **技術スタック**: Next.js 14 + Python機械学習 + Supabase
- **特徴**: 完全無料運用（GitHub Actions + Vercel + Supabase無料枠）

---

## 開発コマンド

### Next.js（フロントエンド）

```bash
# 開発サーバー起動
npm run dev

# 本番ビルド
npm run build

# 本番サーバー起動
npm start

# ESLint実行
npm run lint
```

### Python（データ収集・機械学習）

#### データ収集

```bash
# 現在のデータ状況を確認（最初に実行推奨）
python scraper/check_data_status.py

# 詳細なデータ分析（年別・月別レース数、データ完全性）
python scraper/check_data_details.py

# 手動収集: 柔軟で負荷に優しいスクリプト
python scraper/collect_gentle.py --days 7 --rate 5

# 手動収集: 特定期間のデータを収集
python scraper/collect_historical_data.py --start-date 2024-01-01 --end-date 2024-01-31 --delay 5.0

# 手動収集: 特定月のデータを収集
python scraper/collect_monthly.py --year-month 2024-12 --delay 5.0

# データベース接続テスト
python scraper/test_db.py
```

#### 自動データ収集（GitHub Actions）

プロジェクトには3つの自動収集ワークフローが設定されています：

1. **日次収集** (`daily-kyotei-collection.yml`)
   - 毎日深夜2時（JST）に自動実行
   - 2日前の確定データを収集
   - 今後の新しいデータを自動収集

2. **自動バックフィル** (`auto-monthly-backfill.yml`)
   - 6時間間隔で4パート実行（03:00, 09:00, 15:00, 21:00 JST）
   - 各パートで6会場ずつ収集（1パート約5時間）
   - データベース内の最古データから前月を自動判定
   - 2020年1月まで遡って収集（約5年分、400,000レース）
   - 完了まで約12週間

3. **詳細統計収集** (`collect-detailed-stats.yml`)
   - 月1回（毎月1日深夜4時）に自動実行
   - 選手・会場の詳細統計を更新

4. **週次バックテスト** (`weekly-backtest.yml`)
   - 毎週日曜15:00（JST）に自動実行
   - 300レースで精度検証
   - 結果をDBに保存、精度低下時はアラート

#### 機械学習モデル

```bash
# クイックスタート: デフォルトパラメータで訓練
python ml/evaluate_model.py

# 強化版モデル訓練（推奨）
python ml/train_enhanced_model.py

# ステップ1: ハイパーパラメータ最適化（2-6時間）
python ml/hyperparameter_tuning.py

# ステップ2: 最適パラメータでモデル訓練
python ml/train_model.py

# オプション: 会場別統計計算（5,000レース以上で実行）
python ml/advanced_stats.py

# 統合パイプライン（全自動）
python ml/train_full_pipeline.py

# 予測実行（race_idを指定）- 全5賭け式対応
python ml/predict_race_enhanced.py <race_id>
```

#### バックテスト検証

```bash
# 精度検証（200レース）
python ml/backtest.py --races 200

# 結果をDBに保存
python ml/backtest.py --races 200 --save

# 精度低下チェック付き
python ml/backtest.py --races 200 --save --check-degradation
```

#### 指定日のデータ取得

```bash
# 特定日のレースデータを取得（未来の予定レースも可）
python scraper/fetch_scheduled_races.py 2025-12-07

# 特定会場のみ
python scraper/fetch_scheduled_races.py 2025-12-07 --venue 2
```

---

## アーキテクチャ

### 技術スタック

- **フロントエンド**: Next.js 14 (App Router), React, TypeScript, Tailwind CSS, shadcn/ui
- **バックエンドAPI**: Vercel Serverless Functions
- **データ収集**: Python 3.11 + aiohttp + BeautifulSoup4（非同期スクレイピング）
- **機械学習**: XGBoost + scikit-learn + pandas
- **データベース**: Supabase (PostgreSQL 15)
- **自動化**: GitHub Actions（データ収集を定期実行）

### システム構成

```
┌─────────────────────┐
│  Next.js Frontend   │ ← ユーザー
│  (Vercel)           │
└──────────┬──────────┘
           │
           ↓
┌─────────────────────┐
│  Serverless API     │
│  /api/predict       │ → Python ML Script
│  /api/races         │
└──────────┬──────────┘
           │
           ↓
┌─────────────────────┐       ┌──────────────────┐
│  Supabase           │ ←───  │ GitHub Actions   │
│  (PostgreSQL)       │       │ データ収集        │
└─────────────────────┘       └──────────────────┘
```

### データフロー

1. **データ収集**: GitHub ActionsまたはローカルでPythonスクリプトを実行 → Supabaseに保存
2. **モデル訓練**: DBからデータ取得 → 特徴量生成 → XGBoostで訓練 → モデル保存
3. **予測**: フロントエンド → API → Pythonスクリプト実行 → 予測結果をDBに保存 → フロントエンドに返却

---

## プロジェクト構造

```
boat/
├── app/                        # Next.js App Router
│   ├── page.tsx               # トップページ
│   ├── analytics/             # 分析ダッシュボード
│   │   └── page.tsx
│   └── api/                   # APIエンドポイント
│       ├── predict/           # 予測API
│       ├── races/             # レースデータ取得
│       └── analytics/         # 統計データAPI
│
├── components/                # Reactコンポーネント
│   ├── analytics/            # 分析系コンポーネント
│   └── ui/                   # shadcn/uiコンポーネント
│
├── lib/                       # ユーティリティ
│   ├── supabase.ts           # Supabaseクライアント
│   ├── analytics.ts          # 分析ロジック
│   └── predictions.ts        # 予測ロジック
│
├── ml/                        # 機械学習
│   ├── feature_engineer.py   # 特徴量エンジニアリング
│   ├── enhanced_feature_engineer.py  # 強化版特徴量（35次元）
│   ├── race_predictor.py     # 予測モデル（クラス定義）
│   ├── improved_combination_predictor.py  # 5賭け式確率計算
│   ├── train_model.py        # モデル訓練
│   ├── train_enhanced_model.py  # 強化版訓練（推奨）
│   ├── evaluate_model.py     # モデル評価
│   ├── backtest.py           # バックテスト検証
│   ├── hyperparameter_tuning.py  # ハイパーパラメータ最適化
│   ├── predict_race.py       # 予測実行スクリプト
│   ├── predict_race_enhanced.py  # 強化版予測（5賭け式）
│   └── trained_model_latest.pkl  # 訓練済みモデル（Git管理）
│
├── scraper/                   # データ収集
│   ├── collect_gentle.py           # 推奨: 柔軟な収集スクリプト
│   ├── collect_historical_data.py  # 特定期間のデータ収集
│   ├── collect_monthly.py          # 月単位のデータ収集
│   ├── fetch_scheduled_races.py    # 指定日のレースデータ取得
│   ├── get_next_backfill_month.py  # 次の収集月を自動判定
│   ├── rate_limiter.py             # レート制限機構
│   ├── check_data_status.py        # データ状況確認（概要）
│   ├── check_data_details.py       # データ詳細分析
│   └── boatrace_db_scraper.py      # 詳細統計スクレイパー
│
├── .github/workflows/         # GitHub Actions
│   ├── collect-detailed-stats.yml   # 詳細統計収集（月1回）
│   ├── daily-kyotei-collection.yml  # 日次データ収集（毎日）
│   ├── auto-monthly-backfill.yml    # 自動バックフィル（毎日）
│   ├── weekly-backtest.yml          # 週次バックテスト（毎週日曜）
│   └── monthly-backfill.yml         # 手動バックフィル
│
├── supabase/                  # Supabaseセキュリティ設定
│   ├── enable_rls_policies.sql     # RLSポリシー有効化
│   ├── fix_function_security.sql   # 関数セキュリティ修正
│   └── README.md                   # 実行手順
│
├── README.md                       # プロジェクト概要
├── QUICKSTART.md                   # クイックスタートガイド
├── README_DATA_COLLECTION.md       # データ収集詳細ガイド
├── README_BACKFILL_GUIDE.md        # 過去データ収集ガイド
├── README_TRAINING.md              # モデル訓練ガイド
├── README_INTEGRATION.md           # フロントエンド統合ガイド
└── boatrace-predictor-design.md    # 完全設計書
```

---

## 重要な設計上の注意点

### 1. レート制限（最重要）

データ収集時は**必ずレート制限を遵守**してください。相手サーバーへの負荷を最小限に抑えることが最優先です。

- **推奨**: 5秒/リクエスト
- **並行リクエスト**: 1（同時に1つのみ）
- **実装**: `scraper/rate_limiter.py`で管理済み
- **実行時間**: 夜間（23:00-07:00 JST）を推奨

```python
# デフォルト設定
requests_per_second = 0.2    # 5秒に1リクエスト
requests_per_minute = 20     # 1分に20リクエスト
requests_per_hour = 500      # 1時間に500リクエスト
requests_per_day = 10000     # 1日に10,000リクエスト
```

### 2. データ収集戦略

- **自動バックフィル**: 6時間間隔で4パート実行
  - Part 1: 03:00 JST（会場1-6）
  - Part 2: 09:00 JST（会場7-12）
  - Part 3: 15:00 JST（会場13-18）
  - Part 4: 21:00 JST（会場19-24）
  - 2020年1月まで遡る（約5年分、400,000レース）
  - 完了まで約12週間
- **日次収集**: 毎日深夜2時に2日前のデータを自動収集
  - 今後の新しいデータを自動的に取得
  - データの隙間を作らない
- **既存データのスキップ**: 重複収集を自動的に防止

### 3. 機械学習モデル

#### 特徴量設計（50-100個の特徴量）

1. **選手関連**: 勝率、級別、平均ST、当地成績など
2. **モーター関連**: 2連対率、3連対率
3. **コース関連**: コース別勝率、場の特性
4. **天気関連**: 風速・風向き（最重要）、気温、波高
5. **複合特徴量**: 選手×モーター、コース×風向きなど
6. **時系列特徴量**: 直近成績、トレンド

#### モデル訓練のポイント

- **時系列重み付け**: 新しいデータほど重要度を高くする（実装済み）
  - 最新データ: 重み 1.0
  - 1年前: 重み 0.81
  - 3年前: 重み 0.50（半減期）

- **精度目標**: 30-40%（これは非常に高い精度）
  - ランダム予測: 16.7%
  - 基本モデル（1,000レース）: 20-25%
  - 最適化モデル（10,000レース+）: 30-40%
  - 全機能実装（20,000レース+ 天気データ）: 45-50%

### 4. データベース設計

主要テーブル:
- `races` - レース基本情報
- `race_entries` - 出走情報（6艇分）
- `racers` - 選手マスタ
- `racer_statistics` - 選手成績
- `racer_detailed_stats` - 選手詳細統計
- `venue_detailed_stats` - 会場詳細統計
- `weather_data` - 天気情報
- `predictions` - 予測結果
- `backtest_results` - バックテスト精度履歴

#### セキュリティ設定

すべてのテーブルにRow Level Security (RLS)が有効化されています：
- **読み取り**: 全員許可（匿名ユーザー含む）
- **書き込み**: 全員許可（サービスロール経由を想定）

初回セットアップ時は`supabase/`ディレクトリのSQLスクリプトを実行してください。

### 5. 環境変数

`.env`ファイルに以下を設定:

```env
DATABASE_URL=postgresql://user:password@host:port/database
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

---

## 推奨ワークフロー

### 新規開発者向けセットアップ

```bash
# 1. 依存関係のインストール
npm install
pip install -r scraper/requirements.txt
pip install -r ml/requirements.txt

# 2. 環境変数の設定
# .env ファイルを作成してSupabase接続情報を記載

# 3. データ収集状況を確認
python scraper/check_data_status.py

# 4. データ収集（まだデータがない場合）
python scraper/collect_gentle.py --days 3 --rate 5

# 5. モデル訓練（1,000レース以上ある場合）
python ml/evaluate_model.py

# 6. 開発サーバー起動
npm run dev
```

### 定期的なメンテナンス

```bash
# 1週間ごと: 新しいデータで再訓練
python scraper/collect_gentle.py --days 7
python ml/train_model.py

# データ確認
python scraper/check_data_status.py
```

---

## トラブルシューティング

### データ収集エラー

```bash
# DB接続テスト
python scraper/test_db.py

# スクレイピングテスト
python scraper/test_scraping.py

# レート制限エラー時 → 間隔を延ばす
python scraper/collect_gentle.py --rate 10
```

### モデル訓練エラー

- データ量が1,000レース未満 → もっとデータを収集
- メモリ不足 → `ml/train_model.py`で処理レース数を制限（`LIMIT 10000`）
- 精度が20%未満 → データの整合性を確認（`check_data_status.py`）

### API/フロントエンドエラー

- モデルファイルが見つからない → `python ml/train_model.py`を実行
- 予測が遅い（30秒以上） → 過去データのLIMITを減らす

---

## 参考ドキュメント

- `README.md` - プロジェクト全体概要
- `QUICKSTART.md` - 最短で動かす手順
- `README_DATA_COLLECTION.md` - データ収集の詳細ガイド
- `README_BACKFILL_GUIDE.md` - 過去データ収集ガイド（GitHub Actions）
- `README_TRAINING.md` - モデル訓練の詳細ガイド
- `README_INTEGRATION.md` - フロントエンド統合ガイド
- `supabase/README.md` - Supabaseセキュリティ設定手順
- `boatrace-predictor-design.md` - 完全設計書（2,000行以上）

---

## コーディング規約

### Python

- 非同期処理には`asyncio` + `aiohttp`を使用
- レート制限は`rate_limiter.py`を必ず使用
- データベース操作は`psycopg2`を使用
- エラーハンドリングとリトライ機構を実装

### TypeScript/React

- Next.js 14のApp Routerを使用
- コンポーネントは`components/`ディレクトリに配置
- APIルートは`app/api/`ディレクトリに配置
- Tailwind CSS + shadcn/uiでスタイリング
- Supabaseクライアントは`lib/supabase.ts`を使用

---

## デプロイ

- **フロントエンド**: Vercel（自動デプロイ設定済み）
- **データ収集**: GitHub Actions（自動実行）
- **データベース**: Supabase（無料枠500MB）

すべて無料枠内で運用可能です。
