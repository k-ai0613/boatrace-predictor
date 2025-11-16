"""
データベース接続とデータ挿入のテスト
"""
import os
from dotenv import load_dotenv
import psycopg2
from datetime import datetime

load_dotenv()

def test_db_connection():
    """データベース接続テスト"""
    print("=== Database Connection Test ===")

    try:
        # 環境変数の確認
        db_url = os.getenv('DATABASE_URL')
        print(f"DATABASE_URL: {db_url[:50]}...")

        # データベース接続
        print("\n1. Connecting to database...")
        conn = psycopg2.connect(db_url)
        print("[OK] Connection successful!")

        # テーブルの確認
        print("\n2. Checking tables...")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        print(f"[OK] Found {len(tables)} tables:")
        for table in tables:
            print(f"  - {table[0]}")

        # テストデータの挿入
        print("\n3. Inserting test data...")
        cursor.execute("""
            INSERT INTO races (race_date, venue_id, race_number, grade)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
        """, (datetime.now().date(), 1, 1, 'TEST'))

        race_id = cursor.fetchone()[0]
        print(f"[OK] Test race inserted with ID: {race_id}")

        # データの確認
        print("\n4. Checking inserted data...")
        cursor.execute("SELECT COUNT(*) FROM races;")
        count = cursor.fetchone()[0]
        print(f"[OK] Total races in database: {count}")

        # テストデータの削除
        print("\n5. Cleaning up test data...")
        cursor.execute("DELETE FROM races WHERE grade = 'TEST';")
        conn.commit()
        print("[OK] Test data cleaned up")

        cursor.close()
        conn.close()

        print("\n=== All tests passed! ===")
        return True

    except Exception as e:
        print(f"\n[ERROR] {e}")
        return False

if __name__ == '__main__':
    test_db_connection()
