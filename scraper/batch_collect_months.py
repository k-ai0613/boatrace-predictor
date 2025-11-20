"""
複数月のデータを連続して収集するバッチスクリプト

週末などにローカルで複数月分をまとめて実行する際に使用します。

使用方法:
  python batch_collect_months.py --start-month 2023-06 --end-month 2023-12

例:
  # 2023年6月～12月の7ヶ月分を収集
  python batch_collect_months.py --start-month 2023-06 --end-month 2023-12

  # 2024年全体を収集
  python batch_collect_months.py --start-month 2024-01 --end-month 2024-12
"""

import argparse
from datetime import datetime
from dateutil.relativedelta import relativedelta
import subprocess
import sys


def generate_month_list(start_month_str, end_month_str):
    """
    開始月から終了月までの月リストを生成

    Args:
        start_month_str: "YYYY-MM" 形式
        end_month_str: "YYYY-MM" 形式

    Returns:
        list: ["YYYY-MM", ...] の形式
    """
    start = datetime.strptime(start_month_str + "-01", '%Y-%m-%d')
    end = datetime.strptime(end_month_str + "-01", '%Y-%m-%d')

    if start > end:
        raise ValueError("Start month must be before or equal to end month")

    months = []
    current = start

    while current <= end:
        months.append(current.strftime('%Y-%m'))
        current += relativedelta(months=1)

    return months


def main():
    parser = argparse.ArgumentParser(
        description='Batch collect boat race data for multiple months'
    )
    parser.add_argument(
        '--start-month',
        type=str,
        required=True,
        help='Start month in YYYY-MM format (e.g., 2023-06)'
    )
    parser.add_argument(
        '--end-month',
        type=str,
        required=True,
        help='End month in YYYY-MM format (e.g., 2023-12)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=2.0,
        help='Request delay in seconds (default: 2.0)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show the list of months without executing'
    )

    args = parser.parse_args()

    # 月リストを生成
    try:
        months = generate_month_list(args.start_month, args.end_month)
    except ValueError as e:
        print(f"Error: {e}")
        return 1

    print(f"=== Batch Collection Plan ===")
    print(f"Start month: {args.start_month}")
    print(f"End month: {args.end_month}")
    print(f"Total months: {len(months)}")
    print(f"Request delay: {args.delay}s")
    print()

    print(f"Months to collect:")
    for i, month in enumerate(months, 1):
        print(f"  {i:2d}. {month}")
    print()

    if args.dry_run:
        print("Dry run mode - no data will be collected")
        return 0

    # 確認プロンプト
    response = input(f"Proceed with collection of {len(months)} months? (y/n): ")
    if response.lower() != 'y':
        print("Collection cancelled")
        return 0

    # 各月を順次実行
    successful = 0
    failed = []

    for i, month in enumerate(months, 1):
        print(f"\n{'='*60}")
        print(f"Collecting month {i}/{len(months)}: {month}")
        print(f"{'='*60}\n")

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    'collect_monthly.py',
                    '--year-month', month,
                    '--delay', str(args.delay),
                    '--venues', '24',
                    '--races', '12',
                    '--max-retries', '3'
                ],
                check=True,
                cwd='.'
            )

            successful += 1
            print(f"\n✓ Successfully collected {month}")

        except subprocess.CalledProcessError as e:
            failed.append(month)
            print(f"\n✗ Failed to collect {month} (exit code: {e.returncode})")

            # 失敗時の対応を確認
            response = input("Continue with next month? (y/n/q to quit): ")
            if response.lower() == 'q':
                print("Batch collection interrupted by user")
                break
            elif response.lower() != 'y':
                print("Skipping remaining months")
                break

        except KeyboardInterrupt:
            print("\n\nBatch collection interrupted by user")
            failed.append(month + " (interrupted)")
            break

    # 最終サマリー
    print(f"\n{'='*60}")
    print(f"=== Batch Collection Summary ===")
    print(f"{'='*60}")
    print(f"Total months planned: {len(months)}")
    print(f"Successfully collected: {successful}")
    print(f"Failed: {len(failed)}")

    if failed:
        print(f"\nFailed months:")
        for month in failed:
            print(f"  - {month}")
        print(f"\nTo retry failed months, run:")
        for month in failed:
            if '(interrupted)' not in month:
                print(f"  python collect_monthly.py --year-month {month}")

    return 0 if len(failed) == 0 else 1


if __name__ == '__main__':
    exit(main())
