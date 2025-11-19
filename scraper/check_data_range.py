#!/usr/bin/env python3
"""
データベース内のレースデータ範囲を確認
"""
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()


def check_data_range():
    """データ範囲を確認"""
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()

    try:
        # 最古と最新の日付を取得
        cursor.execute("""
            SELECT
                MIN(race_date) as oldest_date,
                MAX(race_date) as newest_date,
                COUNT(*) as total_races,
                COUNT(DISTINCT race_date) as total_days,
                COUNT(DISTINCT venue_id) as total_venues
            FROM races
        """)

        result = cursor.fetchone()

        if result and result[0]:
            oldest, newest, total_races, total_days, total_venues = result

            print("=" * 60)
            print("データベース内のレースデータ範囲")
            print("=" * 60)
            print(f"最古のレース日: {oldest}")
            print(f"最新のレース日: {newest}")
            print(f"総レース数: {total_races:,}")
            print(f"総日数: {total_days}")
            print(f"会場数: {total_venues}")
            print("=" * 60)

            # フェーズ1データの充足率を確認
            cursor.execute("""
                SELECT
                    COUNT(*) as total_entries,
                    COUNT(local_win_rate) as has_local_win_rate,
                    COUNT(average_st) as has_average_st,
                    COUNT(actual_course) as has_actual_course
                FROM race_entries
            """)

            entry_result = cursor.fetchone()
            if entry_result:
                total, local_wr, avg_st, course = entry_result

                print("\nフェーズ1データの充足率:")
                print(f"総エントリー数: {total:,}")
                print(f"当地勝率あり: {local_wr:,} ({local_wr/total*100:.1f}%)")
                print(f"平均STあり: {avg_st:,} ({avg_st/total*100:.1f}%)")
                print(f"進入コースあり: {course:,} ({course/total*100:.1f}%)")
                print("=" * 60)

                # バックフィル必要日数を計算
                days_to_backfill = total_days
                print(f"\nバックフィル対象: 約{days_to_backfill}日分")
                print(f"推定所要時間: 約{days_to_backfill * 0.05:.1f}〜{days_to_backfill * 0.1:.1f}時間")

        else:
            print("データベースにレースデータがありません")

    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    check_data_range()
