"""
レース予測スクリプト

指定されたrace_idに対して予測を実行し、結果をDBに保存
使用方法:
    python ml/predict_race.py <race_id>
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

# 親ディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.feature_engineer import FeatureEngineer
from ml.race_predictor import RacePredictor
from ml.combination_predictor import CombinationPredictor, format_predictions

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

    # レースエントリー情報
    query = """
        SELECT
            re.race_id,
            re.boat_number,
            re.racer_id,
            re.motor_number,
            re.start_timing,
            re.course,
            re.result_position,
            r.race_date,
            r.venue_id,
            r.race_number,
            r.grade,
            rc.racer_number,
            rc.name as racer_name,
            rc.grade as racer_grade
        FROM race_entries re
        JOIN races r ON re.race_id = r.id
        JOIN racers rc ON re.racer_id = rc.id
        WHERE re.race_id = %s
        ORDER BY re.boat_number
    """

    df = pd.read_sql_query(query, conn, params=(race_id,))
    conn.close()

    if len(df) != 6:
        raise ValueError(f"Race {race_id} does not have exactly 6 boats (found {len(df)})")

    return df, race_info


def fetch_historical_data():
    """過去データを取得（特徴量生成用）"""
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))

    query = """
        SELECT
            re.race_id,
            re.boat_number,
            re.racer_id,
            re.motor_number,
            re.start_timing,
            re.course,
            re.result_position,
            r.race_date,
            r.venue_id,
            r.race_number,
            r.grade,
            rc.racer_number,
            rc.name as racer_name,
            rc.grade as racer_grade
        FROM race_entries re
        JOIN races r ON re.race_id = r.id
        JOIN racers rc ON re.racer_id = rc.id
        WHERE re.result_position IS NOT NULL
        ORDER BY r.race_date DESC
        LIMIT 50000
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    return df


def fetch_racer_stats():
    """選手統計データを取得"""
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))

    query = """
        SELECT
            racer_id,
            AVG(CASE WHEN result_position = 1 THEN 1.0 ELSE 0.0 END) * 100 as win_rate,
            AVG(CASE WHEN result_position <= 2 THEN 1.0 ELSE 0.0 END) * 100 as second_rate,
            AVG(CASE WHEN result_position <= 3 THEN 1.0 ELSE 0.0 END) * 100 as third_rate,
            AVG(start_timing) as avg_start_timing
        FROM race_entries
        WHERE result_position IS NOT NULL
        GROUP BY racer_id
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    return df


def fetch_motor_stats():
    """モーター統計データを取得"""
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))

    query = """
        SELECT
            venue_id,
            motor_number,
            AVG(CASE WHEN result_position <= 2 THEN 1.0 ELSE 0.0 END) * 100 as second_rate,
            AVG(CASE WHEN result_position <= 3 THEN 1.0 ELSE 0.0 END) * 100 as third_rate
        FROM race_entries re
        JOIN races r ON re.race_id = r.id
        WHERE motor_number IS NOT NULL AND result_position IS NOT NULL
        GROUP BY venue_id, motor_number
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    return df


def fetch_racer_detailed_stats():
    """選手詳細統計データを取得"""
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))

    query = """
        SELECT
            racer_number,
            total_races,
            total_wins,
            total_優出,
            total_優勝,
            avg_start_timing,
            sg_appearances,
            flying_count,
            late_start_count,
            grade_stats,
            boat_number_stats,
            course_stats,
            venue_stats
        FROM racer_detailed_stats
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    return df


def fetch_weather_data(venue_id, race_date):
    """天気データを取得"""
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            wind_speed,
            wind_direction,
            temperature,
            wave_height,
            water_temperature
        FROM weather_data
        WHERE venue_id = %s
        AND DATE(record_datetime) = DATE(%s)
        ORDER BY record_datetime DESC
        LIMIT 1
    """, (venue_id, race_date))

    weather = cursor.fetchone()
    conn.close()

    if weather:
        return {
            'wind_speed': weather[0] or 3.0,
            'wind_direction': weather[1] or 180,
            'temperature': weather[2] or 20.0,
            'wave_height': weather[3] or 2.0,
            'water_temperature': weather[4] or 20.0
        }
    else:
        # デフォルト値
        return {
            'wind_speed': 3.0,
            'wind_direction': 180,
            'temperature': 20.0,
            'wave_height': 2.0,
            'water_temperature': 20.0
        }


def prepare_race_features(race_df, historical_df, racer_stats, motor_stats, racer_detailed_stats, weather_data):
    """レースの特徴量を準備"""
    # 統計データをマージ
    race_df = race_df.merge(racer_stats, on='racer_id', how='left', suffixes=('', '_stat'))
    race_df = race_df.merge(
        motor_stats,
        on=['venue_id', 'motor_number'],
        how='left',
        suffixes=('', '_motor')
    )

    # 欠損値を埋める
    race_df['win_rate'] = race_df['win_rate'].fillna(5.0)
    race_df['second_rate'] = race_df['second_rate_motor'].fillna(30.0)
    race_df['third_rate'] = race_df['third_rate_motor'].fillna(50.0)
    race_df['avg_start_timing'] = race_df['avg_start_timing'].fillna(0.17)

    # 天気データを追加
    for key, value in weather_data.items():
        race_df[key] = value

    # 選手統計をコピー
    race_df['racer_win_rate'] = race_df['win_rate']
    race_df['racer_win_rate_venue'] = race_df['win_rate']
    race_df['racer_second_rate'] = race_df['second_rate']
    race_df['racer_third_rate'] = race_df['third_rate']
    race_df['motor_second_rate'] = race_df['second_rate']
    race_df['motor_third_rate'] = race_df['third_rate']
    race_df['grade'] = race_df['racer_grade']

    # FeatureEngineerで特徴量生成（詳細統計を渡す）
    feature_engineer = FeatureEngineer(
        historical_data=historical_df,
        racer_detailed_stats=racer_detailed_stats
    )
    features = feature_engineer.create_features(race_df)

    return features


def save_predictions_to_db(race_id, predictions, model_version='latest'):
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
            float(probs[0]),  # 1着確率
            float(probs[1]),  # 2着確率
            float(probs[2]),  # 3着確率
            float(probs[3]),  # 4着確率
            float(probs[4]),  # 5着確率
            float(probs[5]),  # 6着確率
            model_version
        ))

    conn.commit()
    conn.close()


def predict_race(race_id, model_path='ml/trained_model_latest.pkl', save_to_db=True, verbose=True):
    """
    レースの予測を実行

    Args:
        race_id: レースID
        model_path: モデルファイルのパス
        save_to_db: DBに保存するか
        verbose: 詳細出力

    Returns:
        numpy.ndarray: 予測確率 (6艇 × 6着順)
    """
    if verbose:
        print(f"=== Race Prediction: Race ID {race_id} ===\n")

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
        print(f"  Race: {race_info[1]} / Venue: {race_info[2]} / Race #: {race_info[3]}")
        print(f"  Boats: {len(race_df)}")

    # 3. 過去データと統計を取得
    if verbose:
        print("Fetching historical data and statistics...")

    historical_df = fetch_historical_data()
    racer_stats = fetch_racer_stats()
    motor_stats = fetch_motor_stats()
    racer_detailed_stats = fetch_racer_detailed_stats()

    # 4. 天気データを取得
    venue_id = race_info[2]
    race_date = race_info[1]
    weather_data = fetch_weather_data(venue_id, race_date)

    if verbose:
        print(f"  Weather: Wind {weather_data['wind_speed']}m/s, Temp {weather_data['temperature']}°C")

    # 5. 特徴量を生成
    if verbose:
        print("Generating features...")

    features = prepare_race_features(race_df, historical_df, racer_stats, motor_stats, racer_detailed_stats, weather_data)

    if verbose:
        print(f"  Features: {features.shape[1]} dimensions")

    # 6. 予測を実行
    if verbose:
        print("\nRunning prediction...")

    predictions = predictor.predict_probabilities(features)

    # 7. 連単・連複予測
    if verbose:
        print("\n=== Prediction Results ===\n")
        print("--- Win Probabilities ---")
        for boat_num in range(6):
            win_prob = predictions[boat_num][0]
            print(f"  Boat {boat_num + 1}: {win_prob*100:.2f}%")

        # CombinationPredictorを使用
        combo_predictor = CombinationPredictor(predictions)
        all_predictions = combo_predictor.get_all_predictions(top_n=10)

        print("\n" + format_predictions(all_predictions, verbose=True))

    # 8. DBに保存
    if save_to_db:
        if verbose:
            print("\nSaving predictions to database...")

        model_version = os.path.basename(model_path).replace('.pkl', '')
        save_predictions_to_db(race_id, predictions, model_version)

        if verbose:
            print("  [OK] Saved to predictions table")

    return predictions


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='Predict race results')
    parser.add_argument('race_id', type=int, help='Race ID to predict')
    parser.add_argument('--model', type=str, default='ml/trained_model_latest.pkl',
                        help='Model file path')
    parser.add_argument('--no-save', action='store_true',
                        help='Do not save to database')
    parser.add_argument('--quiet', action='store_true',
                        help='Quiet mode (minimal output)')

    args = parser.parse_args()

    try:
        predictions = predict_race(
            race_id=args.race_id,
            model_path=args.model,
            save_to_db=not args.no_save,
            verbose=not args.quiet
        )

        # JSON形式でも出力（API呼び出し用）
        if args.quiet:
            result = {
                'race_id': args.race_id,
                'predictions': [
                    {
                        'boat_number': i + 1,
                        'win_prob': float(predictions[i][0]),
                        'second_prob': float(predictions[i][1]),
                        'third_prob': float(predictions[i][2]),
                        'fourth_prob': float(predictions[i][3]),
                        'fifth_prob': float(predictions[i][4]),
                        'sixth_prob': float(predictions[i][5])
                    }
                    for i in range(6)
                ]
            }
            print(json.dumps(result))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
