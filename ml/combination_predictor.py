"""
連単・連複予測モジュール

着順予測モデルの出力（6艇×6着順の確率）から
各種舟券の組み合わせ確率を計算する
"""
import numpy as np
import itertools
from typing import List, Tuple, Dict


class CombinationPredictor:
    """連単・連複の組み合わせ確率を計算するクラス"""

    def __init__(self, prediction_probs):
        """
        Args:
            prediction_probs: 着順予測確率 (6艇 × 6着順)
                例: [[0.4, 0.3, 0.2, 0.05, 0.03, 0.02], ...] (6艇分)
        """
        self.probs = np.array(prediction_probs)
        if self.probs.shape != (6, 6):
            raise ValueError("prediction_probs must be (6, 6) shape")

    def predict_win(self) -> Dict[int, float]:
        """
        1着予測

        Returns:
            dict: {艇番: 1着確率}
        """
        win_probs = {}
        for boat_num in range(6):
            win_probs[boat_num + 1] = float(self.probs[boat_num, 0])

        return win_probs

    def predict_nirentan(self, top_n=20) -> List[Tuple[Tuple[int, int], float]]:
        """
        2連単予測（1-2着の順番）

        Args:
            top_n: 上位N組を返す

        Returns:
            list of ((艇1, 艇2), 確率)
        """
        combinations = []

        for boat1 in range(6):
            for boat2 in range(6):
                if boat1 == boat2:
                    continue

                # P(boat1=1着 AND boat2=2着)
                # 近似: P(boat1=1着) × P(boat2=2着|boat1=1着)
                # 簡易版: P(boat1=1着) × P(boat2=2着)

                prob_boat1_1st = self.probs[boat1, 0]
                prob_boat2_2nd = self.probs[boat2, 1]

                # より正確な計算（条件付き確率を考慮）
                # boat1が1着の条件下で、boat2が2着になる確率
                prob = prob_boat1_1st * prob_boat2_2nd

                combinations.append(((boat1 + 1, boat2 + 1), float(prob)))

        # 確率でソート
        combinations.sort(key=lambda x: x[1], reverse=True)

        # 正規化（確率の合計を1にする）
        total_prob = sum(prob for _, prob in combinations)
        if total_prob > 0:
            combinations = [
                (combo, prob / total_prob)
                for combo, prob in combinations
            ]

        return combinations[:top_n]

    def predict_sanrentan(self, top_n=20) -> List[Tuple[Tuple[int, int, int], float]]:
        """
        3連単予測（1-2-3着の順番）

        Args:
            top_n: 上位N組を返す

        Returns:
            list of ((艇1, 艇2, 艇3), 確率)
        """
        combinations = []

        for boat1 in range(6):
            for boat2 in range(6):
                if boat2 == boat1:
                    continue
                for boat3 in range(6):
                    if boat3 == boat1 or boat3 == boat2:
                        continue

                    # P(boat1=1着 AND boat2=2着 AND boat3=3着)
                    prob_boat1_1st = self.probs[boat1, 0]
                    prob_boat2_2nd = self.probs[boat2, 1]
                    prob_boat3_3rd = self.probs[boat3, 2]

                    prob = prob_boat1_1st * prob_boat2_2nd * prob_boat3_3rd

                    combinations.append(
                        ((boat1 + 1, boat2 + 1, boat3 + 1), float(prob))
                    )

        # 確率でソート
        combinations.sort(key=lambda x: x[1], reverse=True)

        # 正規化
        total_prob = sum(prob for _, prob in combinations)
        if total_prob > 0:
            combinations = [
                (combo, prob / total_prob)
                for combo, prob in combinations
            ]

        return combinations[:top_n]

    def predict_nirenpuku(self, top_n=15) -> List[Tuple[Tuple[int, int], float]]:
        """
        2連複予測（1-2着、順不同）

        Args:
            top_n: 上位N組を返す

        Returns:
            list of ((艇1, 艇2), 確率)  ※艇1 < 艇2
        """
        combination_probs = {}

        # 全ての2艇の組み合わせ
        for boat1, boat2 in itertools.combinations(range(6), 2):
            # (boat1, boat2)が1-2着に入る確率
            # = P(boat1=1着 AND boat2=2着) + P(boat2=1着 AND boat1=2着)

            prob1 = self.probs[boat1, 0] * self.probs[boat2, 1]
            prob2 = self.probs[boat2, 0] * self.probs[boat1, 1]

            total_prob = prob1 + prob2

            # 小さい艇番を前に
            key = (boat1 + 1, boat2 + 1) if boat1 < boat2 else (boat2 + 1, boat1 + 1)
            combination_probs[key] = float(total_prob)

        # リストに変換してソート
        combinations = list(combination_probs.items())
        combinations.sort(key=lambda x: x[1], reverse=True)

        # 正規化
        total_prob = sum(prob for _, prob in combinations)
        if total_prob > 0:
            combinations = [
                (combo, prob / total_prob)
                for combo, prob in combinations
            ]

        return combinations[:top_n]

    def predict_sanrenpuku(self, top_n=20) -> List[Tuple[Tuple[int, int, int], float]]:
        """
        3連複予測（1-2-3着、順不同）

        Args:
            top_n: 上位N組を返す

        Returns:
            list of ((艇1, 艇2, 艇3), 確率)  ※艇1 < 艇2 < 艇3
        """
        combination_probs = {}

        # 全ての3艇の組み合わせ
        for boats in itertools.combinations(range(6), 3):
            # この3艇が1-2-3着に入る確率
            # = すべての順列の確率の合計

            total_prob = 0.0
            for perm in itertools.permutations(boats):
                prob = (
                    self.probs[perm[0], 0] *
                    self.probs[perm[1], 1] *
                    self.probs[perm[2], 2]
                )
                total_prob += prob

            # 昇順にソート
            key = tuple(sorted([b + 1 for b in boats]))
            combination_probs[key] = float(total_prob)

        # リストに変換してソート
        combinations = list(combination_probs.items())
        combinations.sort(key=lambda x: x[1], reverse=True)

        # 正規化
        total_prob = sum(prob for _, prob in combinations)
        if total_prob > 0:
            combinations = [
                (combo, prob / total_prob)
                for combo, prob in combinations
            ]

        return combinations[:top_n]

    def get_all_predictions(self, top_n=20) -> Dict:
        """
        全ての予測結果を返す

        Args:
            top_n: 各予測タイプで返す上位N組

        Returns:
            dict: {
                'win': {艇番: 確率},
                'nirentan': [((艇1, 艇2), 確率), ...],
                'sanrentan': [((艇1, 艇2, 艇3), 確率), ...],
                'nirenpuku': [((艇1, 艇2), 確率), ...],
                'sanrenpuku': [((艇1, 艇2, 艇3), 確率), ...]
            }
        """
        return {
            'win': self.predict_win(),
            'nirentan': self.predict_nirentan(top_n),
            'sanrentan': self.predict_sanrentan(top_n),
            'nirenpuku': self.predict_nirenpuku(min(top_n, 15)),
            'sanrenpuku': self.predict_sanrenpuku(top_n)
        }


def format_predictions(predictions: Dict, verbose=True) -> str:
    """
    予測結果を整形して文字列で返す

    Args:
        predictions: get_all_predictions()の出力
        verbose: 詳細表示

    Returns:
        str: 整形された予測結果
    """
    lines = []

    # 1着予測
    lines.append("=== 1着予測 ===")
    win_probs = sorted(predictions['win'].items(), key=lambda x: x[1], reverse=True)
    for boat, prob in win_probs:
        lines.append(f"  {boat}号艇: {prob*100:5.2f}%")

    # 2連単
    lines.append("\n=== 2連単 Top 10 ===")
    for combo, prob in predictions['nirentan'][:10]:
        lines.append(f"  {combo[0]}-{combo[1]}: {prob*100:5.2f}%")

    # 3連単
    if verbose:
        lines.append("\n=== 3連単 Top 10 ===")
        for combo, prob in predictions['sanrentan'][:10]:
            lines.append(f"  {combo[0]}-{combo[1]}-{combo[2]}: {prob*100:5.2f}%")

    # 2連複
    lines.append("\n=== 2連複 Top 10 ===")
    for combo, prob in predictions['nirenpuku'][:10]:
        lines.append(f"  {combo[0]}={combo[1]}: {prob*100:5.2f}%")

    # 3連複
    if verbose:
        lines.append("\n=== 3連複 Top 10 ===")
        for combo, prob in predictions['sanrenpuku'][:10]:
            lines.append(f"  {combo[0]}={combo[1]}={combo[2]}: {prob*100:5.2f}%")

    return "\n".join(lines)


if __name__ == '__main__':
    # テスト実行
    print("=== Combination Predictor Test ===\n")

    # サンプル着順予測確率（6艇×6着順）
    sample_probs = [
        [0.40, 0.25, 0.15, 0.10, 0.07, 0.03],  # 1号艇
        [0.25, 0.30, 0.20, 0.15, 0.07, 0.03],  # 2号艇
        [0.15, 0.20, 0.25, 0.20, 0.15, 0.05],  # 3号艇
        [0.10, 0.12, 0.20, 0.25, 0.20, 0.13],  # 4号艇
        [0.07, 0.08, 0.12, 0.18, 0.30, 0.25],  # 5号艇
        [0.03, 0.05, 0.08, 0.12, 0.21, 0.51],  # 6号艇
    ]

    predictor = CombinationPredictor(sample_probs)
    predictions = predictor.get_all_predictions(top_n=20)

    print(format_predictions(predictions, verbose=True))
