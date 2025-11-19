"""
天気データ収集スクリプト

各ボートレース場の公式サイトから天気データを収集
- 風速・風向き
- 気温・水温
- 波高
- 天気状態

注意: 各会場のHTML構造は異なる可能性があるため、
      実際の運用時には調整が必要です。
"""
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import psycopg2
import sys
import re

# 親ディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.venues_config import VENUES, get_all_venue_ids
from scraper.rate_limiter import RateLimiter

load_dotenv()


class WeatherScraper:
    """天気データスクレイパー"""

    def __init__(self):
        self.session = None
        self.rate_limiter = RateLimiter(
            requests_per_second=0.33,  # 3秒に1リクエスト
            concurrent_requests=2
        )

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'ja,en-US;q=0.7',
        }

        self.db_conn = psycopg2.connect(os.getenv('DATABASE_URL'))

    async def fetch_with_retry(self, url, max_retries=3):
        """リトライ機能付きフェッチ"""
        for attempt in range(max_retries):
            try:
                await self.rate_limiter.acquire()

                async with self.session.get(
                    url,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        return await response.text()
                    elif response.status == 404:
                        return None
                    else:
                        print(f"HTTP {response.status}: {url}")

            except asyncio.TimeoutError:
                print(f"Timeout on attempt {attempt + 1}: {url}")
            except Exception as e:
                print(f"Error on attempt {attempt + 1}: {e}")

            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)

        return None

    def parse_weather_data(self, html, venue_id):
        """
        HTMLから天気データを抽出

        注意: 各会場でHTML構造が異なるため、汎用的なパーサーを実装
              実際の運用時には各会場に合わせて調整が必要
        """
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')

        # 天気データを抽出（会場ごとに異なる可能性がある）
        weather_data = {
            'venue_id': venue_id,
            'record_datetime': datetime.now(),
            'temperature': None,
            'humidity': None,
            'pressure': None,
            'wind_speed': None,
            'wind_direction': None,
            'wind_direction_text': None,
            'wave_height': None,
            'water_temperature': None,
            'weather_condition': None,
            'source': 'venue_official',
            'is_realtime': True
        }

        try:
            # 風速を抽出（例: "風速: 3.5m/s" のようなテキストを探す）
            wind_text = soup.find(string=re.compile(r'風速|風'))
            if wind_text:
                # 数値を抽出
                wind_match = re.search(r'([\d.]+)\s*m/?s?', str(wind_text.parent))
                if wind_match:
                    weather_data['wind_speed'] = float(wind_match.group(1))

            # 風向を抽出
            wind_dir_text = soup.find(string=re.compile(r'風向|風\s*向'))
            if wind_dir_text:
                # 風向テキスト（例: "北東"）を抽出
                for direction in ['北東', '北西', '南東', '南西', '北', '南', '東', '西']:
                    if direction in str(wind_dir_text.parent):
                        weather_data['wind_direction_text'] = direction
                        weather_data['wind_direction'] = self._direction_to_degrees(direction)
                        break

            # 気温を抽出
            temp_text = soup.find(string=re.compile(r'気温|温度'))
            if temp_text:
                temp_match = re.search(r'([\d.]+)\s*℃', str(temp_text.parent))
                if temp_match:
                    weather_data['temperature'] = float(temp_match.group(1))

            # 波高を抽出
            wave_text = soup.find(string=re.compile(r'波|波高'))
            if wave_text:
                wave_match = re.search(r'([\d.]+)\s*cm', str(wave_text.parent))
                if wave_match:
                    weather_data['wave_height'] = float(wave_match.group(1))

            # 天気状態を抽出
            weather_condition_text = soup.find(string=re.compile(r'晴|曇|雨|雪'))
            if weather_condition_text:
                for condition in ['晴れ', '曇り', '雨', '雪', '晴', '曇']:
                    if condition in str(weather_condition_text):
                        weather_data['weather_condition'] = condition.replace('れ', '').replace('り', '')
                        break

        except Exception as e:
            print(f"Parse error for venue {venue_id}: {e}")

        return weather_data

    def _direction_to_degrees(self, direction_text):
        """風向テキストを角度に変換"""
        directions = {
            '北': 0,
            '北東': 45,
            '東': 90,
            '南東': 135,
            '南': 180,
            '南西': 225,
            '西': 270,
            '北西': 315
        }
        return directions.get(direction_text, None)

    async def fetch_venue_weather(self, venue_id, target_date=None):
        """指定会場の天気データを取得"""
        venue = VENUES.get(venue_id)
        if not venue:
            print(f"Unknown venue ID: {venue_id}")
            return None

        # 日付指定がない場合は今日
        if target_date is None:
            target_date = datetime.now()

        # URLを構築
        date_str = target_date.strftime('%Y%m%d')
        url = venue['weather_url'] + date_str

        print(f"Fetching weather for {venue['name']} ({venue_id})...")

        html = await self.fetch_with_retry(url)

        if html:
            weather_data = self.parse_weather_data(html, venue_id)

            if weather_data and (weather_data['wind_speed'] or weather_data['temperature']):
                return weather_data
            else:
                print(f"  No weather data found for {venue['name']}")
        else:
            print(f"  Failed to fetch for {venue['name']}")

        return None

    def save_to_db(self, weather_data_list):
        """天気データをデータベースに保存"""
        if not weather_data_list:
            return

        cursor = self.db_conn.cursor()

        try:
            for data in weather_data_list:
                cursor.execute("""
                    INSERT INTO weather_data
                    (venue_id, record_datetime, temperature, humidity, pressure,
                     wind_speed, wind_direction, wind_direction_text,
                     wave_height, water_temperature, weather_condition,
                     source, is_realtime)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (venue_id, record_datetime) DO UPDATE SET
                        temperature = EXCLUDED.temperature,
                        humidity = EXCLUDED.humidity,
                        pressure = EXCLUDED.pressure,
                        wind_speed = EXCLUDED.wind_speed,
                        wind_direction = EXCLUDED.wind_direction,
                        wind_direction_text = EXCLUDED.wind_direction_text,
                        wave_height = EXCLUDED.wave_height,
                        water_temperature = EXCLUDED.water_temperature,
                        weather_condition = EXCLUDED.weather_condition
                """, (
                    data['venue_id'],
                    data['record_datetime'],
                    data['temperature'],
                    data['humidity'],
                    data['pressure'],
                    data['wind_speed'],
                    data['wind_direction'],
                    data['wind_direction_text'],
                    data['wave_height'],
                    data['water_temperature'],
                    data['weather_condition'],
                    data['source'],
                    data['is_realtime']
                ))

            self.db_conn.commit()
            print(f"Saved {len(weather_data_list)} weather records to database")

        except Exception as e:
            self.db_conn.rollback()
            print(f"Database error: {e}")
        finally:
            cursor.close()

    async def collect_all_venues(self, target_date=None):
        """全会場の天気データを収集"""
        print("=" * 80)
        print(f"  全24会場の天気データ収集")
        print("=" * 80)
        print()

        async with aiohttp.ClientSession() as session:
            self.session = session

            all_weather_data = []

            for venue_id in get_all_venue_ids():
                weather_data = await self.fetch_venue_weather(venue_id, target_date)

                if weather_data:
                    all_weather_data.append(weather_data)

            print()
            print(f"収集完了: {len(all_weather_data)} / 24 会場")

            # データベースに保存
            if all_weather_data:
                self.save_to_db(all_weather_data)

            return all_weather_data

    def close(self):
        """リソースを解放"""
        self.db_conn.close()


async def main():
    """メイン処理"""
    print()
    print("=" * 80)
    print("  天気データ収集スクリプト")
    print("=" * 80)
    print()
    print("注意:")
    print("- このスクリプトは各会場の公式サイトから天気データを収集します")
    print("- HTML構造は会場ごとに異なる可能性があるため、調整が必要です")
    print("- 初回実行時はデータが正しく取得できているか確認してください")
    print()

    scraper = WeatherScraper()

    try:
        weather_data = await scraper.collect_all_venues()

        print()
        print("=" * 80)
        print("  収集結果サマリー")
        print("=" * 80)

        if weather_data:
            print(f"\n総収集件数: {len(weather_data)}件")

            # 統計表示
            wind_count = sum(1 for d in weather_data if d['wind_speed'] is not None)
            temp_count = sum(1 for d in weather_data if d['temperature'] is not None)
            wave_count = sum(1 for d in weather_data if d['wave_height'] is not None)

            print(f"風速データ: {wind_count}件")
            print(f"気温データ: {temp_count}件")
            print(f"波高データ: {wave_count}件")

            if wind_count > 0:
                avg_wind = sum(d['wind_speed'] for d in weather_data if d['wind_speed']) / wind_count
                print(f"\n平均風速: {avg_wind:.1f} m/s")

        else:
            print("\n[WARNING] データが取得できませんでした")
            print("HTML構造の調整が必要な可能性があります")

    finally:
        scraper.close()


if __name__ == '__main__':
    asyncio.run(main())
