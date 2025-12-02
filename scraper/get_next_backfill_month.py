#!/usr/bin/env python3
"""
次に収集すべき月を自動判定するスクリプト

データベース内の最古のデータから、その前月を返します。
2022年1月より古い場合は、収集完了とみなします。
"""
import os
import sys
import psycopg2
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv

load_dotenv()

def get_next_backfill_month(force_month=None):
    """
    次に収集すべき月を取得

    Args:
        force_month: 強制的に指定する月（YYYY-MM形式）

    Returns:
        str: YYYY-MM形式の月、または None（収集完了時）
    """
    # 強制指定がある場合
    if force_month:
        return force_month

    # データベース接続
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()

        # 最古のデータを取得
        cur.execute("SELECT MIN(race_date) FROM races")
        result = cur.fetchone()
        oldest_date = result[0] if result else None

        cur.close()
        conn.close()

        if not oldest_date:
            # データがない場合は2024-12から開始
            return "2024-12"

        # 最古のデータの前月を収集対象とする
        target_date = oldest_date - relativedelta(months=1)

        # 2020年1月より古い場合は終了
        if target_date.year < 2020:
            return None

        return target_date.strftime('%Y-%m')

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        # エラー時は2024-12から開始（安全策）
        return "2024-12"

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Determine next month to backfill'
    )
    parser.add_argument(
        '--force-month',
        type=str,
        default=None,
        help='Force specific month (YYYY-MM format)'
    )

    args = parser.parse_args()

    target_month = get_next_backfill_month(args.force_month)

    if target_month:
        print(target_month)
        sys.exit(0)
    else:
        print("COMPLETED", file=sys.stderr)
        sys.exit(1)
