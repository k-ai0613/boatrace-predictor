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
        """レース結果と出走表データを取得"""
        # レース結果を取得
        result_url = (
            f"{self.base_url}/owpc/pc/race/raceresult"
            f"?hd={date.strftime('%Y%m%d')}"
            f"&jcd={str(venue_id).zfill(2)}"
            f"&rno={race_number}"
        )

        result_html = await self.fetch_with_retry(result_url)
        if not result_html:
            return None

        soup = BeautifulSoup(result_html, 'html.parser')
        race_data = self.parse_race_result(soup, date, venue_id, race_number)

        if not race_data:
            return None

        # 出走表データも取得（エラーが出ても継続）
        try:
            beforeinfo_data = await self.fetch_race_beforeinfo(date, venue_id, race_number)
            if beforeinfo_data and 'beforeinfo' in beforeinfo_data:
                race_data['beforeinfo'] = beforeinfo_data['beforeinfo']
        except Exception as e:
            print(f"Beforeinfo fetch error (continuing): {e}")

        return race_data

    async def fetch_race_beforeinfo(self, date, venue_id, race_number):
        """出走表（事前情報）を取得"""
        url = (
            f"{self.base_url}/owpc/pc/race/beforeinfo"
            f"?hd={date.strftime('%Y%m%d')}"
            f"&jcd={str(venue_id).zfill(2)}"
            f"&rno={race_number}"
        )

        html = await self.fetch_with_retry(url)
        if html:
            soup = BeautifulSoup(html, 'html.parser')
            return self.parse_race_beforeinfo(soup, date, venue_id, race_number)
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

            # 出走時刻を取得
            race_time = None
            time_elem = soup.select_one('.heading2_time, .is-time, .time')
            if time_elem:
                time_text = time_elem.text.strip()
                # "15:30" のような形式から時刻を抽出
                import re
                time_match = re.search(r'(\d{1,2}):(\d{2})', time_text)
                if time_match:
                    race_time = time_match.group(0)  # "15:30" 形式

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
                    'winning_technique': None,  # 決まり手（1着のみ）
                }
                entries.append(entry)

            # STタイミング情報（2つ目のis-w495テーブル）
            if len(tables) >= 2:
                st_table = tables[1]
                st_rows = st_table.select('tbody tr')

                for course_position, st_row in enumerate(st_rows, start=1):
                    # 艇番を取得
                    boat_num_elem = st_row.select_one('.table1_boatImage1Number')
                    if not boat_num_elem:
                        continue

                    boat_num = int(boat_num_elem.text.strip())

                    # STタイミングと決まり手を取得
                    st_time_elem = st_row.select_one('.table1_boatImage1TimeInner')
                    st_timing = None
                    winning_technique = None

                    if st_time_elem:
                        st_full_text = st_time_elem.text.strip()
                        st_parts = st_full_text.split()

                        # ST タイミング（最初の部分）
                        if len(st_parts) > 0:
                            try:
                                st_timing = float(st_parts[0])
                            except ValueError:
                                st_timing = None

                        # 決まり手（2番目の部分、1着のみ）
                        if len(st_parts) > 1:
                            winning_technique = st_parts[1]

                    # 該当する艇のエントリーにSTタイミング、進入コース、決まり手を追加
                    for entry in entries:
                        if entry['boat_number'] == boat_num:
                            entry['start_timing'] = st_timing
                            entry['course'] = course_position  # 実際の進入コース（1-6）
                            if winning_technique:
                                entry['winning_technique'] = winning_technique
                            break

            # 気象情報を取得
            weather_data = self._parse_weather(soup)

            return {
                'date': date,
                'venue_id': venue_id,
                'race_number': race_number,
                'grade': grade,
                'race_time': race_time,
                'entries': entries,
                'weather': weather_data
            }

        except Exception as e:
            print(f"Parse error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def parse_race_beforeinfo(self, soup, date, venue_id, race_number):
        """出走表ページから事前情報を抽出"""
        try:
            beforeinfo_data = {}

            # 出走表テーブルを取得
            table = soup.select_one('table.is-w495')
            if not table:
                return None

            # 各艇のデータを抽出
            tbodies = table.select('tbody.is-fs12')

            for tbody in tbodies:
                # 艇番を取得
                boat_num_elem = tbody.select_one('.is-boatColor1')
                if not boat_num_elem:
                    continue
                boat_number = int(boat_num_elem.text.strip())

                # 選手情報を取得
                racer_td = tbody.select('td')[2]  # 3列目が選手情報

                # 選手登録番号
                racer_num_elem = racer_td.select_one('.is-fs11')
                racer_number = int(racer_num_elem.text.strip()) if racer_num_elem else 0

                # 級別（A1, A2, B1, B2）
                grade_elem = racer_td.select_one('.is-fs14')
                grade = grade_elem.text.strip() if grade_elem else None

                # 勝率、2連率、3連率（複数のspanから取得）
                stats_elems = racer_td.select('.is-fs12')
                win_rate = None
                place_rate_2 = None
                place_rate_3 = None
                local_win_rate = None
                local_place_rate_2 = None
                average_st = None
                flying_count = None
                late_count = None

                if len(stats_elems) >= 3:
                    try:
                        # 全国成績
                        win_rate = float(stats_elems[0].text.strip())
                        place_rate_2 = float(stats_elems[1].text.strip().replace('%', ''))
                        place_rate_3 = float(stats_elems[2].text.strip().replace('%', ''))

                        # 当地成績（通常は全国成績の後に表示される）
                        if len(stats_elems) >= 5:
                            local_win_rate = float(stats_elems[3].text.strip())
                            local_place_rate_2 = float(stats_elems[4].text.strip().replace('%', ''))
                    except (ValueError, IndexError):
                        pass

                # 平均ST（通常は別のエリアに表示）
                avg_st_elem = racer_td.select_one('.avgST, .is-avgST')
                if avg_st_elem:
                    try:
                        st_text = avg_st_elem.text.strip().replace('.', '')
                        average_st = float('0.' + st_text) if st_text else None
                    except (ValueError, AttributeError):
                        pass

                # F・L回数（通常はテーブルの別の部分に表示）
                fl_elems = tbody.select('.is-fBold, .is-flying, .is-late')
                for elem in fl_elems:
                    text = elem.text.strip().upper()
                    if 'F' in text:
                        try:
                            flying_count = int(''.join(filter(str.isdigit, text)))
                        except ValueError:
                            pass
                    elif 'L' in text:
                        try:
                            late_count = int(''.join(filter(str.isdigit, text)))
                        except ValueError:
                            pass

                # 直近成績（前節・今節）
                prev_session_result = None
                current_session_result = None
                recent_5_races = None

                # コース別成績（1-6コース）
                course_1_rate = None
                course_2_rate = None
                course_3_rate = None
                course_4_rate = None
                course_5_rate = None
                course_6_rate = None

                # 決まり手統計（6種類）
                winning_tech_nige = None      # 逃げ
                winning_tech_sashi = None     # 差し
                winning_tech_makuri = None    # まくり
                winning_tech_makuri_sashi = None  # まくり差し
                winning_tech_nuki = None      # 抜き
                winning_tech_megumare = None  # 恵まれ

                # 前節・今節成績は通常、選手情報の下部に表示される
                # "前節 1-2-1-4" のような形式
                session_elems = tbody.select('.is-fs11, .is-fs12')
                for elem in session_elems:
                    text = elem.text.strip()
                    if '前節' in text or '前' in text:
                        # "前節 1-2-1-4" から "1-2-1-4" を抽出
                        import re
                        result_match = re.search(r'(\d+-\d+-\d+-\d+)', text)
                        if result_match:
                            prev_session_result = result_match.group(1)
                    elif '今節' in text or '今' in text:
                        result_match = re.search(r'(\d+-\d+-\d+-\d+)', text)
                        if result_match:
                            current_session_result = result_match.group(1)

                # 直近5走の成績（通常は別のセクションに表示）
                # テーブル内の成績履歴から抽出
                recent_races_elems = tbody.select('.is-fs11, .is-fs12, .chart')
                for elem in recent_races_elems:
                    text = elem.text.strip()
                    # "直近5走" や着順の連続（例: "1 3 2 4 1"）を検索
                    import re
                    # 数字のみの連続パターン（スペース区切りまたはハイフン区切り）
                    race_pattern = re.search(r'(?:^|\s)([1-6]\s*[1-6]\s*[1-6]\s*[1-6]\s*[1-6])(?:\s|$)', text)
                    if race_pattern:
                        # スペースをハイフンに統一
                        recent_5_races = '-'.join(race_pattern.group(1).split())
                        break

                # コース別成績の抽出
                # 通常はテーブル形式で "1コース xx%" のように表示
                course_elems = tbody.select('.is-fs11, .is-fs12, td')
                for elem in course_elems:
                    text = elem.text.strip()
                    import re
                    # "1コース xx%" や "1C xx%" のようなパターン
                    for course_num in range(1, 7):
                        course_pattern = re.search(rf'{course_num}[Cコース].*?(\d+\.?\d*)%?', text)
                        if course_pattern:
                            try:
                                rate_value = float(course_pattern.group(1))
                                if course_num == 1:
                                    course_1_rate = rate_value
                                elif course_num == 2:
                                    course_2_rate = rate_value
                                elif course_num == 3:
                                    course_3_rate = rate_value
                                elif course_num == 4:
                                    course_4_rate = rate_value
                                elif course_num == 5:
                                    course_5_rate = rate_value
                                elif course_num == 6:
                                    course_6_rate = rate_value
                            except ValueError:
                                pass

                # 決まり手統計の抽出
                # 通常は "逃げ XX回" や "逃げ XX%" のように表示
                winning_tech_elems = tbody.select('.is-fs11, .is-fs12, td')
                for elem in winning_tech_elems:
                    text = elem.text.strip()
                    import re

                    # 逃げ
                    if '逃げ' in text or 'にげ' in text:
                        nige_pattern = re.search(r'(\d+\.?\d*)[回%]', text)
                        if nige_pattern:
                            try:
                                winning_tech_nige = float(nige_pattern.group(1))
                            except ValueError:
                                pass

                    # 差し
                    if '差し' in text or 'さし' in text:
                        sashi_pattern = re.search(r'(\d+\.?\d*)[回%]', text)
                        if sashi_pattern:
                            try:
                                winning_tech_sashi = float(sashi_pattern.group(1))
                            except ValueError:
                                pass

                    # まくり
                    if 'まくり' in text and 'まくり差し' not in text:
                        makuri_pattern = re.search(r'(\d+\.?\d*)[回%]', text)
                        if makuri_pattern:
                            try:
                                winning_tech_makuri = float(makuri_pattern.group(1))
                            except ValueError:
                                pass

                    # まくり差し
                    if 'まくり差し' in text:
                        makuri_sashi_pattern = re.search(r'(\d+\.?\d*)[回%]', text)
                        if makuri_sashi_pattern:
                            try:
                                winning_tech_makuri_sashi = float(makuri_sashi_pattern.group(1))
                            except ValueError:
                                pass

                    # 抜き
                    if '抜き' in text or 'ぬき' in text:
                        nuki_pattern = re.search(r'(\d+\.?\d*)[回%]', text)
                        if nuki_pattern:
                            try:
                                winning_tech_nuki = float(nuki_pattern.group(1))
                            except ValueError:
                                pass

                    # 恵まれ
                    if '恵まれ' in text or 'めぐまれ' in text:
                        megumare_pattern = re.search(r'(\d+\.?\d*)[回%]', text)
                        if megumare_pattern:
                            try:
                                winning_tech_megumare = float(megumare_pattern.group(1))
                            except ValueError:
                                pass

                # 体重
                weight_elem = tbody.select('td')[3]
                weight = None
                if weight_elem:
                    weight_text = weight_elem.text.strip().replace('kg', '')
                    try:
                        weight = float(weight_text)
                    except ValueError:
                        pass

                # モーター情報（4列目）
                motor_td = tbody.select('td')[4] if len(tbody.select('td')) > 4 else None
                motor_number = None
                motor_rate_2 = None
                motor_rate_3 = None

                if motor_td:
                    motor_num_elem = motor_td.select_one('.is-fs14')
                    if motor_num_elem:
                        try:
                            motor_number = int(motor_num_elem.text.strip())
                        except ValueError:
                            pass

                    # 2連率と3連率（通常は複数の要素に表示）
                    motor_rate_elems = motor_td.select('.is-fs12')
                    if len(motor_rate_elems) >= 1:
                        try:
                            motor_rate_2 = float(motor_rate_elems[0].text.strip().replace('%', ''))
                        except (ValueError, IndexError):
                            pass
                    if len(motor_rate_elems) >= 2:
                        try:
                            motor_rate_3 = float(motor_rate_elems[1].text.strip().replace('%', ''))
                        except (ValueError, IndexError):
                            pass

                # ボート情報（5列目）
                boat_td = tbody.select('td')[5] if len(tbody.select('td')) > 5 else None
                boat_hull_number = None
                boat_rate_2 = None
                boat_rate_3 = None

                if boat_td:
                    boat_num_elem = boat_td.select_one('.is-fs14')
                    if boat_num_elem:
                        try:
                            boat_hull_number = int(boat_num_elem.text.strip())
                        except ValueError:
                            pass

                    # 2連率と3連率（通常は複数の要素に表示）
                    boat_rate_elems = boat_td.select('.is-fs12')
                    if len(boat_rate_elems) >= 1:
                        try:
                            boat_rate_2 = float(boat_rate_elems[0].text.strip().replace('%', ''))
                        except (ValueError, IndexError):
                            pass
                    if len(boat_rate_elems) >= 2:
                        try:
                            boat_rate_3 = float(boat_rate_elems[1].text.strip().replace('%', ''))
                        except (ValueError, IndexError):
                            pass

                # 展示タイム（6列目）
                exhibition_td = tbody.select('td')[6] if len(tbody.select('td')) > 6 else None
                exhibition_time = None
                exhibition_turn_time = None  # まわり足タイム
                exhibition_straight_time = None  # 直線タイム

                if exhibition_td:
                    time_elem = exhibition_td.select_one('.is-fs14')
                    if time_elem:
                        time_text = time_elem.text.strip()
                        try:
                            exhibition_time = float(time_text)
                        except ValueError:
                            pass

                    # まわり足タイムと直線タイム（通常は別の要素に表示）
                    detail_elems = exhibition_td.select('.is-fs11, .is-fs12')
                    for detail_elem in detail_elems:
                        detail_text = detail_elem.text.strip()
                        # "まわり 6.78" や "直線 6.45" のような形式
                        if 'まわり' in detail_text or '回' in detail_text:
                            try:
                                import re
                                turn_match = re.search(r'(\d+\.\d+)', detail_text)
                                if turn_match:
                                    exhibition_turn_time = float(turn_match.group(1))
                            except ValueError:
                                pass
                        elif '直線' in detail_text or '直' in detail_text:
                            try:
                                import re
                                straight_match = re.search(r'(\d+\.\d+)', detail_text)
                                if straight_match:
                                    exhibition_straight_time = float(straight_match.group(1))
                            except ValueError:
                                pass

                # データを格納
                beforeinfo_data[boat_number] = {
                    'racer_number': racer_number,
                    'racer_grade': grade,
                    'win_rate': win_rate,
                    'place_rate_2': place_rate_2,
                    'place_rate_3': place_rate_3,
                    'weight': weight,
                    'motor_number': motor_number,
                    'motor_rate_2': motor_rate_2,
                    'motor_rate_3': motor_rate_3,
                    'boat_hull_number': boat_hull_number,
                    'boat_rate_2': boat_rate_2,
                    'boat_rate_3': boat_rate_3,
                    'exhibition_time': exhibition_time,
                    # フェーズ1: 追加フィールド
                    'local_win_rate': local_win_rate,
                    'local_place_rate_2': local_place_rate_2,
                    'average_st': average_st,
                    'flying_count': flying_count,
                    'late_count': late_count,
                    # フェーズ2: 追加フィールド
                    'prev_session_result': prev_session_result,
                    'current_session_result': current_session_result,
                    # フェーズ3: 追加フィールド
                    'recent_5_races': recent_5_races,
                    'exhibition_turn_time': exhibition_turn_time,
                    'exhibition_straight_time': exhibition_straight_time,
                    # コース別成績
                    'course_1_rate': course_1_rate,
                    'course_2_rate': course_2_rate,
                    'course_3_rate': course_3_rate,
                    'course_4_rate': course_4_rate,
                    'course_5_rate': course_5_rate,
                    'course_6_rate': course_6_rate,
                    # 決まり手統計
                    'winning_tech_nige': winning_tech_nige,
                    'winning_tech_sashi': winning_tech_sashi,
                    'winning_tech_makuri': winning_tech_makuri,
                    'winning_tech_makuri_sashi': winning_tech_makuri_sashi,
                    'winning_tech_nuki': winning_tech_nuki,
                    'winning_tech_megumare': winning_tech_megumare
                }

            return {
                'date': date,
                'venue_id': venue_id,
                'race_number': race_number,
                'beforeinfo': beforeinfo_data
            }

        except Exception as e:
            print(f"Beforeinfo parse error: {e}")
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

            # 風速と風向き
            wind_elem = weather_div.select_one('.is-wind .weather1_bodyUnitLabelData')
            if wind_elem:
                wind_text = wind_elem.text.strip().replace('m', '')
                try:
                    weather_data['wind_speed'] = float(wind_text)
                except ValueError:
                    weather_data['wind_speed'] = None

            # 風向き（風速の隣または別要素）
            wind_direction_elem = weather_div.select_one('.is-wind .weather1_bodyUnitLabelTitle')
            if wind_direction_elem:
                weather_data['wind_direction'] = wind_direction_elem.text.strip()
            else:
                # 風向きが風速と同じ要素に含まれている場合もある
                wind_full_elem = weather_div.select_one('.is-wind')
                if wind_full_elem:
                    wind_full_text = wind_full_elem.text.strip()
                    # "3m 北東" のような形式から方向を抽出
                    import re
                    direction_match = re.search(r'[東西南北]+', wind_full_text)
                    if direction_match:
                        weather_data['wind_direction'] = direction_match.group(0)
                    else:
                        weather_data['wind_direction'] = None
                else:
                    weather_data['wind_direction'] = None

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

            # 潮位（通常は別の要素に表示）
            tide_elem = weather_div.select_one('.is-tide .weather1_bodyUnitLabelData, .tide')
            if tide_elem:
                tide_text = tide_elem.text.strip().replace('cm', '')
                try:
                    weather_data['tide_level'] = float(tide_text)
                except ValueError:
                    weather_data['tide_level'] = None
            else:
                weather_data['tide_level'] = None

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
                    INSERT INTO races (race_date, venue_id, race_number, grade, race_time)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (race_date, venue_id, race_number) DO UPDATE
                    SET grade = EXCLUDED.grade,
                        race_time = COALESCE(EXCLUDED.race_time, races.race_time)
                    RETURNING id
                """, (
                    race['date'],
                    race['venue_id'],
                    race['race_number'],
                    race['grade'],
                    race.get('race_time')
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

                        # 出走情報を保存（beforeinfoデータがあれば含める）
                        beforeinfo = {}
                        if 'beforeinfo' in race and entry['boat_number'] in race['beforeinfo']:
                            beforeinfo = race['beforeinfo'][entry['boat_number']]

                        cursor.execute("""
                            INSERT INTO race_entries
                            (race_id, boat_number, racer_id, start_timing, result_position,
                             racer_grade, win_rate, place_rate_2, place_rate_3, weight,
                             motor_number, motor_rate_2, motor_rate_3, boat_hull_number, boat_rate_2, boat_rate_3, exhibition_time,
                             local_win_rate, local_place_rate_2, average_st, flying_count, late_count, actual_course,
                             prev_session_result, current_session_result,
                             recent_5_races, exhibition_turn_time, exhibition_straight_time,
                             course_1_rate, course_2_rate, course_3_rate, course_4_rate, course_5_rate, course_6_rate,
                             winning_tech_nige, winning_tech_sashi, winning_tech_makuri, winning_tech_makuri_sashi, winning_tech_nuki, winning_tech_megumare,
                             winning_technique)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (race_id, boat_number) DO UPDATE
                            SET racer_id = EXCLUDED.racer_id,
                                start_timing = EXCLUDED.start_timing,
                                result_position = EXCLUDED.result_position,
                                racer_grade = COALESCE(EXCLUDED.racer_grade, race_entries.racer_grade),
                                win_rate = COALESCE(EXCLUDED.win_rate, race_entries.win_rate),
                                place_rate_2 = COALESCE(EXCLUDED.place_rate_2, race_entries.place_rate_2),
                                place_rate_3 = COALESCE(EXCLUDED.place_rate_3, race_entries.place_rate_3),
                                weight = COALESCE(EXCLUDED.weight, race_entries.weight),
                                motor_number = COALESCE(EXCLUDED.motor_number, race_entries.motor_number),
                                motor_rate_2 = COALESCE(EXCLUDED.motor_rate_2, race_entries.motor_rate_2),
                                motor_rate_3 = COALESCE(EXCLUDED.motor_rate_3, race_entries.motor_rate_3),
                                boat_hull_number = COALESCE(EXCLUDED.boat_hull_number, race_entries.boat_hull_number),
                                boat_rate_2 = COALESCE(EXCLUDED.boat_rate_2, race_entries.boat_rate_2),
                                boat_rate_3 = COALESCE(EXCLUDED.boat_rate_3, race_entries.boat_rate_3),
                                exhibition_time = COALESCE(EXCLUDED.exhibition_time, race_entries.exhibition_time),
                                local_win_rate = COALESCE(EXCLUDED.local_win_rate, race_entries.local_win_rate),
                                local_place_rate_2 = COALESCE(EXCLUDED.local_place_rate_2, race_entries.local_place_rate_2),
                                average_st = COALESCE(EXCLUDED.average_st, race_entries.average_st),
                                flying_count = COALESCE(EXCLUDED.flying_count, race_entries.flying_count),
                                late_count = COALESCE(EXCLUDED.late_count, race_entries.late_count),
                                actual_course = COALESCE(EXCLUDED.actual_course, race_entries.actual_course),
                                prev_session_result = COALESCE(EXCLUDED.prev_session_result, race_entries.prev_session_result),
                                current_session_result = COALESCE(EXCLUDED.current_session_result, race_entries.current_session_result),
                                recent_5_races = COALESCE(EXCLUDED.recent_5_races, race_entries.recent_5_races),
                                exhibition_turn_time = COALESCE(EXCLUDED.exhibition_turn_time, race_entries.exhibition_turn_time),
                                exhibition_straight_time = COALESCE(EXCLUDED.exhibition_straight_time, race_entries.exhibition_straight_time),
                                course_1_rate = COALESCE(EXCLUDED.course_1_rate, race_entries.course_1_rate),
                                course_2_rate = COALESCE(EXCLUDED.course_2_rate, race_entries.course_2_rate),
                                course_3_rate = COALESCE(EXCLUDED.course_3_rate, race_entries.course_3_rate),
                                course_4_rate = COALESCE(EXCLUDED.course_4_rate, race_entries.course_4_rate),
                                course_5_rate = COALESCE(EXCLUDED.course_5_rate, race_entries.course_5_rate),
                                course_6_rate = COALESCE(EXCLUDED.course_6_rate, race_entries.course_6_rate),
                                winning_tech_nige = COALESCE(EXCLUDED.winning_tech_nige, race_entries.winning_tech_nige),
                                winning_tech_sashi = COALESCE(EXCLUDED.winning_tech_sashi, race_entries.winning_tech_sashi),
                                winning_tech_makuri = COALESCE(EXCLUDED.winning_tech_makuri, race_entries.winning_tech_makuri),
                                winning_tech_makuri_sashi = COALESCE(EXCLUDED.winning_tech_makuri_sashi, race_entries.winning_tech_makuri_sashi),
                                winning_tech_nuki = COALESCE(EXCLUDED.winning_tech_nuki, race_entries.winning_tech_nuki),
                                winning_tech_megumare = COALESCE(EXCLUDED.winning_tech_megumare, race_entries.winning_tech_megumare),
                                winning_technique = COALESCE(EXCLUDED.winning_technique, race_entries.winning_technique)
                        """, (
                            race_id,
                            entry['boat_number'],
                            entry['racer_number'],
                            entry['start_timing'],
                            entry['result_position'],
                            beforeinfo.get('racer_grade'),
                            beforeinfo.get('win_rate'),
                            beforeinfo.get('place_rate_2'),
                            beforeinfo.get('place_rate_3'),
                            beforeinfo.get('weight'),
                            beforeinfo.get('motor_number'),
                            beforeinfo.get('motor_rate_2'),
                            beforeinfo.get('motor_rate_3'),
                            beforeinfo.get('boat_hull_number'),
                            beforeinfo.get('boat_rate_2'),
                            beforeinfo.get('boat_rate_3'),
                            beforeinfo.get('exhibition_time'),
                            beforeinfo.get('local_win_rate'),
                            beforeinfo.get('local_place_rate_2'),
                            beforeinfo.get('average_st'),
                            beforeinfo.get('flying_count'),
                            beforeinfo.get('late_count'),
                            entry.get('course'),
                            beforeinfo.get('prev_session_result'),
                            beforeinfo.get('current_session_result'),
                            beforeinfo.get('recent_5_races'),
                            beforeinfo.get('exhibition_turn_time'),
                            beforeinfo.get('exhibition_straight_time'),
                            beforeinfo.get('course_1_rate'),
                            beforeinfo.get('course_2_rate'),
                            beforeinfo.get('course_3_rate'),
                            beforeinfo.get('course_4_rate'),
                            beforeinfo.get('course_5_rate'),
                            beforeinfo.get('course_6_rate'),
                            beforeinfo.get('winning_tech_nige'),
                            beforeinfo.get('winning_tech_sashi'),
                            beforeinfo.get('winning_tech_makuri'),
                            beforeinfo.get('winning_tech_makuri_sashi'),
                            beforeinfo.get('winning_tech_nuki'),
                            beforeinfo.get('winning_tech_megumare'),
                            entry.get('winning_technique')
                        ))

                    # 気象データを保存
                    if race.get('weather'):
                        weather = race['weather']
                        cursor.execute("""
                            INSERT INTO weather_data
                            (race_id, temperature, weather_condition,
                             wind_speed, wind_direction, water_temperature, wave_height, tide_level)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (race_id) DO UPDATE
                            SET temperature = EXCLUDED.temperature,
                                weather_condition = EXCLUDED.weather_condition,
                                wind_speed = EXCLUDED.wind_speed,
                                wind_direction = COALESCE(EXCLUDED.wind_direction, weather_data.wind_direction),
                                water_temperature = EXCLUDED.water_temperature,
                                wave_height = EXCLUDED.wave_height,
                                tide_level = COALESCE(EXCLUDED.tide_level, weather_data.tide_level)
                        """, (
                            race_id,
                            weather.get('temperature'),
                            weather.get('weather'),
                            weather.get('wind_speed'),
                            weather.get('wind_direction'),
                            weather.get('water_temperature'),
                            weather.get('wave_height'),
                            weather.get('tide_level')
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
