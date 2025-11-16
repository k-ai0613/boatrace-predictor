import asyncio
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import random
import os
from dotenv import load_dotenv
import psycopg2
from rate_limiter import RateLimiter

load_dotenv()


class BoatRaceScraper:
    """
    競艇データを収集するスクレイパー

    特徴:
    - 非同期処理による高速化
    - レート制限による負荷軽減
    - リトライ機構
    - データベース保存
    """

    def __init__(self):
        self.base_url = "https://www.boatrace.jp"
        self.session = None
        self.rate_limiter = RateLimiter(
            requests_per_second=0.5,
            concurrent_requests=3
        )

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'ja,en-US;q=0.7',
            'Referer': 'https://www.boatrace.jp/',
        }

        # データベース接続
        # IPv4を強制するために接続文字列を修正
        db_url = os.getenv('DATABASE_URL')
        # GitHub ActionsでIPv6を回避するためのホスト名解決
        import socket
        try:
            # ホスト名からIPv4アドレスを取得
            host = 'db.ngpniiosmxxkryldadna.supabase.co'
            ipv4_addr = socket.getaddrinfo(host, None, socket.AF_INET)[0][4][0]
            # hostaddrパラメータを追加してIPv4を強制
            if '?' in db_url:
                db_url += f'&hostaddr={ipv4_addr}'
            else:
                db_url += f'?hostaddr={ipv4_addr}'
        except Exception as e:
            print(f"Warning: Could not resolve IPv4 address: {e}")

        self.db_conn = psycopg2.connect(db_url)

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
                    elif response.status == 429:
                        wait_time = (2 ** attempt) * 5
                        print(f"Rate limited. Waiting {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    elif response.status == 404:
                        return None
                    else:
                        print(f"HTTP {response.status}: {url}")

            except asyncio.TimeoutError:
                print(f"Timeout on attempt {attempt + 1}")
            except Exception as e:
                print(f"Error on attempt {attempt + 1}: {e}")

            if attempt < max_retries - 1:
                await asyncio.sleep(random.uniform(2, 5))

        return None

    async def fetch_race_result(self, date, venue_id, race_number):
        """レース結果を取得"""
        url = (
            f"{self.base_url}/owpc/pc/race/raceresult"
            f"?hd={date.strftime('%Y%m%d')}"
            f"&jcd={str(venue_id).zfill(2)}"
            f"&rno={race_number}"
        )

        html = await self.fetch_with_retry(url)
        if html:
            soup = BeautifulSoup(html, 'html.parser')
            return self.parse_race_result(
                soup, date, venue_id, race_number
            )
        return None

    def parse_race_result(self, soup, date, venue_id, race_number):
        """HTMLからレースデータを抽出"""
        try:
            # グレード取得（タイトルから判定）
            title_elem = soup.select_one('.heading2_titleName')
            grade = '一般'  # デフォルト
            if title_elem:
                title_text = title_elem.text.strip()
                # タイトルやクラスからグレードを判定
                # 実装を簡素化し、まずは一般で統一

            # レース結果テーブル（1つ目のis-w495）
            tables = soup.select('table.is-w495')
            if len(tables) < 1:
                return None

            result_table = tables[0]

            # 各艇のデータは個別のtbodyに格納されている
            tbodies = result_table.select('tbody')
            entries = []

            for tbody in tbodies:
                row = tbody.select_one('tr')
                if not row:
                    continue

                cols = row.select('td')
                if len(cols) < 4:
                    continue

                # 着順（全角数字の可能性あり）
                position_text = cols[0].text.strip()
                # 全角数字を半角に変換
                position_text = position_text.translate(
                    str.maketrans('０１２３４５６７８９', '0123456789')
                )
                result_position = int(position_text)

                # 枠番/艇番
                boat_number = int(cols[1].text.strip())

                # レーサー情報（span要素から抽出）
                racer_info = cols[2]
                racer_number_elem = racer_info.select_one('span.is-fs12')
                racer_name_elem = racer_info.select_one('span.is-fs18')

                racer_number = int(racer_number_elem.text.strip()) if racer_number_elem else 0
                racer_name = racer_name_elem.text.strip() if racer_name_elem else ''

                # レースタイム
                race_time = cols[3].text.strip()

                entry = {
                    'result_position': result_position,
                    'boat_number': boat_number,
                    'racer_number': racer_number,
                    'racer_name': racer_name,
                    'race_time': race_time,
                    'start_timing': None,  # 後でSTテーブルから取得
                    'course': None,  # STテーブルから進入順を取得
                }
                entries.append(entry)

            # STタイミング情報（2つ目のis-w495テーブル）
            if len(tables) >= 2:
                st_table = tables[1]
                st_rows = st_table.select('tbody tr')

                for st_row in st_rows:
                    # 艇番を取得
                    boat_num_elem = st_row.select_one('.table1_boatImage1Number')
                    if not boat_num_elem:
                        continue

                    boat_num = int(boat_num_elem.text.strip())

                    # STタイミングを取得
                    st_time_elem = st_row.select_one('.table1_boatImage1TimeInner')
                    if st_time_elem:
                        st_text = st_time_elem.text.strip().split()[0]  # ".05 抜き" -> ".05"
                        try:
                            st_timing = float(st_text)
                        except ValueError:
                            st_timing = None
                    else:
                        st_timing = None

                    # 該当する艇のエントリーにSTタイミングを追加
                    for entry in entries:
                        if entry['boat_number'] == boat_num:
                            entry['start_timing'] = st_timing
                            break

            # 気象情報を取得
            weather_data = self._parse_weather(soup)

            return {
                'date': date,
                'venue_id': venue_id,
                'race_number': race_number,
                'grade': grade,
                'entries': entries,
                'weather': weather_data
            }

        except Exception as e:
            print(f"Parse error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _parse_weather(self, soup):
        """気象情報を抽出"""
        try:
            weather_div = soup.select_one('.weather1_body')
            if not weather_div:
                return None

            weather_data = {}

            # 気温
            temp_elem = weather_div.select_one('.is-direction .weather1_bodyUnitLabelData')
            if temp_elem:
                temp_text = temp_elem.text.strip().replace('℃', '')
                try:
                    weather_data['temperature'] = float(temp_text)
                except ValueError:
                    weather_data['temperature'] = None

            # 天候
            weather_elem = weather_div.select_one('.is-weather .weather1_bodyUnitLabelTitle')
            if weather_elem:
                weather_data['weather'] = weather_elem.text.strip()

            # 風速
            wind_elem = weather_div.select_one('.is-wind .weather1_bodyUnitLabelData')
            if wind_elem:
                wind_text = wind_elem.text.strip().replace('m', '')
                try:
                    weather_data['wind_speed'] = float(wind_text)
                except ValueError:
                    weather_data['wind_speed'] = None

            # 水温
            water_temp_elem = weather_div.select_one('.is-waterTemperature .weather1_bodyUnitLabelData')
            if water_temp_elem:
                water_temp_text = water_temp_elem.text.strip().replace('℃', '')
                try:
                    weather_data['water_temperature'] = float(water_temp_text)
                except ValueError:
                    weather_data['water_temperature'] = None

            # 波高
            wave_elem = weather_div.select_one('.is-wave .weather1_bodyUnitLabelData')
            if wave_elem:
                wave_text = wave_elem.text.strip().replace('cm', '')
                try:
                    weather_data['wave_height'] = float(wave_text)
                except ValueError:
                    weather_data['wave_height'] = None

            return weather_data

        except Exception as e:
            print(f"Weather parse error: {e}")
            return None

    async def scrape_single_day(self, date):
        """1日分のデータを取得"""
        print(f"Scraping {date.strftime('%Y-%m-%d')}...")
        results = []

        for venue_id in range(1, 25):
            venue_results = []

            # 12レースを3つずつバッチ処理
            for race_batch in self._batch(range(1, 13), 3):
                tasks = [
                    self.fetch_race_result(date, venue_id, race_num)
                    for race_num in race_batch
                ]
                batch_results = await asyncio.gather(*tasks)
                venue_results.extend([r for r in batch_results if r])

            results.extend(venue_results)
            print(f"  Venue {venue_id}: {len(venue_results)} races")

            await asyncio.sleep(2)

        # データベースに保存
        self.save_to_db(results)

        return results

    def _batch(self, iterable, n):
        """リストをバッチに分割"""
        l = list(iterable)
        for i in range(0, len(l), n):
            yield l[i:i + n]

    def save_to_db(self, results):
        """データベースに保存"""
        cursor = self.db_conn.cursor()

        try:
            for race in results:
                # レース基本情報を保存
                cursor.execute("""
                    INSERT INTO races (race_date, venue_id, race_number, grade)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (race_date, venue_id, race_number) DO UPDATE
                    SET grade = EXCLUDED.grade
                    RETURNING id
                """, (
                    race['date'],
                    race['venue_id'],
                    race['race_number'],
                    race['grade']
                ))

                result = cursor.fetchone()
                if result:
                    race_id = result[0]

                    # 出走情報を保存
                    for entry in race['entries']:
                        # レーサー情報を保存（存在しない場合のみ）
                        cursor.execute("""
                            INSERT INTO racers (racer_number, name)
                            VALUES (%s, %s)
                            ON CONFLICT (racer_number) DO UPDATE
                            SET name = EXCLUDED.name
                        """, (
                            entry['racer_number'],
                            entry['racer_name']
                        ))

                        # 出走情報を保存
                        cursor.execute("""
                            INSERT INTO race_entries
                            (race_id, boat_number, racer_id, start_timing,
                             result_position)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (race_id, boat_number) DO UPDATE
                            SET racer_id = EXCLUDED.racer_id,
                                start_timing = EXCLUDED.start_timing,
                                result_position = EXCLUDED.result_position
                        """, (
                            race_id,
                            entry['boat_number'],
                            entry['racer_number'],
                            entry['start_timing'],
                            entry['result_position']
                        ))

                    # 気象データを保存
                    if race.get('weather'):
                        weather = race['weather']
                        cursor.execute("""
                            INSERT INTO weather_data
                            (race_id, temperature, weather_condition,
                             wind_speed, water_temperature, wave_height)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON CONFLICT (race_id) DO UPDATE
                            SET temperature = EXCLUDED.temperature,
                                weather_condition = EXCLUDED.weather_condition,
                                wind_speed = EXCLUDED.wind_speed,
                                water_temperature = EXCLUDED.water_temperature,
                                wave_height = EXCLUDED.wave_height
                        """, (
                            race_id,
                            weather.get('temperature'),
                            weather.get('weather'),
                            weather.get('wind_speed'),
                            weather.get('water_temperature'),
                            weather.get('wave_height')
                        ))

            self.db_conn.commit()
            print(f"Saved {len(results)} races to database")

        except Exception as e:
            self.db_conn.rollback()
            print(f"Database error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            cursor.close()

    async def run(self, start_date, end_date):
        """期間指定で実行"""
        async with aiohttp.ClientSession() as session:
            self.session = session
            current_date = start_date

            while current_date <= end_date:
                await self.scrape_single_day(current_date)
                current_date += timedelta(days=1)
                await asyncio.sleep(5)

    def close(self):
        """リソースを解放"""
        self.db_conn.close()


async def main():
    """メイン処理"""
    scraper = BoatRaceScraper()

    try:
        # 直近3日分を取得
        end_date = datetime.now()
        start_date = end_date - timedelta(days=3)

        await scraper.run(start_date, end_date)

    finally:
        scraper.close()


if __name__ == '__main__':
    asyncio.run(main())
