"""
バックテストスクリプト

過去レースに対して予測を実行し、実際の結果と比較して精度を検証する

使用方法:
    python ml/backtest.py                    # 直近100レースでテスト
    python ml/backtest.py --races 500        # 500レースでテスト
    python ml/backtest.py --date 2024-11-01  # 指定日以降のレースでテスト
"""
import os
import sys
import argparse
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
from dotenv import load_dotenv
import psycopg2

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.enhanced_feature_engineer import EnhancedFeatureEngineer
from ml.race_predictor import RacePredictor
from ml.improved_combination_predictor import ImprovedCombinationPredictor

load_dotenv()


def fetch_completed_races(limit=100, start_date=None):
    """結果が確定しているレースを取得"""
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()

    # 結果が確定しているレース（result_positionがNULLでない）を取得
    query = """
        SELECT DISTINCT r.id, r.race_date, r.venue_id, r.race_number
        FROM races r
        JOIN race_entries re ON r.id = re.race_id
        WHERE re.result_position IS NOT NULL
    """

    if start_date:
        query += f" AND r.race_date >= '{start_date}'"

    query += """
        GROUP BY r.id
        HAVING COUNT(re.boat_number) = 6
        ORDER BY r.race_date DESC, r.venue_id, r.race_number
    """

    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    races = cursor.fetchall()

    cursor.close()
    conn.close()

    return races


def fetch_race_data(race_id):
    """1レース分のデータを取得"""
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))

    query = """
        SELECT
            re.race_id,
            re.boat_number,
            re.racer_id,
            re.result_position,
            re.racer_grade,
            re.win_rate,
            re.place_rate_2,
            re.place_rate_3,
            re.motor_number,
            re.motor_rate_2,
            re.boat_rate_2,
            re.exhibition_time,
            re.average_st,
            re.flying_count,
            re.late_count,
            r.race_date,
            r.venue_id,
            r.race_number
        FROM race_entries re
        JOIN races r ON re.race_id = r.id
        WHERE re.race_id = %s
        ORDER BY re.boat_number
    """

    df = pd.read_sql_query(query, conn, params=(race_id,))
    conn.close()

    return df


def run_backtest(races, model_path='ml/trained_model_latest.pkl', verbose=True):
    """バックテストを実行"""

    if verbose:
        print("\n" + "=" * 70)
        print("  Backtest - Model Validation")
        print("=" * 70)
        print(f"\nModel: {model_path}")
        print(f"Test races: {len(races)}")
        print()

    # モデルをロード
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found: {model_path}")

    predictor = RacePredictor()
    predictor.load(model_path)

    fe = EnhancedFeatureEngineer()

    # 結果を格納
    results = {
        'total_races': 0,
        'win_correct': 0,           # 1着的中
        'top2_correct': 0,          # 予測上位2艇に1着が含まれる
        'top3_correct': 0,          # 予測上位3艇に1着が含まれる
        'nirentan_top5': 0,         # 2連単 上位5組的中
        'nirentan_top10': 0,        # 2連単 上位10組的中
        'sanrentan_top10': 0,       # 3連単 上位10組的中
        'sanrentan_top20': 0,       # 3連単 上位20組的中
        'nirenpuku_top5': 0,        # 2連複 上位5組的中
        'sanrenpuku_top10': 0,      # 3連複 上位10組的中
    }

    # 詳細ログ
    detailed_results = []

    for i, (race_id, race_date, venue_id, race_number) in enumerate(races):
        try:
            # レースデータ取得
            race_df = fetch_race_data(race_id)

            if len(race_df) != 6:
                continue

            # 実際の結果を取得
            actual_results = race_df.set_index('boat_number')['result_position'].to_dict()
            actual_1st = [k for k, v in actual_results.items() if v == 1]
            actual_2nd = [k for k, v in actual_results.items() if v == 2]
            actual_3rd = [k for k, v in actual_results.items() if v == 3]

            if not actual_1st or not actual_2nd or not actual_3rd:
                continue

            actual_1st = actual_1st[0]
            actual_2nd = actual_2nd[0]
            actual_3rd = actual_3rd[0]

            # 特徴量生成
            features = fe.create_features(race_df)

            # 特徴量の順序を合わせる
            if predictor.feature_names:
                missing_features = set(predictor.feature_names) - set(features.columns)
                for f in missing_features:
                    features[f] = 0
                features = features[predictor.feature_names]

            # 予測
            predictions = predictor.predict_probabilities(features)

            # 組み合わせ予測
            combo_predictor = ImprovedCombinationPredictor(predictions)
            all_predictions = combo_predictor.get_all_predictions(top_n=20)

            # 単勝予測（1着予測）
            win_probs = [(i + 1, predictions[i][0]) for i in range(6)]
            win_probs.sort(key=lambda x: x[1], reverse=True)
            predicted_1st = win_probs[0][0]
            predicted_top2 = [win_probs[0][0], win_probs[1][0]]
            predicted_top3 = [win_probs[0][0], win_probs[1][0], win_probs[2][0]]

            # 結果集計
            results['total_races'] += 1

            # 1着的中
            if predicted_1st == actual_1st:
                results['win_correct'] += 1

            # Top2に1着含まれる
            if actual_1st in predicted_top2:
                results['top2_correct'] += 1

            # Top3に1着含まれる
            if actual_1st in predicted_top3:
                results['top3_correct'] += 1

            # 2連単
            actual_nirentan = f"{actual_1st}-{actual_2nd}"
            nirentan_preds = [item['display'] for item in all_predictions['nirentan'][:10]]
            if actual_nirentan in nirentan_preds[:5]:
                results['nirentan_top5'] += 1
            if actual_nirentan in nirentan_preds[:10]:
                results['nirentan_top10'] += 1

            # 3連単
            actual_sanrentan = f"{actual_1st}-{actual_2nd}-{actual_3rd}"
            sanrentan_preds = [item['display'] for item in all_predictions['sanrentan'][:20]]
            if actual_sanrentan in sanrentan_preds[:10]:
                results['sanrentan_top10'] += 1
            if actual_sanrentan in sanrentan_preds[:20]:
                results['sanrentan_top20'] += 1

            # 2連複
            actual_nirenpuku = f"{min(actual_1st, actual_2nd)}={max(actual_1st, actual_2nd)}"
            nirenpuku_preds = [item['display'] for item in all_predictions['nirenpuku'][:10]]
            if actual_nirenpuku in nirenpuku_preds[:5]:
                results['nirenpuku_top5'] += 1

            # 3連複
            sorted_top3 = sorted([actual_1st, actual_2nd, actual_3rd])
            actual_sanrenpuku = f"{sorted_top3[0]}={sorted_top3[1]}={sorted_top3[2]}"
            sanrenpuku_preds = [item['display'] for item in all_predictions['sanrenpuku'][:10]]
            if actual_sanrenpuku in sanrenpuku_preds[:10]:
                results['sanrenpuku_top10'] += 1

            # 詳細ログ
            detailed_results.append({
                'race_id': race_id,
                'date': race_date,
                'venue': venue_id,
                'race_number': race_number,
                'predicted_1st': predicted_1st,
                'actual_1st': actual_1st,
                'win_correct': predicted_1st == actual_1st,
                'actual_sanrentan': actual_sanrentan,
                'top_sanrentan': sanrentan_preds[0] if sanrentan_preds else None,
            })

            # 進捗表示
            if verbose and (i + 1) % 50 == 0:
                current_acc = results['win_correct'] / results['total_races'] * 100
                print(f"  Progress: {i + 1}/{len(races)} - Win accuracy: {current_acc:.1f}%")

        except Exception as e:
            if verbose:
                print(f"  [!] Race {race_id} error: {e}")
            continue

    return results, detailed_results


def save_results_to_db(results, model_version='enhanced_latest'):
    """バックテスト結果をDBに保存"""
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()

    total = results['total_races']
    if total == 0:
        return False

    try:
        cursor.execute("""
            INSERT INTO backtest_results (
                total_races,
                win_correct, win_accuracy,
                top2_correct, top3_correct,
                nirentan_top5, nirentan_top5_accuracy, nirentan_top10,
                nirenpuku_top5, nirenpuku_top5_accuracy,
                sanrentan_top10, sanrentan_top10_accuracy, sanrentan_top20,
                sanrenpuku_top10, sanrenpuku_top10_accuracy,
                model_version
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            total,
            results['win_correct'], results['win_correct'] / total * 100,
            results['top2_correct'], results['top3_correct'],
            results['nirentan_top5'], results['nirentan_top5'] / total * 100, results['nirentan_top10'],
            results['nirenpuku_top5'], results['nirenpuku_top5'] / total * 100,
            results['sanrentan_top10'], results['sanrentan_top10'] / total * 100, results['sanrentan_top20'],
            results['sanrenpuku_top10'], results['sanrenpuku_top10'] / total * 100,
            model_version
        ))
        conn.commit()
        print("\n[OK] Results saved to database")
        return True
    except Exception as e:
        print(f"\n[ERROR] Failed to save results: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()


def check_accuracy_degradation(current_results, threshold=5.0):
    """精度低下をチェック（前回比較）"""
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()

    try:
        # 直近の結果を取得
        cursor.execute("""
            SELECT win_accuracy, nirentan_top5_accuracy, sanrentan_top10_accuracy
            FROM backtest_results
            ORDER BY run_date DESC
            LIMIT 1 OFFSET 1
        """)
        prev = cursor.fetchone()

        if not prev:
            return None  # 比較対象なし

        total = current_results['total_races']
        current_win = current_results['win_correct'] / total * 100
        current_nirentan = current_results['nirentan_top5'] / total * 100
        current_sanrentan = current_results['sanrentan_top10'] / total * 100

        degradation = {
            'win': prev[0] - current_win,
            'nirentan': prev[1] - current_nirentan,
            'sanrentan': prev[2] - current_sanrentan,
        }

        # 閾値以上の低下があるか
        alerts = []
        if degradation['win'] > threshold:
            alerts.append(f"Win accuracy dropped: {prev[0]:.1f}% -> {current_win:.1f}% (-{degradation['win']:.1f}%)")
        if degradation['nirentan'] > threshold:
            alerts.append(f"Exacta accuracy dropped: {prev[1]:.1f}% -> {current_nirentan:.1f}% (-{degradation['nirentan']:.1f}%)")
        if degradation['sanrentan'] > threshold:
            alerts.append(f"Trifecta accuracy dropped: {prev[2]:.1f}% -> {current_sanrentan:.1f}% (-{degradation['sanrentan']:.1f}%)")

        return alerts if alerts else None

    except Exception as e:
        print(f"[WARNING] Could not check degradation: {e}")
        return None
    finally:
        cursor.close()
        conn.close()


def print_results(results, detailed_results=None):
    """結果を表示"""
    total = results['total_races']

    if total == 0:
        print("No valid races for backtest")
        return

    print("\n" + "=" * 70)
    print("  Backtest Results")
    print("=" * 70)

    print(f"\nTotal races tested: {total}")

    # 的中率
    print("\n[Hit Rate]")
    print("-" * 50)

    win_acc = results['win_correct'] / total * 100
    top2_acc = results['top2_correct'] / total * 100
    top3_acc = results['top3_correct'] / total * 100

    print(f"  Win (1st place):        {results['win_correct']:4d} / {total} = {win_acc:5.1f}%")
    print(f"  Top2 contains winner:   {results['top2_correct']:4d} / {total} = {top2_acc:5.1f}%")
    print(f"  Top3 contains winner:   {results['top3_correct']:4d} / {total} = {top3_acc:5.1f}%")

    print("\n[Exacta (2-Rentan)]")
    print("-" * 50)
    nirentan5 = results['nirentan_top5'] / total * 100
    nirentan10 = results['nirentan_top10'] / total * 100
    print(f"  Top 5 hit:   {results['nirentan_top5']:4d} / {total} = {nirentan5:5.1f}%")
    print(f"  Top 10 hit:  {results['nirentan_top10']:4d} / {total} = {nirentan10:5.1f}%")

    print("\n[Quinella (2-Renpuku)]")
    print("-" * 50)
    nirenpuku5 = results['nirenpuku_top5'] / total * 100
    print(f"  Top 5 hit:   {results['nirenpuku_top5']:4d} / {total} = {nirenpuku5:5.1f}%")

    print("\n[Trifecta (3-Rentan)]")
    print("-" * 50)
    sanrentan10 = results['sanrentan_top10'] / total * 100
    sanrentan20 = results['sanrentan_top20'] / total * 100
    print(f"  Top 10 hit:  {results['sanrentan_top10']:4d} / {total} = {sanrentan10:5.1f}%")
    print(f"  Top 20 hit:  {results['sanrentan_top20']:4d} / {total} = {sanrentan20:5.1f}%")

    print("\n[Trio (3-Renpuku)]")
    print("-" * 50)
    sanrenpuku10 = results['sanrenpuku_top10'] / total * 100
    print(f"  Top 10 hit:  {results['sanrenpuku_top10']:4d} / {total} = {sanrenpuku10:5.1f}%")

    # ベースラインとの比較
    print("\n" + "=" * 70)
    print("  Comparison with Random Baseline")
    print("=" * 70)

    random_win = 16.7  # 1/6
    random_nirentan = 3.3  # 1/30
    random_sanrentan = 0.83  # 1/120

    print(f"\n  {'Metric':<25} {'Model':>10} {'Random':>10} {'Lift':>10}")
    print("  " + "-" * 55)
    print(f"  {'Win (1st place)':<25} {win_acc:>9.1f}% {random_win:>9.1f}% {win_acc/random_win:>9.1f}x")
    print(f"  {'Exacta Top5':<25} {nirentan5:>9.1f}% {random_nirentan*5:>9.1f}% {nirentan5/(random_nirentan*5):>9.1f}x")
    print(f"  {'Trifecta Top10':<25} {sanrentan10:>9.1f}% {random_sanrentan*10:>9.1f}% {sanrentan10/(random_sanrentan*10):>9.1f}x")

    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(description='Backtest prediction model')
    parser.add_argument('--races', type=int, default=100, help='Number of races to test')
    parser.add_argument('--date', type=str, default=None, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--model', type=str, default='ml/trained_model_latest.pkl', help='Model path')
    parser.add_argument('--quiet', action='store_true', help='Suppress progress output')
    parser.add_argument('--save', action='store_true', help='Save results to database')
    parser.add_argument('--check-degradation', action='store_true', help='Check for accuracy degradation')

    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("  Backtest - Model Validation System")
    print("=" * 70)

    # レースを取得
    print("\nFetching completed races...")
    races = fetch_completed_races(limit=args.races, start_date=args.date)
    print(f"Found {len(races)} races with results")

    if len(races) == 0:
        print("No races found for backtest")
        return

    # バックテスト実行
    results, detailed = run_backtest(
        races,
        model_path=args.model,
        verbose=not args.quiet
    )

    # 結果表示
    print_results(results, detailed)

    # DB保存
    if args.save:
        save_results_to_db(results)

    # 精度低下チェック
    if args.check_degradation:
        alerts = check_accuracy_degradation(results)
        if alerts:
            print("\n" + "!" * 70)
            print("  [WARNING] Accuracy Degradation Detected!")
            print("!" * 70)
            for alert in alerts:
                print(f"  - {alert}")
            print("\nConsider retraining the model.")
            sys.exit(1)  # GitHub Actions で失敗として検知可能
        else:
            print("\n[OK] No significant accuracy degradation detected.")


if __name__ == '__main__':
    main()
