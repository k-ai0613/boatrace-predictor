"""
全24会場の直近1週間データを収集

特徴:
- 事前にデータベースをチェックして既存データをスキップ
- サーバー負荷を考慮した慎重なレート制限（5秒/リクエスト）
- 詳細な進捗表示
- 夜間実行推奨（約3-4時間）
"""
import asyncio
import aiohttp
from datetime import datetime, timedelta
import os
import sys
from dotenv import load_dotenv
import psycopg2

# スクレイパーディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from boatrace_scraper import BoatRaceScraper

load_dotenv()


def get_existing_races(start_date, end_date):
    """データベースから既存レースのリストを取得"""
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()

    cursor.execute("""
        SELECT race_date, venue_id, race_number
        FROM races
        WHERE race_date BETWEEN %s AND %s
        ORDER BY race_date, venue_id, race_number
    """, (start_date, end_date))

    existing = set()
    for row in cursor.fetchall():
        race_date, venue_id, race_number = row
        existing.add((race_date, venue_id, race_number))

    cursor.close()
    conn.close()

    return existing


async def collect_all_venues(days=7):
    """全24会場のデータを収集"""
    print("=" * 80)
    print(f"全24会場 × 直近{days}日間のデータ収集を開始")
    print("=" * 80)
    print()

    # 日付範囲を設定
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days - 1)

    print(f"期間: {start_date.strftime('%Y-%m-%d')} ～ {end_date.strftime('%Y-%m-%d')}")
    print(f"会場: 01-24（全24会場）")
    print(f"レート制限: 5秒/リクエスト（サーバー負荷を考慮）")
    print()

    # 既存データをチェック
    print("データベースから既存レースを確認中...")
    existing_races = get_existing_races(start_date.date(), end_date.date())
    print(f"既存レース数: {len(existing_races)}")
    print()

    # 収集対象レースをリストアップ
    all_targets = []
    for current_date in [start_date + timedelta(days=i) for i in range(days)]:
        for venue_id in range(1, 25):  # 全24会場
            for race_number in range(1, 13):  # 12レース
                key = (current_date.date(), venue_id, race_number)
                if key not in existing_races:
                    all_targets.append((current_date, venue_id, race_number))

    total_targets = len(all_targets)
    total_expected = days * 24 * 12
    skipped = total_expected - total_targets

    print(f"収集対象レース数: {total_targets} / {total_expected}")
    print(f"スキップ（既存）: {skipped}")
    print()

    if total_targets == 0:
        print("[完了] 全てのデータが既に収集済みです")
        return

    # 推定時間を計算
    estimated_minutes = (total_targets * 5) / 60
    print(f"推定実行時間: 約{estimated_minutes:.1f}分（{estimated_minutes/60:.1f}時間）")
    print()
    print("収集を開始します...")
    print()

    # スクレイパーを初期化（レート制限を5秒に設定）
    scraper = BoatRaceScraper()
    # レート制限を変更
    from rate_limiter import RateLimiter
    scraper.rate_limiter = RateLimiter(
        requests_per_second=0.2,  # 5秒に1リクエスト
        concurrent_requests=1      # 並行リクエスト数1
    )

    try:
        async with aiohttp.ClientSession() as session:
            scraper.session = session

            collected = 0
            errors = 0

            for idx, (target_date, venue_id, race_number) in enumerate(all_targets, 1):
                date_str = target_date.strftime('%Y-%m-%d')

                print(f"[{idx}/{total_targets}] {date_str} 会場{venue_id:02d} R{race_number:02d}...", end=' ')

                try:
                    result = await scraper.fetch_race_result(target_date, venue_id, race_number)

                    if result:
                        # データベースに保存
                        scraper.save_to_db([result])
                        collected += 1
                        print("✓ 収集成功")
                    else:
                        print("✗ データなし")

                except Exception as e:
                    errors += 1
                    print(f"✗ エラー: {e}")

                # 進捗サマリーを定期的に表示
                if idx % 50 == 0:
                    print()
                    print(f"--- 進捗: {idx}/{total_targets} ({idx*100/total_targets:.1f}%) ---")
                    print(f"    収集成功: {collected}, エラー: {errors}")
                    print()

        print()
        print("=" * 80)
        print("収集完了サマリー")
        print("=" * 80)
        print(f"対象レース: {total_targets}")
        print(f"収集成功: {collected}")
        print(f"エラー: {errors}")
        print(f"スキップ（既存）: {skipped}")
        print(f"合計処理: {total_expected}")
        print()
        print("[SUCCESS] データ収集が完了しました！")

    except Exception as e:
        print()
        print(f"[ERROR] 予期しないエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scraper.close()


if __name__ == '__main__':
    print()
    print("=" * 80)
    print("競艇データ収集スクリプト - 全24会場")
    print("=" * 80)
    print()
    print("注意:")
    print("- このスクリプトは約3-4時間かかります")
    print("- サーバー負荷を考慮し、5秒/リクエストで実行します")
    print("- 夜間実行を推奨します")
    print("- Ctrl+Cで停止可能（次回実行時に未収集分から再開）")
    print()

    input("Enterキーを押して開始...")
    print()

    asyncio.run(collect_all_venues(days=7))
