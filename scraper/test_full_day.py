"""
1日分の全レースを取得するテスト（2025-11-16 桐生競艇場）
"""
import asyncio
import aiohttp
from datetime import datetime
from boatrace_scraper import BoatRaceScraper

async def test_full_day():
    """1日分の全レース（12レース）を取得"""
    print("=== Testing Full Day Scraping ===\n")

    scraper = BoatRaceScraper()
    test_date = datetime(2025, 11, 16)
    venue_id = 1  # 桐生競艇場

    try:
        async with aiohttp.ClientSession() as session:
            scraper.session = session

            results = []
            print(f"Scraping {test_date.strftime('%Y-%m-%d')} Venue {venue_id:02d} (Kiryu)...\n")

            for race_num in range(1, 13):
                print(f"Fetching Race {race_num:02d}...", end=' ')
                result = await scraper.fetch_race_result(test_date, venue_id, race_num)

                if result:
                    print(f"[OK] {len(result['entries'])} boats")
                    results.append(result)
                else:
                    print("[SKIP] No data")

                # レート制限のため少し待機
                await asyncio.sleep(1)

            print(f"\n=== Summary ===")
            print(f"Total races fetched: {len(results)}")
            print(f"Total boats: {sum(len(r['entries']) for r in results)}")

            if results:
                print(f"\n=== Saving to Database ===")
                scraper.save_to_db(results)
                print(f"[SUCCESS] Saved {len(results)} races to database!")

                # 各レースの詳細を表示
                print(f"\n=== Race Details ===")
                for result in results:
                    print(f"\nRace {result['race_number']:02d}:")
                    print(f"  Grade: {result['grade']}")
                    print(f"  Entries: {len(result['entries'])} boats")

                    # 1-3着を表示
                    for entry in sorted(result['entries'], key=lambda x: x['result_position'])[:3]:
                        racer_name = entry['racer_name'].encode('utf-8').decode('utf-8', errors='replace')
                        print(f"    {entry['result_position']}位: 艇{entry['boat_number']} "
                              f"{racer_name} ({entry['race_time']}) ST:{entry['start_timing']}")

                    if result.get('weather'):
                        w = result['weather']
                        weather_text = w.get('weather', 'N/A')
                        print(f"  Weather: {w.get('temperature')}C, {weather_text}, "
                              f"Wind {w.get('wind_speed')}m/s")

            else:
                print("[WARNING] No race data found")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        scraper.close()

if __name__ == '__main__':
    asyncio.run(test_full_day())
