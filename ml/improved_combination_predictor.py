"""
改良版連単・連複予測モジュール

着順予測モデルの出力から各種舟券の組み合わせ確率を計算
- 正規化された確率計算
- 全賭け式対応（単勝、2連複、2連単、3連複、3連単）
- 期待値計算対応
"""
import numpy as np
import itertools
from typing import List, Tuple, Dict, Optional


class ImprovedCombinationPredictor:
    """改良版: 連単・連複の組み合わせ確率を計算"""

    def __init__(self, prediction_probs: np.ndarray):
        """
        Args:
            prediction_probs: 着順予測確率 (6艇 x 6着順)
                各行は1艇の各着順確率 [1着確率, 2着確率, ..., 6着確率]
        """
        self.probs = np.array(prediction_probs)
        if self.probs.shape != (6, 6):
            raise ValueError("prediction_probs must be (6, 6) shape")

        # 確率を正規化（各艇の着順確率の合計が1になるように）
        row_sums = self.probs.sum(axis=1, keepdims=True)
        self.probs = np.where(row_sums > 0, self.probs / row_sums, 1/6)

    def predict_win(self) -> Dict[int, float]:
        """
        単勝予測（1着を当てる）

        Returns:
            dict: {艇番: 1着確率}
        """
        win_probs = {}
        total = 0
        for boat_num in range(6):
            prob = float(self.probs[boat_num, 0])
            win_probs[boat_num + 1] = prob
            total += prob

        # 正規化
        if total > 0:
            win_probs = {k: v / total for k, v in win_probs.items()}

        return win_probs

    def predict_nirentan(self, top_n: int = 30) -> List[Dict]:
        """
        2連単予測（1-2着を順番通り当てる）

        Returns:
            list of dict: [{'combo': (艇1, 艇2), 'prob': 確率}, ...]
        """
        combinations = []

        for boat1 in range(6):
            for boat2 in range(6):
                if boat1 == boat2:
                    continue

                # P(boat1=1着) * P(boat2=2着)
                # より正確には条件付き確率だが、近似として独立確率を使用
                prob = self.probs[boat1, 0] * self.probs[boat2, 1]

                combinations.append({
                    'combo': (boat1 + 1, boat2 + 1),
                    'prob': float(prob),
                    'display': f"{boat1 + 1}-{boat2 + 1}"
                })

        # 確率でソート
        combinations.sort(key=lambda x: x['prob'], reverse=True)

        # 正規化
        total = sum(c['prob'] for c in combinations)
        if total > 0:
            for c in combinations:
                c['prob'] = c['prob'] / total

        return combinations[:top_n]

    def predict_sanrentan(self, top_n: int = 30) -> List[Dict]:
        """
        3連単予測（1-2-3着を順番通り当てる）

        Returns:
            list of dict: [{'combo': (艇1, 艇2, 艇3), 'prob': 確率}, ...]
        """
        combinations = []

        for boat1 in range(6):
            for boat2 in range(6):
                if boat2 == boat1:
                    continue
                for boat3 in range(6):
                    if boat3 == boat1 or boat3 == boat2:
                        continue

                    prob = (
                        self.probs[boat1, 0] *
                        self.probs[boat2, 1] *
                        self.probs[boat3, 2]
                    )

                    combinations.append({
                        'combo': (boat1 + 1, boat2 + 1, boat3 + 1),
                        'prob': float(prob),
                        'display': f"{boat1 + 1}-{boat2 + 1}-{boat3 + 1}"
                    })

        combinations.sort(key=lambda x: x['prob'], reverse=True)

        total = sum(c['prob'] for c in combinations)
        if total > 0:
            for c in combinations:
                c['prob'] = c['prob'] / total

        return combinations[:top_n]

    def predict_nirenpuku(self, top_n: int = 15) -> List[Dict]:
        """
        2連複予測（1-2着を順不同で当てる）

        Returns:
            list of dict: [{'combo': (艇1, 艇2), 'prob': 確率}, ...]
        """
        combinations = []

        for boat1, boat2 in itertools.combinations(range(6), 2):
            # P(boat1, boat2が1-2着) = P(boat1=1着,boat2=2着) + P(boat2=1着,boat1=2着)
            prob = (
                self.probs[boat1, 0] * self.probs[boat2, 1] +
                self.probs[boat2, 0] * self.probs[boat1, 1]
            )

            combinations.append({
                'combo': (boat1 + 1, boat2 + 1),
                'prob': float(prob),
                'display': f"{boat1 + 1}={boat2 + 1}"
            })

        combinations.sort(key=lambda x: x['prob'], reverse=True)

        total = sum(c['prob'] for c in combinations)
        if total > 0:
            for c in combinations:
                c['prob'] = c['prob'] / total

        return combinations[:top_n]

    def predict_sanrenpuku(self, top_n: int = 20) -> List[Dict]:
        """
        3連複予測（1-2-3着を順不同で当てる）

        Returns:
            list of dict: [{'combo': (艇1, 艇2, 艇3), 'prob': 確率}, ...]
        """
        combinations = []

        for boats in itertools.combinations(range(6), 3):
            # 3艇が1-2-3着に入る全順列の確率の合計
            prob = 0.0
            for perm in itertools.permutations(boats):
                prob += (
                    self.probs[perm[0], 0] *
                    self.probs[perm[1], 1] *
                    self.probs[perm[2], 2]
                )

            combinations.append({
                'combo': tuple(b + 1 for b in sorted(boats)),
                'prob': float(prob),
                'display': f"{boats[0]+1}={boats[1]+1}={boats[2]+1}"
            })

        combinations.sort(key=lambda x: x['prob'], reverse=True)

        total = sum(c['prob'] for c in combinations)
        if total > 0:
            for c in combinations:
                c['prob'] = c['prob'] / total

        return combinations[:top_n]

    def get_all_predictions(self, top_n: int = 10) -> Dict:
        """
        全賭け式の予測結果を返す

        Args:
            top_n: 各賭け式で返す上位N組

        Returns:
            dict: {
                'tansho': {...},      # 単勝
                'nirenpuku': [...],   # 2連複
                'nirentan': [...],    # 2連単
                'sanrenpuku': [...],  # 3連複
                'sanrentan': [...]    # 3連単
            }
        """
        return {
            'tansho': self.predict_win(),
            'nirenpuku': self.predict_nirenpuku(top_n),
            'nirentan': self.predict_nirentan(top_n),
            'sanrenpuku': self.predict_sanrenpuku(top_n),
            'sanrentan': self.predict_sanrentan(top_n),
        }

    def calculate_expected_value(
        self,
        bet_type: str,
        odds: Dict,
        top_n: int = 10
    ) -> List[Dict]:
        """
        期待値を計算

        Args:
            bet_type: 'tansho', 'nirenpuku', 'nirentan', 'sanrenpuku', 'sanrentan'
            odds: オッズデータ {組み合わせ文字列: オッズ値}
            top_n: 上位N組を返す

        Returns:
            list of dict: [{'combo': ..., 'prob': ..., 'odds': ..., 'ev': ...}, ...]
        """
        if bet_type == 'tansho':
            predictions = [
                {'combo': (k,), 'prob': v, 'display': str(k)}
                for k, v in self.predict_win().items()
            ]
        elif bet_type == 'nirenpuku':
            predictions = self.predict_nirenpuku(30)
        elif bet_type == 'nirentan':
            predictions = self.predict_nirentan(30)
        elif bet_type == 'sanrenpuku':
            predictions = self.predict_sanrenpuku(20)
        elif bet_type == 'sanrentan':
            predictions = self.predict_sanrentan(30)
        else:
            raise ValueError(f"Unknown bet type: {bet_type}")

        # 期待値を計算
        for pred in predictions:
            display = pred['display']
            if display in odds:
                pred['odds'] = odds[display]
                pred['ev'] = pred['prob'] * odds[display]
            else:
                pred['odds'] = None
                pred['ev'] = None

        # 期待値でソート（期待値がないものは後ろに）
        predictions.sort(
            key=lambda x: x['ev'] if x['ev'] is not None else -1,
            reverse=True
        )

        return predictions[:top_n]


def format_all_predictions(predictions: Dict, max_items: int = 10) -> str:
    """
    全予測結果を整形して文字列で返す

    Args:
        predictions: get_all_predictions()の出力
        max_items: 各賭け式で表示する最大数

    Returns:
        str: 整形された予測結果
    """
    lines = []

    # 単勝
    lines.append("=" * 50)
    lines.append("【単勝】1着を当てる")
    lines.append("=" * 50)
    tansho = sorted(predictions['tansho'].items(), key=lambda x: x[1], reverse=True)
    for boat, prob in tansho:
        bar = "#" * int(prob * 50)
        lines.append(f"  {boat}号艇: {prob*100:5.2f}% {bar}")

    # 2連複
    lines.append("\n" + "=" * 50)
    lines.append("【2連複】1-2着を順不同で当てる")
    lines.append("=" * 50)
    for item in predictions['nirenpuku'][:max_items]:
        lines.append(f"  {item['display']:8s}: {item['prob']*100:5.2f}%")

    # 2連単
    lines.append("\n" + "=" * 50)
    lines.append("【2連単】1-2着を順番通り当てる")
    lines.append("=" * 50)
    for item in predictions['nirentan'][:max_items]:
        lines.append(f"  {item['display']:8s}: {item['prob']*100:5.2f}%")

    # 3連複
    lines.append("\n" + "=" * 50)
    lines.append("【3連複】1-2-3着を順不同で当てる")
    lines.append("=" * 50)
    for item in predictions['sanrenpuku'][:max_items]:
        lines.append(f"  {item['display']:8s}: {item['prob']*100:5.2f}%")

    # 3連単
    lines.append("\n" + "=" * 50)
    lines.append("【3連単】1-2-3着を順番通り当てる")
    lines.append("=" * 50)
    for item in predictions['sanrentan'][:max_items]:
        lines.append(f"  {item['display']:8s}: {item['prob']*100:5.2f}%")

    return "\n".join(lines)


if __name__ == '__main__':
    # テスト実行
    print("=== ImprovedCombinationPredictor Test ===\n")

    # サンプル着順予測確率（6艇x6着順）
    # 1号艇が強く、6号艇が弱い想定
    sample_probs = np.array([
        [0.45, 0.25, 0.15, 0.08, 0.05, 0.02],  # 1号艇（強い）
        [0.20, 0.30, 0.22, 0.15, 0.08, 0.05],  # 2号艇
        [0.15, 0.20, 0.25, 0.20, 0.12, 0.08],  # 3号艇
        [0.10, 0.12, 0.18, 0.25, 0.20, 0.15],  # 4号艇
        [0.07, 0.08, 0.12, 0.18, 0.30, 0.25],  # 5号艇
        [0.03, 0.05, 0.08, 0.14, 0.25, 0.45],  # 6号艇（弱い）
    ])

    predictor = ImprovedCombinationPredictor(sample_probs)
    predictions = predictor.get_all_predictions(top_n=10)

    print(format_all_predictions(predictions))

    # 期待値テスト（オッズがある場合）
    print("\n\n=== 期待値計算テスト ===")
    sample_odds = {
        "1": 1.5, "2": 4.0, "3": 6.0, "4": 10.0, "5": 15.0, "6": 30.0
    }
    ev_results = predictor.calculate_expected_value('tansho', sample_odds)
    print("\n【単勝 期待値順】")
    for item in ev_results:
        if item['odds'] is not None:
            print(f"  {item['combo'][0]}号艇: 確率{item['prob']*100:.1f}% x オッズ{item['odds']:.1f} = 期待値{item['ev']:.2f}")
