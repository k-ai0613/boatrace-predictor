"""
データベースマイグレーションスクリプト
"""
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()


def run_migration():
    """マイグレーションを実行"""
    print("データベース接続中...")
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()

    try:
        print("マイグレーション開始...")

        # 統計テーブル作成マイグレーションを実行
        with open('scraper/migrations/create_racer_statistics.sql', 'r', encoding='utf-8') as f:
            sql = f.read()

        cursor.execute(sql)
        conn.commit()

        print("[OK] Racer statistics table migration completed successfully")

        # 確認 - racer_statistics テーブル
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'racer_statistics'
            ORDER BY ordinal_position
        """)

        print("\n[racer_statistics] テーブル構造:")
        for col_name, col_type in cursor.fetchall():
            print(f"  - {col_name}: {col_type}")

        # テーブルの存在確認
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'racer_statistics'
            )
        """)
        exists = cursor.fetchone()[0]
        print(f"\n[racer_statistics] テーブル作成: {'成功' if exists else '失敗'}")

    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] マイグレーション失敗: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    run_migration()
