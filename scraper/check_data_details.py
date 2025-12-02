#!/usr/bin/env python3
"""
データベースの詳細なデータ状況を確認するスクリプト
"""
import os
import psycopg2
from dotenv import load_dotenv
from datetime import datetime

# .envファイルから環境変数を読み込む
load_dotenv()

def check_data_details():
    """データベースの詳細情報を確認"""

    # データベース接続
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()

    print("=" * 80)
    print("  データベース詳細分析レポート")
    print("=" * 80)
    print()

    # 1. 最古・最新のレースデータ
    print("【1. データ期間】")
    print("-" * 80)
    cur.execute("""
        SELECT
            MIN(race_date) as oldest_date,
            MAX(race_date) as newest_date,
            COUNT(*) as total_races
        FROM races
    """)
    result = cur.fetchone()
    if result:
        oldest, newest, total = result
        print(f"最古のレース: {oldest}")
        print(f"最新のレース: {newest}")
        print(f"総レース数: {total:,} レース")
        if oldest and newest:
            days = (newest - oldest).days
            print(f"期間: {days} 日間")
    print()

    # 2. 年別レース数
    print("【2. 年別レース数】")
    print("-" * 80)
    cur.execute("""
        SELECT
            EXTRACT(YEAR FROM race_date) as year,
            COUNT(*) as race_count
        FROM races
        GROUP BY EXTRACT(YEAR FROM race_date)
        ORDER BY year DESC
    """)
    results = cur.fetchall()
    for year, count in results:
        print(f"{int(year)}年: {count:,} レース")
    print()

    # 3. 月別レース数（直近12ヶ月）
    print("【3. 月別レース数（直近データ）】")
    print("-" * 80)
    cur.execute("""
        SELECT
            TO_CHAR(race_date, 'YYYY-MM') as month,
            COUNT(*) as race_count
        FROM races
        GROUP BY TO_CHAR(race_date, 'YYYY-MM')
        ORDER BY month DESC
        LIMIT 12
    """)
    results = cur.fetchall()
    for month, count in results:
        print(f"{month}: {count:,} レース")
    print()

    # 4. 会場別レース数（上位10会場）
    print("【4. 会場別レース数（上位10会場）】")
    print("-" * 80)
    cur.execute("""
        SELECT
            venue_id,
            COUNT(*) as race_count
        FROM races
        GROUP BY venue_id
        ORDER BY race_count DESC
        LIMIT 10
    """)
    results = cur.fetchall()
    for venue_id, count in results:
        print(f"会場ID {venue_id}: {count:,} レース")
    print()

    # 5. データの完全性チェック
    print("【5. データ完全性チェック】")
    print("-" * 80)

    # レースに対する出走データ
    cur.execute("""
        SELECT
            COUNT(DISTINCT r.race_id) as races_with_entries,
            (SELECT COUNT(*) FROM races) as total_races
        FROM race_entries r
    """)
    result = cur.fetchone()
    if result:
        with_entries, total = result
        percentage = (with_entries / total * 100) if total > 0 else 0
        print(f"出走データがあるレース: {with_entries:,} / {total:,} ({percentage:.1f}%)")

    # レースに対する天気データ
    cur.execute("""
        SELECT
            COUNT(DISTINCT w.race_id) as races_with_weather,
            (SELECT COUNT(*) FROM races) as total_races
        FROM weather_data w
    """)
    result = cur.fetchone()
    if result:
        with_weather, total = result
        percentage = (with_weather / total * 100) if total > 0 else 0
        print(f"天気データがあるレース: {with_weather:,} / {total:,} ({percentage:.1f}%)")
    print()

    # 6. 推奨事項
    print("=" * 80)
    print("  推奨事項")
    print("=" * 80)
    print()

    # データ期間をチェック
    cur.execute("SELECT MIN(race_date), MAX(race_date) FROM races")
    oldest, newest = cur.fetchone()

    if oldest and newest:
        days_span = (newest - oldest).days
        years_span = days_span / 365.25

        if years_span < 1.0:
            print("⚠️  データ期間が1年未満です")
            print("   推奨: 過去1-3年分のデータを収集してください")
            print()
            print("   データ収集コマンド:")
            print("   python scraper/collect_gentle.py --days 365 --rate 5")
        elif years_span < 3.0:
            print("✓  データ期間: 約 {:.1f} 年分".format(years_span))
            print("   より精度を高めるには、さらに過去データの収集を推奨")
        else:
            print("✓  データ期間: 約 {:.1f} 年分（十分）".format(years_span))

    print()
    print("=" * 80)

    cur.close()
    conn.close()

if __name__ == "__main__":
    try:
        check_data_details()
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
