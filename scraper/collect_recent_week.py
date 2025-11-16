"""
直近1週間のレースデータを収集
"""
import asyncio
import aiohttp
from datetime import datetime, timedelta
from boatrace_scraper import BoatRaceScraper

async def collect_recent_week(days=7):
    """直近N日間のデータを収集"""
    print(f"=== Collecting Recent {days} Days Data ===\n")

    scraper = BoatRaceScraper()
    end_date = datetime(2025, 11, 16)  # 最新の確認済み日付
    start_date = end_date - timedelta(days=days - 1)

    print(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"Venues: 01 (Kiryu) only for testing\n")

    all_results = []
    venue_id = 1  # 桐生のみでテスト

    try:
        async with aiohttp.ClientSession() as session:
            scraper.session = session

            current_date = start_date
            while current_date <= end_date:
                print(f"\n=== {current_date.strftime('%Y-%m-%d')} ===")
                day_results = []

                for race_num in range(1, 13):
                    result = await scraper.fetch_race_result(current_date, venue_id, race_num)

                    if result:
                        day_results.append(result)

                    # レート制限のため待機
                    await asyncio.sleep(2)

                if day_results:
                    print(f"[OK] {len(day_results)} races found")
                    all_results.extend(day_results)

                    # データベースに保存（日ごと）
                    scraper.save_to_db(day_results)
                else:
                    print("[INFO] No races on this date")

                current_date += timedelta(days=1)

                # 1日ごとに少し待機
                await asyncio.sleep(3)

            print(f"\n=== Collection Summary ===")
            print(f"Total races collected: {len(all_results)}")
            print(f"Total boats: {sum(len(r['entries']) for r in all_results)}")
            print(f"\n[SUCCESS] Data collection complete!")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        scraper.close()

if __name__ == '__main__':
    # 直近3日間でテスト（1週間は時間がかかるため）
    asyncio.run(collect_recent_week(days=3))
