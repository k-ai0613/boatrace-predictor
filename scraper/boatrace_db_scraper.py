"""
boatrace-db.netから詳細統計データを取得するスクレイパー

使用方法:
  python boatrace_db_scraper.py --mode racers  # 選手詳細データ収集
  python boatrace_db_scraper.py --mode venues  # 会場データ収集
  python boatrace_db_scraper.py --mode all     # 全データ収集
"""

import requests
from bs4 import BeautifulSoup
import time
import os
from dotenv import load_dotenv
import psycopg2
import json
import argparse
import re

load_dotenv()


class BoatraceDBScraper:
    """boatrace-db.netサイトからデータを収集するスクレイパー"""

    def __init__(self, delay=2.0):
        self.base_url = "https://boatrace-db.net"
        self.delay = delay  # レート制限（秒）
        self.db_conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })

    def close(self):
        """データベース接続を閉じる"""
        if self.db_conn:
            self.db_conn.close()

    def _fetch_with_retry(self, url, max_retries=5, timeout=60):
        """
        リトライ機能付きHTTPリクエスト（指数バックオフ実装）

        Args:
            url: リクエストURL
            max_retries: 最大リトライ回数（デフォルト: 5）
            timeout: タイムアウト秒数（デフォルト: 60）

        Returns:
            requests.Response: レスポンスオブジェクト、失敗時はNone
        """
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=timeout)

                if response.status_code == 200:
                    return response
                elif response.status_code == 404:
                    print(f"  404 Not Found: {url}")
                    return None
                elif response.status_code == 429:
                    # レート制限エラー - 長めに待つ
                    wait_time = min(30, self.delay * (2 ** attempt))  # 最大30秒
                    print(f"  Rate limit (429), waiting {wait_time:.1f}s... ({attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                elif response.status_code >= 500:
                    # サーバーエラー - 指数バックオフ
                    wait_time = min(20, self.delay * (2 ** attempt))  # 最大20秒
                    print(f"  Server error {response.status_code}, waiting {wait_time:.1f}s... ({attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"  HTTP {response.status_code}: {url}")
                    return None

            except requests.exceptions.Timeout:
                # タイムアウトエラー - 長めの指数バックオフ
                wait_time = min(30, 5 + self.delay * (2 ** attempt))  # 基礎5秒 + 指数バックオフ、最大30秒
                print(f"  Timeout error, waiting {wait_time:.1f}s... ({attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                continue

            except requests.exceptions.ConnectionError as e:
                # 接続エラー - 指数バックオフ
                wait_time = min(25, self.delay * (2 ** attempt))  # 最大25秒
                print(f"  Connection error, waiting {wait_time:.1f}s... ({attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                continue

            except Exception as e:
                print(f"  Unexpected error: {e}")
                import traceback
                traceback.print_exc()
                return None

        print(f"  Failed after {max_retries} retries: {url}")
        return None

    def get_registered_racers(self):
        """
        データベースに登録済みの選手番号リストを取得

        Returns:
            list: 選手番号のリスト
        """
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT DISTINCT racer_number FROM racers ORDER BY racer_number")
        racers = [row[0] for row in cursor.fetchall()]
        cursor.close()
        print(f"Found {len(racers)} registered racers in database")
        return racers

    def fetch_racer_detail(self, racer_number):
        """
        選手詳細ページを取得

        Args:
            racer_number: 選手番号

        Returns:
            dict: 選手詳細データ、取得失敗時はNone
        """
        url = f"{self.base_url}/racer/index2/regno/{racer_number}/"

        try:
            print(f"Fetching racer {racer_number}: {url}")
            response = self._fetch_with_retry(url)  # デフォルト: max_retries=5, timeout=60

            if not response:
                print(f"  Failed to fetch racer {racer_number}")
                return None

            soup = BeautifulSoup(response.content, 'html.parser')

            # データ抽出
            racer_data = {
                'racer_number': racer_number,
                'registration_period': None,
                'branch': None,
                'total_races': 0,
                'total_wins': 0,
                'overall_win_rate': 0.0,
                'overall_1st_rate': 0.0,
                'overall_2nd_rate': 0.0,
                'overall_3rd_rate': 0.0,
                'avg_start_timing': 0.0,
                'grade_stats': {},
                'boat_number_stats': {},
                'course_stats': {},
                'venue_stats': {},
                'sg_appearances': 0,
                'flying_count': 0,
                'late_start_count': 0
            }

            # プロフィール情報を抽出
            racer_data = self._parse_racer_profile(soup, racer_data)

            # 通算成績を抽出
            racer_data = self._parse_racer_overall_stats(soup, racer_data)

            # 艇番別成績を抽出
            racer_data = self._parse_boat_number_stats(soup, racer_data)

            # コース別成績を抽出
            racer_data = self._parse_course_stats(soup, racer_data)

            # 場別成績を抽出
            racer_data = self._parse_venue_stats(soup, racer_data)

            print(f"  Success: {racer_data.get('branch', 'Unknown')}支部")

            time.sleep(self.delay)  # レート制限
            return racer_data

        except Exception as e:
            print(f"  Error fetching racer {racer_number}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _parse_racer_profile(self, soup, racer_data):
        """プロフィール情報を抽出"""
        try:
            # h1から選手番号と名前を取得（念のため）
            h1 = soup.find('h1')
            if h1:
                text = h1.get_text()
                # "5000 岡本  翔太郎オカモト ショウタロウ" のような形式

            # 登録期を抽出（リンクテキストから）
            for link in soup.find_all('a'):
                link_text = link.get_text()
                if '登録' in link_text and '期' in link_text:
                    # "登録121期" から数値を抽出
                    match = re.search(r'登録(\d+)期', link_text)
                    if match:
                        racer_data['registration_period'] = int(match.group(1))

                # 支部を抽出
                if '支部' in link_text:
                    # "山口支部" から支部名を抽出
                    branch = link_text.replace('支部', '')
                    racer_data['branch'] = branch

        except Exception as e:
            print(f"  Error parsing profile: {e}")

        return racer_data

    def _parse_racer_overall_stats(self, soup, racer_data):
        """通算成績を抽出"""
        try:
            tables = soup.find_all('table')
            grade_stats = {}

            for i, table in enumerate(tables):
                # ヘッダー行を確認
                headers = []
                header_row = table.find('tr')
                if header_row:
                    headers = [th.get_text().strip() for th in header_row.find_all(['th', 'td'])]

                # グレード別成績テーブルを特定（テーブル1）
                if ('グレード' in headers and '出場節数' in headers and '平均ST' in headers):
                    rows = table.find_all('tr')[1:]  # ヘッダー行をスキップ

                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 8:
                            grade = cells[0].get_text().strip()
                            try:
                                races = self._parse_number(cells[2].get_text().strip())
                                wins = self._parse_number(cells[3].get_text().strip())
                                win_rate = self._parse_float(cells[4].get_text().strip())
                                rate_1st = self._parse_float(cells[5].get_text().strip())
                                rate_2nd = self._parse_float(cells[6].get_text().strip())
                                rate_3rd = self._parse_float(cells[7].get_text().strip())

                                grade_stats[grade] = {
                                    'races': races,
                                    'wins': wins,
                                    'win_rate': win_rate,
                                    '1st_rate': rate_1st,
                                    '2nd_rate': rate_2nd,
                                    '3rd_rate': rate_3rd
                                }

                                # 「一般」または「総合」グレードの成績を全体統計として使用
                                if grade in ['一般', '総合']:
                                    racer_data['total_races'] = races
                                    racer_data['total_wins'] = wins
                                    racer_data['overall_win_rate'] = win_rate
                                    racer_data['overall_1st_rate'] = rate_1st
                                    racer_data['overall_2nd_rate'] = rate_2nd
                                    racer_data['overall_3rd_rate'] = rate_3rd

                            except (ValueError, IndexError) as e:
                                continue

                    racer_data['grade_stats'] = grade_stats
                    break  # 最初に見つかったテーブルで処理終了

        except Exception as e:
            print(f"  Error parsing overall stats: {e}")

        return racer_data

    def _parse_number(self, text):
        """数値を安全に抽出"""
        try:
            # カンマと%を削除
            cleaned = text.replace(',', '').replace('%', '').strip()
            if cleaned and cleaned.replace('.', '').replace('-', '').isdigit():
                return int(cleaned) if '.' not in cleaned else int(float(cleaned))
            return 0
        except:
            return 0

    def _parse_float(self, text):
        """浮動小数点数を安全に抽出"""
        try:
            # カンマと%を削除
            cleaned = text.replace(',', '').replace('%', '').strip()
            if cleaned and cleaned.replace('.', '').replace('-', '').isdigit():
                return float(cleaned)
            return 0.0
        except:
            return 0.0

    def _parse_boat_number_stats(self, soup, racer_data):
        """艇番別成績を抽出"""
        try:
            tables = soup.find_all('table')
            boat_stats = {}

            for table in tables:
                headers = []
                header_row = table.find('tr')
                if header_row:
                    headers = [th.get_text().strip() for th in header_row.find_all(['th', 'td'])]

                # 艇番別成績テーブルを特定（テーブル3）
                if '艇番' in headers and '1着数' in headers and '優出' in headers:
                    rows = table.find_all('tr')[1:]

                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 5:
                            boat_no = cells[0].get_text().strip()
                            try:
                                races = self._parse_number(cells[1].get_text().strip())
                                wins = self._parse_number(cells[2].get_text().strip())
                                rate_1st = self._parse_float(cells[3].get_text().strip())
                                rate_2nd = self._parse_float(cells[4].get_text().strip())

                                boat_stats[boat_no] = {
                                    'races': races,
                                    'wins': wins,
                                    '1st_rate': rate_1st,
                                    '2nd_rate': rate_2nd
                                }
                            except (ValueError, IndexError):
                                continue

                    racer_data['boat_number_stats'] = boat_stats
                    break

        except Exception as e:
            print(f"  Error parsing boat number stats: {e}")

        return racer_data

    def _parse_course_stats(self, soup, racer_data):
        """コース別成績を抽出（決まり手含む）"""
        try:
            tables = soup.find_all('table')
            course_stats = {}

            for table in tables:
                headers = []
                header_row = table.find('tr')
                if header_row:
                    headers = [th.get_text().strip() for th in header_row.find_all(['th', 'td'])]

                # Table 6: コース別決まり手テーブルを特定
                # ヘッダー: コース、出走数、1着数、逃げ、差し、まくり、まくり差し、抜き、恵まれ
                if 'コース' in headers and '逃げ' in headers and '差し' in headers:
                    rows = table.find_all('tr')[1:]

                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 9:
                            course_no = cells[0].get_text().strip()
                            try:
                                races = self._parse_number(cells[1].get_text().strip())
                                wins = self._parse_number(cells[2].get_text().strip())

                                # 決まり手を抽出
                                kimarite = {
                                    '逃げ': self._parse_number(cells[3].get_text().strip()),
                                    '差し': self._parse_number(cells[4].get_text().strip()),
                                    'まくり': self._parse_number(cells[5].get_text().strip()),
                                    'まくり差し': self._parse_number(cells[6].get_text().strip()),
                                    '抜き': self._parse_number(cells[7].get_text().strip()),
                                    '恵まれ': self._parse_number(cells[8].get_text().strip())
                                }

                                course_stats[course_no] = {
                                    'races': races,
                                    'wins': wins,
                                    '1st_rate': round(wins / races * 100, 1) if races > 0 else 0.0,
                                    '決まり手': kimarite
                                }
                            except (ValueError, IndexError, ZeroDivisionError):
                                continue

                    racer_data['course_stats'] = course_stats
                    break

                # 代替: 平均STを含むコース別成績テーブル（決まり手なし）
                elif 'コース' in headers and '平均ST' in headers and not course_stats:
                    rows = table.find_all('tr')[1:]

                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 7:
                            course_no = cells[0].get_text().strip()
                            try:
                                races = self._parse_number(cells[1].get_text().strip())
                                rate_1st = self._parse_float(cells[3].get_text().strip())
                                rate_2nd = self._parse_float(cells[4].get_text().strip())
                                avg_st = self._parse_float(cells[6].get_text().strip())

                                course_stats[course_no] = {
                                    'races': races,
                                    '1st_rate': rate_1st,
                                    '2nd_rate': rate_2nd,
                                    'avg_st': avg_st
                                }
                            except (ValueError, IndexError):
                                continue

                    racer_data['course_stats'] = course_stats

        except Exception as e:
            print(f"  Error parsing course stats: {e}")

        return racer_data

    def _parse_venue_stats(self, soup, racer_data):
        """場別成績を抽出"""
        try:
            tables = soup.find_all('table')
            venue_stats = {}

            for table in tables:
                headers = []
                header_row = table.find('tr')
                if header_row:
                    headers = [th.get_text().strip() for th in header_row.find_all(['th', 'td'])]

                # 場別成績テーブルを特定（24会場）
                if '場' in ''.join(headers) and '出場節数' in ''.join(headers):
                    rows = table.find_all('tr')[1:]

                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 9:
                            venue_name = cells[0].get_text().strip()
                            try:
                                races = int(cells[2].get_text().strip()) if cells[2].get_text().strip().isdigit() else 0
                                rate_1st = float(cells[5].get_text().strip()) if cells[5].get_text().strip() else 0.0
                                rate_2nd = float(cells[6].get_text().strip()) if cells[6].get_text().strip() else 0.0

                                venue_stats[venue_name] = {
                                    'races': races,
                                    '1st_rate': rate_1st,
                                    '2nd_rate': rate_2nd
                                }
                            except (ValueError, IndexError):
                                continue

                    racer_data['venue_stats'] = venue_stats
                    break

        except Exception as e:
            print(f"  Error parsing venue stats: {e}")

        return racer_data

    def save_racer_stats(self, racer_data):
        """
        選手詳細統計をデータベースに保存

        Args:
            racer_data: 選手詳細データ

        Returns:
            bool: 成功時True
        """
        cursor = self.db_conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO racer_detailed_stats (
                    racer_number, registration_period, branch,
                    total_races, total_wins, overall_win_rate,
                    overall_1st_rate, overall_2nd_rate, overall_3rd_rate,
                    avg_start_timing,
                    grade_stats, boat_number_stats, course_stats, venue_stats,
                    sg_appearances, flying_count, late_start_count
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (racer_number) DO UPDATE SET
                    registration_period = EXCLUDED.registration_period,
                    branch = EXCLUDED.branch,
                    total_races = EXCLUDED.total_races,
                    total_wins = EXCLUDED.total_wins,
                    overall_win_rate = EXCLUDED.overall_win_rate,
                    overall_1st_rate = EXCLUDED.overall_1st_rate,
                    overall_2nd_rate = EXCLUDED.overall_2nd_rate,
                    overall_3rd_rate = EXCLUDED.overall_3rd_rate,
                    avg_start_timing = EXCLUDED.avg_start_timing,
                    grade_stats = EXCLUDED.grade_stats,
                    boat_number_stats = EXCLUDED.boat_number_stats,
                    course_stats = EXCLUDED.course_stats,
                    venue_stats = EXCLUDED.venue_stats,
                    sg_appearances = EXCLUDED.sg_appearances,
                    flying_count = EXCLUDED.flying_count,
                    late_start_count = EXCLUDED.late_start_count,
                    updated_at = NOW()
            """, (
                racer_data['racer_number'],
                racer_data.get('registration_period'),
                racer_data.get('branch'),
                racer_data.get('total_races', 0),
                racer_data.get('total_wins', 0),
                racer_data.get('overall_win_rate', 0.0),
                racer_data.get('overall_1st_rate', 0.0),
                racer_data.get('overall_2nd_rate', 0.0),
                racer_data.get('overall_3rd_rate', 0.0),
                racer_data.get('avg_start_timing', 0.0),
                json.dumps(racer_data.get('grade_stats', {})),
                json.dumps(racer_data.get('boat_number_stats', {})),
                json.dumps(racer_data.get('course_stats', {})),
                json.dumps(racer_data.get('venue_stats', {})),
                racer_data.get('sg_appearances', 0),
                racer_data.get('flying_count', 0),
                racer_data.get('late_start_count', 0)
            ))

            self.db_conn.commit()
            return True

        except Exception as e:
            self.db_conn.rollback()
            print(f"Database error: {e}")
            return False

    def collect_all_racer_stats(self, limit=None, racer_ids=None):
        """
        登録済み選手の詳細統計を収集

        Args:
            limit: 収集する選手数の上限（Noneの場合は全選手）
            racer_ids: 収集する選手番号のリスト（Noneの場合はDBから取得）
        """
        # 特定の選手IDが指定されている場合
        if racer_ids:
            racers = racer_ids
            print(f"\n=== Starting racer stats collection (specific IDs) ===")
            print(f"Racer IDs: {racer_ids}")
        else:
            racers = self.get_registered_racers()
            print(f"\n=== Starting racer stats collection ===")
            print(f"Total racers in database: {len(racers)}")

        # 数を制限
        if limit and limit < len(racers):
            racers = racers[:limit]
            print(f"Limiting to first {limit} racers")

        print(f"Total racers to collect: {len(racers)}\n")

        success_count = 0
        failed_count = 0

        for i, racer_number in enumerate(racers, 1):
            print(f"[{i}/{len(racers)}] Processing racer {racer_number}")

            racer_data = self.fetch_racer_detail(racer_number)

            if racer_data:
                if self.save_racer_stats(racer_data):
                    success_count += 1
                else:
                    failed_count += 1
            else:
                failed_count += 1

        print(f"\n=== Collection Complete ===")
        print(f"Success: {success_count}")
        print(f"Failed: {failed_count}")
        print(f"Total: {len(racers)}")

    def collect_venue_stats(self, limit=None):
        """
        全24会場の詳細統計を収集

        Args:
            limit: 収集する会場数の上限（Noneの場合は全24会場）
        """
        print("\n=== Venue stats collection ===")

        venues = {
            1: '桐生', 2: '戸田', 3: '江戸川', 4: '平和島', 5: '多摩川', 6: '浜名湖',
            7: '蒲郡', 8: '常滑', 9: '津', 10: '三国', 11: 'びわこ', 12: '住之江',
            13: '尼崎', 14: '鳴門', 15: '丸亀', 16: '児島', 17: '宮島', 18: '徳山',
            19: '下関', 20: '若松', 21: '芦屋', 22: '福岡', 23: '唐津', 24: '大村'
        }

        # 数を制限
        if limit:
            venues = dict(list(venues.items())[:limit])
            print(f"Limiting to first {limit} venues")

        print(f"Total venues to collect: {len(venues)}\n")

        success_count = 0
        failed_count = 0

        for venue_id, venue_name in venues.items():
            print(f"[{venue_id}/{len(venues)}] Processing venue: {venue_name}")

            # 会場詳細データをスクレイピング
            venue_data = self.fetch_venue_detail(venue_id, venue_name)

            if venue_data:
                if self.save_venue_stats(venue_data):
                    success_count += 1
                else:
                    failed_count += 1
            else:
                failed_count += 1

        print(f"\n=== Venue collection complete ===")
        print(f"Success: {success_count}")
        print(f"Failed: {failed_count}")

    def fetch_venue_detail(self, venue_id, venue_name):
        """
        会場詳細ページを取得

        Args:
            venue_id: 会場ID (1-24)
            venue_name: 会場名

        Returns:
            dict: 会場詳細データ、取得失敗時はNone
        """
        url = f"{self.base_url}/stadium/index2/pid/{venue_id}/"

        try:
            print(f"Fetching venue {venue_id} ({venue_name}): {url}")
            response = self._fetch_with_retry(url)  # デフォルト: max_retries=5, timeout=60

            if not response:
                print(f"  Failed to fetch venue {venue_id}")
                return None

            soup = BeautifulSoup(response.content, 'html.parser')

            # データ抽出
            venue_data = {
                'venue_id': venue_id,
                'venue_name': venue_name,
                'course_stats': {},
                'motor_stats': [],
                'boat_stats': [],
                'exhibition_time_stats': {},
                'winning_number_stats': {}
            }

            # コース別成績を抽出
            venue_data = self._parse_venue_course_stats(soup, venue_data)

            # モーター成績を抽出
            venue_data = self._parse_venue_motor_stats(soup, venue_data)

            # ボート成績を抽出
            venue_data = self._parse_venue_boat_stats(soup, venue_data)

            # 展示タイム順位別成績を抽出
            venue_data = self._parse_venue_exhibition_stats(soup, venue_data)

            print(f"  Success: {len(venue_data.get('motor_stats', []))} motors, {len(venue_data.get('boat_stats', []))} boats")

            time.sleep(self.delay)  # レート制限
            return venue_data

        except Exception as e:
            print(f"  Error fetching venue {venue_id}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _parse_venue_course_stats(self, soup, venue_data):
        """会場のコース別成績を抽出"""
        try:
            tables = soup.find_all('table')
            course_stats = {}

            for table in tables:
                headers = []
                header_row = table.find('tr')
                if header_row:
                    headers = [th.get_text().strip() for th in header_row.find_all(['th', 'td'])]

                # コース別成績テーブルを検出（決まり手含む）
                if 'コース' in headers and '1着率' in headers and '逃げ' in headers:
                    rows = table.find_all('tr')[1:]

                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 8:
                            course_no = cells[0].get_text().strip()
                            try:
                                rate_1st = self._parse_float(cells[1].get_text().strip())
                                rate_2nd = self._parse_float(cells[2].get_text().strip())

                                # 決まり手を抽出（%形式）
                                kimarite = {
                                    '逃げ': self._parse_float(cells[3].get_text().strip()),
                                    '差し': self._parse_float(cells[4].get_text().strip()),
                                    'まくり': self._parse_float(cells[5].get_text().strip()),
                                    'まくり差し': self._parse_float(cells[6].get_text().strip()),
                                    '抜き': self._parse_float(cells[7].get_text().strip())
                                }

                                course_stats[course_no] = {
                                    '1st_rate': rate_1st,
                                    '2nd_rate': rate_2nd,
                                    '決まり手': kimarite
                                }
                            except (ValueError, IndexError):
                                continue

                    venue_data['course_stats'] = course_stats
                    break

        except Exception as e:
            print(f"  Error parsing venue course stats: {e}")

        return venue_data

    def _parse_venue_motor_stats(self, soup, venue_data):
        """会場のモーター成績を抽出"""
        try:
            tables = soup.find_all('table')
            motor_stats = []

            for table in tables:
                headers = []
                header_row = table.find('tr')
                if header_row:
                    headers = [th.get_text().strip() for th in header_row.find_all(['th', 'td'])]

                # モーター成績テーブルを検出
                if 'モーター' in headers and '2連率' in headers and '出走数' in headers:
                    rows = table.find_all('tr')[1:]

                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 5:
                            try:
                                motor_no = self._parse_number(cells[0].get_text().strip())
                                races = self._parse_number(cells[1].get_text().strip())
                                win_rate = self._parse_float(cells[2].get_text().strip())
                                rate_1st = self._parse_float(cells[3].get_text().strip())
                                rate_2nd = self._parse_float(cells[4].get_text().strip())

                                if motor_no > 0:  # 有効なモーター番号のみ
                                    motor_stats.append({
                                        'motor_no': motor_no,
                                        'races': races,
                                        'win_rate': win_rate,
                                        '1st_rate': rate_1st,
                                        '2nd_rate': rate_2nd
                                    })
                            except (ValueError, IndexError):
                                continue

                    venue_data['motor_stats'] = motor_stats
                    break

        except Exception as e:
            print(f"  Error parsing motor stats: {e}")

        return venue_data

    def _parse_venue_boat_stats(self, soup, venue_data):
        """会場のボート成績を抽出"""
        try:
            tables = soup.find_all('table')
            boat_stats = []

            for table in tables:
                headers = []
                header_row = table.find('tr')
                if header_row:
                    headers = [th.get_text().strip() for th in header_row.find_all(['th', 'td'])]

                # ボート成績テーブルを検出
                if 'ボート' in headers and '2連率' in headers and '出走数' in headers:
                    rows = table.find_all('tr')[1:]

                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 5:
                            try:
                                boat_no = self._parse_number(cells[0].get_text().strip())
                                races = self._parse_number(cells[1].get_text().strip())
                                win_rate = self._parse_float(cells[2].get_text().strip())
                                rate_1st = self._parse_float(cells[3].get_text().strip())
                                rate_2nd = self._parse_float(cells[4].get_text().strip())

                                if boat_no > 0:  # 有効なボート番号のみ
                                    boat_stats.append({
                                        'boat_no': boat_no,
                                        'races': races,
                                        'win_rate': win_rate,
                                        '1st_rate': rate_1st,
                                        '2nd_rate': rate_2nd
                                    })
                            except (ValueError, IndexError):
                                continue

                    venue_data['boat_stats'] = boat_stats
                    break

        except Exception as e:
            print(f"  Error parsing boat stats: {e}")

        return venue_data

    def _parse_venue_exhibition_stats(self, soup, venue_data):
        """会場の展示タイム順位別成績を抽出"""
        try:
            tables = soup.find_all('table')
            exhibition_stats = {}

            for table in tables:
                headers = []
                header_row = table.find('tr')
                if header_row:
                    headers = [th.get_text().strip() for th in header_row.find_all(['th', 'td'])]

                # 展示タイム順位別成績テーブルを検出
                if '展示' in ''.join(headers) and '順位' in ''.join(headers) and '1着率' in headers:
                    rows = table.find_all('tr')[1:]

                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 3:
                            try:
                                rank = cells[0].get_text().strip()
                                races = self._parse_number(cells[1].get_text().strip())
                                rate_1st = self._parse_float(cells[2].get_text().strip())

                                exhibition_stats[rank] = {
                                    'races': races,
                                    '1st_rate': rate_1st
                                }
                            except (ValueError, IndexError):
                                continue

                    venue_data['exhibition_time_stats'] = exhibition_stats
                    break

        except Exception as e:
            print(f"  Error parsing exhibition stats: {e}")

        return venue_data

    def save_venue_stats(self, venue_data):
        """会場データをデータベースに保存"""
        cursor = self.db_conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO venue_detailed_stats (
                    venue_id, venue_name, course_stats, motor_stats,
                    boat_stats, exhibition_time_stats, winning_number_stats
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (venue_id) DO UPDATE SET
                    venue_name = EXCLUDED.venue_name,
                    course_stats = EXCLUDED.course_stats,
                    motor_stats = EXCLUDED.motor_stats,
                    boat_stats = EXCLUDED.boat_stats,
                    exhibition_time_stats = EXCLUDED.exhibition_time_stats,
                    winning_number_stats = EXCLUDED.winning_number_stats,
                    updated_at = NOW()
            """, (
                venue_data['venue_id'],
                venue_data['venue_name'],
                json.dumps(venue_data.get('course_stats', {})),
                json.dumps(venue_data.get('motor_stats', [])),
                json.dumps(venue_data.get('boat_stats', [])),
                json.dumps(venue_data.get('exhibition_time_stats', {})),
                json.dumps(venue_data.get('winning_number_stats', {}))
            ))

            self.db_conn.commit()
            return True

        except Exception as e:
            self.db_conn.rollback()
            print(f"  Database error: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description='Collect detailed stats from boatrace-db.net')
    parser.add_argument('--mode', type=str, default='racers',
                        choices=['racers', 'venues', 'all'],
                        help='Collection mode (default: racers)')
    parser.add_argument('--delay', type=float, default=2.0,
                        help='Request delay in seconds (default: 2.0)')

    # テスト用オプション
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit number of racers to collect (for testing)')
    parser.add_argument('--venue-limit', type=int, default=None,
                        help='Limit number of venues to collect (for testing)')
    parser.add_argument('--racer-ids', type=str, default=None,
                        help='Comma-separated racer IDs to collect (e.g., "4001,4002,4003")')

    args = parser.parse_args()

    scraper = BoatraceDBScraper(delay=args.delay)

    try:
        # 特定の選手IDが指定されている場合
        racer_ids = None
        if args.racer_ids:
            racer_ids = [int(x.strip()) for x in args.racer_ids.split(',')]

        if args.mode == 'racers':
            scraper.collect_all_racer_stats(limit=args.limit, racer_ids=racer_ids)
        elif args.mode == 'venues':
            scraper.collect_venue_stats(limit=args.venue_limit)
        elif args.mode == 'all':
            scraper.collect_all_racer_stats(limit=args.limit, racer_ids=racer_ids)
            scraper.collect_venue_stats(limit=args.venue_limit)

    finally:
        scraper.close()


if __name__ == '__main__':
    main()
