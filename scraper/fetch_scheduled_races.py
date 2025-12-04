"""
指定日のレースデータを取得するスクリプト

使用例:
    python scraper/fetch_scheduled_races.py 2025-12-07
    python scraper/fetch_scheduled_races.py 2025-12-07 --venue 2  # 戸田のみ
"""
import argparse
import time
from datetime import datetime
from kyotei24_scraper import Kyotei24Scraper


def fetch_races_for_date(target_date, venue_ids=None, delay=3.0):
    """
    指定日のレースデータを取得

    Args:
        target_date: datetime object
        venue_ids: 取得する会場IDのリスト（Noneの場合は全24会場）
        delay: リクエスト間隔（秒）
    """
    scraper = Kyotei24Scraper()

    if venue_ids is None:
        venue_ids = list(range(1, 25))

    date_str = target_date.strftime('%Y-%m-%d')
    print(f"\n{'='*60}")
    print(f"  {date_str} のレースデータを取得")
    print(f"{'='*60}\n")
    print(f"対象会場: {venue_ids}")
    print(f"リクエスト間隔: {delay}秒")
    print()

    total_saved = 0
    total_skipped = 0

    try:
        for venue_id in venue_ids:
            venue_name = get_venue_name(venue_id)
            print(f"\n--- {venue_name} (会場{venue_id}) ---")

            for race_number in range(1, 13):
                print(f"  R{race_number:02d}: ", end="", flush=True)

                try:
                    race_data = scraper.fetch_race_data(target_date, venue_id, race_number)

                    if race_data and race_data.get('entries'):
                        # データベースに保存
                        if scraper.save_to_db(race_data):
                            total_saved += 1
                            print(f"OK ({len(race_data['entries'])}艇)")
                        else:
                            print("保存失敗")
                    else:
                        total_skipped += 1
                        print("データなし")

                except Exception as e:
                    total_skipped += 1
                    print(f"エラー: {e}")

                # レート制限
                time.sleep(delay)

    except KeyboardInterrupt:
        print("\n\n中断されました")
    finally:
        scraper.close()

    print(f"\n{'='*60}")
    print(f"  完了: {total_saved}レース保存, {total_skipped}件スキップ")
    print(f"{'='*60}\n")

    return total_saved


def get_venue_name(venue_id):
    """会場IDから会場名を取得"""
    venues = {
        1: '桐生', 2: '戸田', 3: '江戸川', 4: '平和島', 5: '多摩川', 6: '浜名湖',
        7: '蒲郡', 8: '常滑', 9: '津', 10: '三国', 11: '琵琶湖', 12: '住之江',
        13: '尼崎', 14: '鳴門', 15: '丸亀', 16: '児島', 17: '宮島', 18: '徳山',
        19: '下関', 20: '若松', 21: '芦屋', 22: '福岡', 23: '唐津', 24: '大村'
    }
    return venues.get(venue_id, f'会場{venue_id}')


def main():
    parser = argparse.ArgumentParser(description='指定日のレースデータを取得')
    parser.add_argument('date', type=str, help='取得日 (YYYY-MM-DD形式)')
    parser.add_argument('--venue', type=int, default=None, help='特定会場のみ取得 (1-24)')
    parser.add_argument('--delay', type=float, default=3.0, help='リクエスト間隔（秒）')

    args = parser.parse_args()

    try:
        target_date = datetime.strptime(args.date, '%Y-%m-%d')
    except ValueError:
        print("日付はYYYY-MM-DD形式で指定してください")
        return

    venue_ids = [args.venue] if args.venue else None

    fetch_races_for_date(target_date, venue_ids, args.delay)


if __name__ == '__main__':
    main()
