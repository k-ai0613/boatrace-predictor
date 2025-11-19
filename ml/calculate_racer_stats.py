"""
レーサー統計計算スクリプト
過去のレース結果から各レーサーの統計データを計算してracer_statisticsテーブルに保存
"""
import os
import json
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import Json
from datetime import datetime

load_dotenv()


def calculate_stats_for_racer(cursor, racer_number):
    """指定レーサーの統計を計算"""
    stats = {
        'weather': {},
        'venue': {},
        'course': {},
        'winning_technique': {}
    }

    # データ範囲を取得
    cursor.execute("""
        SELECT MIN(r.race_date), MAX(r.race_date)
        FROM race_entries re
        JOIN races r ON re.race_id = r.id
        WHERE re.racer_id = %s
    """, (racer_number,))
    date_range = cursor.fetchone()
    data_from_date = date_range[0] if date_range else None
    data_to_date = date_range[1] if date_range else None

    # 天候別統計
    cursor.execute("""
        SELECT
            wd.weather_condition,
            COUNT(*) as races,
            SUM(CASE WHEN re.result_position = 1 THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN re.result_position <= 2 THEN 1 ELSE 0 END) as place_2,
            SUM(CASE WHEN re.result_position <= 3 THEN 1 ELSE 0 END) as place_3
        FROM race_entries re
        JOIN races r ON re.race_id = r.id
        LEFT JOIN weather_data wd ON wd.race_id = r.id
        WHERE re.racer_id = %s AND re.result_position IS NOT NULL
        GROUP BY wd.weather_condition
    """, (racer_number,))

    for row in cursor.fetchall():
        weather, races, wins, place_2, place_3 = row
        if weather:  # NULL weather は除外
            stats['weather'][weather] = {
                'races': races,
                'wins': wins,
                'place_2': place_2,
                'place_3': place_3,
                'win_rate': round(wins / races * 100, 2) if races > 0 else 0,
                'place_rate_2': round(place_2 / races * 100, 2) if races > 0 else 0,
                'place_rate_3': round(place_3 / races * 100, 2) if races > 0 else 0
            }

    # 会場別統計
    cursor.execute("""
        SELECT
            r.venue_id,
            COUNT(*) as races,
            SUM(CASE WHEN re.result_position = 1 THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN re.result_position <= 2 THEN 1 ELSE 0 END) as place_2,
            SUM(CASE WHEN re.result_position <= 3 THEN 1 ELSE 0 END) as place_3
        FROM race_entries re
        JOIN races r ON re.race_id = r.id
        WHERE re.racer_id = %s AND re.result_position IS NOT NULL
        GROUP BY r.venue_id
    """, (racer_number,))

    for row in cursor.fetchall():
        venue_id, races, wins, place_2, place_3 = row
        stats['venue'][str(venue_id)] = {
            'races': races,
            'wins': wins,
            'place_2': place_2,
            'place_3': place_3,
            'win_rate': round(wins / races * 100, 2) if races > 0 else 0,
            'place_rate_2': round(place_2 / races * 100, 2) if races > 0 else 0,
            'place_rate_3': round(place_3 / races * 100, 2) if races > 0 else 0
        }

    # コース別統計（実績ベース）
    cursor.execute("""
        SELECT
            re.actual_course,
            COUNT(*) as races,
            SUM(CASE WHEN re.result_position = 1 THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN re.result_position <= 2 THEN 1 ELSE 0 END) as place_2,
            SUM(CASE WHEN re.result_position <= 3 THEN 1 ELSE 0 END) as place_3
        FROM race_entries re
        WHERE re.racer_id = %s AND re.result_position IS NOT NULL AND re.actual_course IS NOT NULL
        GROUP BY re.actual_course
    """, (racer_number,))

    for row in cursor.fetchall():
        course, races, wins, place_2, place_3 = row
        stats['course'][str(course)] = {
            'races': races,
            'wins': wins,
            'place_2': place_2,
            'place_3': place_3,
            'win_rate': round(wins / races * 100, 2) if races > 0 else 0,
            'place_rate_2': round(place_2 / races * 100, 2) if races > 0 else 0,
            'place_rate_3': round(place_3 / races * 100, 2) if races > 0 else 0
        }

    # 決まり手統計（実績ベース）
    cursor.execute("""
        SELECT
            re.winning_technique,
            COUNT(*) as count
        FROM race_entries re
        WHERE re.racer_id = %s
        AND re.result_position = 1
        AND re.winning_technique IS NOT NULL
        GROUP BY re.winning_technique
    """, (racer_number,))

    for row in cursor.fetchall():
        technique, count = row
        stats['winning_technique'][technique] = count

    return stats, data_from_date, data_to_date


def calculate_all_racer_stats():
    """全レーサーの統計を計算してDBに保存"""
    print("データベース接続中...")
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()

    try:
        # 全レーサーを取得
        cursor.execute("SELECT racer_number FROM racers ORDER BY racer_number")
        racers = cursor.fetchall()

        print(f"統計計算開始... ({len(racers)} 人のレーサー)")

        processed = 0
        for (racer_number,) in racers:
            stats, data_from_date, data_to_date = calculate_stats_for_racer(cursor, racer_number)

            # 統計をDBに保存
            cursor.execute("""
                INSERT INTO racer_statistics
                (racer_number, weather_stats, venue_stats, course_stats, winning_technique_stats,
                 data_from_date, data_to_date, calculated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (racer_number) DO UPDATE
                SET weather_stats = EXCLUDED.weather_stats,
                    venue_stats = EXCLUDED.venue_stats,
                    course_stats = EXCLUDED.course_stats,
                    winning_technique_stats = EXCLUDED.winning_technique_stats,
                    data_from_date = EXCLUDED.data_from_date,
                    data_to_date = EXCLUDED.data_to_date,
                    calculated_at = EXCLUDED.calculated_at
            """, (
                racer_number,
                Json(stats['weather']),
                Json(stats['venue']),
                Json(stats['course']),
                Json(stats['winning_technique']),
                data_from_date,
                data_to_date,
                datetime.now()
            ))

            processed += 1
            if processed % 100 == 0:
                print(f"  処理済み: {processed}/{len(racers)}")
                conn.commit()  # 定期的にコミット

        conn.commit()
        print(f"[OK] 統計計算完了: {processed} 人のレーサー")

        # 結果サマリー
        cursor.execute("SELECT COUNT(*) FROM racer_statistics")
        total_stats = cursor.fetchone()[0]
        print(f"\n統計レコード数: {total_stats}")

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] 統計計算失敗: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    calculate_all_racer_stats()
