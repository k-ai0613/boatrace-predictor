#!/usr/bin/env python3
"""
racesテーブルのスキーマを確認するスクリプト
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def check_schema():
    """テーブルスキーマを確認"""
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()

    print("=" * 80)
    print("  racesテーブルのカラム情報")
    print("=" * 80)
    print()

    cur.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'races'
        ORDER BY ordinal_position
    """)

    results = cur.fetchall()
    for column_name, data_type in results:
        print(f"{column_name:30} : {data_type}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    try:
        check_schema()
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
