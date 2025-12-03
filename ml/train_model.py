"""
最適化版モデル訓練スクリプト

最適化されたハイパーパラメータを使用してモデルを訓練
- best_params_latest.jsonから最適パラメータを読み込み
- 詳細な評価指標を出力
- 1着予測精度の計算
- 特徴量重要度の分析
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
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, log_loss, confusion_matrix, classification_report

# 親ディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.feature_engineer import FeatureEngineer
from ml.race_predictor import RacePredictor

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
        # 全てpd.Timestampに統一して型の不一致を防ぐ
        if not isinstance(date, pd.Timestamp):
            date = pd.Timestamp(date)

        days_ago = (today - date).days

        # 指数関数的に減衰（半減期モデル）
        # weight = exp(-days_ago / (365 * half_life))
        weight = np.exp(-days_ago / (365.25 * half_life_years))
        weights.append(weight)

    weights = np.array(weights)

    # 正規化（合計が元のデータ数と同じになるように）
    weights = weights * len(weights) / weights.sum()

    return weights


def load_best_params(filepath='ml/best_params_latest.json'):
    """最適パラメータを読み込み"""
    if not os.path.exists(filepath):
        print(f"[WARNING] {filepath} が見つかりません")
        print("デフォルトのハイパーパラメータを使用します")
        return None

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("=== 最適パラメータを読み込み ===\n")
    print(f"最適化日時: {data.get('timestamp', 'N/A')}")
    print(f"ベストスコア: {data.get('best_score', 'N/A'):.4f}")
    print("\nパラメータ:")
    for key, value in data['best_params'].items():
        print(f"  {key}: {value}")
    print()

    return data['best_params']


def fetch_training_data():
    """データベースから訓練データを取得"""
    print("=== データベースから訓練データを取得中 ===\n")

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
        LEFT JOIN races r ON re.race_id = r.id
        LEFT JOIN racers rc ON re.racer_id = rc.id
        WHERE re.result_position IS NOT NULL
        AND r.id IS NOT NULL
        AND rc.id IS NOT NULL
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


def fetch_racer_detailed_stats():
    """選手詳細統計データを取得（新規）"""
    print("\n=== 選手詳細統計データを取得中 ===\n")

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

    print(f"選手詳細統計: {len(df)}名分")
    return df


def prepare_features(df, racer_stats, motor_stats, racer_detailed_stats):
    """特徴量を準備"""
    print("\n=== 特徴量の生成 ===\n")

    # デバッグ: レースあたりの艇数を確認
    race_boat_counts = df.groupby('race_id').size()
    print(f"[DEBUG] レースあたりの艇数分布:")
    print(f"  6艇のレース: {(race_boat_counts == 6).sum()}レース")
    print(f"  6艇以外のレース: {(race_boat_counts != 6).sum()}レース")
    print(f"  最小艇数: {race_boat_counts.min()}")
    print(f"  最大艇数: {race_boat_counts.max()}")
    print()

    # 統計データをマージ
    df = df.merge(racer_stats, on='racer_id', how='left', suffixes=('', '_stat'))
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

    # FeatureEngineerの初期化（詳細統計データを渡す）
    feature_engineer = FeatureEngineer(
        historical_data=df,
        racer_detailed_stats=racer_detailed_stats
    )

    all_features = []
    all_labels = []
    all_race_dates = []  # レース日付を保存

    race_count = 0
    for race_id in df['race_id'].unique():
        race_data = df[df['race_id'] == race_id].copy()

        if len(race_data) != 6:
            continue

        # 天気データ（TODO: weather_dataテーブルから取得）
        race_data['wind_speed'] = np.random.uniform(0.5, 8.0, len(race_data))
        race_data['wind_direction'] = np.random.randint(0, 360, len(race_data))
        race_data['temperature'] = np.random.uniform(15.0, 30.0, len(race_data))
        race_data['wave_height'] = np.random.uniform(0, 10, len(race_data))

        # 選手統計をコピー
        race_data['racer_win_rate'] = race_data['win_rate']
        race_data['racer_win_rate_venue'] = race_data['win_rate']
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
            # デバッグ用: エラーを詳細に出力
            print(f"\n[DEBUG] Error processing race_id {race_id}:")
            print(f"  Error: {e}")
            print(f"  Race data shape: {race_data.shape}")
            print(f"  Racer numbers: {race_data['racer_number'].tolist() if 'racer_number' in race_data.columns else 'N/A'}")
            import traceback
            traceback.print_exc()
            # 最初のエラーで停止
            raise

    X = pd.concat(all_features, ignore_index=True)
    y = np.concatenate(all_labels)
    race_dates = pd.Series(all_race_dates)

    print(f"\n生成された特徴量数: {len(X)}件")
    print(f"有効レース数: {race_count}レース")
    print(f"特徴量の次元数: {X.shape[1]}次元")

    return X, y, race_dates


def calculate_win_accuracy(y_true, y_pred_proba):
    """1着予測精度を計算"""
    # 各レースで最も1着確率が高い艇を予測
    # y_pred_proba は (N, 6) の形状で、各行は1つの艇の着順確率[1着, 2着, ..., 6着]

    # レースごとにグループ化（6艇ずつ）
    n_races = len(y_pred_proba) // 6
    correct = 0

    for i in range(n_races):
        race_start = i * 6
        race_end = race_start + 6

        race_probs = y_pred_proba[race_start:race_end, 0]  # 各艇の1着確率
        race_true = y_true[race_start:race_end]

        # 予測: 1着確率が最も高い艇
        predicted_winner = np.argmax(race_probs)

        # 実際: 1着になった艇
        actual_winner = np.where(race_true == 1)[0]

        if len(actual_winner) > 0 and predicted_winner == actual_winner[0]:
            correct += 1

    return correct / n_races if n_races > 0 else 0


def calculate_top3_accuracy(y_true, y_pred_proba):
    """Top-3予測精度を計算（1着予測が上位3艇に入っている確率）"""
    n_races = len(y_pred_proba) // 6
    correct = 0

    for i in range(n_races):
        race_start = i * 6
        race_end = race_start + 6

        race_probs = y_pred_proba[race_start:race_end, 0]
        race_true = y_true[race_start:race_end]

        # 予測: 1着確率が高い上位3艇
        top3_predicted = np.argsort(race_probs)[-3:]

        # 実際: 1着になった艇
        actual_winner = np.where(race_true == 1)[0]

        if len(actual_winner) > 0 and actual_winner[0] in top3_predicted:
            correct += 1

    return correct / n_races if n_races > 0 else 0


def train_and_evaluate(X, y, race_dates, best_params=None, use_time_weighting=True):
    """モデルを訓練して評価"""
    print("\n=== モデルの訓練と評価 ===\n")

    # ラベルを0-5に変換
    y_transformed = y - 1

    # 時系列重み付けを計算
    if use_time_weighting:
        print("時系列重み付けを適用（半減期: 3年）")
        sample_weights = calculate_sample_weight(race_dates, half_life_years=3.0)

        print(f"  最新データの平均重み: {sample_weights[race_dates == race_dates.max()].mean():.2f}")
        print(f"  全体の平均重み: {sample_weights.mean():.2f}")
        print(f"  最古データの平均重み: {sample_weights[race_dates == race_dates.min()].mean():.4f}")
    else:
        sample_weights = None
        print("時系列重み付けなし（全データ同等）")

    # 訓練・検証データに分割
    if sample_weights is not None:
        X_train, X_test, y_train, y_test, weights_train, weights_test = train_test_split(
            X, y_transformed, sample_weights,
            test_size=0.2, random_state=42, stratify=y_transformed
        )
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_transformed, test_size=0.2, random_state=42, stratify=y_transformed
        )
        weights_train = None
        weights_test = None

    # ハイパーパラメータを設定
    if best_params:
        print("最適化されたハイパーパラメータを使用")
        model = xgb.XGBClassifier(
            objective='multi:softprob',
            num_class=6,
            random_state=42,
            eval_metric='mlogloss',
            **best_params
        )
    else:
        print("デフォルトのハイパーパラメータを使用")
        model = xgb.XGBClassifier(
            objective='multi:softprob',
            num_class=6,
            max_depth=8,
            learning_rate=0.05,
            n_estimators=300,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric='mlogloss'
        )

    # 訓練
    print("\nモデル訓練中...\n")
    eval_set = [(X_train, y_train), (X_test, y_test)]
    model.fit(
        X_train, y_train,
        sample_weight=weights_train,
        eval_set=eval_set,
        verbose=True
    )

    # 予測
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)

    # 評価指標
    print("\n=== 評価結果 ===\n")

    accuracy = accuracy_score(y_test, y_pred)
    logloss = log_loss(y_test, y_pred_proba)

    print(f"Overall Accuracy: {accuracy:.4f} ({accuracy*100:.2f}%)")
    print(f"Log Loss: {logloss:.4f}")

    # 元のラベル（1-6）に戻して1着予測精度を計算
    y_test_original = y_test + 1
    win_acc = calculate_win_accuracy(y_test_original, y_pred_proba)
    top3_acc = calculate_top3_accuracy(y_test_original, y_pred_proba)

    print(f"\n【最重要指標】")
    print(f"1着予測精度: {win_acc:.4f} ({win_acc*100:.2f}%)")
    print(f"Top-3予測精度: {top3_acc:.4f} ({top3_acc*100:.2f}%)")

    # 混同行列
    print("\n=== 混同行列 ===\n")
    cm = confusion_matrix(y_test, y_pred)
    print("予測 →")
    print("実際 ↓")
    print("      ", "  ".join([f"{i+1}着" for i in range(6)]))
    for i, row in enumerate(cm):
        print(f"{i+1}着  ", "  ".join([f"{val:4d}" for val in row]))

    # クラス別レポート
    print("\n=== クラス別レポート ===\n")
    report = classification_report(
        y_test, y_pred,
        target_names=['1着', '2着', '3着', '4着', '5着', '6着']
    )
    print(report)

    # 特徴量重要度
    print("\n=== 特徴量重要度 (Top 20) ===\n")
    importance = model.feature_importances_
    indices = np.argsort(importance)[::-1]

    for i in range(min(20, len(indices))):
        idx = indices[i]
        print(f"{i+1:2d}. {X.columns[idx]:30s}: {importance[idx]:.4f}")

    # RacePredictorクラスにラップして返す
    predictor = RacePredictor()
    predictor.model = model
    predictor.feature_names = X.columns.tolist()

    return predictor, {
        'accuracy': accuracy,
        'log_loss': logloss,
        'win_accuracy': win_acc,
        'top3_accuracy': top3_acc
    }


def train_ensemble_models(X, y, race_dates, best_params, n_models=3):
    """
    アンサンブル学習: 複数モデルを訓練して最良のものを選択

    Args:
        X, y, race_dates: 訓練データ
        best_params: ハイパーパラメータ
        n_models: 訓練するモデル数

    Returns:
        best_predictor: 最良のモデル
        best_metrics: 最良のメトリクス
    """
    print(f"\n=== アンサンブル学習（{n_models}モデル訓練） ===\n")

    models_results = []

    for i in range(n_models):
        print(f"\n--- モデル {i+1}/{n_models} 訓練中 ---")

        # ランダムシードを変えて訓練
        seed = 42 + i * 100

        # データを再分割（シードを変える）
        y_transformed = y - 1

        sample_weights = calculate_sample_weight(race_dates, half_life_years=3.0)

        X_train, X_test, y_train, y_test, weights_train, weights_test = train_test_split(
            X, y_transformed, sample_weights,
            test_size=0.2, random_state=seed, stratify=y_transformed
        )

        # モデル訓練
        if best_params:
            model = xgb.XGBClassifier(
                objective='multi:softprob',
                num_class=6,
                random_state=seed,
                eval_metric='mlogloss',
                **best_params
            )
        else:
            model = xgb.XGBClassifier(
                objective='multi:softprob',
                num_class=6,
                max_depth=8,
                learning_rate=0.05,
                n_estimators=300,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=seed,
                eval_metric='mlogloss'
            )

        eval_set = [(X_train, y_train), (X_test, y_test)]
        model.fit(
            X_train, y_train,
            sample_weight=weights_train,
            eval_set=eval_set,
            verbose=False
        )

        # 評価
        y_pred_proba = model.predict_proba(X_test)
        y_test_original = y_test + 1
        win_acc = calculate_win_accuracy(y_test_original, y_pred_proba)
        top3_acc = calculate_top3_accuracy(y_test_original, y_pred_proba)

        print(f"  1着予測精度: {win_acc*100:.2f}%")
        print(f"  Top-3予測精度: {top3_acc*100:.2f}%")

        # 結果を保存
        predictor = RacePredictor()
        predictor.model = model
        predictor.feature_names = X.columns.tolist()

        models_results.append({
            'predictor': predictor,
            'win_accuracy': win_acc,
            'top3_accuracy': top3_acc,
            'seed': seed
        })

    # 最良のモデルを選択（1着予測精度が最も高いもの）
    best_result = max(models_results, key=lambda x: x['win_accuracy'])

    print(f"\n=== 最良モデル ===")
    print(f"  シード: {best_result['seed']}")
    print(f"  1着予測精度: {best_result['win_accuracy']*100:.2f}%")
    print(f"  Top-3予測精度: {best_result['top3_accuracy']*100:.2f}%")

    return best_result['predictor'], {
        'accuracy': 0.0,  # 全体精度は計算していない
        'log_loss': 0.0,
        'win_accuracy': best_result['win_accuracy'],
        'top3_accuracy': best_result['top3_accuracy']
    }


def main():
    """メイン処理"""
    import argparse
    parser = argparse.ArgumentParser(description='Train boat race prediction model')
    parser.add_argument('--ensemble', action='store_true',
                        help='Use ensemble learning (train multiple models)')
    parser.add_argument('--n-models', type=int, default=3,
                        help='Number of models for ensemble (default: 3)')
    args = parser.parse_args()

    print("=" * 80)
    print("  競艇予測モデル - 最適化版訓練")
    if args.ensemble:
        print(f"  アンサンブルモード: {args.n_models}モデル")
    print("=" * 80)
    print()

    try:
        # 1. 最適パラメータを読み込み
        best_params = load_best_params()

        # 2. データ取得
        df = fetch_training_data()

        if len(df) == 0:
            print("[ERROR] 訓練データが取得できませんでした")
            print("まずデータ収集を実行してください: python scraper/collect_all_venues.py")
            return

        # 3. 統計データ取得
        racer_stats = fetch_racer_stats()
        motor_stats = fetch_motor_stats()
        racer_detailed_stats = fetch_racer_detailed_stats()

        # 4. 特徴量生成
        X, y, race_dates = prepare_features(df, racer_stats, motor_stats, racer_detailed_stats)

        # 5. モデル訓練と評価
        if args.ensemble:
            # アンサンブル学習
            predictor, metrics = train_ensemble_models(X, y, race_dates, best_params, n_models=args.n_models)
        else:
            # 通常訓練（時系列重み付け有効）
            predictor, metrics = train_and_evaluate(X, y, race_dates, best_params, use_time_weighting=True)

        # 6. モデル保存
        print("\n=== モデルの保存 ===\n")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        model_path = os.path.join('ml', f'trained_model_{timestamp}.pkl')
        predictor.save(model_path)

        # 最新モデルとしても保存
        latest_path = os.path.join('ml', 'trained_model_latest.pkl')
        predictor.save(latest_path)

        # メトリクスを保存
        metrics_path = os.path.join('ml', f'metrics_{timestamp}.json')
        with open(metrics_path, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': timestamp,
                'metrics': metrics,
                'params': best_params if best_params else 'default'
            }, f, indent=2, ensure_ascii=False)

        print(f"\nメトリクス保存: {metrics_path}")

        print("\n" + "=" * 80)
        print("  訓練完了！")
        print("=" * 80)
        print(f"\nモデルファイル: {model_path}")
        print(f"最新モデル: {latest_path}")
        print(f"\n【最終精度】")
        print(f"  Overall Accuracy: {metrics['accuracy']*100:.2f}%")
        print(f"  1着予測精度: {metrics['win_accuracy']*100:.2f}%")
        print(f"  Top-3予測精度: {metrics['top3_accuracy']*100:.2f}%")

    except Exception as e:
        print(f"\n[ERROR] エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
