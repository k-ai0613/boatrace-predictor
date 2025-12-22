"""
Supabaseデータ容量管理スクリプト

機能:
- データベース容量をチェック
- 90%（450MB）を超えた場合、4年以上前のレースデータを削除
- 削除対象: races, race_entries のみ
- 削除しない: backtest_results, predictions, racer_*, venue_*, weather_data など
"""

import os
import sys
import argparse
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
import psycopg2

load_dotenv()


def setup_logging():
    """ロギングを設定"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


def get_database_size(conn):
    """データベースの現在の容量を取得（バイト単位）"""
    cursor = conn.cursor()
    cursor.execute("SELECT pg_database_size(current_database())")
    size_bytes = cursor.fetchone()[0]
    cursor.close()
    return size_bytes


def get_table_sizes(conn):
    """各テーブルのサイズを取得"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            tablename,
            pg_total_relation_size(quote_ident(tablename)) as size
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY size DESC
    """)
    tables = cursor.fetchall()
    cursor.close()
    return tables


def bytes_to_mb(bytes_val):
    """バイトをMBに変換"""
    return bytes_val / (1024 * 1024)


def get_old_races_count(conn, cutoff_date):
    """削除対象の古いレース数を取得"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM races WHERE race_date < %s
    """, (cutoff_date,))
    count = cursor.fetchone()[0]
    cursor.close()
    return count


def get_old_race_entries_count(conn, cutoff_date):
    """削除対象の古いrace_entries数を取得"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM race_entries re
        JOIN races r ON re.race_id = r.id
        WHERE r.race_date < %s
    """, (cutoff_date,))
    count = cursor.fetchone()[0]
    cursor.close()
    return count


def delete_old_data(conn, cutoff_date, dry_run=False, logger=None):
    """
    4年以上前のレースデータを削除

    削除順序:
    1. race_entries（外部キー制約のため先に削除）
    2. races
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    cursor = conn.cursor()

    try:
        # 削除対象のrace_idを取得
        cursor.execute("""
            SELECT id FROM races WHERE race_date < %s
        """, (cutoff_date,))
        old_race_ids = [row[0] for row in cursor.fetchall()]

        if not old_race_ids:
            logger.info("削除対象のレースはありません")
            return 0, 0

        logger.info(f"削除対象レース数: {len(old_race_ids)}")

        if dry_run:
            logger.info("[DRY RUN] 実際の削除は行いません")
            # race_entriesの数を推定
            cursor.execute("""
                SELECT COUNT(*) FROM race_entries WHERE race_id = ANY(%s)
            """, (old_race_ids,))
            entries_count = cursor.fetchone()[0]
            return len(old_race_ids), entries_count

        # 1. race_entriesを削除
        cursor.execute("""
            DELETE FROM race_entries WHERE race_id = ANY(%s)
        """, (old_race_ids,))
        deleted_entries = cursor.rowcount
        logger.info(f"削除されたrace_entries: {deleted_entries}")

        # 2. racesを削除
        cursor.execute("""
            DELETE FROM races WHERE id = ANY(%s)
        """, (old_race_ids,))
        deleted_races = cursor.rowcount
        logger.info(f"削除されたraces: {deleted_races}")

        conn.commit()
        logger.info("削除完了（コミット済み）")

        return deleted_races, deleted_entries

    except Exception as e:
        conn.rollback()
        logger.error(f"削除中にエラーが発生: {e}")
        raise


def vacuum_database(conn, logger=None):
    """VACUUMを実行してストレージを解放"""
    if logger is None:
        logger = logging.getLogger(__name__)

    # VACUUMはトランザクション外で実行する必要がある
    old_isolation = conn.isolation_level
    conn.set_isolation_level(0)  # AUTOCOMMIT

    cursor = conn.cursor()
    try:
        logger.info("VACUUM ANALYZE を実行中...")
        cursor.execute("VACUUM ANALYZE races")
        cursor.execute("VACUUM ANALYZE race_entries")
        logger.info("VACUUM 完了")
    finally:
        cursor.close()
        conn.set_isolation_level(old_isolation)


def main():
    parser = argparse.ArgumentParser(description='Supabaseデータ容量管理')
    parser.add_argument('--threshold', type=float, default=90.0,
                        help='削除開始の容量閾値（%%）デフォルト: 90')
    parser.add_argument('--max-size-mb', type=float, default=500.0,
                        help='データベースの最大容量（MB）デフォルト: 500')
    parser.add_argument('--years', type=int, default=4,
                        help='この年数より古いデータを削除 デフォルト: 4')
    parser.add_argument('--dry-run', action='store_true',
                        help='実際の削除は行わず、削除対象を表示のみ')
    parser.add_argument('--force', action='store_true',
                        help='閾値に関係なく強制的に古いデータを削除')
    parser.add_argument('--status', action='store_true',
                        help='容量状況のみを表示（削除なし）')

    args = parser.parse_args()

    logger = setup_logging()

    # データベース接続
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL が設定されていません")
        sys.exit(1)

    try:
        conn = psycopg2.connect(database_url)
        logger.info("データベース接続成功")
    except Exception as e:
        logger.error(f"データベース接続失敗: {e}")
        sys.exit(1)

    try:
        # 現在の容量を取得
        current_size = get_database_size(conn)
        current_size_mb = bytes_to_mb(current_size)
        max_size_mb = args.max_size_mb
        usage_percent = (current_size_mb / max_size_mb) * 100

        logger.info("=" * 60)
        logger.info("データベース容量状況")
        logger.info("=" * 60)
        logger.info(f"現在の使用量: {current_size_mb:.2f} MB / {max_size_mb:.0f} MB")
        logger.info(f"使用率: {usage_percent:.1f}%")
        logger.info(f"閾値: {args.threshold}%")
        logger.info("")

        # テーブル別サイズを表示
        logger.info("テーブル別サイズ:")
        tables = get_table_sizes(conn)
        for table_name, size in tables[:10]:  # 上位10テーブル
            logger.info(f"  {table_name}: {bytes_to_mb(size):.2f} MB")
        logger.info("")

        # ステータス表示のみの場合は終了
        if args.status:
            conn.close()
            return

        # 削除基準日を計算
        cutoff_date = datetime.now() - timedelta(days=args.years * 365)
        logger.info(f"削除基準日: {cutoff_date.strftime('%Y-%m-%d')}（{args.years}年以上前）")

        # 削除対象数を確認
        old_races = get_old_races_count(conn, cutoff_date)
        old_entries = get_old_race_entries_count(conn, cutoff_date)
        logger.info(f"削除対象レース数: {old_races}")
        logger.info(f"削除対象race_entries数: {old_entries}")
        logger.info("")

        # 閾値チェック
        threshold_mb = max_size_mb * (args.threshold / 100)

        if not args.force and current_size_mb < threshold_mb:
            logger.info(f"容量は閾値（{threshold_mb:.0f} MB）未満のため、削除は不要です")
            conn.close()
            return

        if args.force:
            logger.info("--force オプションにより強制削除を実行します")
        else:
            logger.info(f"容量が閾値（{threshold_mb:.0f} MB）を超えているため、古いデータを削除します")

        # 削除実行
        if old_races == 0:
            logger.info("削除対象のデータがありません")
        else:
            deleted_races, deleted_entries = delete_old_data(
                conn, cutoff_date, dry_run=args.dry_run, logger=logger
            )

            if not args.dry_run and (deleted_races > 0 or deleted_entries > 0):
                # VACUUM実行（実削除後のみ）
                vacuum_database(conn, logger)

                # 削除後の容量を確認
                new_size = get_database_size(conn)
                new_size_mb = bytes_to_mb(new_size)
                saved_mb = current_size_mb - new_size_mb

                logger.info("")
                logger.info("=" * 60)
                logger.info("削除結果サマリー")
                logger.info("=" * 60)
                logger.info(f"削除前: {current_size_mb:.2f} MB")
                logger.info(f"削除後: {new_size_mb:.2f} MB")
                logger.info(f"解放容量: {saved_mb:.2f} MB")
                logger.info(f"削除レース数: {deleted_races}")
                logger.info(f"削除race_entries数: {deleted_entries}")

    finally:
        conn.close()
        logger.info("データベース接続を閉じました")


if __name__ == '__main__':
    main()
