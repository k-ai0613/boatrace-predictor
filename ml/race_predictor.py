import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, log_loss
import pickle
import numpy as np
import pandas as pd


class RacePredictor:
    """レース結果を予測するクラス"""

    def __init__(self):
        self.model = None
        self.feature_names = None

    def train(self, training_data, labels):
        """
        モデルを訓練

        Args:
            training_data: 特徴量（DataFrame）
            labels: 着順ラベル (1-6)
        """
        X = training_data
        y = labels - 1  # 0-5に変換（XGBoostのため）

        # 訓練・検証データに分割
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # XGBoostで多クラス分類
        self.model = xgb.XGBClassifier(
            objective='multi:softprob',
            num_class=6,              # 1-6着
            max_depth=8,
            learning_rate=0.05,
            n_estimators=300,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric='mlogloss'
        )

        # 訓練
        eval_set = [(X_train, y_train), (X_test, y_test)]
        self.model.fit(
            X_train, y_train,
            eval_set=eval_set,
            verbose=True
        )

        # 評価
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)

        y_pred_proba = self.model.predict_proba(X_test)
        logloss = log_loss(y_test, y_pred_proba)

        print(f"\n=== Model Evaluation ===")
        print(f"Accuracy: {accuracy:.3f}")
        print(f"Log Loss: {logloss:.3f}")

        # 特徴量重要度
        self._print_feature_importance(X.columns)

        self.feature_names = X.columns.tolist()

    def predict_probabilities(self, race_features):
        """
        各艇の着順確率を予測

        Args:
            race_features: 1レース6艇分の特徴量（DataFrame）

        Returns:
            numpy.ndarray: 確率行列 (6艇 × 6着順)
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        probs = self.model.predict_proba(race_features)
        return probs  # shape: (6, 6)

    def recommend_bets(self, probabilities, odds_data=None):
        """
        推奨購入券種を計算

        Args:
            probabilities: 着順確率 (6艇 × 6着順)
            odds_data: オッズデータ（オプション）

        Returns:
            list: 推奨購入券種のリスト
        """
        recommendations = []

        # 1. 単勝
        for boat in range(6):
            win_prob = probabilities[boat][0]  # 1着確率

            if odds_data and 'win' in odds_data:
                expected_value = win_prob * odds_data['win'][boat]
            else:
                expected_value = win_prob

            if win_prob > 0.25:  # 25%以上の確率
                recommendations.append({
                    'type': '単勝',
                    'bet': f"{boat + 1}",
                    'probability': win_prob,
                    'expected_value': expected_value if odds_data else None,
                    'confidence': self._calculate_confidence(win_prob)
                })

        # 2. 2連単
        for boat1 in range(6):
            for boat2 in range(6):
                if boat1 == boat2:
                    continue

                # 1着・2着の同時確率
                prob = probabilities[boat1][0] * probabilities[boat2][1]

                if odds_data and 'exacta' in odds_data:
                    expected_value = prob * odds_data['exacta'][boat1][boat2]
                else:
                    expected_value = prob

                if prob > 0.10:  # 10%以上
                    recommendations.append({
                        'type': '2連単',
                        'bet': f"{boat1 + 1}-{boat2 + 1}",
                        'probability': prob,
                        'expected_value': expected_value if odds_data else None,
                        'confidence': self._calculate_confidence(prob)
                    })

        # 3. 3連単
        for boat1 in range(6):
            for boat2 in range(6):
                for boat3 in range(6):
                    if boat1 == boat2 or boat2 == boat3 or boat1 == boat3:
                        continue

                    prob = (probabilities[boat1][0] *
                           probabilities[boat2][1] *
                           probabilities[boat3][2])

                    if prob > 0.05:  # 5%以上
                        recommendations.append({
                            'type': '3連単',
                            'bet': f"{boat1 + 1}-{boat2 + 1}-{boat3 + 1}",
                            'probability': prob,
                            'expected_value': None,
                            'confidence': self._calculate_confidence(prob)
                        })

        # 4. 2連複
        for boat1 in range(6):
            for boat2 in range(boat1 + 1, 6):
                # boat1-boat2 または boat2-boat1 の確率
                prob = (probabilities[boat1][0] * probabilities[boat2][1] +
                       probabilities[boat2][0] * probabilities[boat1][1])

                if prob > 0.15:
                    recommendations.append({
                        'type': '2連複',
                        'bet': f"{boat1 + 1}={boat2 + 1}",
                        'probability': prob,
                        'expected_value': None,
                        'confidence': self._calculate_confidence(prob)
                    })

        # 期待値または確率でソート
        if odds_data:
            recommendations.sort(
                key=lambda x: x['expected_value'] or 0,
                reverse=True
            )
        else:
            recommendations.sort(
                key=lambda x: x['probability'],
                reverse=True
            )

        return recommendations

    def _calculate_confidence(self, probability):
        """信頼度を計算"""
        if probability > 0.5:
            return "高"
        elif probability > 0.3:
            return "中"
        else:
            return "低"

    def _print_feature_importance(self, feature_names):
        """特徴量重要度を表示"""
        importance = self.model.feature_importances_
        indices = np.argsort(importance)[::-1]

        print("\n=== Feature Importance (Top 20) ===")
        for i in range(min(20, len(indices))):
            idx = indices[i]
            print(f"{i+1}. {feature_names[idx]}: {importance[idx]:.4f}")

    def save(self, filepath):
        """モデルを保存"""
        model_data = {
            'model': self.model,
            'feature_names': self.feature_names
        }
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        print(f"Model saved to {filepath}")

    def load(self, filepath):
        """モデルを読み込み"""
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        self.model = model_data['model']
        self.feature_names = model_data['feature_names']
        print(f"Model loaded from {filepath}")
