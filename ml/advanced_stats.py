"""
会場別選手成績計算スクリプト

選手の会場別（当地）成績を計算してデータベースに保存
- 会場別勝率
- 会場別2連対率
- 会場別3連対率
- 会場別平均ST
"""
import os
import sys
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_batch

load_dotenv()


def fetch_race_data():
    """データベースからレースデータを取得"""
    print("=== レースデータを取得中 ===\n")

    conn = psycopg2.connect(os.getenv('DATABASE_URL'))

    query = """
        SELECT
            re.racer_id,
            r.venue_id,
            r.race_date,
            re.result_position,
            re.start_timing
        FROM race_entries re
        JOIN races r ON re.race_id = r.id
        WHERE re.result_position IS NOT NULL
        ORDER BY r.race_date, r.venue_id
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    print(f"取得データ数: {len(df)}件")
    print(f"選手数: {df['racer_id'].nunique()}名")
    print(f"会場数: {df['venue_id'].nunique()}場")
    print(f"日付範囲: {df['race_date'].min()} ～ {df['race_date'].max()}\n")

    return df


def calculate_venue_stats(df, min_races=5):
    """
    会場別選手成績を計算

    Args:
        df: レースデータ
        min_races: 最低レース数（この数以下のデータは統計として信頼性が低いため除外）

    Returns:
        DataFrame: 会場別選手成績
    """
    print(f"=== 会場別選手成績を計算中（最低レース数: {min_races}） ===\n")

    # 選手×会場でグループ化
    grouped = df.groupby(['racer_id', 'venue_id'])

    stats_list = []

    for (racer_id, venue_id), group in grouped:
        race_count = len(group)

        # 最低レース数を満たさない場合はスキップ
        if race_count < min_races:
            continue

        # 勝率（1着率）
        win_rate = (group['result_position'] == 1).sum() / race_count * 100

        # 2連対率（1着または2着）
        second_rate = (group['result_position'] <= 2).sum() / race_count * 100

        # 3連対率（1着、2着、または3着）
        third_rate = (group['result_position'] <= 3).sum() / race_count * 100

        # 平均ST
        avg_st = group['start_timing'].mean()

        # 平均着順
        avg_position = group['result_position'].mean()

        stats_list.append({
            'racer_id': racer_id,
            'venue_id': venue_id,
            'race_count': race_count,
            'win_rate': win_rate,
            'second_rate': second_rate,
            'third_rate': third_rate,
            'avg_start_timing': avg_st,
            'avg_position': avg_position
        })

    stats_df = pd.DataFrame(stats_list)

    print(f"計算完了: {len(stats_df)}件の統計")
    print(f"選手数: {stats_df['racer_id'].nunique()}名")
    print(f"平均レース数: {stats_df['race_count'].mean():.1f}レース")
    print(f"平均勝率: {stats_df['win_rate'].mean():.2f}%\n")

    return stats_df


def create_racer_venue_stats_table():
    """racer_venue_statsテーブルを作成"""
    print("=== racer_venue_stats テーブルを作成 ===\n")

    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()

    # テーブルが存在する場合は削除
    cursor.execute("DROP TABLE IF EXISTS racer_venue_stats")

    # テーブル作成
    cursor.execute("""
        CREATE TABLE racer_venue_stats (
            id SERIAL PRIMARY KEY,
            racer_id INT NOT NULL,
            venue_id INT NOT NULL,
            race_count INT NOT NULL,
            win_rate FLOAT,
            second_rate FLOAT,
            third_rate FLOAT,
            avg_start_timing FLOAT,
            avg_position FLOAT,
            updated_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(racer_id, venue_id)
        )
    """)

    # インデックス作成
    cursor.execute("""
        CREATE INDEX idx_racer_venue_stats_racer
        ON racer_venue_stats(racer_id)
    """)

    cursor.execute("""
        CREATE INDEX idx_racer_venue_stats_venue
        ON racer_venue_stats(venue_id)
    """)

    conn.commit()
    cursor.close()
    conn.close()

    print("テーブル作成完了\n")


def save_to_database(stats_df):
    """統計データをデータベースに保存"""
    print("=== データベースに保存中 ===\n")

    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()

    # データをタプルのリストに変換
    data = [
        (
            row['racer_id'],
            row['venue_id'],
            row['race_count'],
            row['win_rate'],
            row['second_rate'],
            row['third_rate'],
            row['avg_start_timing'],
            row['avg_position']
        )
        for _, row in stats_df.iterrows()
    ]

    # バッチで挿入
    execute_batch(cursor, """
        INSERT INTO racer_venue_stats
        (racer_id, venue_id, race_count, win_rate, second_rate, third_rate,
         avg_start_timing, avg_position)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (racer_id, venue_id)
        DO UPDATE SET
            race_count = EXCLUDED.race_count,
            win_rate = EXCLUDED.win_rate,
            second_rate = EXCLUDED.second_rate,
            third_rate = EXCLUDED.third_rate,
            avg_start_timing = EXCLUDED.avg_start_timing,
            avg_position = EXCLUDED.avg_position,
            updated_at = NOW()
    """, data, page_size=1000)

    conn.commit()
    cursor.close()
    conn.close()

    print(f"保存完了: {len(data)}件\n")


def show_sample_stats(stats_df):
    """サンプル統計を表示"""
    print("=== サンプル統計（上位10名） ===\n")

    # 勝率が高い上位10名
    top_10 = stats_df.nlargest(10, 'win_rate')

    print("会場別勝率 Top 10:")
    print("-" * 80)
    for idx, row in top_10.iterrows():
        print(f"選手ID: {row['racer_id']:4d} | "
              f"会場: {row['venue_id']:2d} | "
              f"出走数: {row['race_count']:3d} | "
              f"勝率: {row['win_rate']:5.2f}% | "
              f"2連対率: {row['second_rate']:5.2f}% | "
              f"平均ST: {row['avg_start_timing']:.3f}")

    print()


def main():
    """メイン処理"""
    print("=" * 80)
    print("  会場別選手成績計算")
    print("=" * 80)
    print()

    try:
        # 1. データ取得
        df = fetch_race_data()

        if len(df) == 0:
            print("[ERROR] データが取得できませんでした")
            print("まずデータ収集を実行してください: python scraper/collect_all_venues.py")
            return

        # 2. 会場別統計を計算
        stats_df = calculate_venue_stats(df, min_races=5)

        if len(stats_df) == 0:
            print("[WARNING] 統計データが生成できませんでした")
            print("データが不足している可能性があります")
            return

        # 3. テーブル作成
        create_racer_venue_stats_table()

        # 4. データベースに保存
        save_to_database(stats_df)

        # 5. サンプル統計を表示
        show_sample_stats(stats_df)

        print("=" * 80)
        print("  計算完了！")
        print("=" * 80)
        print()
        print("次のステップ:")
        print("1. モデル訓練時に racer_venue_stats テーブルを使用")
        print("2. feature_engineer.py で会場別勝率を特徴量に追加")
        print("3. 精度向上を確認（+1-2%の改善を期待）")

    except Exception as e:
        print(f"\n[ERROR] エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
