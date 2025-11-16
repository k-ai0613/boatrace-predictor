"""
修正したスクレイパーのテスト
"""
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
from boatrace_scraper import BoatRaceScraper

async def test_fixed_scraper():
    """修正したスクレイパーのテスト"""
    print("=== Testing Fixed Scraper ===\n")

    scraper = BoatRaceScraper()

    try:
        # 2025-11-16のデータでテスト
        test_date = datetime(2025, 11, 16)

        async with aiohttp.ClientSession() as session:
            scraper.session = session

            # 桐生競艇場の1レース目を取得
            print(f"Fetching race data for {test_date.strftime('%Y-%m-%d')} Venue 01, Race 1...")
            result = await scraper.fetch_race_result(test_date, 1, 1)

            if result:
                print("[SUCCESS] Race data retrieved!\n")

                print(f"Date: {result['date']}")
                print(f"Venue ID: {result['venue_id']}")
                print(f"Race Number: {result['race_number']}")
                print(f"Grade: {result['grade']}")
                print(f"\n=== Race Entries ({len(result['entries'])} boats) ===")

                for entry in result['entries']:
                    print(f"\nPosition {entry['result_position']}:")
                    print(f"  Boat Number: {entry['boat_number']}")
                    print(f"  Racer Number: {entry['racer_number']}")
                    print(f"  Racer Name: {entry['racer_name']}")
                    print(f"  Race Time: {entry['race_time']}")
                    print(f"  Start Timing: {entry['start_timing']}")

                if result.get('weather'):
                    print(f"\n=== Weather Data ===")
                    weather = result['weather']
                    print(f"  Temperature: {weather.get('temperature')}C")
                    print(f"  Weather: {weather.get('weather')}")
                    print(f"  Wind Speed: {weather.get('wind_speed')}m")
                    print(f"  Water Temperature: {weather.get('water_temperature')}C")
                    print(f"  Wave Height: {weather.get('wave_height')}cm")

                # データベースに保存してみる
                print(f"\n=== Saving to Database ===")
                scraper.save_to_db([result])
                print("[SUCCESS] Data saved to database!")

            else:
                print("[ERROR] Failed to retrieve race data")

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        scraper.close()

if __name__ == '__main__':
    asyncio.run(test_fixed_scraper())
