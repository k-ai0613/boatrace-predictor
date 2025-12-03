"""
予測モデルの精度検証スクリプト
"""
import os
import sys
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# 親ディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.feature_engineer import FeatureEngineer
from ml.race_predictor import RacePredictor

load_dotenv()


def fetch_training_data():
    """データベースから訓練データを取得"""
    print("=== データベースから訓練データを取得中 ===\n")

    conn = psycopg2.connect(os.getenv('DATABASE_URL'))

    # race_entries と racers, races を結合してデータ取得
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
        ORDER BY r.race_date DESC, r.venue_id, r.race_number, re.boat_number
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    print(f"取得データ数: {len(df)}件")
    print(f"レース数: {df['race_id'].nunique()}レース")
    print(f"選手数: {df['racer_id'].nunique()}名")
    print(f"日付範囲: {df['race_date'].min()} ～ {df['race_date'].max()}")

    return df


def fetch_racer_stats():
    """選手統計データを取得（実データ）"""
    print("\n=== 選手統計データを取得中 ===\n")

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

    print(f"選手統計: {len(df)}名分")
    return df


def fetch_motor_stats():
    """モーター統計データを取得（実データ）"""
    print("\n=== モーター統計データを取得中 ===\n")

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

    print(f"モーター統計: {len(df)}個")
    return df


def prepare_features(df, racer_stats, motor_stats):
    """特徴量を準備（実データ使用）"""
    print("\n=== 特徴量の生成 ===\n")

    # 統計データをマージ
    df = df.merge(racer_stats, on='racer_id', how='left', suffixes=('', '_stat'))

    # モーター統計をマージ
    df = df.merge(
        motor_stats,
        on=['venue_id', 'motor_number'],
        how='left',
        suffixes=('', '_motor')
    )

    # 欠損値を埋める
    df['win_rate'] = df['win_rate'].fillna(5.0)
    df['second_rate'] = df['second_rate_motor'].fillna(30.0)
    df['third_rate'] = df['third_rate_motor'].fillna(50.0)
    df['avg_start_timing'] = df['avg_start_timing'].fillna(0.17)

    # FeatureEngineerの初期化（履歴データとして全データを渡す）
    feature_engineer = FeatureEngineer(historical_data=df)

    all_features = []
    all_labels = []

    # レースごとに特徴量を生成
    race_count = 0
    for race_id in df['race_id'].unique():
        race_data = df[df['race_id'] == race_id].copy()

        if len(race_data) != 6:
            # 6艇揃っていないレースはスキップ
            continue

        # 天気データ（現時点ではダミー値、将来的にweather_dataテーブルから取得）
        # TODO: weather_dataテーブルから実データを取得する実装を追加
        race_data['wind_speed'] = np.random.uniform(0.5, 8.0, len(race_data))
        race_data['wind_direction'] = np.random.randint(0, 360, len(race_data))
        race_data['temperature'] = np.random.uniform(15.0, 30.0, len(race_data))
        race_data['wave_height'] = np.random.uniform(0, 10, len(race_data))

        # 選手統計をコピー
        race_data['racer_win_rate'] = race_data['win_rate']
        race_data['racer_win_rate_venue'] = race_data['win_rate']  # 簡易的に全国勝率を使用
        race_data['racer_second_rate'] = race_data['second_rate']
        race_data['racer_third_rate'] = race_data['third_rate']
        race_data['motor_second_rate'] = race_data['second_rate']
        race_data['motor_third_rate'] = race_data['third_rate']
        race_data['grade'] = race_data['racer_grade']

        try:
            features = feature_engineer.create_features(race_data)
            labels = race_data['result_position'].values

            all_features.append(features)
            all_labels.append(labels)
            race_count += 1

            if race_count % 1000 == 0:
                print(f"  処理済みレース数: {race_count}")

        except Exception as e:
            # エラーは無視してスキップ
            continue

    # 全特徴量を結合
    X = pd.concat(all_features, ignore_index=True)
    y = np.concatenate(all_labels)

    print(f"\n生成された特徴量数: {len(X)}件")
    print(f"有効レース数: {race_count}レース")
    print(f"特徴量の次元数: {X.shape[1]}次元")
    print(f"特徴量名: {list(X.columns)}")

    return X, y


def evaluate_model(X, y):
    """モデルを訓練して評価"""
    print("\n=== モデルの訓練と評価 ===\n")

    # 予測モデルの初期化
    predictor = RacePredictor()

    # モデル訓練
    print("モデル訓練中...\n")
    predictor.train(X, y)

    return predictor


def main():
    """メイン処理"""
    print("=" * 60)
    print("  競艇予測モデル精度検証")
    print("=" * 60)
    print()

    try:
        # 1. データ取得
        df = fetch_training_data()

        if len(df) == 0:
            print("[ERROR] 訓練データが取得できませんでした")
            print("まずデータ収集を実行してください: python scraper/collect_all_venues.py")
            return

        # 2. 統計データ取得
        racer_stats = fetch_racer_stats()
        motor_stats = fetch_motor_stats()

        # 3. 特徴量生成
        X, y = prepare_features(df, racer_stats, motor_stats)

        # 4. モデル訓練と評価
        predictor = evaluate_model(X, y)

        # 5. モデル保存
        print("\n=== モデルの保存 ===")
        model_path = os.path.join(os.path.dirname(__file__), 'trained_model.pkl')
        predictor.save(model_path)

        print("\n" + "=" * 60)
        print("  精度検証完了！")
        print("=" * 60)
        print(f"\nモデルファイル: {model_path}")
        print("\n次のステップ:")
        print("1. モデル精度をさらに向上させるには: python ml/hyperparameter_tuning.py")
        print("2. 最適化されたモデルを訓練するには: python ml/train_model.py")

    except Exception as e:
        print(f"\n[ERROR] エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
