# データ収集ガイド

負荷を抑えた安全なデータ収集方法を説明します。

---

## 📋 目次

1. [収集スクリプトの種類](#収集スクリプトの種類)
2. [推奨される収集方法](#推奨される収集方法)
3. [負荷対策の詳細](#負荷対策の詳細)
4. [使用方法](#使用方法)
5. [トラブルシューティング](#トラブルシューティング)

---

## 📂 収集スクリプトの種類

### 1. **collect_gentle.py** ⭐ **推奨**
最も柔軟で負荷に優しいスクリプト

**特徴:**
- ✅ コマンドライン引数で細かい調整が可能
- ✅ プログレスバー表示（tqdmインストール時）
- ✅ 詳細なログ記録
- ✅ 段階的収集モード（少量ずつ）
- ✅ 中断・再開に対応（既存データを自動スキップ）

**推奨用途:**
- 初めてのデータ収集
- サーバーへの負荷を最小限に抑えたい
- 少量ずつテストしながら収集したい

### 2. **collect_all_venues.py**
全会場の一括収集

**特徴:**
- ✅ シンプルな使い方
- ✅ 全24会場×7日分を自動収集
- ✅ レート制限: 5秒/リクエスト
- ✅ 既存データのスキップ

**推奨用途:**
- 標準的なデータ収集
- 夜間の自動実行

### 3. **GitHub Actions** (自動実行)
過去データの段階的収集

**設定ファイル:**
- `.github/workflows/scrape_historical.yml` - 過去データ収集
- `.github/workflows/scrape_daily.yml` - 日次データ収集
- `.github/workflows/scrape_weather.yml` - 天気データ収集

**推奨用途:**
- 長期間のデータを自動収集
- 手動実行の手間を省きたい

---

## 🎯 推奨される収集方法

### Phase 1: テスト収集（10-30分）

まず少量のデータで動作確認します。

```bash
# 最も安全: 1日分、会場1-3のみ、10秒/リクエスト
python scraper/collect_gentle.py --days 1 --venues 1-3 --rate 10

# 所要時間: 約6分（36レース × 10秒）
```

**確認事項:**
- エラーなく実行完了するか
- データがDBに正しく保存されているか
- スクレイピングが成功しているか

```bash
# データ確認
python scraper/check_data_status.py
```

### Phase 2: 小規模収集（1-2時間）

動作確認後、少し規模を拡大します。

```bash
# 推奨: 3日分、全会場、5秒/リクエスト
python scraper/collect_gentle.py --days 3 --rate 5

# 所要時間: 約1-2時間（864レース × 5秒）
```

### Phase 3: 本格収集（3-10時間）

本格的にデータを収集します。

```bash
# 標準: 7日分、全会場、5秒/リクエスト
python scraper/collect_all_venues.py

# または
python scraper/collect_gentle.py --days 7 --rate 5

# 所要時間: 約4-5時間（2,016レース × 5秒）
```

**推奨実行時間:**
- 夜間（23:00-07:00）
- サーバー負荷が低い時間帯

### Phase 4: 過去データ収集（GitHub Actions）

GitHub Actionsで自動的に過去データを収集します。

1. GitHubリポジトリの **Actions** タブを開く
2. **Scrape Historical Data** を選択
3. **Run workflow** をクリック
4. パラメータ設定:
   - `phase`: 1（直近1年分）
   - `days`: 7（1回で7日分）

**自動実行:**
- 毎日深夜3時（JST）に自動実行
- 1日1日分ずつ収集
- 数ヶ月かけて徐々にデータを蓄積

---

## 🛡️ 負荷対策の詳細

### 現在の実装（すべて実装済み）

#### 1. レート制限
```python
# デフォルト設定
requests_per_second = 0.2    # 5秒に1リクエスト
requests_per_minute = 20     # 1分に20リクエスト
requests_per_hour = 500      # 1時間に500リクエスト
requests_per_day = 10000     # 1日に10,000リクエスト
```

#### 2. 並行リクエスト制限
```python
concurrent_requests = 1  # 同時に1つのみ実行
```

#### 3. リトライ機構
- 最大3回まで自動リトライ
- 指数バックオフ（2秒 → 10秒 → 25秒）
- 429エラー（レート制限）を検出して待機

#### 4. 既存データのスキップ
- DBをチェックして収集済みデータを自動スキップ
- 重複収集を防止

#### 5. タイムアウト設定
```python
timeout = 30秒  # リクエストタイムアウト
```

### レート制限の調整指針

| 用途 | リクエスト間隔 | 推定時間（1週間分） | 負荷レベル |
|------|---------------|-------------------|-----------|
| テスト | 10秒/req | 約8-10時間 | 最小 ⭐⭐⭐ |
| 推奨 | 5秒/req | 約4-5時間 | 低 ⭐⭐ |
| 標準 | 3秒/req | 約2.5-3時間 | 中 ⭐ |
| 高速 | 2秒/req | 約1.5-2時間 | 高（非推奨） |

**推奨:**
- 初回: 10秒/req
- 通常: 5秒/req
- 急ぎ: 3秒/req（夜間のみ）

---

## 💻 使用方法

### collect_gentle.py の使い方

#### 基本的な使用方法

```bash
# デフォルト設定（7日分、全会場、5秒/req）
python scraper/collect_gentle.py
```

#### オプション一覧

```bash
# 日数を指定
python scraper/collect_gentle.py --days 3

# 会場を指定（範囲）
python scraper/collect_gentle.py --venues 1-5

# 会場を指定（個別）
python scraper/collect_gentle.py --venues 1,3,5,10

# レート制限を調整
python scraper/collect_gentle.py --rate 10

# 最大収集数を制限
python scraper/collect_gentle.py --max-races 100

# 開始会場を指定
python scraper/collect_gentle.py --start-venue 10

# 詳細ログを表示
python scraper/collect_gentle.py --verbose

# 組み合わせ例
python scraper/collect_gentle.py --days 3 --venues 1-5 --rate 10 --max-races 100
```

#### 推奨コマンド例

```bash
# テスト: 1日分、会場1-3、10秒間隔
python scraper/collect_gentle.py --days 1 --venues 1-3 --rate 10

# 慎重: 3日分、全会場、10秒間隔
python scraper/collect_gentle.py --days 3 --rate 10

# 標準: 7日分、全会場、5秒間隔
python scraper/collect_gentle.py --days 7 --rate 5

# 少量テスト: 最大50レース
python scraper/collect_gentle.py --max-races 50 --rate 10

# 特定会場のみ: 会場10-15
python scraper/collect_gentle.py --venues 10-15 --days 7
```

### プログレスバーのインストール（オプション）

```bash
# より見やすい進捗表示のため
pip install tqdm
```

---

## 🔍 トラブルシューティング

### エラー1: "Connection timeout"
**原因:** ネットワーク接続が不安定

**解決策:**
- レート制限を緩くする（10秒/req）
- タイムアウト時間を延長
- ネットワーク接続を確認

### エラー2: "HTTP 429 - Too Many Requests"
**原因:** リクエストが多すぎる

**解決策:**
```bash
# レート制限をさらに緩くする
python scraper/collect_gentle.py --rate 15
```

### エラー3: "Database connection error"
**原因:** DB接続情報が間違っている

**解決策:**
1. `.env` ファイルの`DATABASE_URL`を確認
2. Supabaseの接続情報を確認
3. ネットワーク接続を確認

```bash
# DB接続テスト
python scraper/test_db.py
```

### エラー4: "No data found"
**原因:** 指定した日付・会場にレースがない

**解決策:**
- 過去のレース開催日を確認
- 別の日付や会場を試す

### エラー5: 中断された場合
**対処方法:**

```bash
# 同じコマンドを再実行
# 既存データは自動的にスキップされます
python scraper/collect_gentle.py --days 7 --rate 5
```

---

## 📊 収集後の確認

### データ量の確認

```bash
# データベースの状態を確認
python scraper/check_data_status.py
```

**出力例:**
```
総レース数: 2,016 レース
期間: 2024-01-01 ～ 2024-01-07
データ期間: 7 日間
年数換算: 約 0.0 年分
```

### データの検証

```bash
# データの整合性を確認
python scraper/verify_data.py
```

---

## 📈 収集計画の例

### 目標: 1,000レース（最低限）

```bash
# Week 1: テストと基本収集
python scraper/collect_gentle.py --days 3 --rate 5
# → 約860レース

# Week 2: 追加収集
python scraper/collect_gentle.py --days 2 --rate 5
# → 約580レース

# 合計: 約1,440レース
```

### 目標: 10,000レース（推奨）

```bash
# Phase 1: 直近データ（1-2週間）
python scraper/collect_gentle.py --days 14 --rate 5
# → 約4,030レース

# Phase 2: GitHub Actionsで自動収集（3-4週間）
# .github/workflows/scrape_historical.yml を手動実行
# Phase: 1, Days: 7 で毎週実行
# → 約6,000レース

# 合計: 約10,000レース
```

### 目標: 20,000レース以上（最高精度）

```bash
# GitHub Actionsで長期間自動収集（2-3ヶ月）
# 自動実行に任せて徐々にデータを蓄積
# → 20,000レース以上
```

---

## ⚡ パフォーマンス最適化

### DB接続のプーリング

大量のデータを収集する場合、DB接続をプールします（既に実装済み）。

### メモリ使用量の削減

バッチサイズを調整:
```bash
python scraper/collect_gentle.py --batch-size 5
```

---

## 🎓 ベストプラクティス

1. **段階的に収集する**
   - まず少量でテスト
   - 徐々に規模を拡大

2. **夜間に実行する**
   - サーバー負荷が低い時間帯
   - 23:00-07:00 を推奨

3. **ログを確認する**
   - `scraper_gentle.log` でエラーをチェック

4. **定期的にデータを確認する**
   - `check_data_status.py` で進捗を確認

5. **中断しても大丈夫**
   - 既存データは自動スキップされる
   - 何度でも再実行可能

---

## 📝 まとめ

### すぐに始める

```bash
# Step 1: テスト収集（10分）
python scraper/collect_gentle.py --days 1 --venues 1-3 --rate 10

# Step 2: データ確認
python scraper/check_data_status.py

# Step 3: 本格収集（夜間実行）
python scraper/collect_gentle.py --days 7 --rate 5
```

### 推奨設定

- **レート制限**: 5秒/req（慎重なら10秒）
- **並行リクエスト**: 1
- **実行時間**: 夜間（23:00-07:00）
- **データ確認**: 定期的に実行

**双方のサーバーに優しい収集を心がけましょう！**
