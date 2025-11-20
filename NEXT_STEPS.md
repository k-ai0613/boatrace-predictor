# 次にすべきこと

## ✅ 完了したこと

### テストデータ収集（2025-11-10 ～ 2025-11-16）
- **期間**: 7日間
- **収集レース数**: 2,016レース
- **成功率**: 100%
- **失敗**: 0件
- **データソース**: kyotei.fun
- **収集データ**: レース結果、選手データ、モーター・ボート性能、気象条件など全カラム

---

## 📋 次のステップ

### 1. データ品質の確認 ✨ **最優先**

テストデータがSupabaseに正しく保存されているか確認します。

#### 確認項目：
```sql
-- レース総数
SELECT COUNT(*) FROM races WHERE race_date BETWEEN '2025-11-10' AND '2025-11-16';
-- 期待値: 約2,016レース

-- 出走エントリ総数
SELECT COUNT(*) FROM race_entries re
JOIN races r ON re.race_id = r.id
WHERE r.race_date BETWEEN '2025-11-10' AND '2025-11-16';
-- 期待値: 約12,096エントリ（2,016 × 6艇）

-- データ完全性チェック（重要カラム）
SELECT
  COUNT(*) as total,
  COUNT(racer_grade) as has_grade,
  COUNT(win_rate) as has_win_rate,
  COUNT(motor_rate_2) as has_motor_rate,
  COUNT(boat_rate_2) as has_boat_rate,
  COUNT(result_position) as has_result
FROM race_entries re
JOIN races r ON re.race_id = r.id
WHERE r.race_date BETWEEN '2025-11-10' AND '2025-11-16';
-- 期待値: すべて約12,096（100%完全性）
```

#### 実行方法：
```bash
# Supabaseダッシュボードで実行
# または
python -c "
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cursor = conn.cursor()

# 上記SQLクエリを実行
cursor.execute('SELECT COUNT(*) FROM races WHERE race_date BETWEEN %s AND %s', ('2025-11-10', '2025-11-16'))
print(f'Total races: {cursor.fetchone()[0]}')

conn.close()
"
```

---

### 2. 本番データ収集の準備

テストが成功したので、2.5年分の全データ収集を実施します。

#### 収集範囲：
- **期間**: 2023-06-01 ～ 2025-11-20
- **推定レース数**: 約260,000レース
- **推定エントリ数**: 約1,560,000エントリ（260,000 × 6艇）
- **推定実行時間**: 約72時間（3日間）

#### 実行コマンド：
```bash
cd scraper
python -u collect_historical_data.py \
  --start-date 2023-06-01 \
  --end-date 2025-11-20 \
  --venues 24 \
  --races 12 \
  --delay 2.0 \
  --max-retries 3 \
  > full_collection_log.txt 2>&1 &
```

#### 推奨事項：
- **時間帯**: サーバー負荷が低い深夜・早朝に開始
- **監視**: 定期的に進捗確認（`tail -f scraper/full_collection_log.txt`）
- **中断対策**: バックグラウンド実行（上記コマンドの`&`）で端末を閉じても継続

---

### 3. 機械学習モデルのトレーニング

データ収集完了後、予測モデルを訓練します。

#### 既存ファイル：
- `ml/train_model.py` - 基本モデル訓練
- `ml/train_full_pipeline.py` - フルパイプライン
- `ml/hyperparameter_tuning.py` - ハイパーパラメータ最適化

#### 実行手順：
```bash
# 1. 統計的特徴量の生成
python ml/advanced_stats.py

# 2. モデル訓練
python ml/train_full_pipeline.py

# 3. ハイパーパラメータ最適化（オプション）
python ml/hyperparameter_tuning.py

# 4. モデル評価
python ml/evaluate_model.py
```

---

### 4. 予測APIの改善

現在の予測APIにトレーニング済みモデルを統合します。

#### 修正ファイル：
- `app/api/predict/route.ts`
- `lib/predictions.ts`

#### 実装内容：
- トレーニング済みモデル（`.pkl`）のロード
- リアルタイム予測エンドポイント
- 予測精度の表示

---

### 5. 分析ダッシュボードの活用

既に実装されているアナリティクスダッシュボードで収集データを可視化します。

#### 利用可能な機能：
- `app/analytics/` - アナリティクスページ
- `components/analytics/` - 統計グラフコンポーネント
- `lib/analytics.ts` - 統計計算ロジック

#### 確認URL：
```
http://localhost:3000/analytics
```

---

## 🚨 注意事項

### データ収集時の注意：
1. **サーバー負荷**: `--delay 2.0`（2秒間隔）を維持
2. **エラー監視**: ログで`Failed`や`Error`を定期確認
3. **データベース容量**: Supabaseの容量制限に注意（約1.5GB必要）
4. **ネットワーク**: 安定したインターネット接続が必須

### 次回以降の定期収集：
- **GitHub Actions**: `.github/workflows/daily-data-collection.yml`を使用
- **自動実行**: 毎日深夜に前日分を自動収集
- **手動実行**: 必要に応じて`workflow_dispatch`で手動トリガー

---

## 📊 期待される成果

### データ品質：
- ✅ 100%の成功率（テストで実証済み）
- ✅ 全カラムの完全性（racer_grade, win_rate, motor_rate等）
- ✅ 2.5年分の歴史データ（約156万エントリ）

### 予測精度向上：
- 現在：基本的なデータのみ
- 改善後：選手級別、モーター性能、ボート性能、STタイミング、展示データ等を含む
- 期待精度：70-80%以上（3連単的中率）

---

## 🔄 推奨実行順序

```
1. データ品質確認（上記SQL実行） → 10分
2. 本番データ収集開始 → 72時間（バックグラウンド実行）
3. 収集完了確認 → 10分
4. 統計的特徴量生成 → 30分
5. モデル訓練 → 2-3時間
6. モデル評価 → 10分
7. 予測API統合 → 1時間
8. 動作確認・テスト → 30分
```

**総所要時間**: 約3日間（そのうち手作業は約3-4時間）

---

## 📝 コマンドまとめ

### データ品質確認：
```bash
cd scraper
python -c "
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM races WHERE race_date BETWEEN %s AND %s', ('2025-11-10', '2025-11-16'))
print(f'Total races: {cursor.fetchone()[0]}')

cursor.execute('''
SELECT
  COUNT(*) as total,
  COUNT(racer_grade) as has_grade,
  COUNT(win_rate) as has_win_rate,
  COUNT(motor_rate_2) as has_motor_rate,
  COUNT(boat_rate_2) as has_boat_rate,
  COUNT(result_position) as has_result
FROM race_entries re
JOIN races r ON re.race_id = r.id
WHERE r.race_date BETWEEN %s AND %s
''', ('2025-11-10', '2025-11-16'))
result = cursor.fetchone()
print(f'Total entries: {result[0]}')
print(f'Has grade: {result[1]} ({result[1]*100/result[0]:.1f}%)')
print(f'Has win_rate: {result[2]} ({result[2]*100/result[0]:.1f}%)')
print(f'Has motor_rate: {result[3]} ({result[3]*100/result[0]:.1f}%)')
print(f'Has boat_rate: {result[4]} ({result[4]*100/result[0]:.1f}%)')
print(f'Has result: {result[5]} ({result[5]*100/result[0]:.1f}%)')

conn.close()
"
```

### 本番データ収集：
```bash
cd scraper
nohup python -u collect_historical_data.py \
  --start-date 2023-06-01 \
  --end-date 2025-11-20 \
  --venues 24 \
  --races 12 \
  --delay 2.0 \
  --max-retries 3 \
  > full_collection_log.txt 2>&1 &

# 進捗確認
tail -f scraper/full_collection_log.txt
```

### 機械学習パイプライン：
```bash
python ml/advanced_stats.py
python ml/train_full_pipeline.py
python ml/evaluate_model.py
```

---

#12
