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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def close(self):
        """データベース接続を閉じる"""
        if self.db_conn:
            self.db_conn.close()

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
            response = self.session.get(url, timeout=30)

            if response.status_code != 200:
                print(f"  Failed: HTTP {response.status_code}")
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

                # DEBUG: Print headers
                # print(f"  Table {i} headers: {headers[:5]}")  # 最初の5列のみ

                # グレード別成績テーブルを特定（より柔軟に）
                if ('グレード' in ''.join(headers) or
                    '出走数' in ''.join(headers) or
                    ('勝率' in ''.join(headers) and '1着率' in ''.join(headers))):
                    rows = table.find_all('tr')[1:]  # ヘッダー行をスキップ

                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 10:
                            grade = cells[0].get_text().strip()
                            try:
                                races = int(cells[2].get_text().strip()) if cells[2].get_text().strip().isdigit() else 0
                                wins = int(cells[3].get_text().strip()) if cells[3].get_text().strip().isdigit() else 0
                                win_rate = float(cells[4].get_text().strip()) if cells[4].get_text().strip() else 0.0
                                rate_1st = float(cells[5].get_text().strip()) if cells[5].get_text().strip() else 0.0
                                rate_2nd = float(cells[6].get_text().strip()) if cells[6].get_text().strip() else 0.0
                                rate_3rd = float(cells[7].get_text().strip()) if cells[7].get_text().strip() else 0.0

                                grade_stats[grade] = {
                                    'races': races,
                                    'wins': wins,
                                    'win_rate': win_rate,
                                    '1st_rate': rate_1st,
                                    '2nd_rate': rate_2nd,
                                    '3rd_rate': rate_3rd
                                }

                                # 「一般」グレードの成績を全体統計として使用
                                if grade == '一般':
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

                # 艇番別成績テーブルを特定
                if '艇番' in ''.join(headers):
                    rows = table.find_all('tr')[1:]

                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 6:
                            boat_no = cells[0].get_text().strip()
                            try:
                                races = int(cells[1].get_text().strip()) if cells[1].get_text().strip().isdigit() else 0
                                rate_1st = float(cells[3].get_text().strip()) if cells[3].get_text().strip() else 0.0
                                rate_2nd = float(cells[4].get_text().strip()) if cells[4].get_text().strip() else 0.0

                                boat_stats[boat_no] = {
                                    'races': races,
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
        """コース別成績を抽出"""
        try:
            tables = soup.find_all('table')
            course_stats = {}

            for table in tables:
                headers = []
                header_row = table.find('tr')
                if header_row:
                    headers = [th.get_text().strip() for th in header_row.find_all(['th', 'td'])]

                # コース別成績テーブルを特定
                if 'コース' in ''.join(headers) and '平均ST' in ''.join(headers):
                    rows = table.find_all('tr')[1:]

                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 7:
                            course_no = cells[0].get_text().strip()
                            try:
                                races = int(cells[1].get_text().strip()) if cells[1].get_text().strip().isdigit() else 0
                                rate_1st = float(cells[3].get_text().strip()) if cells[3].get_text().strip() else 0.0
                                rate_2nd = float(cells[4].get_text().strip()) if cells[4].get_text().strip() else 0.0
                                avg_st = float(cells[6].get_text().strip()) if cells[6].get_text().strip() else 0.0

                                course_stats[course_no] = {
                                    'races': races,
                                    '1st_rate': rate_1st,
                                    '2nd_rate': rate_2nd,
                                    'avg_st': avg_st
                                }
                            except (ValueError, IndexError):
                                continue

                    racer_data['course_stats'] = course_stats
                    break

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

    def collect_all_racer_stats(self):
        """登録済み全選手の詳細統計を収集"""
        racers = self.get_registered_racers()

        print(f"\n=== Starting racer stats collection ===")
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

    def collect_venue_stats(self):
        """全24会場の詳細統計を収集"""
        print("\n=== Venue stats collection ===")

        venues = {
            1: '桐生', 2: '戸田', 3: '江戸川', 4: '平和島', 5: '多摩川', 6: '浜名湖',
            7: '蒲郡', 8: '常滑', 9: '津', 10: '三国', 11: 'びわこ', 12: '住之江',
            13: '尼崎', 14: '鳴門', 15: '丸亀', 16: '児島', 17: '宮島', 18: '徳山',
            19: '下関', 20: '若松', 21: '芦屋', 22: '福岡', 23: '唐津', 24: '大村'
        }

        success_count = 0
        failed_count = 0

        for venue_id, venue_name in venues.items():
            print(f"[{venue_id}/24] Processing venue: {venue_name}")

            # 基本的な会場データを保存（詳細なスクレイピングは今後実装）
            venue_data = {
                'venue_id': venue_id,
                'venue_name': venue_name,
                'course_stats': {},
                'motor_stats': [],
                'boat_stats': [],
                'exhibition_time_stats': {},
                'winning_number_stats': {}
            }

            if self.save_venue_stats(venue_data):
                success_count += 1
            else:
                failed_count += 1

            time.sleep(self.delay)

        print(f"\n=== Venue collection complete ===")
        print(f"Success: {success_count}")
        print(f"Failed: {failed_count}")

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

    args = parser.parse_args()

    scraper = BoatraceDBScraper(delay=args.delay)

    try:
        if args.mode == 'racers':
            scraper.collect_all_racer_stats()
        elif args.mode == 'venues':
            scraper.collect_venue_stats()
        elif args.mode == 'all':
            scraper.collect_all_racer_stats()
            scraper.collect_venue_stats()

    finally:
        scraper.close()


if __name__ == '__main__':
    main()
