"""
負荷に優しいデータ収集スクリプト（改善版）

特徴:
- コマンドライン引数で柔軟な設定
- プログレスバー表示
- 詳細なログ記録
- 段階的収集モード
- より細かいレート制限調整
"""
import asyncio
import aiohttp
import argparse
import logging
from datetime import datetime, timedelta
from boatrace_scraper import BoatRaceScraper
from rate_limiter import RateLimiter
import os
from dotenv import load_dotenv
import psycopg2

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    print("Note: Install 'tqdm' for better progress visualization (pip install tqdm)")

load_dotenv()


def setup_logging(log_file='scraper.log'):
    """ロギングを設定"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


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


async def collect_data(
    days=7,
    venues=None,
    rate_limit=5.0,
    batch_size=10,
    max_races=None,
    start_venue=1,
    logger=None
):
    """
    データを収集

    Args:
        days: 収集する日数（直近から遡る）
        venues: 収集する会場のリスト（Noneの場合は全24会場）
        rate_limit: リクエスト間隔（秒）
        batch_size: 一度に処理する件数
        max_races: 最大収集レース数（Noneの場合は制限なし）
        start_venue: 開始会場ID
        logger: ロガー
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    logger.info("=" * 80)
    logger.info("データ収集開始")
    logger.info("=" * 80)

    # 日付範囲を設定
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days - 1)

    # 会場リストを設定
    if venues is None:
        venues = list(range(start_venue, 25))
    else:
        venues = [v for v in venues if v >= start_venue]

    logger.info(f"期間: {start_date.strftime('%Y-%m-%d')} ～ {end_date.strftime('%Y-%m-%d')}")
    logger.info(f"会場: {venues}")
    logger.info(f"レート制限: {rate_limit}秒/リクエスト")
    logger.info(f"バッチサイズ: {batch_size}件")
    if max_races:
        logger.info(f"最大収集数: {max_races}レース")
    logger.info("")

    # 既存データをチェック
    logger.info("既存データを確認中...")
    existing_races = get_existing_races(start_date.date(), end_date.date())
    logger.info(f"既存レース数: {len(existing_races)}")
    logger.info("")

    # 収集対象レースをリストアップ
    all_targets = []
    for current_date in [start_date + timedelta(days=i) for i in range(days)]:
        for venue_id in venues:
            for race_number in range(1, 13):
                key = (current_date.date(), venue_id, race_number)
                if key not in existing_races:
                    all_targets.append((current_date, venue_id, race_number))

                    # 最大収集数に達したら終了
                    if max_races and len(all_targets) >= max_races:
                        break
            if max_races and len(all_targets) >= max_races:
                break
        if max_races and len(all_targets) >= max_races:
            break

    total_targets = len(all_targets)
    total_expected = days * len(venues) * 12
    skipped = len(existing_races)

    logger.info(f"収集対象: {total_targets}レース")
    logger.info(f"スキップ: {skipped}レース（既存）")
    logger.info("")

    if total_targets == 0:
        logger.info("全てのデータが既に収集済みです")
        return

    # 推定時間を計算
    estimated_seconds = total_targets * rate_limit
    estimated_minutes = estimated_seconds / 60
    estimated_hours = estimated_minutes / 60

    logger.info(f"推定実行時間:")
    if estimated_hours >= 1:
        logger.info(f"  約{estimated_hours:.1f}時間（{estimated_minutes:.0f}分）")
    else:
        logger.info(f"  約{estimated_minutes:.1f}分")
    logger.info("")

    # ユーザー確認（自動実行のため一時的にコメントアウト）
    # print("収集を開始しますか？")
    # print("  y: 開始")
    # print("  n: キャンセル")
    # response = input("> ")
    # if response.lower() != 'y':
    #     logger.info("キャンセルされました")
    #     return

    logger.info("収集を開始します...")
    logger.info("")

    # スクレイパーを初期化
    scraper = BoatRaceScraper()
    scraper.rate_limiter = RateLimiter(
        requests_per_second=1.0 / rate_limit,
        concurrent_requests=1
    )

    try:
        async with aiohttp.ClientSession() as session:
            scraper.session = session

            collected = 0
            errors = 0
            error_details = []

            # プログレスバーを作成
            if HAS_TQDM:
                pbar = tqdm(total=total_targets, desc="収集進捗", unit="レース")
            else:
                pbar = None

            for idx, (target_date, venue_id, race_number) in enumerate(all_targets, 1):
                date_str = target_date.strftime('%Y-%m-%d')

                try:
                    result = await scraper.fetch_race_result(target_date, venue_id, race_number)

                    if result:
                        scraper.save_to_db([result])
                        collected += 1
                        logger.debug(f"✓ {date_str} 会場{venue_id:02d} R{race_number:02d}")

                        if pbar:
                            pbar.set_postfix({
                                '成功': collected,
                                'エラー': errors
                            })
                    else:
                        logger.debug(f"✗ {date_str} 会場{venue_id:02d} R{race_number:02d} - データなし")

                except Exception as e:
                    errors += 1
                    error_msg = f"{date_str} 会場{venue_id:02d} R{race_number:02d}: {str(e)}"
                    error_details.append(error_msg)
                    logger.error(f"✗ {error_msg}")

                if pbar:
                    pbar.update(1)

                # 定期的なサマリー表示（プログレスバーがない場合）
                if not pbar and idx % batch_size == 0:
                    progress_pct = (idx / total_targets) * 100
                    logger.info(f"進捗: {idx}/{total_targets} ({progress_pct:.1f}%) - 成功: {collected}, エラー: {errors}")

            if pbar:
                pbar.close()

        logger.info("")
        logger.info("=" * 80)
        logger.info("収集完了")
        logger.info("=" * 80)
        logger.info(f"対象レース: {total_targets}")
        logger.info(f"収集成功: {collected}")
        logger.info(f"エラー: {errors}")
        logger.info(f"スキップ: {skipped}")
        logger.info(f"成功率: {(collected/total_targets*100):.1f}%")
        logger.info("")

        if error_details:
            logger.info("エラー詳細:")
            for error in error_details[:10]:  # 最初の10件のみ表示
                logger.info(f"  - {error}")
            if len(error_details) > 10:
                logger.info(f"  ... 他{len(error_details)-10}件")
            logger.info("")

        logger.info("データ収集が完了しました！")

    except KeyboardInterrupt:
        logger.info("")
        logger.info("中断されました")
        logger.info(f"収集済み: {collected}レース")
        logger.info("次回実行時に未収集分から再開されます")
    except Exception as e:
        logger.error(f"予期しないエラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scraper.close()


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(
        description='競艇データ収集スクリプト（負荷に優しい）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 直近1週間、全会場、デフォルト設定
  python scraper/collect_gentle.py

  # 直近3日間、レート制限10秒
  python scraper/collect_gentle.py --days 3 --rate 10

  # 会場1-5のみ、最大100レース
  python scraper/collect_gentle.py --venues 1-5 --max-races 100

  # 会場10から開始、レート制限3秒
  python scraper/collect_gentle.py --start-venue 10 --rate 3

推奨設定:
  - 通常: デフォルト（5秒/リクエスト）
  - 慎重: --rate 10（10秒/リクエスト）
  - 高速: --rate 2（2秒/リクエスト）※負荷注意
        """
    )

    parser.add_argument(
        '--days', type=int, default=7,
        help='収集する日数（直近から遡る、デフォルト: 7）'
    )
    parser.add_argument(
        '--venues', type=str, default=None,
        help='収集する会場（例: 1-5, 1,3,5,10、デフォルト: 全会場）'
    )
    parser.add_argument(
        '--rate', type=float, default=5.0,
        help='リクエスト間隔（秒、デフォルト: 5.0）'
    )
    parser.add_argument(
        '--batch-size', type=int, default=10,
        help='進捗表示のバッチサイズ（デフォルト: 10）'
    )
    parser.add_argument(
        '--max-races', type=int, default=None,
        help='最大収集レース数（デフォルト: 制限なし）'
    )
    parser.add_argument(
        '--start-venue', type=int, default=1,
        help='開始会場ID（デフォルト: 1）'
    )
    parser.add_argument(
        '--log-file', type=str, default='scraper_gentle.log',
        help='ログファイル名（デフォルト: scraper_gentle.log）'
    )
    parser.add_argument(
        '--verbose', action='store_true',
        help='詳細なログを表示'
    )

    args = parser.parse_args()

    # ロギング設定
    logger = setup_logging(args.log_file)
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # 会場リストの解析
    venues = None
    if args.venues:
        try:
            if '-' in args.venues:
                # 範囲指定（例: 1-5）
                start, end = map(int, args.venues.split('-'))
                venues = list(range(start, end + 1))
            else:
                # 個別指定（例: 1,3,5）
                venues = [int(v.strip()) for v in args.venues.split(',')]
        except ValueError:
            logger.error("会場指定が不正です。例: 1-5 または 1,3,5")
            return

    # データ収集を実行
    asyncio.run(collect_data(
        days=args.days,
        venues=venues,
        rate_limit=args.rate,
        batch_size=args.batch_size,
        max_races=args.max_races,
        start_venue=args.start_venue,
        logger=logger
    ))


if __name__ == '__main__':
    print()
    print("=" * 80)
    print("競艇データ収集スクリプト - 負荷に優しいバージョン")
    print("=" * 80)
    print()

    main()
