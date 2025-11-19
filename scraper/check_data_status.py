"""
データ収集状況確認スクリプト

現在のデータベースの状態を確認し、次のステップを提案
- レース数、選手数、期間
- データの充足度
- 推奨される次のアクション
"""
import os
from dotenv import load_dotenv
import psycopg2
from datetime import datetime, timedelta

load_dotenv()


def check_database_status():
    """データベースの状態を確認"""
    print("=" * 80)
    print("  データ収集状況レポート")
    print("=" * 80)
    print()

    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()

    # 1. レース基本情報
    print("【1. レースデータ】")
    print("-" * 80)

    cursor.execute("SELECT COUNT(*) FROM races")
    total_races = cursor.fetchone()[0]
    print(f"総レース数: {total_races:,} レース")

    if total_races > 0:
        cursor.execute("SELECT MIN(race_date), MAX(race_date) FROM races")
        min_date, max_date = cursor.fetchone()
        print(f"期間: {min_date} ～ {max_date}")

        # 期間の日数
        date_range = (max_date - min_date).days + 1
        print(f"データ期間: {date_range} 日間")

        # 年数換算
        years = date_range / 365.25
        print(f"年数換算: 約 {years:.1f} 年分")

        # 1日あたりのレース数
        races_per_day = total_races / date_range
        print(f"1日平均: {races_per_day:.1f} レース")

    print()

    # 2. 出走データ
    print("【2. 出走データ】")
    print("-" * 80)

    cursor.execute("SELECT COUNT(*) FROM race_entries WHERE result_position IS NOT NULL")
    total_entries = cursor.fetchone()[0]
    print(f"総出走数: {total_entries:,} 件")

    if total_races > 0:
        entries_per_race = total_entries / total_races
        print(f"1レース平均: {entries_per_race:.1f} 艇")

    print()

    # 3. 選手データ
    print("【3. 選手データ】")
    print("-" * 80)

    cursor.execute("SELECT COUNT(DISTINCT racer_id) FROM race_entries")
    total_racers = cursor.fetchone()[0]
    print(f"登録選手数: {total_racers:,} 名")

    # グレード別集計
    cursor.execute("""
        SELECT grade, COUNT(DISTINCT racer_number)
        FROM racers
        WHERE grade IS NOT NULL
        GROUP BY grade
        ORDER BY grade
    """)
    grade_stats = cursor.fetchall()
    if grade_stats:
        print("\nグレード別:")
        for grade, count in grade_stats:
            print(f"  {grade}: {count:,} 名")

    print()

    # 4. 会場別統計
    print("【4. 会場別統計テーブル】")
    print("-" * 80)

    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'racer_venue_stats'
        )
    """)
    table_exists = cursor.fetchone()[0]

    if table_exists:
        cursor.execute("SELECT COUNT(*) FROM racer_venue_stats")
        stats_count = cursor.fetchone()[0]
        print(f"[OK] テーブル作成済み: {stats_count:,} 件の統計")

        cursor.execute("SELECT COUNT(DISTINCT racer_id) FROM racer_venue_stats")
        racers_with_stats = cursor.fetchone()[0]
        print(f"   統計がある選手: {racers_with_stats:,} 名")
    else:
        print("[NG] テーブル未作成")
        print("   → python ml/advanced_stats.py で作成可能")

    print()

    # 5. 天気データ
    print("【5. 天気データ】")
    print("-" * 80)

    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'weather_data'
        )
    """)
    weather_table_exists = cursor.fetchone()[0]

    if weather_table_exists:
        cursor.execute("SELECT COUNT(*) FROM weather_data")
        weather_count = cursor.fetchone()[0]
        print(f"[OK] テーブル作成済み: {weather_count:,} 件")

        if weather_count > 0:
            cursor.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE wind_speed IS NOT NULL) as wind_count,
                    COUNT(*) FILTER (WHERE temperature IS NOT NULL) as temp_count,
                    COUNT(*) FILTER (WHERE wave_height IS NOT NULL) as wave_count
                FROM weather_data
            """)
            wind_count, temp_count, wave_count = cursor.fetchone()
            print(f"   風速データ: {wind_count:,} 件")
            print(f"   気温データ: {temp_count:,} 件")
            print(f"   波高データ: {wave_count:,} 件")
    else:
        print("[NG] テーブル未作成")
        print("   → python scraper/weather_scraper.py で収集可能")

    print()

    cursor.close()
    conn.close()

    return {
        'total_races': total_races,
        'total_entries': total_entries,
        'total_racers': total_racers,
        'has_venue_stats': table_exists,
        'has_weather_data': weather_table_exists,
        'date_range_days': date_range if total_races > 0 else 0
    }


def suggest_next_steps(status):
    """次のステップを提案"""
    print("=" * 80)
    print("  推奨される次のステップ")
    print("=" * 80)
    print()

    total_races = status['total_races']

    if total_races == 0:
        print("[NG] データが収集されていません")
        print()
        print("【最優先】データ収集を開始してください:")
        print()
        print("  1. 直近1週間分のデータを収集:")
        print("     python scraper/collect_all_venues.py")
        print()
        print("  2. GitHub Actionsで過去データを収集:")
        print("     - GitHubの Actions タブを開く")
        print("     - 'Scrape Historical Data' を手動実行")
        print("     - Phase: 1, Days: 7")
        print()
        return

    # データ量に応じた提案
    print(f"[OK] 現在のレース数: {total_races:,} レース")
    print()

    if total_races < 1000:
        print("[INFO] データ量: 少ない（< 1,000レース）")
        print()
        print("【推奨】さらにデータを収集:")
        print("  - 目標: 1,000レース以上（基本的なモデル訓練に必要）")
        print("  - GitHub Actionsで継続的に収集")
        print()

    elif total_races < 5000:
        print("[INFO] データ量: 普通（1,000-5,000レース）")
        print()
        print("【次のステップ】")
        print()
        print("  1. 基本モデルの訓練:")
        print("     python ml/evaluate_model.py")
        print("     期待精度: 20-30%")
        print()
        print("  2. さらにデータを収集:")
        print("     目標: 5,000レース以上（精度向上に必要）")
        print()

    elif total_races < 10000:
        print("[INFO] データ量: 良好（5,000-10,000レース）")
        print()
        print("【次のステップ】")
        print()

        if not status['has_venue_stats']:
            print("  1. 会場別統計を計算:")
            print("     python ml/advanced_stats.py")
            print()

        print("  2. ハイパーパラメータ最適化:")
        print("     python ml/hyperparameter_tuning.py")
        print("     所要時間: 2-6時間")
        print()
        print("  3. 最適パラメータでモデル訓練:")
        print("     python ml/train_model.py")
        print("     期待精度: 30-35%")
        print()

    else:
        print("[INFO] データ量: 非常に良好（10,000レース以上）")
        print()
        print("【次のステップ】高精度モデルの構築")
        print()

        steps = []
        step_num = 1

        if not status['has_venue_stats']:
            print(f"  {step_num}. 会場別統計を計算:")
            print("     python ml/advanced_stats.py")
            print()
            step_num += 1

        if not status['has_weather_data']:
            print(f"  {step_num}. 天気データを収集:")
            print("     python scraper/weather_scraper.py")
            print()
            step_num += 1

        print(f"  {step_num}. ハイパーパラメータ最適化（時系列重み付け有効）:")
        print("     python ml/hyperparameter_tuning.py")
        print("     所要時間: 2-6時間")
        print()
        step_num += 1

        print(f"  {step_num}. 最適パラメータでモデル訓練:")
        print("     python ml/train_model.py")
        print("     期待精度: 35-45%")
        print()
        step_num += 1

        print(f"  {step_num}. 統合パイプライン実行（推奨）:")
        print("     python ml/train_full_pipeline.py")
        print("     全ステップを自動実行")
        print()

    # データ期間に応じた追加提案
    if status['date_range_days'] > 0:
        years = status['date_range_days'] / 365.25
        if years < 1:
            print("[TIP] ヒント: データ期間が1年未満です")
            print("   - 精度向上のため、さらに過去データを収集することを推奨")
            print("   - 目標: 1-3年分のデータ")
            print()


def main():
    """メイン処理"""
    try:
        # データベースの状態を確認
        status = check_database_status()

        # 次のステップを提案
        suggest_next_steps(status)

        print("=" * 80)
        print()

    except Exception as e:
        print(f"\n[ERROR] エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
