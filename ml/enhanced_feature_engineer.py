"""
強化版特徴量エンジニアリング

race_entriesテーブルの実データを最大限活用して特徴量を生成
- 勝率、2連対率、3連対率
- モーター2連対率、3連対率
- 展示タイム（非常に重要）
- 平均スタートタイミング
- 会場・コース特性
"""
import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()


class EnhancedFeatureEngineer:
    """race_entriesの実データを活用した特徴量エンジニアリング"""

    # 会場IDと名前のマッピング
    VENUE_NAMES = {
        1: '桐生', 2: '戸田', 3: '江戸川', 4: '平和島', 5: '多摩川', 6: '浜名湖',
        7: '蒲郡', 8: '常滑', 9: '津', 10: '三国', 11: '琵琶湖', 12: '住之江',
        13: '尼崎', 14: '鳴門', 15: '丸亀', 16: '児島', 17: '宮島', 18: '徳山',
        19: '下関', 20: '若松', 21: '芦屋', 22: '福岡', 23: '唐津', 24: '大村'
    }

    # 会場別のコース1勝率（統計データ）
    VENUE_COURSE1_WIN_RATE = {
        1: 0.52, 2: 0.48, 3: 0.42, 4: 0.49, 5: 0.53, 6: 0.55,
        7: 0.54, 8: 0.54, 9: 0.52, 10: 0.52, 11: 0.50, 12: 0.54,
        13: 0.55, 14: 0.57, 15: 0.56, 16: 0.55, 17: 0.56, 18: 0.58,
        19: 0.55, 20: 0.54, 21: 0.60, 22: 0.52, 23: 0.55, 24: 0.57
    }

    # コース別の平均勝率
    COURSE_WIN_RATE = {
        1: 0.54, 2: 0.14, 3: 0.12, 4: 0.11, 5: 0.06, 6: 0.03
    }

    def __init__(self, historical_stats=None):
        """
        Args:
            historical_stats: 事前計算した統計データ（オプション）
        """
        self.historical_stats = historical_stats

    def create_features(self, race_data):
        """
        1レース分の特徴量を生成（race_entriesの実データを活用）

        Args:
            race_data: 1レースの6艇分のデータ（DataFrame）
                必須カラム: boat_number, venue_id
                オプション: win_rate, motor_rate_2, exhibition_time, average_st, etc.

        Returns:
            DataFrame: 特徴量（6行 × 特徴量数列）
        """
        features_list = []

        for idx, boat in race_data.iterrows():
            features = {}

            # 1. 基本特徴量（実データ優先）
            features.update(self._basic_features(boat))

            # 2. モーター特徴量
            features.update(self._motor_features(boat))

            # 3. 展示タイム特徴量（非常に重要）
            features.update(self._exhibition_features(boat))

            # 4. スタート特徴量
            features.update(self._start_features(boat))

            # 5. コース特徴量
            features.update(self._course_features(boat))

            # 6. レース内相対特徴量
            features.update(self._relative_features(boat, race_data))

            # 7. 詳細統計特徴量（racer_detailed_statsから）
            features.update(self._detailed_stats_features(boat))

            # 8. 複合特徴量
            features.update(self._composite_features(features))

            features_list.append(features)

        return pd.DataFrame(features_list)

    def _basic_features(self, boat):
        """基本的な選手・艇関連の特徴量"""
        # race_entriesの実データを使用（なければデフォルト値）
        win_rate = boat.get('win_rate')
        if win_rate is None or pd.isna(win_rate):
            win_rate = boat.get('racer_win_rate', 5.0)

        place_rate_2 = boat.get('place_rate_2')
        if place_rate_2 is None or pd.isna(place_rate_2):
            place_rate_2 = 30.0

        place_rate_3 = boat.get('place_rate_3')
        if place_rate_3 is None or pd.isna(place_rate_3):
            place_rate_3 = 50.0

        # 級別スコア
        grade = boat.get('racer_grade', boat.get('grade', 'B1'))
        grade_score = {'A1': 4, 'A2': 3, 'B1': 2, 'B2': 1}.get(grade, 2)

        return {
            'win_rate': float(win_rate),
            'place_rate_2': float(place_rate_2),
            'place_rate_3': float(place_rate_3),
            'grade_score': grade_score,
            'is_a_class': 1 if grade in ['A1', 'A2'] else 0,
            'is_a1': 1 if grade == 'A1' else 0,
        }

    def _motor_features(self, boat):
        """モーター関連の特徴量"""
        motor_rate_2 = boat.get('motor_rate_2')
        if motor_rate_2 is None or pd.isna(motor_rate_2):
            motor_rate_2 = boat.get('motor_second_rate', 30.0)

        motor_rate_3 = boat.get('motor_rate_3')
        if motor_rate_3 is None or pd.isna(motor_rate_3):
            motor_rate_3 = boat.get('motor_third_rate', 50.0)

        # ボート2連対率も使用（あれば）
        boat_rate_2 = boat.get('boat_rate_2')
        if boat_rate_2 is None or pd.isna(boat_rate_2):
            boat_rate_2 = 30.0

        return {
            'motor_rate_2': float(motor_rate_2),
            'motor_rate_3': float(motor_rate_3),
            'boat_rate_2': float(boat_rate_2),
            'motor_quality': 1 if motor_rate_2 > 40 else 0,  # 良いモーター
            'motor_poor': 1 if motor_rate_2 < 25 else 0,  # 悪いモーター
        }

    def _exhibition_features(self, boat):
        """展示タイム関連の特徴量（予測に非常に重要）"""
        exhibition_time = boat.get('exhibition_time')
        if exhibition_time is None or pd.isna(exhibition_time):
            exhibition_time = 6.80  # 平均的な展示タイム

        # 展示ターンタイム・直線タイム（あれば）
        turn_time = boat.get('exhibition_turn_time')
        if turn_time is None or pd.isna(turn_time):
            turn_time = 5.50

        straight_time = boat.get('exhibition_straight_time')
        if straight_time is None or pd.isna(straight_time):
            straight_time = 7.50

        return {
            'exhibition_time': float(exhibition_time),
            'exhibition_turn_time': float(turn_time),
            'exhibition_straight_time': float(straight_time),
            # 展示タイムが速いほどポイント高い（6.7秒が基準）
            'exhibition_quality': max(0, (6.80 - exhibition_time) * 10),
        }

    def _start_features(self, boat):
        """スタート関連の特徴量"""
        average_st = boat.get('average_st')
        if average_st is None or pd.isna(average_st):
            average_st = boat.get('avg_start_timing', 0.15)

        flying_count = boat.get('flying_count', 0) or 0
        late_count = boat.get('late_count', 0) or 0

        return {
            'average_st': float(average_st),
            'flying_count': int(flying_count),
            'late_count': int(late_count),
            # スタートが速いほどポイント高い（0.15が基準）
            'start_quality': max(0, (0.18 - average_st) * 50),
            'start_risk': flying_count + late_count * 0.5,
        }

    def _course_features(self, boat):
        """コース関連の特徴量"""
        venue_id = boat.get('venue_id', 1)
        if venue_id is None or pd.isna(venue_id):
            venue_id = 1
        venue_id = int(venue_id)

        boat_number = boat.get('boat_number', 1)
        if boat_number is None or pd.isna(boat_number):
            boat_number = 1
        boat_number = int(boat_number)

        # スタート展示のコース（枠番と同じことが多い）
        course = boat.get('course')
        if course is None or pd.isna(course):
            course = boat.get('actual_course')
        if course is None or pd.isna(course):
            course = boat_number
        course = int(course)

        # 会場のコース1勝率
        venue_course1_rate = self.VENUE_COURSE1_WIN_RATE.get(venue_id, 0.54)

        # コース別の平均勝率
        course_win_rate = self.COURSE_WIN_RATE.get(course, 0.10)

        return {
            'boat_number': boat_number,
            'course': course,
            'venue_id': venue_id,
            'is_course_1': 1 if course == 1 else 0,
            'is_inner_course': 1 if course <= 3 else 0,
            'course_win_rate': course_win_rate,
            'venue_course1_rate': venue_course1_rate,
            # インコースの優位性（コース1が特に有利）
            'course_advantage': max(0, (4 - course) * 0.1),
        }

    def _relative_features(self, boat, race_data):
        """レース内での相対的な特徴量"""
        # 展示タイムの相対順位
        exhibition_time = boat.get('exhibition_time')
        if exhibition_time is None or pd.isna(exhibition_time):
            exhibition_time = 6.80

        all_exhibition = race_data['exhibition_time'].fillna(6.80).values
        exhibition_rank = sum(1 for t in all_exhibition if t < exhibition_time) + 1

        # 勝率の相対順位
        win_rate = boat.get('win_rate')
        if win_rate is None or pd.isna(win_rate):
            win_rate = 5.0

        all_win_rate = race_data['win_rate'].fillna(5.0).values
        win_rate_rank = sum(1 for r in all_win_rate if r > win_rate) + 1

        return {
            'exhibition_rank': exhibition_rank,
            'win_rate_rank': win_rate_rank,
            'is_top_exhibition': 1 if exhibition_rank == 1 else 0,
            'is_top_win_rate': 1 if win_rate_rank == 1 else 0,
        }

    def _detailed_stats_features(self, boat):
        """詳細統計特徴量（racer_detailed_statsから）"""
        features = {}

        # 選手の総合成績
        racer_win_rate = boat.get('racer_overall_win_rate')
        features['racer_win_rate'] = float(racer_win_rate) if racer_win_rate and not pd.isna(racer_win_rate) else 0.0

        features['racer_second_rate'] = float(boat.get('racer_2nd_rate', 0)) if boat.get('racer_2nd_rate') and not pd.isna(boat.get('racer_2nd_rate')) else 0.0
        features['racer_third_rate'] = float(boat.get('racer_3rd_rate', 0)) if boat.get('racer_3rd_rate') and not pd.isna(boat.get('racer_3rd_rate')) else 0.0

        # 選手の平均ST
        racer_avg_st = boat.get('racer_avg_st')
        features['racer_avg_st'] = float(racer_avg_st) if racer_avg_st and not pd.isna(racer_avg_st) else 0.15

        # SG出場回数
        sg_appearances = boat.get('sg_appearances')
        features['sg_appearances'] = int(sg_appearances) if sg_appearances and not pd.isna(sg_appearances) else 0
        features['high_grade_experience'] = 1 if features['sg_appearances'] > 0 else 0

        # フライング・出遅れ
        features['late_start_count'] = int(boat.get('racer_late_count', 0) or 0)
        features['penalty_risk_score'] = features['late_start_count'] * 0.5

        # グレード別成績（grade_stats）
        grade_stats = boat.get('grade_stats')
        if grade_stats and isinstance(grade_stats, dict):
            sg_stats = grade_stats.get('SG', {})
            features['sg_win_rate'] = float(sg_stats.get('win_rate', 0))
            features['sg_experience_score'] = 1 if sg_stats.get('races', 0) > 0 else 0

            g1_stats = grade_stats.get('G1', {})
            features['g1_win_rate'] = float(g1_stats.get('win_rate', 0))

            g2_stats = grade_stats.get('G2', {})
            features['g2_win_rate'] = float(g2_stats.get('win_rate', 0))

            g3_stats = grade_stats.get('G3', {})
            features['g3_win_rate'] = float(g3_stats.get('win_rate', 0))

            features['racer_grade_score'] = (
                features['sg_win_rate'] * 2.0 +
                features['g1_win_rate'] * 1.5 +
                features['g2_win_rate'] * 1.2 +
                features['g3_win_rate'] * 1.0
            )

            total_yusyutsu = sum(g.get('yusyutsu', 0) for g in grade_stats.values() if isinstance(g, dict))
            total_yusho = sum(g.get('yusho', 0) for g in grade_stats.values() if isinstance(g, dict))
            features['total_yusyutsu'] = total_yusyutsu
            features['total_yusho'] = total_yusho
            features['yusyutsu_rate'] = total_yusyutsu * 0.1
            features['yusho_rate'] = total_yusho * 0.2
        else:
            features['sg_win_rate'] = 0.0
            features['sg_experience_score'] = 0
            features['g1_win_rate'] = 0.0
            features['g2_win_rate'] = 0.0
            features['g3_win_rate'] = 0.0
            features['racer_grade_score'] = 0.0
            features['total_yusyutsu'] = 0
            features['total_yusho'] = 0
            features['yusyutsu_rate'] = 0.0
            features['yusho_rate'] = 0.0

        # コース別成績（course_stats）
        course_stats = boat.get('course_stats')
        boat_number = int(boat.get('boat_number', 1))

        if course_stats and isinstance(course_stats, dict):
            course_data = None
            for key in course_stats.keys():
                if str(boat_number) in key:
                    course_data = course_stats[key]
                    break

            if course_data and isinstance(course_data, dict):
                features['course_specific_1st_rate'] = float(course_data.get('1st_rate', 0))
                features['course_win_rate_venue'] = float(course_data.get('win_rate', 0))
                features['course_nige_rate'] = float(course_data.get('nige_rate', 0)) if 'nige_rate' in course_data else 0.0
                features['course_sashi_rate'] = float(course_data.get('sashi_rate', 0)) if 'sashi_rate' in course_data else 0.0
                features['course_makuri_rate'] = float(course_data.get('makuri_rate', 0)) if 'makuri_rate' in course_data else 0.0
            else:
                features['course_specific_1st_rate'] = 0.0
                features['course_win_rate_venue'] = 0.0
                features['course_nige_rate'] = 0.0
                features['course_sashi_rate'] = 0.0
                features['course_makuri_rate'] = 0.0
        else:
            features['course_specific_1st_rate'] = 0.0
            features['course_win_rate_venue'] = 0.0
            features['course_nige_rate'] = 0.0
            features['course_sashi_rate'] = 0.0
            features['course_makuri_rate'] = 0.0

        # 会場別成績（venue_stats）
        venue_stats = boat.get('venue_stats')
        venue_id = int(boat.get('venue_id', 1))

        if venue_stats and isinstance(venue_stats, dict):
            venue_data = None
            venue_name = self.VENUE_NAMES.get(venue_id, '')
            for key in venue_stats.keys():
                if venue_name and venue_name in key:
                    venue_data = venue_stats[key]
                    break

            if venue_data and isinstance(venue_data, dict):
                features['venue_specific_win_rate'] = float(venue_data.get('win_rate', 0))
                features['venue_specific_1st_rate'] = float(venue_data.get('1st_rate', 0))
                features['venue_specific_2nd_rate'] = float(venue_data.get('2nd_rate', 0))
                features['racer_win_rate_venue'] = float(venue_data.get('win_rate', 0))
                features['racer_avg_st_venue'] = float(venue_data.get('avg_st', 0.15))
                features['venue_experience'] = int(venue_data.get('races', 0))
                features['racer_venue_experience'] = features['venue_experience']
            else:
                features['venue_specific_win_rate'] = 0.0
                features['venue_specific_1st_rate'] = 0.0
                features['venue_specific_2nd_rate'] = 0.0
                features['racer_win_rate_venue'] = 0.0
                features['racer_avg_st_venue'] = 0.15
                features['venue_experience'] = 0
                features['racer_venue_experience'] = 0
        else:
            features['venue_specific_win_rate'] = 0.0
            features['venue_specific_1st_rate'] = 0.0
            features['venue_specific_2nd_rate'] = 0.0
            features['racer_win_rate_venue'] = 0.0
            features['racer_avg_st_venue'] = 0.15
            features['venue_experience'] = 0
            features['racer_venue_experience'] = 0

        # 総合能力スコア
        features['total_ability_score'] = (
            features['racer_win_rate'] * 0.3 +
            features['racer_grade_score'] * 0.2 +
            features['venue_specific_win_rate'] * 0.2 +
            features['course_specific_1st_rate'] * 0.3
        )

        # その他の特徴量（デフォルト値）
        features['racer_motor_score'] = 0.0
        features['motor_second_rate'] = float(boat.get('motor_rate_2', 30.0) or 30.0)
        features['motor_third_rate'] = float(boat.get('motor_rate_3', 50.0) or 50.0)
        features['boat_num_specific_1st_rate'] = 0.0
        features['boat_num_specific_2nd_rate'] = 0.0
        features['boat_num_affinity'] = 0.0
        features['recent_5races_avg'] = features['racer_win_rate']
        features['recent_10races_avg'] = features['racer_win_rate']
        features['trend_score'] = 0.0
        features['temperature'] = 0.0
        features['wind_speed'] = 0.0
        features['wind_direction'] = 0.0
        features['wave_height'] = 0.0
        features['wind_impact_score'] = 0.0

        return features

    def _composite_features(self, features):
        """複合特徴量"""
        # 総合力スコア
        total_score = (
            features['win_rate'] * 0.3 +
            features['motor_rate_2'] * 0.2 +
            features['exhibition_quality'] * 0.2 +
            features['course_advantage'] * 10 +
            features['start_quality'] * 0.1
        )

        # コース1 × 能力 の相互作用
        course1_ability = features['is_course_1'] * features['win_rate'] * 0.1

        # モーター × 展示タイムの相互作用
        motor_exhibition = features['motor_rate_2'] * features['exhibition_quality'] * 0.01

        return {
            'total_score': total_score,
            'course1_ability': course1_ability,
            'motor_exhibition_score': motor_exhibition,
        }


def fetch_training_data_enhanced():
    """訓練データを取得（race_entriesの全データを含む）"""
    print("=== 強化版: 訓練データを取得中 ===\n")

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
            r.grade as race_grade
        FROM race_entries re
        LEFT JOIN races r ON re.race_id = r.id
        WHERE re.result_position IS NOT NULL
        AND r.id IS NOT NULL
        ORDER BY r.race_date DESC, r.venue_id, r.race_number, re.boat_number
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    print(f"取得データ数: {len(df):,}件")
    print(f"レース数: {df['race_id'].nunique():,}レース")
    print(f"日付範囲: {df['race_date'].min()} ～ {df['race_date'].max()}")

    # データ品質チェック
    print(f"\n=== データ品質 ===")
    print(f"win_rate非null: {df['win_rate'].notna().sum():,} ({df['win_rate'].notna().mean()*100:.1f}%)")
    print(f"exhibition_time非null: {df['exhibition_time'].notna().sum():,} ({df['exhibition_time'].notna().mean()*100:.1f}%)")
    print(f"motor_rate_2非null: {df['motor_rate_2'].notna().sum():,} ({df['motor_rate_2'].notna().mean()*100:.1f}%)")

    return df


if __name__ == '__main__':
    # テスト実行
    print("=== EnhancedFeatureEngineer Test ===\n")

    # データ取得
    df = fetch_training_data_enhanced()

    # 特徴量エンジニア初期化
    fe = EnhancedFeatureEngineer()

    # 1レースのテスト
    sample_race_id = df['race_id'].iloc[0]
    sample_race = df[df['race_id'] == sample_race_id]

    print(f"\nサンプルレース: {sample_race_id}")
    print(f"艇数: {len(sample_race)}")

    if len(sample_race) == 6:
        features = fe.create_features(sample_race)
        print(f"\n生成された特徴量: {features.shape[1]}次元")
        print(f"\n特徴量一覧:")
        for col in features.columns:
            print(f"  {col}")

        print(f"\n特徴量サンプル（1号艇）:")
        for col, val in features.iloc[0].items():
            print(f"  {col}: {val:.4f}")
