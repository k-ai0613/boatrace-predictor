# 🚀 クイックスタートガイド

競艇予測モデルを最短で構築するための手順を説明します。

---

## ⏱️ 所要時間

- **最短**: 4時間（データ収集1週間分 + 基本モデル訓練）
- **推奨**: 1-2週間（データ収集1年分 + 最適化）
- **最高精度**: 3-4ヶ月（データ収集20年分 + 全機能実装）

---

## 📋 前提条件

### 1. 環境構築

```bash
# リポジトリをクローン
git clone <your-repo-url>
cd boat

# 依存パッケージをインストール
pip install -r scraper/requirements.txt

# データベース接続情報を設定
# .env ファイルを作成して以下を記載:
DATABASE_URL=postgresql://user:password@host:port/database
```

### 2. データベースセットアップ

- Supabase（無料）を推奨
- PostgreSQL 15以上
- 設計書の「データベース設計」セクションを参照

---

## 🎯 最短経路（4時間コース）

### Step 1: データ収集状況を確認

```bash
python scraper/check_data_status.py
```

### Step 2: 直近1週間分のデータを収集

```bash
# 推奨: 負荷に優しいスクリプト
python scraper/collect_gentle.py --days 3 --rate 5

# または従来のスクリプト
python scraper/collect_all_venues.py
```

**所要時間:** 約1-4時間

**詳細:** `README_DATA_COLLECTION.md` を参照

### Step 3: 基本モデルを訓練

```bash
python ml/evaluate_model.py
```

**期待精度:** 20-25%

**出力:** `ml/trained_model.pkl`

---

## 🏆 推奨経路（1-2週間コース）

### Step 1: データ収集開始

#### 1-1. 直近データを収集

```bash
# 推奨: 負荷に優しいスクリプト
python scraper/collect_gentle.py --days 7 --rate 5

# または従来のスクリプト
python scraper/collect_all_venues.py
```

**詳細:** `README_DATA_COLLECTION.md` を参照

#### 1-2. GitHub Actionsで過去データを自動収集

1. GitHubリポジトリの **Actions** タブを開く
2. **Scrape Historical Data** を選択
3. **Run workflow** をクリック
4. パラメータ設定:
   - `phase`: `1` (直近1年分)
   - `days`: `7` (1回で7日分)
5. 定期的に実行（週に2-3回）

**目標:** 5,000-10,000レース

### Step 2: 定期的に進捗確認

```bash
# 1週間ごとに確認
python scraper/check_data_status.py
```

### Step 3: データが5,000レース以上になったら

#### 3-1. 会場別統計を計算

```bash
python ml/advanced_stats.py
```

#### 3-2. ハイパーパラメータ最適化

```bash
python ml/hyperparameter_tuning.py
```

**所要時間:** 2-6時間

**出力:** `ml/best_params_latest.json`

#### 3-3. 最適パラメータでモデル訓練

```bash
python ml/train_model.py
```

**期待精度:** 30-35%

---

## 🌟 最高精度経路（3-4ヶ月コース）

### Phase 1: データ収集（1-2ヶ月）

```bash
# GitHub Actionsで継続的に過去データを収集
# 目標: 20,000レース以上（約2-3年分）
```

### Phase 2: 天気データ収集

```bash
# 天気データを収集（初回テスト）
python scraper/weather_scraper.py

# GitHub Actionsで自動収集を有効化
# .github/workflows/scrape_weather.yml
```

**注意:** HTML構造の調整が必要な場合あり

### Phase 3: 全機能を使用してモデル訓練

```bash
# 統合パイプライン（全自動）
python ml/train_full_pipeline.py
```

または個別に実行:

```bash
# 1. 会場別統計計算
python ml/advanced_stats.py

# 2. ハイパーパラメータ最適化（時系列重み付け有効）
python ml/hyperparameter_tuning.py

# 3. 最適パラメータでモデル訓練
python ml/train_model.py
```

**期待精度:** 40-50%+

---

## 📊 精度の目安

| データ量 | 機能 | 期待精度 |
|---------|------|---------|
| 1,000レース | 基本 | 20-25% |
| 5,000レース | 基本 + 最適化 | 25-30% |
| 10,000レース | + 会場別統計 | 30-35% |
| 20,000レース | + 時系列重み付け | 35-40% |
| 20,000レース+ | + 天気データ | **45-50%** |

---

## ⚡ ワンコマンド実行

データが10,000レース以上ある場合、全ステップを自動実行:

```bash
python ml/train_full_pipeline.py
```

**実行内容:**
1. データ収集状況の確認
2. 会場別統計の計算
3. ハイパーパラメータ最適化
4. 最適パラメータでモデル訓練
5. 精度評価とレポート出力

---

## 🔍 トラブルシューティング

### データが収集できない

```bash
# データベース接続を確認
python scraper/test_db.py

# スクレイピングのテスト
python scraper/test_scraping.py
```

### 精度が全く上がらない（< 20%）

**チェックリスト:**
- [ ] データが1,000レース以上あるか
- [ ] 各レースに6艇のデータが揃っているか
- [ ] 着順データ（result_position）が正しいか

```bash
python scraper/check_data_status.py
```

### メモリ不足エラー

データ量が多い場合、処理するレース数を制限:

```python
# ml/train_model.py の prepare_features() 内
if race_count >= 10000:  # 10,000レースまで
    break
```

---

## 📖 詳細ドキュメント

- **データ収集ガイド**: `README_DATA_COLLECTION.md` ⭐ **NEW**
- **完全な訓練ガイド**: `README_TRAINING.md`
- **フロントエンド統合ガイド**: `README_INTEGRATION.md`
- **システム設計書**: `boatrace-predictor-design.md`
- **GitHub Actions設定**: `.github/workflows/`

---

## 🎓 学習曲線

### Week 1: セットアップとデータ収集
- 環境構築
- 直近データ収集
- 基本モデル訓練

### Week 2-4: データ蓄積
- GitHub Actionsで自動収集
- 定期的な進捗確認

### Week 4-8: 最適化
- 会場別統計計算
- ハイパーパラメータ最適化
- モデル再訓練

### Week 8-16: 高精度化
- 天気データ収集
- 全機能統合
- 精度40-50%達成

---

## ✅ チェックリスト

### 初回セットアップ
- [ ] リポジトリクローン
- [ ] 依存パッケージインストール
- [ ] .env ファイル作成
- [ ] データベース接続確認

### データ収集
- [ ] 直近1週間分収集完了
- [ ] GitHub Actions設定
- [ ] 定期的な進捗確認

### モデル訓練
- [ ] 基本モデル訓練（1,000レース以上）
- [ ] 会場別統計計算（5,000レース以上）
- [ ] ハイパーパラメータ最適化
- [ ] 最適パラメータでモデル再訓練

### 高精度化
- [ ] 天気データ収集
- [ ] 時系列重み付け使用
- [ ] 精度40%以上達成

---

## 🚀 今すぐ始める

```bash
# 1. 現在の状況を確認
python scraper/check_data_status.py

# 2. データ収集を開始
python scraper/collect_all_venues.py

# 3. （データ収集完了後）モデル訓練
python ml/evaluate_model.py
```

**成功を祈ります！🎉**
