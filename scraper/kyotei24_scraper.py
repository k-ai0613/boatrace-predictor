"""
kyotei24.jp / kyotei.fun サイトからデータを取得するスクレイパー

URL形式: https://info.kyotei.fun/info-{YYYYMMDD}-{会場番号}-{レース番号}.html
例: https://info.kyotei.fun/info-20251116-01-12.html
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()


class Kyotei24Scraper:
    """kyotei.funサイトからデータを収集するスクレイパー"""

    def __init__(self):
        self.base_url = "https://info.kyotei.fun"
        self.db_conn = psycopg2.connect(os.getenv('DATABASE_URL'))

    def fetch_race_data(self, date, venue_id, race_number):
        """
        1レース分のデータを取得

        Args:
            date: datetime object
            venue_id: 会場ID (1-24)
            race_number: レース番号 (1-12)

        Returns:
            dict: レースデータ、取得失敗時はNone
        """
        # URL構築
        date_str = date.strftime('%Y%m%d')
        venue_str = str(venue_id).zfill(2)
        url = f"{self.base_url}/info-{date_str}-{venue_str}-{race_number}.html"

        try:
            response = requests.get(url, timeout=30)

            if response.status_code != 200:
                print(f"Failed to fetch: {url} (status: {response.status_code})")
                return None

            # HTMLをパース
            soup = BeautifulSoup(response.content, 'html.parser')

            # メインテーブル（Table 3）を取得
            tables = soup.find_all('table')
            if len(tables) < 3:
                print(f"Not enough tables in page: {url}")
                return None

            main_table = tables[2]  # Table 3

            # レースデータを抽出
            race_data = self.parse_race_table(main_table, date, venue_id, race_number)

            return race_data

        except Exception as e:
            print(f"Error fetching {url}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def parse_race_table(self, table, date, venue_id, race_number):
        """
        メインテーブルからデータを抽出

        Args:
            table: BeautifulSoup table element
            date: datetime object
            venue_id: 会場ID
            race_number: レース番号

        Returns:
            dict: レースデータ
        """
        rows = table.find_all('tr')

        # 各行のデータを格納
        row_data = {}
        for i, row in enumerate(rows):
            cells = row.find_all(['td', 'th'])
            if cells:
                # 最初のセルはラベル、残りは各艇のデータ
                label = cells[0].text.strip()
                values = [cell.text.strip() for cell in cells[1:]]
                row_data[i] = {'label': label, 'values': values}

        # 6艇分のデータを抽出
        entries = []
        for boat_idx in range(6):  # 6艇
            entry = self.extract_boat_data(row_data, boat_idx)
            if entry:
                entries.append(entry)

        return {
            'date': date,
            'venue_id': venue_id,
            'race_number': race_number,
            'entries': entries
        }

    def extract_boat_data(self, row_data, boat_idx):
        """
        1艇分のデータを抽出

        Args:
            row_data: 行データの辞書
            boat_idx: 艇のインデックス (0-5)

        Returns:
            dict: 1艇分のデータ
        """
        try:
            # boat_idxに対応する列からデータを取得
            entry = {}

            # Row 1: 順位（結果）
            if 0 in row_data and len(row_data[0]['values']) > boat_idx:
                result_text = row_data[0]['values'][boat_idx]
                entry['result_position'] = int(result_text) if result_text.isdigit() else None

            # Row 2: 選手番号（行3が実際の選手番号）
            if 2 in row_data and len(row_data[2]['values']) > boat_idx:
                racer_num_text = row_data[2]['values'][boat_idx]
                entry['racer_number'] = int(racer_num_text) if racer_num_text.isdigit() else 0

            # Row 3: 選手名（行4）
            if 3 in row_data and len(row_data[3]['values']) > boat_idx:
                name_text = row_data[3]['values'][boat_idx]
                # "吉田凌太 (32)" から名前を抽出
                match = re.match(r'(.+?)\s*\(', name_text)
                entry['racer_name'] = match.group(1).strip() if match else name_text

            # Row 5: 選手情報（体重を含む）
            if 5 in row_data and len(row_data[5]['values']) > boat_idx:
                info_text = row_data[5]['values'][boat_idx]
                # 体重を抽出 "52kg"
                weight_match = re.search(r'(\d+)kg', info_text)
                if weight_match:
                    entry['weight'] = float(weight_match.group(1))

            # Row 13: 級別（級過去2期）
            if 13 in row_data and len(row_data[13]['values']) > boat_idx:
                grade_text = row_data[13]['values'][boat_idx]
                # "A1" のようなフォーマットから級別を抽出（最初のA1/B1/A2/B2）
                grade_match = re.search(r'[AB][12]', grade_text)
                entry['racer_grade'] = grade_match.group(0) if grade_match else None

            # Row 7: 順位（レース結果、Row 8が実際の順位）
            # Row 10: STタイミング
            if 10 in row_data and len(row_data[10]['values']) > boat_idx:
                st_text = row_data[10]['values'][boat_idx]
                try:
                    entry['start_timing'] = float(st_text) if st_text else None
                except ValueError:
                    entry['start_timing'] = None

            # Row 11: 展示タイム
            if 11 in row_data and len(row_data[11]['values']) > boat_idx:
                ex_time_text = row_data[11]['values'][boat_idx]
                try:
                    entry['exhibition_time'] = float(ex_time_text) if ex_time_text else None
                except ValueError:
                    entry['exhibition_time'] = None

            # Row 14: 全国勝率・2連率
            if 14 in row_data and len(row_data[14]['values']) > boat_idx:
                national_text = row_data[14]['values'][boat_idx]
                # "44.78\n(6.43)" のようなフォーマット
                numbers = re.findall(r'(\d+\.?\d*)', national_text)
                if len(numbers) >= 2:
                    entry['place_rate_2'] = float(numbers[0])
                    entry['win_rate'] = float(numbers[1])

            # Row 15: 当地勝率・2連率
            if 15 in row_data and len(row_data[15]['values']) > boat_idx:
                local_text = row_data[15]['values'][boat_idx]
                numbers = re.findall(r'(\d+\.?\d*)', local_text)
                if len(numbers) >= 2:
                    entry['local_place_rate_2'] = float(numbers[0])
                    entry['local_win_rate'] = float(numbers[1])

            # Row 16: モーター2連率・番号
            if 16 in row_data and len(row_data[16]['values']) > boat_idx:
                motor_text = row_data[16]['values'][boat_idx]
                # "47.42\n[16]" のようなフォーマット
                rate_match = re.search(r'(\d+\.?\d*)', motor_text)
                num_match = re.search(r'\[(\d+)\]', motor_text)
                if rate_match:
                    entry['motor_rate_2'] = float(rate_match.group(1))
                if num_match:
                    entry['motor_number'] = int(num_match.group(1))

            # Row 17: ボート2連率・番号
            if 17 in row_data and len(row_data[17]['values']) > boat_idx:
                boat_text = row_data[17]['values'][boat_idx]
                rate_match = re.search(r'(\d+\.?\d*)', boat_text)
                num_match = re.search(r'\[(\d+)\]', boat_text)
                if rate_match:
                    entry['boat_rate_2'] = float(rate_match.group(1))
                if num_match:
                    entry['boat_hull_number'] = int(num_match.group(1))

            # Row 21: 平均ST
            if 21 in row_data and len(row_data[21]['values']) > boat_idx:
                avg_st_text = row_data[21]['values'][boat_idx]
                try:
                    entry['average_st'] = float(avg_st_text) if avg_st_text else None
                except ValueError:
                    entry['average_st'] = None

            # Row 29: フライング
            if 29 in row_data and len(row_data[29]['values']) > boat_idx:
                flying_text = row_data[29]['values'][boat_idx]
                entry['flying_count'] = int(flying_text) if flying_text.isdigit() else None

            # Row 30: 出遅れ
            if 30 in row_data and len(row_data[30]['values']) > boat_idx:
                late_text = row_data[30]['values'][boat_idx]
                entry['late_count'] = int(late_text) if late_text.isdigit() else None

            # Row 26: 2連率（期別）
            if 26 in row_data and len(row_data[26]['values']) > boat_idx:
                period_2_text = row_data[26]['values'][boat_idx]
                numbers = re.findall(r'(\d+\.?\d*)', period_2_text)
                if numbers:
                    entry['period_place_rate_2'] = float(numbers[0])

            # Row 27: 3連率（期別）
            if 27 in row_data and len(row_data[27]['values']) > boat_idx:
                period_3_text = row_data[27]['values'][boat_idx]
                numbers = re.findall(r'(\d+\.?\d*)', period_3_text)
                if numbers:
                    entry['place_rate_3'] = float(numbers[0])

            # 艇番は boat_idx + 1
            entry['boat_number'] = boat_idx + 1

            return entry

        except Exception as e:
            print(f"Error extracting boat {boat_idx + 1} data: {e}")
            return None

    def save_to_db(self, race_data):
        """データベースに保存"""
        cursor = self.db_conn.cursor()

        try:
            # レース基本情報を保存
            cursor.execute("""
                INSERT INTO races (race_date, venue_id, race_number, grade)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (race_date, venue_id, race_number) DO UPDATE
                SET grade = EXCLUDED.grade
                RETURNING id
            """, (
                race_data['date'],
                race_data['venue_id'],
                race_data['race_number'],
                '一般'  # グレードはデフォルト
            ))

            result = cursor.fetchone()
            if result:
                race_id = result[0]

                # 出走情報を保存
                for entry in race_data['entries']:
                    # デバッグ: エントリーデータを出力
                    print(f"  DEBUG: Saving entry for boat {entry.get('boat_number')}: racer_grade={entry.get('racer_grade')}, win_rate={entry.get('win_rate')}, weight={entry.get('weight')}")

                    # レーサー情報を保存
                    cursor.execute("""
                        INSERT INTO racers (racer_number, name)
                        VALUES (%s, %s)
                        ON CONFLICT (racer_number) DO UPDATE
                        SET name = EXCLUDED.name
                    """, (
                        entry.get('racer_number', 0),
                        entry.get('racer_name', '')
                    ))

                    # 出走情報を保存
                    cursor.execute("""
                        INSERT INTO race_entries
                        (race_id, boat_number, racer_id, start_timing, result_position,
                         racer_grade, win_rate, place_rate_2, place_rate_3, weight,
                         motor_number, motor_rate_2, boat_hull_number, boat_rate_2,
                         exhibition_time, local_win_rate, local_place_rate_2,
                         average_st, flying_count, late_count)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (race_id, boat_number) DO UPDATE
                        SET racer_id = EXCLUDED.racer_id,
                            start_timing = EXCLUDED.start_timing,
                            result_position = EXCLUDED.result_position,
                            racer_grade = EXCLUDED.racer_grade,
                            win_rate = EXCLUDED.win_rate,
                            place_rate_2 = EXCLUDED.place_rate_2,
                            place_rate_3 = EXCLUDED.place_rate_3,
                            weight = EXCLUDED.weight,
                            motor_number = EXCLUDED.motor_number,
                            motor_rate_2 = EXCLUDED.motor_rate_2,
                            boat_hull_number = EXCLUDED.boat_hull_number,
                            boat_rate_2 = EXCLUDED.boat_rate_2,
                            exhibition_time = EXCLUDED.exhibition_time,
                            local_win_rate = EXCLUDED.local_win_rate,
                            local_place_rate_2 = EXCLUDED.local_place_rate_2,
                            average_st = EXCLUDED.average_st,
                            flying_count = EXCLUDED.flying_count,
                            late_count = EXCLUDED.late_count
                    """, (
                        race_id,
                        entry.get('boat_number'),
                        entry.get('racer_number', 0),
                        entry.get('start_timing'),
                        entry.get('result_position'),
                        entry.get('racer_grade'),
                        entry.get('win_rate'),
                        entry.get('place_rate_2'),
                        entry.get('place_rate_3'),
                        entry.get('weight'),
                        entry.get('motor_number'),
                        entry.get('motor_rate_2'),
                        entry.get('boat_hull_number'),
                        entry.get('boat_rate_2'),
                        entry.get('exhibition_time'),
                        entry.get('local_win_rate'),
                        entry.get('local_place_rate_2'),
                        entry.get('average_st'),
                        entry.get('flying_count'),
                        entry.get('late_count')
                    ))

            self.db_conn.commit()
            print(f"Saved race {race_data['date'].strftime('%Y-%m-%d')} venue {race_data['venue_id']} race {race_data['race_number']}")
            return True

        except Exception as e:
            self.db_conn.rollback()
            print(f"Database error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def close(self):
        """リソースを解放"""
        self.db_conn.close()


if __name__ == '__main__':
    # テスト実行
    scraper = Kyotei24Scraper()

    try:
        # 2025-11-16 会場01 レース12でテスト
        test_date = datetime(2025, 11, 16)
        race_data = scraper.fetch_race_data(test_date, 1, 12)

        if race_data:
            print("=== Test Successful ===")
            print(f"Date: {race_data['date']}")
            print(f"Venue: {race_data['venue_id']}")
            print(f"Race: {race_data['race_number']}")
            print(f"Entries: {len(race_data['entries'])}")

            # 最初の艇のデータを表示
            if race_data['entries']:
                first_entry = race_data['entries'][0]
                print("\nFirst boat data:")
                for key, value in first_entry.items():
                    print(f"  {key}: {value}")

            # データベースに保存
            print("\nSaving to database...")
            scraper.save_to_db(race_data)
        else:
            print("Failed to fetch data")

    finally:
        scraper.close()
