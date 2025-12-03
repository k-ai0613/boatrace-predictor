"""
月次データ収集スクリプト

指定された年月（YYYY-MM）の全データを収集します。
サーバー負荷を軽減するため、月ごとに分割して実行します。

使用方法:
  python collect_monthly.py --year-month 2023-06

例:
  python collect_monthly.py --year-month 2023-06  # 2023年6月分を収集
  python collect_monthly.py --year-month 2024-12  # 2024年12月分を収集
  python collect_monthly.py --year-month 2024-12 --start-venue 1 --end-venue 12  # 会場1-12のみ
  python collect_monthly.py --year-month 2024-12 --start-venue 13 --end-venue 24  # 会場13-24のみ
"""

import argparse
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from collect_historical_data import collect_data


def get_month_date_range(year_month_str):
    """
    年月文字列から月初日と月末日を取得

    Args:
        year_month_str: "YYYY-MM" 形式の文字列

    Returns:
        tuple: (start_date, end_date) datetime objects
    """
    # 月初日
    start_date = datetime.strptime(year_month_str + "-01", '%Y-%m-%d')

    # 月末日（次月の1日 - 1日）
    next_month = start_date + relativedelta(months=1)
    end_date = next_month - timedelta(days=1)

    return start_date, end_date


def main():
    parser = argparse.ArgumentParser(
        description='Collect boat race data for a specific month from kyotei.fun'
    )
    parser.add_argument(
        '--year-month',
        type=str,
        required=True,
        help='Year and month in YYYY-MM format (e.g., 2023-06)'
    )
    parser.add_argument(
        '--venues',
        type=int,
        default=24,
        help='Number of venues (1-24, default: 24) - for backward compatibility'
    )
    parser.add_argument(
        '--start-venue',
        type=int,
        default=1,
        help='Start venue number (1-24, default: 1)'
    )
    parser.add_argument(
        '--end-venue',
        type=int,
        default=None,
        help='End venue number (1-24, default: same as --venues)'
    )
    parser.add_argument(
        '--races',
        type=int,
        default=12,
        help='Number of races per venue (1-12, default: 12)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=5.0,
        help='Request delay in seconds (default: 5.0)'
    )
    parser.add_argument(
        '--max-retries',
        type=int,
        default=3,
        help='Maximum retry attempts (default: 3)'
    )

    args = parser.parse_args()

    # end_venueが指定されていない場合はvenuesを使用
    end_venue = args.end_venue if args.end_venue is not None else args.venues

    # 年月のバリデーション
    try:
        start_date, end_date = get_month_date_range(args.year_month)
    except ValueError as e:
        print(f"Error: Invalid year-month format '{args.year_month}'. Use YYYY-MM format.")
        return 1

    # 未来の月はエラー
    if start_date > datetime.now():
        print(f"Error: Cannot collect data for future month '{args.year_month}'")
        return 1

    # 会場範囲のバリデーション
    start_venue = max(1, min(24, args.start_venue))
    end_venue = max(1, min(24, end_venue))
    venue_count = end_venue - start_venue + 1

    # データ収集範囲を表示
    print(f"=== Monthly Data Collection ===")
    print(f"Target month: {args.year_month}")
    print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"Total days: {(end_date - start_date).days + 1}")
    print(f"Venues: {start_venue}-{end_venue} ({venue_count} venues)")
    print(f"Estimated races: {(end_date - start_date).days + 1} days × {venue_count} venues × {args.races} races")
    print(f"Request delay: {args.delay}s")
    print()

    # データ収集実行
    try:
        collect_data(
            start_date=start_date,
            end_date=end_date,
            max_venues=end_venue,  # 後方互換性のため
            max_races=args.races,
            delay=args.delay,
            max_retries=args.max_retries,
            start_venue=start_venue,
            end_venue=end_venue
        )
        return 0
    except KeyboardInterrupt:
        print("\n\nCollection interrupted by user")
        return 130
    except Exception as e:
        print(f"\n\nCollection failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
