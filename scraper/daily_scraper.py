"""
日次データ収集スクリプト
GitHub Actionsから1日3回実行される
"""
import asyncio
from datetime import datetime, timedelta
from boatrace_scraper import BoatRaceScraper


async def main():
    """当日と前日のデータを収集"""
    scraper = BoatRaceScraper()

    try:
        # 前日と当日のデータを取得
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)

        print(f"=== Daily Scraping Started ===")
        print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

        await scraper.run(start_date, end_date)

        print(f"=== Daily Scraping Completed ===")

    except Exception as e:
        print(f"ERROR: {e}")
        raise
    finally:
        scraper.close()


if __name__ == '__main__':
    asyncio.run(main())
