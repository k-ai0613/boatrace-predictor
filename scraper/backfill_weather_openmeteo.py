"""
天気データバックフィル（Open-Meteo API版）

Open-Meteo Historical Weather APIを使用して過去の天気データを取得し、
racesテーブルに保存する。

Open-Meteo API:
- 無料、APIキー不要
- 過去データは1940年から利用可能
- レート制限: 10,000リクエスト/日

使用方法:
    python scraper/backfill_weather_openmeteo.py
    python scraper/backfill_weather_openmeteo.py --limit 500
    python scraper/backfill_weather_openmeteo.py --dry-run
"""

import os
import sys
import time
import argparse
import asyncio
import aiohttp
from datetime import datetime, timedelta
from dotenv import load_dotenv
import psycopg2

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.venue_coordinates import VENUE_COORDINATES

load_dotenv()


class OpenMeteoWeatherBackfiller:
    """Open-Meteo APIを使った天気データバックフィラー"""

    # Open-Meteo Historical Weather API
    API_URL = "https://archive-api.open-meteo.com/v1/archive"

    def __init__(self, delay=0.5):
        """
        Args:
            delay: リクエスト間の遅延（秒）。Open-Meteoは寛容だが、礼儀として設定
        """
        self.delay = delay
        self.session = None
        self.db_conn = psycopg2.connect(os.getenv('DATABASE_URL'))

        # 統計
        self.stats = {
            'processed': 0,
            'updated': 0,
            'failed': 0,
            'api_calls': 0
        }

        # キャッシュ（同日同会場のデータを再利用）
        self.weather_cache = {}

    def get_pending_combinations(self, limit=None):
        """
        天気データが未取得の日×会場の組み合わせを取得
        """
        cursor = self.db_conn.cursor()

        query = """
            SELECT DISTINCT race_date, venue_id
            FROM races
            WHERE temperature IS NULL
            AND race_date < CURRENT_DATE
            ORDER BY race_date DESC, venue_id
        """

        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query)
        combinations = cursor.fetchall()
        cursor.close()

        return combinations

    def get_progress(self):
        """進捗を取得"""
        cursor = self.db_conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(DISTINCT (race_date, venue_id)) FILTER (WHERE temperature IS NOT NULL) as completed,
                COUNT(DISTINCT (race_date, venue_id)) as total
            FROM races
            WHERE race_date < CURRENT_DATE
        """)
        result = cursor.fetchone()
        cursor.close()

        return result[0], result[1]

    async def fetch_weather(self, race_date, venue_id):
        """
        Open-Meteo APIから天気データを取得

        Args:
            race_date: レース日付
            venue_id: 会場ID

        Returns:
            dict: 天気データ、取得失敗時はNone
        """
        # キャッシュチェック
        cache_key = (race_date, venue_id)
        if cache_key in self.weather_cache:
            return self.weather_cache[cache_key]

        # 会場の緯度経度を取得
        venue_info = VENUE_COORDINATES.get(venue_id)
        if not venue_info:
            print(f"  Unknown venue_id: {venue_id}")
            return None

        lat, lon, venue_name = venue_info

        # 日付をフォーマット
        date_str = race_date.strftime('%Y-%m-%d')

        # APIリクエスト
        params = {
            'latitude': lat,
            'longitude': lon,
            'start_date': date_str,
            'end_date': date_str,
            'hourly': 'temperature_2m,wind_speed_10m,wind_direction_10m,weather_code',
            'timezone': 'Asia/Tokyo'
        }

        try:
            self.stats['api_calls'] += 1
            async with self.session.get(
                self.API_URL,
                params=params,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    print(f"  API error {response.status}: {error_text[:100]}")
                    return None

                data = await response.json()
                weather = self.parse_weather(data)

                # キャッシュに保存
                self.weather_cache[cache_key] = weather
                return weather

        except asyncio.TimeoutError:
            print(f"  Timeout: {race_date} venue {venue_id}")
            return None
        except Exception as e:
            print(f"  Error: {race_date} venue {venue_id} - {e}")
            return None

    def parse_weather(self, api_response):
        """
        Open-MeteoのAPIレスポンスを解析

        レース時間帯（12:00-17:00頃）の平均を使用
        """
        try:
            hourly = api_response.get('hourly', {})

            # 時間別データを取得
            temps = hourly.get('temperature_2m', [])
            winds = hourly.get('wind_speed_10m', [])
            wind_dirs = hourly.get('wind_direction_10m', [])
            weather_codes = hourly.get('weather_code', [])

            if not temps:
                return None

            # レース時間帯（12:00-17:00、インデックス12-17）の平均
            race_hours = range(12, 18)

            def avg(data, hours):
                values = [data[h] for h in hours if h < len(data) and data[h] is not None]
                return sum(values) / len(values) if values else None

            temperature = avg(temps, race_hours)
            wind_speed = avg(winds, race_hours)
            wind_direction_deg = avg(wind_dirs, race_hours)

            # 風向きを方位に変換
            wind_direction = self.degree_to_direction(wind_direction_deg)

            # 天気コードを天気条件に変換
            weather_condition = self.code_to_condition(
                weather_codes[14] if len(weather_codes) > 14 else None  # 14時の天気
            )

            return {
                'temperature': round(temperature, 1) if temperature else None,
                'wind_speed': round(wind_speed) if wind_speed else None,
                'wind_direction': wind_direction,
                'water_temperature': None,  # Open-Meteoからは取得不可
                'wave_height': None,  # Open-Meteoからは取得不可
                'weather_condition': weather_condition
            }

        except Exception as e:
            print(f"  Parse error: {e}")
            return None

    def degree_to_direction(self, degrees):
        """風向きの角度を方位に変換"""
        if degrees is None:
            return None

        # 8方位に変換
        directions = ['北', '北東', '東', '南東', '南', '南西', '西', '北西']
        index = round(degrees / 45) % 8
        return directions[index]

    def code_to_condition(self, code):
        """
        WMO Weather Codeを天気条件に変換

        https://open-meteo.com/en/docs
        0: Clear sky
        1-3: Mainly clear, partly cloudy, overcast
        45-48: Fog
        51-57: Drizzle
        61-67: Rain
        71-77: Snow
        80-82: Rain showers
        85-86: Snow showers
        95-99: Thunderstorm
        """
        if code is None:
            return None

        if code == 0:
            return '晴'
        elif code in [1, 2]:
            return '晴'
        elif code == 3:
            return '曇'
        elif code in range(45, 49):
            return '曇'
        elif code in range(51, 58) or code in range(61, 68) or code in range(80, 83):
            return '雨'
        elif code in range(71, 78) or code in range(85, 87):
            return '雪'
        elif code in range(95, 100):
            return '雨'
        else:
            return '曇'

    def update_races_weather(self, race_date, venue_id, weather_data):
        """
        指定日×会場の全レースに天気データを更新
        """
        cursor = self.db_conn.cursor()

        try:
            cursor.execute("""
                UPDATE races
                SET temperature = %s,
                    wind_speed = %s,
                    wind_direction = %s,
                    water_temperature = %s,
                    wave_height = %s,
                    weather_condition = %s
                WHERE race_date = %s AND venue_id = %s
                RETURNING id
            """, (
                weather_data['temperature'],
                weather_data['wind_speed'],
                weather_data['wind_direction'],
                weather_data['water_temperature'],
                weather_data['wave_height'],
                weather_data['weather_condition'],
                race_date,
                venue_id
            ))

            updated_count = cursor.rowcount
            self.db_conn.commit()
            return updated_count

        except Exception as e:
            self.db_conn.rollback()
            print(f"  DB error: {e}")
            return 0
        finally:
            cursor.close()

    async def process_combination(self, race_date, venue_id, dry_run=False):
        """
        1つの日×会場の組み合わせを処理
        """
        self.stats['processed'] += 1

        # 天気データを取得
        weather_data = await self.fetch_weather(race_date, venue_id)

        if weather_data is None:
            self.stats['failed'] += 1
            return False

        if dry_run:
            print(f"  [DRY-RUN] Would update: {race_date} venue {venue_id}")
            print(f"    Weather: {weather_data}")
            self.stats['updated'] += 1
            return True

        # DBを更新
        updated_count = self.update_races_weather(race_date, venue_id, weather_data)

        if updated_count > 0:
            self.stats['updated'] += 1
            return True
        else:
            self.stats['failed'] += 1
            return False

    async def run(self, limit=None, dry_run=False):
        """
        バックフィルを実行
        """
        print("=" * 60)
        print("  Weather Backfill (Open-Meteo API)")
        print("=" * 60)
        print()

        # 進捗を表示
        completed, total = self.get_progress()
        pending = total - completed

        print(f"Total combinations: {total:,}")
        print(f"Completed: {completed:,}")
        print(f"Pending: {pending:,}")
        print()

        # 未処理の組み合わせを取得
        combinations = self.get_pending_combinations(limit)

        if not combinations:
            print("No pending combinations found.")
            return

        print(f"Processing {len(combinations)} combinations...")
        print(f"Delay: {self.delay}s per request")
        print(f"Estimated time: {len(combinations) * self.delay / 60:.1f} minutes")
        print()

        async with aiohttp.ClientSession() as session:
            self.session = session

            for i, (race_date, venue_id) in enumerate(combinations, 1):
                # 進捗表示
                if i % 100 == 0 or i == 1:
                    print(f"[{i}/{len(combinations)}] Processing... (API calls: {self.stats['api_calls']})")

                success = await self.process_combination(race_date, venue_id, dry_run)

                # 詳細表示（エラー時または最初の10件）
                if not success or i <= 10:
                    status = "OK" if success else "FAIL"
                    print(f"  {race_date} venue {venue_id:2d}: {status}")

                # レート制限
                await asyncio.sleep(self.delay)

        # 最終統計
        print()
        print("=" * 60)
        print("  Summary")
        print("=" * 60)
        print(f"Processed: {self.stats['processed']}")
        print(f"Updated: {self.stats['updated']}")
        print(f"Failed: {self.stats['failed']}")
        print(f"API calls: {self.stats['api_calls']}")
        print(f"Success rate: {self.stats['updated']*100/max(1,self.stats['processed']):.1f}%")

    def close(self):
        """リソースを解放"""
        self.db_conn.close()


async def main():
    parser = argparse.ArgumentParser(description='Backfill weather data using Open-Meteo API')
    parser.add_argument('--limit', type=int, default=None,
                        help='Maximum combinations to process (default: all)')
    parser.add_argument('--delay', type=float, default=0.5,
                        help='Delay between requests in seconds (default: 0.5)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Do not actually update database')

    args = parser.parse_args()

    backfiller = OpenMeteoWeatherBackfiller(delay=args.delay)

    try:
        await backfiller.run(limit=args.limit, dry_run=args.dry_run)
    finally:
        backfiller.close()


if __name__ == '__main__':
    asyncio.run(main())
