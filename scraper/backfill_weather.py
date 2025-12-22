"""
天気データバックフィルスクリプト

boatrace.jp公式サイトから過去レースの天気データを取得し、
racesテーブルに追加する。

日×会場単位で効率的に取得（同日同会場の天気は同じ）

使用方法:
    python scraper/backfill_weather.py
    python scraper/backfill_weather.py --limit 500
    python scraper/backfill_weather.py --dry-run
"""

import os
import sys
import re
import time
import argparse
import asyncio
import aiohttp
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import psycopg2

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()


class WeatherBackfiller:
    """天気データバックフィラー"""

    def __init__(self, delay=3.0):
        self.delay = delay
        self.session = None
        self.db_conn = psycopg2.connect(os.getenv('DATABASE_URL'))

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'ja,en-US;q=0.7',
        }

        # 統計
        self.stats = {
            'processed': 0,
            'updated': 0,
            'failed': 0,
            'skipped': 0
        }

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

    def get_completed_count(self):
        """完了済みの組み合わせ数を取得"""
        cursor = self.db_conn.cursor()
        cursor.execute("""
            SELECT COUNT(DISTINCT (race_date, venue_id))
            FROM races
            WHERE temperature IS NOT NULL
        """)
        count = cursor.fetchone()[0]
        cursor.close()
        return count

    def get_total_combinations(self):
        """全組み合わせ数を取得"""
        cursor = self.db_conn.cursor()
        cursor.execute("""
            SELECT COUNT(DISTINCT (race_date, venue_id))
            FROM races
            WHERE race_date < CURRENT_DATE
        """)
        count = cursor.fetchone()[0]
        cursor.close()
        return count

    async def fetch_weather_from_boatrace(self, race_date, venue_id):
        """
        boatrace.jp/beforeinfoから天気データを取得

        Args:
            race_date: レース日付
            venue_id: 会場ID

        Returns:
            dict: 天気データ、取得失敗時はNone
        """
        # URL構築（1Rのbeforeinfoを取得）
        date_str = race_date.strftime('%Y%m%d')
        venue_str = str(venue_id).zfill(2)
        url = f"https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno=1&jcd={venue_str}&hd={date_str}"

        try:
            async with self.session.get(
                url,
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    return None

                html = await response.text()
                return self.parse_weather(html)

        except asyncio.TimeoutError:
            print(f"  Timeout: {race_date} venue {venue_id}")
            return None
        except Exception as e:
            print(f"  Error: {race_date} venue {venue_id} - {e}")
            return None

    def parse_weather(self, html):
        """
        HTMLから天気データを抽出

        boatrace.jpのbeforeinfoページ形式:
        "水面気象情報　XX:XX現在
        気温 X.X℃
        晴/曇/雨
        風速 Xm
        水温 X.X℃
        波高 Xcm"
        """
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')

        weather_data = {
            'temperature': None,
            'wind_speed': None,
            'wind_direction': None,
            'water_temperature': None,
            'wave_height': None,
            'weather_condition': None
        }

        try:
            # 水面気象情報セクションを探す
            weather_section = soup.find(string=re.compile(r'水面気象情報'))

            if not weather_section:
                # 別の方法で探す
                weather_section = soup.find('div', class_='weather1')

            if weather_section:
                # 親要素のテキストを取得
                parent = weather_section.find_parent('div') if hasattr(weather_section, 'find_parent') else None
                text = parent.get_text() if parent else str(weather_section.parent)
            else:
                # ページ全体から探す
                text = soup.get_text()

            # 気温を抽出
            temp_match = re.search(r'気温\s*([\d.]+)\s*℃', text)
            if temp_match:
                weather_data['temperature'] = float(temp_match.group(1))

            # 風速を抽出
            wind_match = re.search(r'風速\s*(\d+)\s*m', text)
            if wind_match:
                weather_data['wind_speed'] = int(wind_match.group(1))

            # 水温を抽出
            water_temp_match = re.search(r'水温\s*([\d.]+)\s*℃', text)
            if water_temp_match:
                weather_data['water_temperature'] = float(water_temp_match.group(1))

            # 波高を抽出
            wave_match = re.search(r'波高\s*(\d+)\s*cm', text)
            if wave_match:
                weather_data['wave_height'] = int(wave_match.group(1))

            # 天気を抽出
            for condition in ['晴', '曇', '雨', '雪']:
                if condition in text:
                    weather_data['weather_condition'] = condition
                    break

            # 風向を抽出（あれば）
            wind_dir_patterns = [
                r'(北東|北西|南東|南西|北|南|東|西)\s*\d+m',
                r'風向[:\s]*(北東|北西|南東|南西|北|南|東|西)'
            ]
            for pattern in wind_dir_patterns:
                wind_dir_match = re.search(pattern, text)
                if wind_dir_match:
                    weather_data['wind_direction'] = wind_dir_match.group(1)
                    break

        except Exception as e:
            print(f"  Parse error: {e}")
            return None

        # 少なくとも1つのデータがあれば返す
        if any(v is not None for v in weather_data.values()):
            return weather_data

        return None

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
        weather_data = await self.fetch_weather_from_boatrace(race_date, venue_id)

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
        print("  Weather Backfill")
        print("=" * 60)
        print()

        # 統計を表示
        total = self.get_total_combinations()
        completed = self.get_completed_count()
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
                if i % 50 == 0 or i == 1:
                    print(f"[{i}/{len(combinations)}] Processing...")

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
        print(f"Success rate: {self.stats['updated']*100/max(1,self.stats['processed']):.1f}%")

    def close(self):
        """リソースを解放"""
        self.db_conn.close()


async def main():
    parser = argparse.ArgumentParser(description='Backfill weather data from boatrace.jp')
    parser.add_argument('--limit', type=int, default=None,
                        help='Maximum combinations to process (default: all)')
    parser.add_argument('--delay', type=float, default=3.0,
                        help='Delay between requests in seconds (default: 3.0)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Do not actually update database')

    args = parser.parse_args()

    backfiller = WeatherBackfiller(delay=args.delay)

    try:
        await backfiller.run(limit=args.limit, dry_run=args.dry_run)
    finally:
        backfiller.close()


if __name__ == '__main__':
    asyncio.run(main())
