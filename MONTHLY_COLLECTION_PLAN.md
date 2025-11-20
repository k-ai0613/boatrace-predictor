# 月次データ収集計画

2023年6月～2025年11月の30ヶ月分のデータを月ごとに収集します。

## 📊 収集概要

- **総期間**: 2023-06 ～ 2025-11（30ヶ月）
- **推定総レース数**: 約260,000レース
- **1ヶ月あたりの推定レース数**: 約8,600レース
- **1ヶ月あたりの推定実行時間**: 3-4時間
- **リクエスト間隔**: 2秒（サーバー負荷軽減）

## 🎯 実行方法

### GitHub Actionsで実行（推奨）

1. GitHub リポジトリの **Actions** タブに移動
2. 左側から **Monthly Data Backfill** を選択
3. **Run workflow** ボタンをクリック
4. 年月を入力（例: `2023-06`）
5. **Run workflow** で実行開始

### ローカルで実行

```bash
cd scraper
python collect_monthly.py --year-month 2023-06
```

## ✅ 収集進捗チェックリスト

### 2023年（7ヶ月）

- [ ] 2023-06（6月）
- [ ] 2023-07（7月）
- [ ] 2023-08（8月）
- [ ] 2023-09（9月）
- [ ] 2023-10（10月）
- [ ] 2023-11（11月）
- [ ] 2023-12（12月）

### 2024年（12ヶ月）

- [ ] 2024-01（1月）
- [ ] 2024-02（2月）
- [ ] 2024-03（3月）
- [ ] 2024-04（4月）
- [ ] 2024-05（5月）
- [ ] 2024-06（6月）
- [ ] 2024-07（7月）
- [ ] 2024-08（8月）
- [ ] 2024-09（9月）
- [ ] 2024-10（10月）
- [ ] 2024-11（11月）
- [ ] 2024-12（12月）

### 2025年（11ヶ月）

- [ ] 2025-01（1月）
- [ ] 2025-02（2月）
- [ ] 2025-03（3月）
- [ ] 2025-04（4月）
- [ ] 2025-05（5月）
- [ ] 2025-06（6月）
- [ ] 2025-07（7月）
- [ ] 2025-08（8月）
- [ ] 2025-09（9月）
- [ ] 2025-10（10月）
- [ ] 2025-11（11月）

## 📅 推奨実行スケジュール

### パターンA: 週末集中型
毎週末に5-6ヶ月分を実行

- **第1週末**: 2023-06 ～ 2023-11（6ヶ月）
- **第2週末**: 2023-12 ～ 2024-05（6ヶ月）
- **第3週末**: 2024-06 ～ 2024-11（6ヶ月）
- **第4週末**: 2024-12 ～ 2025-05（6ヶ月）
- **第5週末**: 2025-06 ～ 2025-11（6ヶ月）

### パターンB: 分散型
毎日1-2ヶ月ずつ実行

- 1日1ヶ月 → 約30日で完了
- 1日2ヶ月 → 約15日で完了

## 🔍 データ確認方法

### Supabaseで確認

```sql
-- 月ごとのレース数を確認
SELECT
    DATE_TRUNC('month', race_date) as month,
    COUNT(*) as race_count
FROM races
WHERE race_date >= '2023-06-01'
GROUP BY month
ORDER BY month;

-- 月ごとのデータ完全性を確認
SELECT
    DATE_TRUNC('month', r.race_date) as month,
    COUNT(*) as total_entries,
    COUNT(re.racer_grade) as has_grade,
    ROUND(COUNT(re.racer_grade)::numeric / COUNT(*) * 100, 1) as completeness_pct
FROM race_entries re
JOIN races r ON re.race_id = r.id
WHERE r.race_date >= '2023-06-01'
GROUP BY month
ORDER BY month;
```

### ローカルPythonで確認

```bash
cd scraper
python -c "
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cursor = conn.cursor()

cursor.execute('''
    SELECT
        TO_CHAR(race_date, 'YYYY-MM') as month,
        COUNT(*) as race_count
    FROM races
    WHERE race_date >= '2023-06-01'
    GROUP BY TO_CHAR(race_date, 'YYYY-MM')
    ORDER BY month
''')

print('Month      | Races')
print('-----------+-------')
for row in cursor.fetchall():
    print(f'{row[0]} | {row[1]:5d}')

conn.close()
"
```

## ⚠️ 注意事項

1. **サーバー負荷**
   - リクエスト間隔は最低2秒を維持
   - 連続実行は避け、月ごとに間隔を空ける

2. **GitHub Actions制限**
   - タイムアウト: 6時間
   - 1ヶ月分は通常3-4時間で完了
   - 失敗時は該当月を再実行

3. **データベース容量**
   - 30ヶ月分で約1.5GB必要
   - Supabaseの容量制限に注意

4. **エラー対応**
   - ログファイルを確認（Artifactsからダウンロード）
   - 失敗した月は再実行可能
   - ON CONFLICT処理により重複実行OK

## 📈 完了後の次ステップ

1. **データ品質確認**
   - 各月のデータ完全性チェック
   - NULL率の確認

2. **機械学習モデル訓練**
   - `ml/train_full_pipeline.py` 実行
   - ハイパーパラメータ最適化

3. **予測API統合**
   - トレーニング済みモデルをAPIに組み込み
   - リアルタイム予測機能の実装

4. **継続運用**
   - 日次自動収集（毎日深夜2時＋夕方6時）
   - 月次バックフィル（必要に応じて）

---

**作成日**: 2025-11-20
**最終更新**: 2025-11-20
