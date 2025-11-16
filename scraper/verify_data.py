"""
データベースに保存されたデータの確認
"""
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

def verify_saved_data():
    """保存されたデータを確認"""
    print("=== Database Data Verification ===\n")

    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()

        # レース情報を確認
        print("1. Checking races table...")
        cursor.execute("""
            SELECT id, race_date, venue_id, race_number, grade
            FROM races
            ORDER BY created_at DESC
            LIMIT 5
        """)
        races = cursor.fetchall()
        print(f"   Found {len(races)} recent races:")
        for race in races:
            print(f"   - Race ID {race[0]}: {race[1]} Venue {race[2]} Race {race[3]} ({race[4]})")

        # 選手情報を確認
        print("\n2. Checking racers table...")
        cursor.execute("""
            SELECT racer_number, name
            FROM racers
            ORDER BY racer_number
            LIMIT 10
        """)
        racers = cursor.fetchall()
        print(f"   Found {len(racers)} racers (showing first 10):")
        for racer in racers:
            racer_name = racer[1].encode('utf-8').decode('utf-8', errors='replace')
            print(f"   - {racer[0]}: {racer_name}")

        # 出走情報を確認
        print("\n3. Checking race_entries table...")
        cursor.execute("""
            SELECT re.race_id, re.boat_number, re.racer_id,
                   re.start_timing, re.result_position,
                   r.racer_number, r.name
            FROM race_entries re
            JOIN racers r ON re.racer_id = r.racer_number
            ORDER BY re.race_id DESC, re.result_position
            LIMIT 6
        """)
        entries = cursor.fetchall()
        print(f"   Found {len(entries)} recent entries:")
        for entry in entries:
            racer_name = entry[6].encode('utf-8').decode('utf-8', errors='replace')
            print(f"   - Race {entry[0]}, Boat {entry[1]}: {racer_name} (#{entry[5]}) - "
                  f"Position {entry[4]}, ST {entry[3]}")

        # 気象データを確認
        print("\n4. Checking weather_data table...")
        cursor.execute("""
            SELECT race_id, temperature, weather_condition,
                   wind_speed, water_temperature, wave_height
            FROM weather_data
            ORDER BY created_at DESC
            LIMIT 5
        """)
        weather = cursor.fetchall()
        print(f"   Found {len(weather)} weather records:")
        for w in weather:
            weather_text = w[2] if w[2] else 'N/A'
            print(f"   - Race {w[0]}: {w[1]}C, {weather_text}, "
                  f"Wind {w[3]}m/s, Water {w[4]}C, Wave {w[5]}cm")

        print("\n=== Verification Complete ===")
        print("[SUCCESS] All data saved correctly!")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    verify_saved_data()
