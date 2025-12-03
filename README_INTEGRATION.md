# フロントエンド統合ガイド

競艇予測システムのフロントエンド統合が完了しました。このガイドでは、システムの使い方とテスト方法を説明します。

---

## 📋 完成した機能

### ✅ バックエンド（ML）
- ✅ `ml/predict_race.py` - レース予測スクリプト
  - 訓練済みモデル（`ml/trained_model_latest.pkl`）を使用
  - race_idを指定して予測を実行
  - 結果をDBの`predictions`テーブルに保存

### ✅ API
- ✅ `/api/predict` - 予測API
  - Pythonスクリプトを呼び出してML予測を実行
  - 既存の予測があればそれを返す
  - エラー時はフォールバック（均等確率）を返す

- ✅ `/api/races` - レースデータ取得API
- ✅ `/api/analytics/course` - コース統計API
- ✅ `/api/analytics/boats` - 艇別統計API
- ✅ `/api/analytics/top-racers` - トップ選手API

### ✅ フロントエンド
- ✅ `/app/analytics` - 分析ダッシュボード
  - レース予測タブ
  - 艇別データタブ
  - 選手ランキングタブ
  - コース分析タブ

- ✅ コンポーネント
  - `RacePrediction` - 予測結果表示
  - `RaceSelector` - レース選択
  - `BoatStatistics` - 艇別統計
  - `CourseAnalysis` - コース分析
  - `TopRacers` - トップ選手ランキング

---

## 🚀 使用方法

### 1. 前提条件

#### データベース
- Supabaseプロジェクトのセットアップ完了
- 以下のテーブルが存在すること:
  - `races` - レース情報
  - `race_entries` - 出走情報
  - `racers` - 選手情報
  - `predictions` - 予測結果
  - `weather_data` - 天気データ（オプション）
  - `racer_venue_stats` - 会場別選手統計（オプション）

#### Python環境
```bash
# 必要なパッケージがインストール済みであること
pip install -r scraper/requirements.txt

# または個別に
pip install xgboost scikit-learn pandas numpy psycopg2-binary python-dotenv
```

#### モデルファイル
- `ml/trained_model_latest.pkl` が存在すること
- まだない場合は、先にモデルを訓練:
```bash
python ml/train_model.py
```

#### 環境変数
`.env` ファイルに以下を設定:
```env
DATABASE_URL=postgresql://user:password@host:port/database
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

### 2. 開発サーバーの起動

```bash
# Next.js開発サーバーを起動
npm run dev
```

ブラウザで http://localhost:3000 を開く

### 3. 予測機能の使用

#### 方法1: フロントエンドから
1. http://localhost:3000/analytics にアクセス
2. 「レース予測」タブを開く
3. 会場・日付・レース番号を選択
4. 予測結果が表示されます

#### 方法2: API直接呼び出し
```bash
# cURLで予測APIを呼び出し
curl -X POST http://localhost:3000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"raceId": 12345}'
```

#### 方法3: Pythonスクリプト直接実行
```bash
# レースID 12345 の予測を実行
python ml/predict_race.py 12345

# 静かモード（JSON出力のみ）
python ml/predict_race.py 12345 --quiet

# DBに保存しない（テスト用）
python ml/predict_race.py 12345 --no-save
```

---

## 🔍 動作確認手順

### Step 1: データ確認
```bash
# データベースに十分なデータがあるか確認
python scraper/check_data_status.py
```

**必要最低限:**
- レース数: 1,000レース以上
- 選手数: 100名以上
- データ期間: 3ヶ月以上

### Step 2: モデルの存在確認
```bash
# モデルファイルが存在するか確認
ls -l ml/trained_model_latest.pkl
```

存在しない場合:
```bash
# モデルを訓練
python ml/train_model.py
```

### Step 3: Python予測スクリプトのテスト
```bash
# 既存のレースIDで予測をテスト
# レースIDはDBから取得
python ml/predict_race.py <race_id>
```

**確認ポイント:**
- エラーなく実行完了
- "Saved to predictions table" と表示される
- 各艇の1着確率が表示される

### Step 4: APIのテスト
```bash
# 開発サーバーを起動
npm run dev

# 別のターミナルでAPIをテスト
curl -X POST http://localhost:3000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"raceId": <race_id>}'
```

**期待される出力:**
```json
{
  "predictions": [
    {
      "boatNumber": 1,
      "racerName": "選手名",
      "racerNumber": 1234,
      "grade": "A1",
      "motorNumber": "12",
      "winProb": 0.35,
      "secondProb": 0.20,
      ...
    },
    ...
  ],
  "recommendations": [
    {
      "type": "単勝",
      "bet": "1",
      "probability": 0.35,
      "confidence": "中"
    },
    ...
  ],
  "modelVersion": "trained_model_latest"
}
```

### Step 5: フロントエンドのテスト
1. http://localhost:3000/analytics にアクセス
2. 「レース予測」タブを選択
3. レースを選択して予測を表示
4. 以下が正しく表示されるか確認:
   - 推奨買い目（単勝、2連単、3連単等）
   - 天候情報（風速、気温など）
   - レース分析コメント
   - 各艇の着順確率予測

---

## ⚠️ トラブルシューティング

### エラー1: "Model file not found"
**原因:** モデルファイルが存在しない

**解決策:**
```bash
# モデルを訓練
python ml/train_model.py
```

### エラー2: "Race ID not found"
**原因:** 指定したrace_idがDBに存在しない

**解決策:**
```bash
# DBから有効なrace_idを取得
psql $DATABASE_URL -c "SELECT id FROM races LIMIT 10;"
```

### エラー3: "Failed to retrieve predictions after generation"
**原因:** Pythonスクリプトの実行に失敗した

**解決策:**
1. Pythonスクリプトを直接実行してエラーを確認:
```bash
python ml/predict_race.py <race_id>
```

2. Pythonのパスを確認:
```bash
# Windowsの場合
where python

# Mac/Linuxの場合
which python3
```

3. 必要なパッケージがインストールされているか確認:
```bash
pip list | grep xgboost
pip list | grep scikit-learn
```

### エラー4: "Race does not have exactly 6 boats"
**原因:** レースデータが不完全

**解決策:**
- 完全なレース（6艇すべてのデータがある）を選択
- データ収集スクリプトを再実行

### エラー5: Next.jsでTypeScriptエラー
**原因:** 型定義の不一致

**解決策:**
```bash
# 型チェック
npm run build

# エラーがあれば修正
```

### エラー6: 予測が遅い（30秒以上かかる）
**原因:** 過去データが多すぎる

**解決策:**
`ml/predict_race.py` の `fetch_historical_data()` 関数を編集:
```python
# LIMIT 50000 → LIMIT 10000 に変更
query = """
    ...
    LIMIT 10000  -- 処理を高速化
"""
```

---

## 📊 パフォーマンスの目安

| 項目 | 目標値 |
|------|--------|
| Python予測スクリプト実行時間 | 5-15秒 |
| API応答時間（初回） | 10-20秒 |
| API応答時間（キャッシュ済み） | < 1秒 |
| フロントエンド表示速度 | < 2秒 |

---

## 🔧 カスタマイズ

### 予測の精度調整
`ml/hyperparameter_tuning.py` でハイパーパラメータを再最適化:
```bash
python ml/hyperparameter_tuning.py
python ml/train_model.py
```

### 推奨買い目のしきい値調整
`app/api/predict/route.ts` の `calculateRecommendations()` 関数を編集:
```typescript
// 単勝のしきい値を変更
if (pred.winProb > 0.25) {  // 0.25 → 0.30 など
  recommendations.push({
    type: '単勝',
    ...
  })
}
```

### 天気データの追加
1. 天気データを収集:
```bash
python scraper/weather_scraper.py
```

2. GitHub Actionsで自動収集を有効化（既に設定済み）

---

## 📝 次のステップ

### 1. データ収集の強化
- [ ] 天気データの定期収集を開始
- [ ] 過去20年分のデータを収集（GitHub Actions使用）
- [ ] 会場別統計の計算（`python ml/advanced_stats.py`）

### 2. 精度向上
- [ ] より多くのデータでモデルを再訓練
- [ ] ハイパーパラメータの再最適化
- [ ] 特徴量の追加（オッズデータなど）

### 3. 本番環境へのデプロイ
- [ ] Vercelへのデプロイ
- [ ] Python環境のセットアップ（Vercel Serverless Functions）
- [ ] 環境変数の設定
- [ ] ドメインの設定

### 4. 追加機能
- [ ] オッズデータの収集と表示
- [ ] 期待値計算機能
- [ ] 予測履歴の保存と分析
- [ ] ユーザー認証機能

---

## 📖 関連ドキュメント

- **クイックスタートガイド**: `QUICKSTART.md`
- **モデル訓練ガイド**: `README_TRAINING.md`
- **システム設計書**: `boatrace-predictor-design.md`
- **GitHub Actions設定**: `.github/workflows/`

---

## 🎉 完成！

フロントエンドとMLモデルの統合が完了しました。

**現在の状態:**
- ✅ MLモデルとの連携完了
- ✅ 予測API実装完了
- ✅ フロントエンド表示完了
- ✅ エラーハンドリング実装済み

**次のアクション:**
1. データを収集（最低1,000レース）
2. モデルを訓練
3. フロントエンドでレースを選択して予測を確認
4. 精度を確認して改善

**頑張ってください！🚤**
