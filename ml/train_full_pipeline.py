"""
統合訓練パイプラインスクリプト

データ確認から最終モデル訓練まで全ステップを自動実行:
1. データ収集状況の確認
2. 会場別統計の計算
3. ハイパーパラメータ最適化
4. 最適パラメータでモデル訓練
5. 精度評価とレポート
"""
import os
import sys
import subprocess
import json
from datetime import datetime

# 親ディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def print_header(title):
    """ヘッダーを表示"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def run_script(script_path, description):
    """Pythonスクリプトを実行"""
    print(f"\n▶ {description}")
    print(f"  実行: python {script_path}\n")

    result = subprocess.run(
        [sys.executable, script_path],
        capture_output=False,
        text=True
    )

    if result.returncode != 0:
        print(f"\n❌ エラー: {description} が失敗しました")
        return False

    print(f"\n✅ 完了: {description}")
    return True


def check_file_exists(filepath):
    """ファイルの存在確認"""
    return os.path.exists(filepath)


def check_table_exists(table_name):
    """テーブルの存在確認"""
    from dotenv import load_dotenv
    import psycopg2

    load_dotenv()

    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = %s
            )
        """, (table_name,))

        exists = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        return exists
    except Exception as e:
        print(f"データベース確認エラー: {e}")
        return False


def get_race_count():
    """レース数を取得"""
    from dotenv import load_dotenv
    import psycopg2

    load_dotenv()

    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM races")
        count = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        return count
    except Exception as e:
        print(f"データベース確認エラー: {e}")
        return 0


def main():
    """メイン処理"""
    print_header("競艇予測モデル - 統合訓練パイプライン")

    print("このスクリプトは以下のステップを自動実行します:")
    print("1. データ収集状況の確認")
    print("2. 会場別統計の計算")
    print("3. ハイパーパラメータ最適化")
    print("4. 最適パラメータでモデル訓練")
    print("5. 精度評価とレポート")
    print()

    response = input("続行しますか？ (y/n): ")
    if response.lower() != 'y':
        print("中止しました")
        return

    start_time = datetime.now()

    # Step 1: データ収集状況の確認
    print_header("Step 1: データ収集状況の確認")

    race_count = get_race_count()
    print(f"現在のレース数: {race_count:,} レース")

    if race_count < 1000:
        print("\n❌ データが不足しています（最低 1,000レース必要）")
        print("まずデータ収集を実行してください:")
        print("  python scraper/collect_all_venues.py")
        return

    print(f"✅ データ量: 十分（{race_count:,} レース）")

    # Step 2: 会場別統計の計算
    print_header("Step 2: 会場別統計の計算")

    if check_table_exists('racer_venue_stats'):
        print("✅ 会場別統計テーブルは既に存在します")
        print("   スキップします")
    else:
        print("会場別統計を計算します...")
        if not run_script('ml/advanced_stats.py', '会場別統計の計算'):
            print("\n会場別統計の計算をスキップして続行します...")

    # Step 3: ハイパーパラメータ最適化
    print_header("Step 3: ハイパーパラメータ最適化")

    best_params_path = 'ml/best_params_latest.json'

    if check_file_exists(best_params_path):
        print(f"✅ 最適パラメータファイルが存在します: {best_params_path}")

        # ファイルの日時を確認
        mtime = os.path.getmtime(best_params_path)
        file_date = datetime.fromtimestamp(mtime)
        days_old = (datetime.now() - file_date).days

        print(f"   作成日時: {file_date.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   経過日数: {days_old} 日")

        if days_old > 7:
            print("\n⚠️ 最適パラメータが1週間以上古いです")
            response = input("   再最適化しますか？ (y/n): ")
            if response.lower() == 'y':
                if not run_script('ml/hyperparameter_tuning.py', 'ハイパーパラメータ最適化'):
                    print("\n最適化に失敗しましたが、既存のパラメータで続行します...")
        else:
            print("   既存のパラメータを使用します")

    else:
        print("最適パラメータファイルが見つかりません")
        print("ハイパーパラメータ最適化を実行します（2-6時間かかる可能性があります）")

        if race_count >= 5000:
            response = input("実行しますか？ (y/n, スキップする場合は n): ")
            if response.lower() == 'y':
                if not run_script('ml/hyperparameter_tuning.py', 'ハイパーパラメータ最適化'):
                    print("\n最適化に失敗しましたが、デフォルトパラメータで続行します...")
            else:
                print("スキップしました（デフォルトパラメータを使用）")
        else:
            print(f"⚠️ データ量が少ない（{race_count:,} < 5,000）ため、スキップします")
            print("   デフォルトパラメータを使用します")

    # Step 4: 最適パラメータでモデル訓練
    print_header("Step 4: 最適パラメータでモデル訓練")

    if not run_script('ml/train_model.py', 'モデル訓練'):
        print("\n❌ モデル訓練に失敗しました")
        return

    # Step 5: 完了レポート
    print_header("完了レポート")

    end_time = datetime.now()
    elapsed_time = end_time - start_time

    hours = int(elapsed_time.total_seconds() // 3600)
    minutes = int((elapsed_time.total_seconds() % 3600) // 60)

    print(f"総実行時間: {hours}時間{minutes}分")
    print()

    # 最新のメトリクスを読み込んで表示
    metrics_files = [
        f for f in os.listdir('ml')
        if f.startswith('metrics_') and f.endswith('.json')
    ]

    if metrics_files:
        latest_metrics = sorted(metrics_files, reverse=True)[0]
        metrics_path = os.path.join('ml', latest_metrics)

        with open(metrics_path, 'r', encoding='utf-8') as f:
            metrics_data = json.load(f)

        print("【最終精度】")
        print(f"  Overall Accuracy: {metrics_data['metrics']['accuracy']*100:.2f}%")
        print(f"  1着予測精度: {metrics_data['metrics']['win_accuracy']*100:.2f}%")
        print(f"  Top-3予測精度: {metrics_data['metrics']['top3_accuracy']*100:.2f}%")
        print()

    print("【作成されたファイル】")
    print(f"  モデル: ml/trained_model_latest.pkl")
    if metrics_files:
        print(f"  メトリクス: {metrics_path}")
    if check_file_exists(best_params_path):
        print(f"  最適パラメータ: {best_params_path}")
    print()

    print("【次のステップ】")
    print("1. モデルの精度を確認")
    print("2. さらにデータを収集して再訓練")
    print("3. 天気データを収集して精度向上（python scraper/weather_scraper.py）")
    print("4. フロントエンドと統合")
    print()

    print("=" * 80)
    print("  訓練完了！ お疲れ様でした 🎉")
    print("=" * 80)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n中断されました")
    except Exception as e:
        print(f"\n[ERROR] エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
