#!/usr/bin/env python3
"""
既存データのバックフィルスクリプト（負荷軽減版）

使い方:
  python backfill_gentle.py --start 2024-10-19 --end 2024-11-23
  python backfill_gentle.py --days 36  # 過去36日分
"""
import asyncio
import argparse
from datetime import datetime, timedelta
import os
import sys
import random

# スクレイパーディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from boatrace_scraper import BoatRaceScraper


class GentleBackfillScraper(BoatRaceScraper):
    """
    負荷を抑えたバックフィル用スクレイパー
    """

    def __init__(self):
        super().__init__()
        # レート制限をより緩やかに設定（7秒間隔、同時リクエスト2）
        from rate_limiter import RateLimiter
        self.rate_limiter = RateLimiter(
            requests_per_second=1/7,  # 7秒に1リクエスト
            concurrent_requests=2      # 同時2リクエストまで
        )

    def _batch(self, iterable, batch_size):
        """イテラブルをバッチに分割"""
        items = list(iterable)
        for i in range(0, len(items), batch_size):
            yield items[i:i + batch_size]

    async def fetch_with_retry(self, url, max_retries=3):
        """
        リトライ機能付きフェッチ（ランダム遅延追加）
        """
        # 0.5〜2秒のランダム遅延を追加
        await asyncio.sleep(random.uniform(0.5, 2.0))
        return await super().fetch_with_retry(url, max_retries)

    async def scrape_single_day(self, date):
        """
        1日分のデータを取得（進捗表示強化版）
        """
        print(f"\n{'='*60}")
        print(f"日付: {date.strftime('%Y-%m-%d')} の再取得開始")
        print(f"{'='*60}")

        results = []
        total_races = 0
        skipped_races = 0

        for venue_id in range(1, 25):
            venue_results = []

            # 12レースを2つずつバッチ処理（同時リクエスト数2に対応）
            for race_batch in self._batch(range(1, 13), 2):
                tasks = [
                    self.fetch_race_result(date, venue_id, race_num)
                    for race_num in race_batch
                ]
                batch_results = await asyncio.gather(*tasks)

                for r in batch_results:
                    if r:
                        venue_results.append(r)
                        total_races += 1
                    else:
                        skipped_races += 1

            if venue_results:
                results.extend(venue_results)
                print(f"  会場 {venue_id:02d}: {len(venue_results)} レース取得")

            # 会場間で少し待機
            await asyncio.sleep(1)

        # データベースに保存
        if results:
            self.save_to_db(results)
            print(f"\n✓ 完了: {total_races} レース保存 (スキップ: {skipped_races})")
        else:
            print(f"\n- データなし (スキップ: {skipped_races})")

        return results

    async def backfill_range(self, start_date, end_date):
        """
        期間指定でバックフィル実行
        """
        async with self._create_session() as session:
            self.session = session

            current_date = start_date
            total_days = (end_date - start_date).days + 1
            day_count = 0

            print("\n" + "="*60)
            print(f"バックフィル開始")
            print(f"期間: {start_date.strftime('%Y-%m-%d')} 〜 {end_date.strftime('%Y-%m-%d')}")
            print(f"日数: {total_days}日")
            print("="*60)

            while current_date <= end_date:
                day_count += 1
                print(f"\n進捗: [{day_count}/{total_days}]")

                await self.scrape_single_day(current_date)

                current_date += timedelta(days=1)

                # 日付間で少し待機
                if current_date <= end_date:
                    await asyncio.sleep(3)

            print("\n" + "="*60)
            print(f"✓ バックフィル完了: {total_days}日分のデータを再取得しました")
            print("="*60)

    def _create_session(self):
        """セッション作成"""
        import aiohttp
        return aiohttp.ClientSession()


async def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='既存データのバックフィル')
    parser.add_argument('--start', type=str, help='開始日 (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, help='終了日 (YYYY-MM-DD)')
    parser.add_argument('--days', type=int, help='過去N日分（終了日=今日）')

    args = parser.parse_args()

    # 日付範囲の決定
    if args.days:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=args.days - 1)
    elif args.start and args.end:
        start_date = datetime.strptime(args.start, '%Y-%m-%d')
        end_date = datetime.strptime(args.end, '%Y-%m-%d')
    else:
        print("エラー: --start と --end、または --days を指定してください")
        print("\n使用例:")
        print("  python backfill_gentle.py --start 2024-10-19 --end 2024-11-23")
        print("  python backfill_gentle.py --days 36")
        return

    scraper = GentleBackfillScraper()

    try:
        await scraper.backfill_range(start_date, end_date)
    finally:
        scraper.close()


if __name__ == '__main__':
    asyncio.run(main())
