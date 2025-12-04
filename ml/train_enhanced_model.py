"""
強化版モデル訓練スクリプト

race_entriesの実データを最大限活用
- 展示タイム、モーター2連対率、平均STなどを直接使用
- 時系列重み付けで最新データを重視
- 目標精度: 1着予測 45%
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
from sklearn.metrics import accuracy_score, log_loss, classification_report
import pickle

# 親ディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.enhanced_feature_engineer import EnhancedFeatureEngineer, fetch_training_data_enhanced
from ml.race_predictor import RacePredictor

load_dotenv()


def calculate_sample_weight(race_dates, half_life_years=2.0):
    """
    時系列重み付け: 新しいデータほど重要度を高くする
    半減期を2年に短縮してより最新データを重視
    """
    today = datetime.now()
    weights = []

    for date in race_dates:
        if not isinstance(date, pd.Timestamp):
            date = pd.Timestamp(date)

        days_ago = (today - date).days
        weight = np.exp(-days_ago / (365.25 * half_life_years))
        weights.append(weight)

    weights = np.array(weights)
    weights = weights * len(weights) / weights.sum()

    return weights


def prepare_enhanced_features(df):
    """強化版特徴量エンジニアリング"""
    print("\n=== 強化版特徴量の生成 ===\n")

    fe = EnhancedFeatureEngineer()

    all_features = []
    all_labels = []
    all_race_dates = []

    race_ids = df['race_id'].unique()
    total_races = len(race_ids)
    valid_races = 0

    for i, race_id in enumerate(race_ids):
        race_data = df[df['race_id'] == race_id].copy()

        if len(race_data) != 6:
            continue

        try:
            features = fe.create_features(race_data)
            labels = race_data['result_position'].values

            all_features.append(features)
            all_labels.append(labels)

            race_date = race_data['race_date'].iloc[0]
            all_race_dates.extend([race_date] * 6)

            valid_races += 1

            if valid_races % 1000 == 0:
                print(f"  処理済みレース数: {valid_races}/{total_races}")

        except Exception as e:
            print(f"  [Warning] Race {race_id} skipped: {e}")
            continue

    X = pd.concat(all_features, ignore_index=True)
    y = np.concatenate(all_labels)
    race_dates = pd.Series(all_race_dates)

    print(f"\n有効レース数: {valid_races}レース")
    print(f"特徴量サンプル数: {len(X)}件")
    print(f"特徴量の次元数: {X.shape[1]}次元")

    return X, y, race_dates


def calculate_win_accuracy(y_true, y_pred_proba):
    """1着予測精度を計算"""
    n_races = len(y_pred_proba) // 6
    correct = 0

    for i in range(n_races):
        race_start = i * 6
        race_end = race_start + 6

        race_probs = y_pred_proba[race_start:race_end, 0]
        race_true = y_true[race_start:race_end]

        predicted_winner = np.argmax(race_probs)
        actual_winner = np.where(race_true == 1)[0]

        if len(actual_winner) > 0 and predicted_winner == actual_winner[0]:
            correct += 1

    return correct / n_races if n_races > 0 else 0


def calculate_top3_accuracy(y_true, y_pred_proba):
    """Top-3予測精度（1着予測が上位3艇に入っている確率）"""
    n_races = len(y_pred_proba) // 6
    correct = 0

    for i in range(n_races):
        race_start = i * 6
        race_end = race_start + 6

        race_probs = y_pred_proba[race_start:race_end, 0]
        race_true = y_true[race_start:race_end]

        top3_predicted = np.argsort(race_probs)[-3:]
        actual_winner = np.where(race_true == 1)[0]

        if len(actual_winner) > 0 and actual_winner[0] in top3_predicted:
            correct += 1

    return correct / n_races if n_races > 0 else 0


def calculate_exacta_accuracy(y_true, y_pred_proba, top_n=5):
    """2連単的中率（上位N組での的中率）"""
    n_races = len(y_pred_proba) // 6
    correct = 0

    for i in range(n_races):
        race_start = i * 6
        race_end = race_start + 6

        race_probs = y_pred_proba[race_start:race_end]
        race_true = y_true[race_start:race_end]

        # 実際の1着・2着
        actual_1st = np.where(race_true == 1)[0]
        actual_2nd = np.where(race_true == 2)[0]

        if len(actual_1st) == 0 or len(actual_2nd) == 0:
            continue

        actual_1st = actual_1st[0]
        actual_2nd = actual_2nd[0]

        # 2連単の組み合わせを予測確率でソート
        exacta_probs = []
        for b1 in range(6):
            for b2 in range(6):
                if b1 != b2:
                    prob = race_probs[b1, 0] * race_probs[b2, 1]
                    exacta_probs.append(((b1, b2), prob))

        exacta_probs.sort(key=lambda x: x[1], reverse=True)

        # 上位N組に実際の組み合わせがあるか
        top_n_combos = [combo for combo, _ in exacta_probs[:top_n]]
        if (actual_1st, actual_2nd) in top_n_combos:
            correct += 1

    return correct / n_races if n_races > 0 else 0


def train_enhanced_model(X, y, race_dates, best_params=None):
    """強化版モデル訓練"""
    print("\n=== 強化版モデルの訓練 ===\n")

    y_transformed = y - 1

    # 時系列重み付け
    sample_weights = calculate_sample_weight(race_dates, half_life_years=2.0)
    print(f"時系列重み付け: 半減期2年")
    print(f"  最新データの平均重み: {sample_weights[race_dates == race_dates.max()].mean():.2f}")

    # 訓練・検証データに分割
    X_train, X_test, y_train, y_test, weights_train, _ = train_test_split(
        X, y_transformed, sample_weights,
        test_size=0.2, random_state=42, stratify=y_transformed
    )

    # ハイパーパラメータ
    if best_params is None:
        best_params = {
            'max_depth': 8,
            'learning_rate': 0.05,
            'n_estimators': 500,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'min_child_weight': 3,
            'gamma': 0.1,
            'reg_alpha': 0.1,
            'reg_lambda': 1.0,
        }

    model = xgb.XGBClassifier(
        objective='multi:softprob',
        num_class=6,
        random_state=42,
        eval_metric='mlogloss',
        early_stopping_rounds=50,
        **best_params
    )

    print(f"訓練データ: {len(X_train)}件")
    print(f"検証データ: {len(X_test)}件\n")

    # 訓練
    eval_set = [(X_train, y_train), (X_test, y_test)]
    model.fit(
        X_train, y_train,
        sample_weight=weights_train,
        eval_set=eval_set,
        verbose=50
    )

    # 予測
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)

    # 評価
    print("\n" + "=" * 60)
    print("  評価結果")
    print("=" * 60)

    accuracy = accuracy_score(y_test, y_pred)
    logloss = log_loss(y_test, y_pred_proba)

    y_test_original = y_test + 1
    win_acc = calculate_win_accuracy(y_test_original, y_pred_proba)
    top3_acc = calculate_top3_accuracy(y_test_original, y_pred_proba)
    exacta_acc = calculate_exacta_accuracy(y_test_original, y_pred_proba, top_n=5)

    print(f"\n【基本指標】")
    print(f"  Overall Accuracy: {accuracy*100:.2f}%")
    print(f"  Log Loss: {logloss:.4f}")

    print(f"\n【重要指標】")
    print(f"  1着予測精度: {win_acc*100:.2f}%")
    print(f"  Top-3予測精度: {top3_acc*100:.2f}%")
    print(f"  2連単Top5的中率: {exacta_acc*100:.2f}%")

    # 目標との比較
    print(f"\n[目標との比較]")
    target_win_acc = 0.45
    if win_acc >= target_win_acc:
        print(f"  [OK] 1着予測: {win_acc*100:.2f}% >= 目標 {target_win_acc*100:.0f}%")
    else:
        print(f"  [!] 1着予測: {win_acc*100:.2f}% < 目標 {target_win_acc*100:.0f}%")
        print(f"      -> データ量増加で改善見込み（現在約{len(X)//6}レース）")

    # 特徴量重要度
    print(f"\n【特徴量重要度 Top 15】")
    importance = model.feature_importances_
    indices = np.argsort(importance)[::-1]

    for i in range(min(15, len(indices))):
        idx = indices[i]
        print(f"  {i+1:2d}. {X.columns[idx]:25s}: {importance[idx]:.4f}")

    # RacePredictorにラップ
    predictor = RacePredictor()
    predictor.model = model
    predictor.feature_names = X.columns.tolist()

    return predictor, {
        'accuracy': accuracy,
        'log_loss': logloss,
        'win_accuracy': win_acc,
        'top3_accuracy': top3_acc,
        'exacta_top5_accuracy': exacta_acc
    }


def main():
    """メイン処理"""
    print("=" * 70)
    print("  競艇予測モデル - 強化版訓練")
    print("  目標: 1着予測精度 45%")
    print("=" * 70)
    print()

    try:
        # 1. データ取得
        df = fetch_training_data_enhanced()

        if len(df) == 0:
            print("[ERROR] 訓練データが取得できませんでした")
            return

        # 2. 特徴量生成
        X, y, race_dates = prepare_enhanced_features(df)

        # 3. 最適パラメータを読み込み（あれば）
        best_params = None
        params_path = 'ml/best_params_latest.json'
        if os.path.exists(params_path):
            with open(params_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                best_params = data.get('best_params')
                print(f"最適パラメータを読み込み: {params_path}")

        # 4. モデル訓練
        predictor, metrics = train_enhanced_model(X, y, race_dates, best_params)

        # 5. モデル保存
        print("\n=== モデルの保存 ===\n")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        model_path = os.path.join('ml', f'enhanced_model_{timestamp}.pkl')
        predictor.save(model_path)

        # 最新モデルとしても保存
        latest_path = os.path.join('ml', 'trained_model_latest.pkl')
        predictor.save(latest_path)

        # メトリクスを保存
        metrics_path = os.path.join('ml', f'enhanced_metrics_{timestamp}.json')
        with open(metrics_path, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': timestamp,
                'model_type': 'enhanced',
                'data_size': len(X) // 6,
                'metrics': metrics,
            }, f, indent=2, ensure_ascii=False)

        print(f"モデル保存: {model_path}")
        print(f"最新モデル: {latest_path}")
        print(f"メトリクス: {metrics_path}")

        print("\n" + "=" * 70)
        print("  訓練完了！")
        print("=" * 70)
        print(f"\n【最終精度】")
        print(f"  1着予測: {metrics['win_accuracy']*100:.2f}%")
        print(f"  Top-3予測: {metrics['top3_accuracy']*100:.2f}%")
        print(f"  2連単Top5: {metrics['exacta_top5_accuracy']*100:.2f}%")

        # データ量増加による改善見込み
        current_races = len(X) // 6
        if current_races < 50000:
            print(f"\n【精度向上の見込み】")
            print(f"  現在のデータ量: {current_races:,}レース")
            print(f"  データ収集完了後: 約160,000レース")
            print(f"  期待される1着精度: 40-50%")

    except Exception as e:
        print(f"\n[ERROR] エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
