"""
race_entriesからracersテーブルに不足している選手を登録
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cursor = conn.cursor()

# race_entriesから不足している選手IDを取得
query = """
    SELECT DISTINCT re.racer_id
    FROM race_entries re
    LEFT JOIN racers rc ON re.racer_id = rc.id
    WHERE rc.id IS NULL
    ORDER BY re.racer_id
"""

cursor.execute(query)
missing_racer_ids = [row[0] for row in cursor.fetchall()]

print(f"不足している選手ID数: {len(missing_racer_ids)}")

if len(missing_racer_ids) > 0:
    print("\n選手を登録中...")

    count = 0
    errors = 0
    for racer_id in missing_racer_ids:
        # racer_id=0はスキップ（既存のracer_number=0と衝突）
        if racer_id == 0:
            continue

        # racer_numberは一意制約があるので使用しない（NULLにする）
        # ただし、NOT NULL制約がある場合はracer_idを使用
        racer_number = racer_id + 10000  # 重複回避のためオフセット
        name = f'Racer{racer_id}'  # 仮の名前

        try:
            cursor.execute("""
                INSERT INTO racers (id, racer_number, name)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (racer_id, racer_number, name))
            conn.commit()  # 各INSERTごとにコミット
            count += 1

            if count % 100 == 0:
                print(f"  {count}名登録...")
        except Exception as e:
            conn.rollback()  # エラー時はロールバック
            errors += 1
            if errors <= 5:  # 最初の5つのエラーのみ表示
                print(f"  Error racer_id={racer_id}: {e}")

    print(f"\n[OK] {count}名の選手を登録しました")
    if errors > 0:
        print(f"[WARNING] {errors}名のエラーがありました")

else:
    print("不足している選手はいません")

# 確認
cursor.execute("SELECT COUNT(*) FROM racers")
total_racers = cursor.fetchone()[0]
print(f"\nracersテーブル総数: {total_racers}")

conn.close()
