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
        # TODO: HTMLから登録期、支部を抽出
        # 実装はHTMLの構造確認後に追加
        return racer_data

    def _parse_racer_overall_stats(self, soup, racer_data):
        """通算成績を抽出"""
        # TODO: HTMLから通算成績を抽出
        # 実装はHTMLの構造確認後に追加
        return racer_data

    def _parse_boat_number_stats(self, soup, racer_data):
        """艇番別成績を抽出"""
        # TODO: HTMLから艇番別成績を抽出
        # 実装はHTMLの構造確認後に追加
        return racer_data

    def _parse_course_stats(self, soup, racer_data):
        """コース別成績を抽出"""
        # TODO: HTMLからコース別成績を抽出
        # 実装はHTMLの構造確認後に追加
        return racer_data

    def _parse_venue_stats(self, soup, racer_data):
        """場別成績を抽出"""
        # TODO: HTMLから場別成績を抽出
        # 実装はHTMLの構造確認後に追加
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
        print("TODO: Implement venue stats collection")
        # TODO: 会場データ収集機能を実装


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
