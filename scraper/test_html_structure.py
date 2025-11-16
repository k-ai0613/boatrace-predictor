"""
HTMLの構造を詳しく調査
"""
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

BASE_URL = "https://www.boatrace.jp"

async def investigate_html():
    """HTMLの詳細構造を調査"""
    print("=== HTML Structure Investigation ===\n")

    # 2025-11-16のデータを取得
    date_str = "20251116"
    url = f"{BASE_URL}/owpc/pc/race/raceresult?hd={date_str}&jcd=01&rno=1"

    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            if response.status == 200:
                html = await response.text()

                # HTMLをファイルに保存
                with open('race_result_sample.html', 'w', encoding='utf-8') as f:
                    f.write(html)
                print("[OK] HTML saved to 'race_result_sample.html'\n")

                soup = BeautifulSoup(html, 'html.parser')

                # すべてのテーブルを探す
                tables = soup.find_all('table')
                print(f"[INFO] Found {len(tables)} tables in total\n")

                for i, table in enumerate(tables):
                    print(f"--- Table {i+1} ---")
                    class_attr = table.get('class', [])
                    print(f"Classes: {class_attr}")

                    rows = table.find_all('tr')
                    print(f"Rows: {len(rows)}")

                    if len(rows) > 0:
                        first_row = rows[0]
                        cells = first_row.find_all(['td', 'th'])
                        print(f"First row cells: {len(cells)}")

                        if len(cells) > 0:
                            print("First row content:")
                            for j, cell in enumerate(cells[:5]):  # 最初の5セルのみ表示
                                print(f"  Cell {j+1}: {cell.text.strip()[:30]}")
                    print()

                # 特定のクラスを持つテーブルを探す
                print("\n--- Looking for result table ---")
                result_tables = soup.select('table.is-w495')
                print(f"Tables with class 'is-w495': {len(result_tables)}")

                if result_tables:
                    table = result_tables[0]
                    tbody = table.find('tbody')
                    if tbody:
                        rows = tbody.find_all('tr')
                        print(f"tbody rows: {len(rows)}")

                        if len(rows) > 0:
                            print("\nFirst boat data:")
                            first_row = rows[0]
                            all_cells = first_row.find_all(['td', 'th'])
                            print(f"Total cells in first row: {len(all_cells)}")

                            for i, cell in enumerate(all_cells):
                                text = cell.text.strip()
                                print(f"  Cell {i+1}: '{text[:50]}'")

if __name__ == '__main__':
    asyncio.run(investigate_html())
