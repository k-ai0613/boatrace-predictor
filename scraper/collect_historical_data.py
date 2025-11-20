"""
kyotei.funから過去データを一括収集するスクリプト

使用方法:
  python collect_historical_data.py --start-date 2023-06-01 --end-date 2025-11-20

オプション:
  --start-date: 開始日（YYYY-MM-DD形式、デフォルト: 2023-06-01）
  --end-date: 終了日（YYYY-MM-DD形式、デフォルト: 今日）
  --venues: 会場数（1-24、デフォルト: 24）
  --races: 1会場あたりのレース数（1-12、デフォルト: 12）
  --delay: リクエスト間隔（秒、デフォルト: 1.0）
  --max-retries: 最大再試行回数（デフォルト: 3）
"""

import argparse
from datetime import datetime, timedelta
import time
import sys
from kyotei24_scraper import Kyotei24Scraper


def collect_data(start_date, end_date, max_venues=24, max_races=12, delay=1.0, max_retries=3):
    """
    指定期間のデータを収集

    Args:
        start_date: 開始日（datetime）
        end_date: 終了日（datetime）
        max_venues: 収集する会場数（1-24）
        max_races: 1会場あたりのレース数（1-12）
        delay: リクエスト間隔（秒）
        max_retries: 最大再試行回数
    """
    scraper = Kyotei24Scraper()

    # 統計情報
    stats = {
        'total_races': 0,
        'successful': 0,
        'failed': 0,
        'skipped': 0
    }

    # 日付範囲を計算
    current_date = start_date
    total_days = (end_date - start_date).days + 1

    print(f"=== Historical Data Collection Started ===")
    print(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"Total days: {total_days}")
    print(f"Venues: 1-{max_venues}")
    print(f"Races per venue: 1-{max_races}")
    print(f"Request delay: {delay}s")
    print(f"Estimated total races: {total_days * max_venues * max_races}")
    print()

    try:
        day_count = 0
        while current_date <= end_date:
            day_count += 1
            date_str = current_date.strftime('%Y-%m-%d')

            print(f"[Day {day_count}/{total_days}] {date_str}")

            day_success = 0
            day_failed = 0

            for venue_id in range(1, max_venues + 1):
                venue_success = 0

                for race_number in range(1, max_races + 1):
                    stats['total_races'] += 1

                    # 再試行ロジック
                    success = False
                    for attempt in range(max_retries):
                        try:
                            # データ取得
                            race_data = scraper.fetch_race_data(current_date, venue_id, race_number)

                            if race_data and race_data.get('entries'):
                                # データベースに保存
                                if scraper.save_to_db(race_data):
                                    stats['successful'] += 1
                                    venue_success += 1
                                    success = True
                                    break
                                else:
                                    # 保存失敗
                                    stats['failed'] += 1
                                    break
                            else:
                                # データが存在しない（レース未開催など）
                                stats['skipped'] += 1
                                success = True
                                break

                        except Exception as e:
                            if attempt < max_retries - 1:
                                print(f"  Venue {venue_id:2d} Race {race_number:2d}: Retry {attempt + 1}/{max_retries} - {e}")
                                time.sleep(delay * 2)  # エラー時は待機時間を2倍に
                            else:
                                print(f"  Venue {venue_id:2d} Race {race_number:2d}: Failed after {max_retries} attempts - {e}")
                                stats['failed'] += 1
                                break

                    # レート制限
                    if success:
                        time.sleep(delay)

                if venue_success > 0:
                    day_success += venue_success
                    print(f"  Venue {venue_id:2d}: {venue_success} races saved")

            # 日次サマリー
            print(f"  Day summary: {day_success} successful, {day_failed} failed")
            print(f"  Total progress: {stats['successful']}/{stats['total_races']} races ({stats['successful']*100/stats['total_races']:.1f}%)")
            print()

            # 次の日へ
            current_date += timedelta(days=1)

    except KeyboardInterrupt:
        print("\n\n=== Collection Interrupted by User ===")
    finally:
        scraper.close()

        # 最終統計
        print("\n=== Collection Completed ===")
        print(f"Total races attempted: {stats['total_races']}")
        print(f"Successfully saved: {stats['successful']}")
        print(f"Failed: {stats['failed']}")
        print(f"Skipped (no data): {stats['skipped']}")
        if stats['total_races'] > 0:
            print(f"Success rate: {stats['successful']*100/stats['total_races']:.1f}%")


def main():
    parser = argparse.ArgumentParser(description='Collect historical boat race data from kyotei.fun')
    parser.add_argument('--start-date', type=str, default='2023-06-01',
                        help='Start date (YYYY-MM-DD format, or "yesterday")')
    parser.add_argument('--end-date', type=str, default=None,
                        help='End date (YYYY-MM-DD format, "yesterday", or default: today)')
    parser.add_argument('--venues', type=int, default=24,
                        help='Number of venues (1-24, default: 24)')
    parser.add_argument('--races', type=int, default=12,
                        help='Number of races per venue (1-12, default: 12)')
    parser.add_argument('--delay', type=float, default=1.0,
                        help='Request delay in seconds (default: 1.0)')
    parser.add_argument('--max-retries', type=int, default=3,
                        help='Maximum retry attempts (default: 3)')

    args = parser.parse_args()

    # 日付をパース
    if args.start_date == 'yesterday':
        start_date = datetime.now() - timedelta(days=1)
    elif args.start_date == 'today':
        start_date = datetime.now()
    else:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d')

    if args.end_date:
        if args.end_date == 'yesterday':
            end_date = datetime.now() - timedelta(days=1)
        elif args.end_date == 'today':
            end_date = datetime.now()
        else:
            end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
    else:
        end_date = datetime.now()

    # バリデーション
    if start_date > end_date:
        print("Error: Start date must be before end date")
        sys.exit(1)

    if not (1 <= args.venues <= 24):
        print("Error: Venues must be between 1 and 24")
        sys.exit(1)

    if not (1 <= args.races <= 12):
        print("Error: Races must be between 1 and 12")
        sys.exit(1)

    # データ収集開始
    collect_data(
        start_date=start_date,
        end_date=end_date,
        max_venues=args.venues,
        max_races=args.races,
        delay=args.delay,
        max_retries=args.max_retries
    )


if __name__ == '__main__':
    main()
