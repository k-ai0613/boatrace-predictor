"""
過去データ収集スクリプト
20年分のデータを段階的に収集

Phase 1: 直近1年（2024年） - 5日
Phase 2: 2-3年前（2022-2023） - 10日
Phase 3: 4-5年前（2020-2021） - 10日
Phase 4: 6-10年前（2015-2019） - 25日
Phase 5: 11-20年前（2005-2014） - 50日
"""
import asyncio
import argparse
from datetime import datetime, timedelta
from boatrace_scraper import BoatRaceScraper


# フェーズ定義
PHASES = {
    1: {
        'name': '直近1年',
        'start_year': 2024,
        'end_year': 2024,
        'priority': '最高'
    },
    2: {
        'name': '2-3年前',
        'start_year': 2022,
        'end_year': 2023,
        'priority': '高'
    },
    3: {
        'name': '4-5年前',
        'start_year': 2020,
        'end_year': 2021,
        'priority': '中'
    },
    4: {
        'name': '6-10年前',
        'start_year': 2015,
        'end_year': 2019,
        'priority': '中'
    },
    5: {
        'name': '11-20年前',
        'start_year': 2005,
        'end_year': 2014,
        'priority': '低'
    }
}


async def scrape_phase(phase_num, max_days=1):
    """指定フェーズのデータを収集"""
    if phase_num not in PHASES:
        print(f"ERROR: Invalid phase {phase_num}")
        return

    phase_info = PHASES[phase_num]
    print(f"\n=== Phase {phase_num}: {phase_info['name']} ===")
    print(f"Years: {phase_info['start_year']}-{phase_info['end_year']}")
    print(f"Priority: {phase_info['priority']}")
    print(f"Max days to scrape: {max_days}")

    scraper = BoatRaceScraper()

    try:
        # 収集済みの最新日付を取得（実装は省略）
        # ここでは単純に開始年の1月1日からmax_days分を取得
        start_date = datetime(phase_info['start_year'], 1, 1)
        end_date = start_date + timedelta(days=max_days - 1)

        # 終了年を超えないようにチェック
        phase_end = datetime(phase_info['end_year'], 12, 31)
        if end_date > phase_end:
            end_date = phase_end

        print(f"Scraping: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

        await scraper.run(start_date, end_date)

        print(f"\n=== Phase {phase_num} Completed ===")

    except Exception as e:
        print(f"ERROR in phase {phase_num}: {e}")
        raise
    finally:
        scraper.close()


async def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='過去データ収集')
    parser.add_argument('--phase', type=int, default=1,
                       help='収集フェーズ (1-5)')
    parser.add_argument('--max-days', type=int, default=1,
                       help='最大収集日数')

    args = parser.parse_args()

    await scrape_phase(args.phase, args.max_days)


if __name__ == '__main__':
    asyncio.run(main())
