"""
ハイパーパラメータ最適化スクリプト

XGBoostモデルの最適なハイパーパラメータを探索
- RandomizedSearchCVによる効率的な探索
- 層化K分割交差検証による精度評価
- 最適パラメータの自動保存
"""
import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
import psycopg2

import xgboost as xgb
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold
from sklearn.metrics import accuracy_score, make_scorer
from scipy.stats import uniform, randint

# 親ディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.feature_engineer import FeatureEngineer

load_dotenv()


def calculate_sample_weight(race_dates, half_life_years=3.0):
    """
    時系列重み付け: 新しいデータほど重要度を高くする

    Args:
        race_dates: レース日付のリスト
        half_life_years: 半減期（年）。この期間で重みが半分になる

    Returns:
        numpy.ndarray: サンプル重み（各データポイントの重要度）
    """
    from datetime import datetime

    today = datetime.now()
    weights = []

    for date in race_dates:
        if isinstance(date, str):
            date = pd.to_datetime(date)

        days_ago = (today - date).days

        # 指数関数的に減衰（半減期モデル）
        weight = np.exp(-days_ago / (365.25 * half_life_years))
        weights.append(weight)

    weights = np.array(weights)

    # 正規化（合計が元のデータ数と同じになるように）
    weights = weights * len(weights) / weights.sum()

    return weights


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
    """選手統計データを取得"""
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
    """モーター統計データを取得"""
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
    """特徴量を準備"""
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

    # FeatureEngineerの初期化
    feature_engineer = FeatureEngineer(historical_data=df)

    all_features = []
    all_labels = []
    all_race_dates = []  # レース日付を保存

    # レースごとに特徴量を生成
    race_count = 0
    for race_id in df['race_id'].unique():
        race_data = df[df['race_id'] == race_id].copy()

        if len(race_data) != 6:
            # 6艇揃っていないレースはスキップ
            continue

        # 天気データ（現時点ではダミー値、将来的にweather_dataテーブルから取得）
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

            # レース日付を6回（6艇分）追加
            race_date = race_data['race_date'].iloc[0]
            all_race_dates.extend([race_date] * 6)

            race_count += 1

            if race_count % 1000 == 0:
                print(f"  処理済みレース数: {race_count}")

        except Exception as e:
            # エラーは無視してスキップ
            continue

    # 全特徴量を結合
    X = pd.concat(all_features, ignore_index=True)
    y = np.concatenate(all_labels)
    race_dates = pd.Series(all_race_dates)

    print(f"\n生成された特徴量数: {len(X)}件")
    print(f"有効レース数: {race_count}レース")
    print(f"特徴量の次元数: {X.shape[1]}次元")
    print(f"特徴量名: {list(X.columns)}")

    return X, y, race_dates


def custom_win_accuracy(y_true, y_pred):
    """
    1着予測の精度を計算（カスタム評価指標）

    着順予測で最も重要なのは1着を当てること
    """
    # y_predは確率行列ではなく予測クラス（0-5）
    # 実際の1着は y_true == 1（元の着順）
    correct_wins = np.sum((y_true == 1) & (y_pred == 0))  # 0は1着（0-indexedなので）
    total_wins = np.sum(y_true == 1)

    if total_wins == 0:
        return 0.0

    return correct_wins / total_wins


def optimize_hyperparameters(X, y, race_dates, n_iter=50, cv_folds=5, use_time_weighting=True):
    """
    ハイパーパラメータを最適化

    Args:
        X: 特徴量
        y: ラベル（1-6の着順）
        race_dates: レース日付
        n_iter: ランダムサーチの試行回数
        cv_folds: 交差検証の分割数
        use_time_weighting: 時系列重み付けを使用するか

    Returns:
        best_params: 最適なハイパーパラメータ
        best_score: 最良スコア
    """
    print("\n=== ハイパーパラメータ最適化開始 ===\n")

    # ラベルを0-5に変換
    y_transformed = y - 1

    # 時系列重み付けを計算
    if use_time_weighting:
        print("時系列重み付けを適用（半減期: 3年）")
        sample_weights = calculate_sample_weight(race_dates, half_life_years=3.0)

        print(f"  最新データの平均重み: {sample_weights[race_dates == race_dates.max()].mean():.2f}")
        print(f"  全体の平均重み: {sample_weights.mean():.2f}")
        print(f"  最古データの平均重み: {sample_weights[race_dates == race_dates.min()].mean():.4f}\n")
    else:
        sample_weights = None
        print("時系列重み付けなし（全データ同等）\n")

    # パラメータ探索空間
    param_distributions = {
        'max_depth': randint(3, 12),                    # 木の深さ
        'learning_rate': uniform(0.01, 0.19),           # 学習率: 0.01-0.20
        'n_estimators': randint(100, 500),              # 木の数: 100-500
        'subsample': uniform(0.6, 0.4),                 # サブサンプリング率: 0.6-1.0
        'colsample_bytree': uniform(0.6, 0.4),          # 特徴量サンプリング率: 0.6-1.0
        'min_child_weight': randint(1, 10),             # 子ノードの最小重み
        'gamma': uniform(0, 0.5),                       # 分割の最小損失削減量
        'reg_alpha': uniform(0, 1.0),                   # L1正則化
        'reg_lambda': uniform(0, 2.0),                  # L2正則化
    }

    # ベースモデル
    base_model = xgb.XGBClassifier(
        objective='multi:softprob',
        num_class=6,
        random_state=42,
        eval_metric='mlogloss',
        n_jobs=-1
    )

    # 層化K分割交差検証
    cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)

    # カスタム評価指標（精度）
    accuracy_scorer = make_scorer(accuracy_score)

    # RandomizedSearchCV
    random_search = RandomizedSearchCV(
        estimator=base_model,
        param_distributions=param_distributions,
        n_iter=n_iter,
        scoring=accuracy_scorer,
        cv=cv,
        verbose=2,
        random_state=42,
        n_jobs=-1
    )

    print(f"探索パラメータ数: {len(param_distributions)}")
    print(f"試行回数: {n_iter}")
    print(f"交差検証分割数: {cv_folds}")
    print(f"総訓練回数: {n_iter * cv_folds}")
    print("\n最適化開始...\n")

    # 最適化実行
    if sample_weights is not None:
        random_search.fit(X, y_transformed, sample_weight=sample_weights)
    else:
        random_search.fit(X, y_transformed)

    print("\n=== 最適化完了 ===\n")
    print(f"最良スコア (Accuracy): {random_search.best_score_:.4f}")
    print(f"\n最適ハイパーパラメータ:")
    for param, value in random_search.best_params_.items():
        print(f"  {param}: {value}")

    # 上位10個の結果を表示
    print("\n=== 上位10個の結果 ===")
    results_df = pd.DataFrame(random_search.cv_results_)
    results_df = results_df.sort_values('rank_test_score')

    for idx, row in results_df.head(10).iterrows():
        print(f"\nRank {int(row['rank_test_score'])}:")
        print(f"  Score: {row['mean_test_score']:.4f} (+/- {row['std_test_score']:.4f})")
        print(f"  Params: {row['params']}")

    return random_search.best_params_, random_search.best_score_


def save_best_params(params, score, output_dir='ml'):
    """最適パラメータを保存"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    result = {
        'timestamp': timestamp,
        'best_score': float(score),
        'best_params': params,
        'note': 'RandomizedSearchCV with StratifiedKFold CV'
    }

    # JSONファイルとして保存
    filepath = os.path.join(output_dir, f'best_params_{timestamp}.json')
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n最適パラメータを保存: {filepath}")

    # 最新の設定として別名でも保存
    latest_filepath = os.path.join(output_dir, 'best_params_latest.json')
    with open(latest_filepath, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"最新設定として保存: {latest_filepath}")


def main():
    """メイン処理"""
    print("=" * 80)
    print("  競艇予測モデル - ハイパーパラメータ最適化")
    print("=" * 80)
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
        X, y, race_dates = prepare_features(df, racer_stats, motor_stats)

        if len(X) < 100:
            print(f"[WARNING] データが少なすぎます（{len(X)}件）")
            print("最適化には少なくとも1000件以上のデータを推奨します")
            response = input("続行しますか？ (y/n): ")
            if response.lower() != 'y':
                return

        # 4. ハイパーパラメータ最適化（時系列重み付け有効）
        best_params, best_score = optimize_hyperparameters(
            X, y, race_dates,
            n_iter=50,              # 試行回数（時間がある場合は100以上推奨）
            cv_folds=5,             # 交差検証分割数
            use_time_weighting=True # 時系列重み付けを使用
        )

        # 5. 最適パラメータを保存
        save_best_params(best_params, best_score)

        print("\n" + "=" * 80)
        print("  最適化完了！")
        print("=" * 80)
        print("\n次のステップ:")
        print("1. ml/best_params_latest.json を確認")
        print("2. python ml/train_model.py で最適パラメータを使用してモデル訓練")
        print("3. モデルの精度を評価")

    except Exception as e:
        print(f"\n[ERROR] エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
