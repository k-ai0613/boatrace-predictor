"""
スクレイピングテスト - 競艇公式サイトへの接続確認
"""
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

BASE_URL = "https://www.boatrace.jp"

async def test_scraping():
    """スクレイピングテスト"""
    print("=== Scraping Test ===\n")

    # 最近の日付を試す（今日から過去7日分）
    async with aiohttp.ClientSession() as session:
        for days_ago in range(7):
            test_date = datetime.now() - timedelta(days=days_ago)
            date_str = test_date.strftime('%Y%m%d')

            print(f"Testing date: {test_date.strftime('%Y-%m-%d')} ({date_str})")

            # 桐生競艇場（venue_id=01）、1レース目で試す
            url = f"{BASE_URL}/owpc/pc/race/raceresult?hd={date_str}&jcd=01&rno=1"
            print(f"URL: {url}")

            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    print(f"Status: {response.status}")

                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')

                        # レース結果テーブルを探す
                        result_table = soup.select_one('table.is-w495')

                        if result_table:
                            print("[OK] Race result table found!")

                            # 行数を確認
                            rows = result_table.select('tbody tr')
                            print(f"[OK] Found {len(rows)} rows (boats)")

                            if len(rows) > 0:
                                # 最初の行のデータを表示
                                first_row = rows[0]
                                cols = first_row.select('td')
                                print(f"[OK] First row has {len(cols)} columns")

                                if len(cols) >= 4:
                                    print(f"\nSample data:")
                                    print(f"  Position: {cols[0].text.strip()}")
                                    print(f"  Boat #: {cols[1].text.strip()}")
                                    print(f"  Racer #: {cols[2].text.strip()}")
                                    print(f"  Name: {cols[3].text.strip()}")

                                print(f"\n[SUCCESS] Found race data for {test_date.strftime('%Y-%m-%d')}!")
                                return True
                        else:
                            print("[WARN] Result table not found - maybe no race on this date")

                    elif response.status == 404:
                        print("[WARN] Page not found - no race on this date")
                    else:
                        print(f"[WARN] Unexpected status code: {response.status}")

            except asyncio.TimeoutError:
                print("[ERROR] Request timeout")
            except Exception as e:
                print(f"[ERROR] {e}")

            print("-" * 60)
            await asyncio.sleep(2)  # レート制限のため待機

        print("\n[INFO] No race data found in the last 7 days")
        print("[INFO] Note: Boat races may not be held every day")
        return False

if __name__ == '__main__':
    asyncio.run(test_scraping())
