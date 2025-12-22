"""
強化版レース予測スクリプト

強化版特徴量エンジニアリングと改良版組み合わせ予測を使用
全5賭け式の予測を出力

使用方法:
    python ml/predict_race_enhanced.py <race_id>
    python ml/predict_race_enhanced.py <race_id> --quiet  # JSON出力
"""
import os
import sys
import json
import argparse
import pandas as pd
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
import psycopg2

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.enhanced_feature_engineer import EnhancedFeatureEngineer
from ml.race_predictor import RacePredictor
from ml.improved_combination_predictor import ImprovedCombinationPredictor, format_all_predictions

load_dotenv()


def fetch_race_data(race_id):
    """指定されたレースのデータを取得"""
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()

    # レース基本情報
    cursor.execute("""
        SELECT id, race_date, venue_id, race_number, grade
        FROM races
        WHERE id = %s
    """, (race_id,))

    race_info = cursor.fetchone()
    if not race_info:
        conn.close()
        raise ValueError(f"Race ID {race_id} not found")

    # レースエントリー情報（race_entriesの全データ + racer_detailed_statsを取得）
    query = """
        SELECT
            re.race_id,
            re.boat_number,
            re.racer_id,
            re.motor_number,
            re.start_timing,
            re.course,
            re.result_position,
            re.racer_grade,
            re.win_rate,
            re.place_rate_2,
            re.place_rate_3,
            re.motor_rate_2,
            re.motor_rate_3,
            re.boat_rate_2,
            re.boat_rate_3,
            re.exhibition_time,
            re.exhibition_turn_time,
            re.exhibition_straight_time,
            re.average_st,
            re.flying_count,
            re.late_count,
            re.actual_course,
            r.race_date,
            r.venue_id,
            r.race_number,
            r.grade as race_grade,
            rc.name as racer_name,
            rc.racer_number,
            rds.overall_win_rate as racer_overall_win_rate,
            rds.overall_1st_rate as racer_1st_rate,
            rds.overall_2nd_rate as racer_2nd_rate,
            rds.overall_3rd_rate as racer_3rd_rate,
            rds.avg_start_timing as racer_avg_st,
            rds.sg_appearances,
            rds.flying_count as racer_flying_count,
            rds.late_start_count as racer_late_count,
            rds.grade_stats,
            rds.course_stats,
            rds.venue_stats
        FROM race_entries re
        JOIN races r ON re.race_id = r.id
        LEFT JOIN racers rc ON re.racer_id = rc.id
        LEFT JOIN racer_detailed_stats rds ON rc.racer_number = rds.racer_number
        WHERE re.race_id = %s
        ORDER BY re.boat_number
    """

    df = pd.read_sql_query(query, conn, params=(race_id,))
    conn.close()

    if len(df) != 6:
        raise ValueError(f"Race {race_id} does not have exactly 6 boats (found {len(df)})")

    return df, race_info


def save_predictions_to_db(race_id, predictions, model_version='enhanced_latest'):
    """予測結果をDBに保存"""
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()

    # 既存の予測を削除
    cursor.execute("DELETE FROM predictions WHERE race_id = %s", (race_id,))

    # 新しい予測を挿入
    for boat_number, probs in enumerate(predictions, start=1):
        cursor.execute("""
            INSERT INTO predictions (
                race_id,
                boat_number,
                predicted_win_prob,
                predicted_second_prob,
                predicted_third_prob,
                predicted_fourth_prob,
                predicted_fifth_prob,
                predicted_sixth_prob,
                model_version,
                created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, (
            race_id,
            boat_number,
            float(probs[0]),
            float(probs[1]),
            float(probs[2]),
            float(probs[3]),
            float(probs[4]),
            float(probs[5]),
            model_version
        ))

    conn.commit()
    conn.close()


def predict_race(race_id, model_path='ml/trained_model_latest.pkl', save_to_db=True, verbose=True):
    """
    レースの予測を実行（強化版）

    Args:
        race_id: レースID
        model_path: モデルファイルのパス
        save_to_db: DBに保存するか
        verbose: 詳細出力

    Returns:
        dict: 全賭け式の予測結果
    """
    if verbose:
        print(f"=== Enhanced Race Prediction: Race ID {race_id} ===\n")

    # 1. モデルをロード
    if verbose:
        print(f"Loading model: {model_path}")

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")

    predictor = RacePredictor()
    predictor.load(model_path)

    # 2. レースデータを取得
    if verbose:
        print("Fetching race data...")

    race_df, race_info = fetch_race_data(race_id)

    if verbose:
        venue_names = {
            1: '桐生', 2: '戸田', 3: '江戸川', 4: '平和島', 5: '多摩川', 6: '浜名湖',
            7: '蒲郡', 8: '常滑', 9: '津', 10: '三国', 11: '琵琶湖', 12: '住之江',
            13: '尼崎', 14: '鳴門', 15: '丸亀', 16: '児島', 17: '宮島', 18: '徳山',
            19: '下関', 20: '若松', 21: '芦屋', 22: '福岡', 23: '唐津', 24: '大村'
        }
        venue_name = venue_names.get(race_info[2], f"会場{race_info[2]}")
        print(f"  Date: {race_info[1]}")
        print(f"  Venue: {venue_name}")
        print(f"  Race #: {race_info[3]}")

    # 3. 特徴量を生成（強化版）
    if verbose:
        print("\nGenerating enhanced features...")

    fe = EnhancedFeatureEngineer()
    features = fe.create_features(race_df)

    if verbose:
        print(f"  Features: {features.shape[1]} dimensions")

    # 4. 予測を実行
    if verbose:
        print("\nRunning prediction...")

    # 特徴量の順序を確認してモデルに合わせる
    if predictor.feature_names:
        # モデルの特徴量順に並べ替え
        missing_features = set(predictor.feature_names) - set(features.columns)
        extra_features = set(features.columns) - set(predictor.feature_names)

        if missing_features:
            if verbose:
                print(f"  Warning: Missing features: {missing_features}")
            # 欠損特徴量は0で埋める
            for f in missing_features:
                features[f] = 0

        features = features[predictor.feature_names]

    predictions = predictor.predict_probabilities(features)

    # 5. 組み合わせ予測
    combo_predictor = ImprovedCombinationPredictor(predictions)
    all_predictions = combo_predictor.get_all_predictions(top_n=10)

    if verbose:
        print("\n" + "=" * 60)
        print("  予測結果")
        print("=" * 60)

        # 出走表
        print("\n【出走表】")
        for idx, row in race_df.iterrows():
            boat = int(row['boat_number'])
            name = row.get('racer_name') or 'Unknown'
            name = str(name)[:6]
            grade = row.get('racer_grade') or 'B1'
            win_rate = row.get('win_rate') or 0
            motor = row.get('motor_rate_2') or 0
            exh = row.get('exhibition_time') or 0
            print(f"  {boat}号艇 {name:6s} ({grade}) 勝率:{win_rate:.1f}% モーター:{motor:.1f}% 展示:{exh:.2f}")

        # 着順確率
        print("\n【着順確率】")
        print("  艇番   1着    2着    3着    4着    5着    6着")
        for boat in range(6):
            probs = predictions[boat]
            print(f"  {boat+1}号艇  {probs[0]*100:5.1f}% {probs[1]*100:5.1f}% {probs[2]*100:5.1f}% {probs[3]*100:5.1f}% {probs[4]*100:5.1f}% {probs[5]*100:5.1f}%")

        # 全賭け式予測
        print("\n" + format_all_predictions(all_predictions, max_items=5))

    # 6. DBに保存
    if save_to_db:
        if verbose:
            print("\nSaving predictions to database...")

        save_predictions_to_db(race_id, predictions, 'enhanced_latest')

        if verbose:
            print("  [OK] Saved to predictions table")

    # 7. 結果を返す
    return {
        'race_id': race_id,
        'predictions': [
            {
                'boat_number': i + 1,
                'racer_name': race_df.iloc[i].get('racer_name') or 'Unknown',
                'racer_grade': race_df.iloc[i].get('racer_grade') or 'B1',
                'win_prob': float(predictions[i][0]),
                'second_prob': float(predictions[i][1]),
                'third_prob': float(predictions[i][2]),
                'fourth_prob': float(predictions[i][3]),
                'fifth_prob': float(predictions[i][4]),
                'sixth_prob': float(predictions[i][5])
            }
            for i in range(6)
        ],
        'recommendations': {
            'tansho': all_predictions['tansho'],
            'nirenpuku': [
                {'combo': item['display'], 'prob': item['prob']}
                for item in all_predictions['nirenpuku'][:5]
            ],
            'nirentan': [
                {'combo': item['display'], 'prob': item['prob']}
                for item in all_predictions['nirentan'][:5]
            ],
            'sanrenpuku': [
                {'combo': item['display'], 'prob': item['prob']}
                for item in all_predictions['sanrenpuku'][:5]
            ],
            'sanrentan': [
                {'combo': item['display'], 'prob': item['prob']}
                for item in all_predictions['sanrentan'][:5]
            ]
        }
    }


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='Enhanced race prediction')
    parser.add_argument('race_id', type=int, help='Race ID to predict')
    parser.add_argument('--model', type=str, default='ml/trained_model_latest.pkl',
                        help='Model file path')
    parser.add_argument('--no-save', action='store_true',
                        help='Do not save to database')
    parser.add_argument('--quiet', action='store_true',
                        help='Quiet mode (JSON output only)')

    args = parser.parse_args()

    try:
        result = predict_race(
            race_id=args.race_id,
            model_path=args.model,
            save_to_db=not args.no_save,
            verbose=not args.quiet
        )

        if args.quiet:
            print(json.dumps(result, ensure_ascii=False))

    except Exception as e:
        if args.quiet:
            print(json.dumps({'error': str(e)}, ensure_ascii=False))
        else:
            print(f"Error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
