import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv
import psycopg2
import json

load_dotenv()


class FeatureEngineer:
    """特徴量を生成するクラス"""

    def __init__(self, historical_data, racer_detailed_stats=None):
        """
        Args:
            historical_data: 過去のレースデータ（DataFrame）
            racer_detailed_stats: 選手詳細統計データ（DataFrame）
        """
        self.historical_data = historical_data
        self.racer_detailed_stats = racer_detailed_stats
        self.venue_course_stats = self._calculate_venue_course_stats()

        # 詳細統計が提供されていない場合は取得
        if self.racer_detailed_stats is None:
            self.racer_detailed_stats = self._fetch_racer_detailed_stats()

    def _fetch_racer_detailed_stats(self):
        """racer_detailed_statsテーブルからデータを取得"""
        try:
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
        except Exception as e:
            print(f"Warning: Could not fetch racer_detailed_stats: {e}")
            return pd.DataFrame()

    def create_features(self, race_data):
        """
        1レース分の特徴量を生成

        Args:
            race_data: 1レースの6艇分のデータ（DataFrame）

        Returns:
            DataFrame: 特徴量（6行 × 特徴量数列）
        """
        features_list = []

        for idx, boat in race_data.iterrows():
            features = {}

            # 1. 選手関連（基本）
            features.update(self._racer_features(boat))

            # 2. モーター関連
            features.update(self._motor_features(boat))

            # 3. コース関連
            features.update(self._course_features(boat))

            # 4. 天気関連
            features.update(self._weather_features(boat))

            # 5. 複合特徴量
            features.update(self._composite_features(boat, features))

            # 6. 時系列特徴量
            features.update(self._temporal_features(boat))

            # === 新規: 詳細統計ベースの特徴量 ===

            # 7. 実績関連（優出・優勝・SG）
            features.update(self._championship_features(boat))

            # 8. ペナルティ関連（フライング・出遅れ）
            features.update(self._penalty_features(boat))

            # 9. 会場別詳細成績
            features.update(self._venue_detailed_features(boat))

            # 10. グレード別成績
            features.update(self._grade_performance_features(boat))

            # 11. 艇番別成績
            features.update(self._boat_number_features(boat))

            # 12. コース別戦術（決まり手）
            features.update(self._course_tactics_features(boat))

            features_list.append(features)

        return pd.DataFrame(features_list)

    def _racer_features(self, boat):
        """選手関連の特徴量"""
        return {
            'racer_win_rate': boat.get('racer_win_rate', 0.0),
            'racer_win_rate_venue': boat.get('racer_win_rate_venue', 0.0),
            'racer_second_rate': boat.get('racer_second_rate', 0.0),
            'racer_third_rate': boat.get('racer_third_rate', 0.0),
            'racer_grade_score': self._grade_to_score(boat.get('grade', 'B2')),
            'racer_avg_st': boat.get('avg_start_timing', 0.17),
            'racer_avg_st_venue': boat.get('avg_st_venue', boat.get('avg_start_timing', 0.17)),
            'racer_venue_experience': boat.get('venue_race_count', 0),
        }

    def _motor_features(self, boat):
        """モーター関連の特徴量"""
        return {
            'motor_second_rate': boat.get('motor_second_rate', 0.0),
            'motor_third_rate': boat.get('motor_third_rate', 0.0),
        }

    def _course_features(self, boat):
        """コース関連の特徴量"""
        venue_id = boat.get('venue_id', 1)
        course = boat.get('course')

        # courseがNoneの場合はboat_numberを使用
        if course is None:
            course = boat.get('boat_number', 1)

        # それでもNoneの場合はデフォルト値
        if course is None:
            course = 1

        # この場・このコースでの1着率
        course_win_rate = self.venue_course_stats.get(
            (venue_id, course),
            {'win_rate': 0.15}
        )['win_rate']

        return {
            'course': course,
            'course_win_rate_venue': course_win_rate,
            'is_inner_course': 1 if course <= 3 else 0,
            'is_course_1': 1 if course == 1 else 0,
        }

    def _weather_features(self, boat):
        """天気関連の特徴量"""
        wind_speed = boat.get('wind_speed', 0)
        wind_direction = boat.get('wind_direction', 0)
        course = boat.get('course', boat.get('boat_number', 1))

        return {
            'wind_speed': wind_speed,
            'wind_direction': wind_direction,
            'wind_impact_score': self._calculate_wind_impact(
                wind_speed, wind_direction, course
            ),
            'temperature': boat.get('temperature', 20),
            'wave_height': boat.get('wave_height', 0),
        }

    def _composite_features(self, boat, base_features):
        """複合特徴量"""
        return {
            'racer_motor_score': (
                base_features['racer_win_rate'] *
                base_features['motor_second_rate']
            ) if base_features['motor_second_rate'] > 0 else 0,
            'course_advantage': (
                base_features['course_win_rate_venue'] *
                base_features['racer_grade_score']
            ),
            'total_ability_score': (
                base_features['racer_win_rate'] * 0.4 +
                base_features['motor_second_rate'] * 0.3 +
                base_features['course_win_rate_venue'] * 0.3
            )
        }

    def _temporal_features(self, boat):
        """時系列特徴量"""
        racer_id = boat.get('racer_id', 0)
        recent_races = self._get_recent_races(racer_id, n=10)

        if len(recent_races) == 0:
            return {
                'recent_5races_avg': 3.5,
                'recent_10races_avg': 3.5,
                'trend_score': 0
            }

        recent_5 = recent_races.head(5)['result_position'].mean()
        recent_10 = recent_races['result_position'].mean()

        # トレンドスコア（最近が良ければプラス）
        if len(recent_races) >= 5:
            first_half = recent_races.tail(5)['result_position'].mean()
            second_half = recent_races.head(5)['result_position'].mean()
            trend_score = first_half - second_half  # 着順が下がる=良い
        else:
            trend_score = 0

        return {
            'recent_5races_avg': recent_5,
            'recent_10races_avg': recent_10,
            'trend_score': trend_score
        }

    def _grade_to_score(self, grade):
        """級別をスコア化"""
        scores = {'A1': 4, 'A2': 3, 'B1': 2, 'B2': 1}
        return scores.get(grade, 0)

    def _calculate_wind_impact(self, wind_speed, wind_direction, course):
        """
        風がコースに与える影響を計算

        風向きとコースの関係:
        - 追い風: スピードが出やすい
        - 向かい風: スピードが落ちる
        - 横風: コースによって有利不利
        """
        # 簡易的な計算
        if wind_speed < 2:
            return 0  # 影響小

        # コース1は追い風で有利、向かい風で不利
        base_impact = wind_speed * np.cos(np.radians(wind_direction - 90))

        if course == 1:
            return base_impact
        elif course in [2, 3]:
            return base_impact * 0.5
        else:
            return -base_impact * 0.3

    def _calculate_venue_course_stats(self):
        """場・コース別の統計を事前計算"""
        stats = {}

        if self.historical_data is None or len(self.historical_data) == 0:
            # デフォルト値を返す
            for venue_id in range(1, 25):
                for course in range(1, 7):
                    stats[(venue_id, course)] = {'win_rate': 0.15}
            return stats

        for venue_id in range(1, 25):
            venue_data = self.historical_data[
                self.historical_data['venue_id'] == venue_id
            ]

            for course in range(1, 7):
                course_data = venue_data[venue_data['course'] == course]

                if len(course_data) > 0:
                    win_rate = (course_data['result_position'] == 1).mean()
                    stats[(venue_id, course)] = {'win_rate': win_rate}
                else:
                    stats[(venue_id, course)] = {'win_rate': 0.15}

        return stats

    def _get_recent_races(self, racer_id, n=10):
        """選手の直近n走を取得"""
        if self.historical_data is None or len(self.historical_data) == 0:
            return pd.DataFrame()

        racer_races = self.historical_data[
            self.historical_data['racer_id'] == racer_id
        ].sort_values('race_date', ascending=False)

        return racer_races.head(n)

    # ===== 新規: 詳細統計ベースの特徴量生成 =====

    def _get_racer_detailed_data(self, racer_number):
        """選手番号から詳細統計データを取得"""
        if self.racer_detailed_stats is None or len(self.racer_detailed_stats) == 0:
            return None

        data = self.racer_detailed_stats[
            self.racer_detailed_stats['racer_number'] == racer_number
        ]

        if len(data) == 0:
            return None

        return data.iloc[0]

    def _championship_features(self, boat):
        """実績関連の特徴量（優出・優勝・SG出場）"""
        racer_number = boat.get('racer_number', 0)
        detailed = self._get_racer_detailed_data(racer_number)

        if detailed is None:
            return {
                'total_yusyutsu': 0,
                'total_yusho': 0,
                'sg_appearances': 0,
                'yusyutsu_rate': 0.0,
                'yusho_rate': 0.0,
                'sg_experience_score': 0.0
            }

        total_races = detailed.get('total_races', 1)
        if total_races == 0:
            total_races = 1

        yusyutsu = detailed.get('total_優出', 0) or 0
        yusho = detailed.get('total_優勝', 0) or 0
        sg_apps = detailed.get('sg_appearances', 0) or 0

        return {
            'total_yusyutsu': yusyutsu,
            'total_yusho': yusho,
            'sg_appearances': sg_apps,
            'yusyutsu_rate': yusyutsu / total_races * 100,
            'yusho_rate': yusho / total_races * 100,
            'sg_experience_score': min(sg_apps / 10.0, 10.0)  # 正規化（最大10）
        }

    def _penalty_features(self, boat):
        """ペナルティ関連の特徴量（フライング・出遅れ）"""
        racer_number = boat.get('racer_number', 0)
        detailed = self._get_racer_detailed_data(racer_number)

        if detailed is None:
            return {
                'flying_count': 0,
                'late_start_count': 0,
                'penalty_risk_score': 0.0
            }

        flying = detailed.get('flying_count', 0) or 0
        late = detailed.get('late_start_count', 0) or 0

        # リスクスコア（高いほどリスク高い）
        penalty_risk = (flying * 2 + late) / 10.0  # 正規化

        return {
            'flying_count': flying,
            'late_start_count': late,
            'penalty_risk_score': min(penalty_risk, 10.0)
        }

    def _venue_detailed_features(self, boat):
        """会場別詳細成績の特徴量"""
        racer_number = boat.get('racer_number', 0)
        venue_id = boat.get('venue_id', 1)
        detailed = self._get_racer_detailed_data(racer_number)

        if detailed is None or detailed.get('venue_stats') is None:
            return {
                'venue_specific_win_rate': 0.0,
                'venue_specific_1st_rate': 0.0,
                'venue_specific_2nd_rate': 0.0,
                'venue_experience': 0
            }

        try:
            venue_stats = detailed.get('venue_stats')
            if isinstance(venue_stats, str):
                venue_stats = json.loads(venue_stats)

            # 会場名をキーとして検索（例: "桐生", "戸田" など）
            venue_data = None
            for venue_name, stats in venue_stats.items():
                # venue_idから会場名へのマッピング（簡易版）
                # TODO: venue_idと会場名の正確なマッピングが必要
                venue_data = stats
                break  # 暫定: 最初のマッチを使用

            if venue_data is None:
                return {
                    'venue_specific_win_rate': 0.0,
                    'venue_specific_1st_rate': 0.0,
                    'venue_specific_2nd_rate': 0.0,
                    'venue_experience': 0
                }

            return {
                'venue_specific_win_rate': venue_data.get('win_rate', 0.0),
                'venue_specific_1st_rate': venue_data.get('1st_rate', 0.0),
                'venue_specific_2nd_rate': venue_data.get('2nd_rate', 0.0),
                'venue_experience': venue_data.get('races', 0)
            }

        except (json.JSONDecodeError, AttributeError, KeyError):
            return {
                'venue_specific_win_rate': 0.0,
                'venue_specific_1st_rate': 0.0,
                'venue_specific_2nd_rate': 0.0,
                'venue_experience': 0
            }

    def _grade_performance_features(self, boat):
        """グレード別成績の特徴量"""
        racer_number = boat.get('racer_number', 0)
        detailed = self._get_racer_detailed_data(racer_number)

        if detailed is None or detailed.get('grade_stats') is None:
            return {
                'sg_win_rate': 0.0,
                'g1_win_rate': 0.0,
                'g2_win_rate': 0.0,
                'g3_win_rate': 0.0,
                'high_grade_experience': 0.0
            }

        try:
            grade_stats = detailed.get('grade_stats')
            if isinstance(grade_stats, str):
                grade_stats = json.loads(grade_stats)

            sg_data = grade_stats.get('SG', {})
            g1_data = grade_stats.get('G1', {})
            g2_data = grade_stats.get('G2', {})
            g3_data = grade_stats.get('G3', {})

            # 高グレード経験スコア
            high_grade_exp = (
                sg_data.get('races', 0) * 3 +
                g1_data.get('races', 0) * 2 +
                g2_data.get('races', 0) * 1
            ) / 100.0  # 正規化

            return {
                'sg_win_rate': sg_data.get('win_rate', 0.0),
                'g1_win_rate': g1_data.get('win_rate', 0.0),
                'g2_win_rate': g2_data.get('win_rate', 0.0),
                'g3_win_rate': g3_data.get('win_rate', 0.0),
                'high_grade_experience': min(high_grade_exp, 10.0)
            }

        except (json.JSONDecodeError, AttributeError, KeyError):
            return {
                'sg_win_rate': 0.0,
                'g1_win_rate': 0.0,
                'g2_win_rate': 0.0,
                'g3_win_rate': 0.0,
                'high_grade_experience': 0.0
            }

    def _boat_number_features(self, boat):
        """艇番別成績の特徴量"""
        racer_number = boat.get('racer_number', 0)
        boat_number = boat.get('boat_number', 1)
        detailed = self._get_racer_detailed_data(racer_number)

        if detailed is None or detailed.get('boat_number_stats') is None:
            return {
                'boat_num_specific_1st_rate': 16.7,  # デフォルト（1/6）
                'boat_num_specific_2nd_rate': 33.3,
                'boat_num_affinity': 0.0
            }

        try:
            boat_stats = detailed.get('boat_number_stats')
            if isinstance(boat_stats, str):
                boat_stats = json.loads(boat_stats)

            boat_data = boat_stats.get(str(boat_number), {})

            first_rate = boat_data.get('1st_rate', 16.7)
            second_rate = boat_data.get('2nd_rate', 33.3)

            # 親和性スコア（平均より高ければプラス）
            affinity = (first_rate - 16.7) / 10.0

            return {
                'boat_num_specific_1st_rate': first_rate,
                'boat_num_specific_2nd_rate': second_rate,
                'boat_num_affinity': affinity
            }

        except (json.JSONDecodeError, AttributeError, KeyError):
            return {
                'boat_num_specific_1st_rate': 16.7,
                'boat_num_specific_2nd_rate': 33.3,
                'boat_num_affinity': 0.0
            }

    def _course_tactics_features(self, boat):
        """コース別戦術（決まり手）の特徴量"""
        racer_number = boat.get('racer_number', 0)
        course = boat.get('course', boat.get('boat_number', 1))
        detailed = self._get_racer_detailed_data(racer_number)

        if detailed is None or detailed.get('course_stats') is None:
            return {
                'course_specific_1st_rate': 16.7,
                'course_nige_rate': 0.0,
                'course_sashi_rate': 0.0,
                'course_makuri_rate': 0.0
            }

        try:
            course_stats = detailed.get('course_stats')
            if isinstance(course_stats, str):
                course_stats = json.loads(course_stats)

            course_data = course_stats.get(str(course), {})

            first_rate = course_data.get('1st_rate', 16.7)
            kimaritet = course_data.get('決まり手', {})

            # 決まり手の割合を計算
            total_wins = sum(kimaritet.values()) if kimaritet else 1
            nige = kimaritet.get('逃げ', 0) / total_wins * 100 if total_wins > 0 else 0
            sashi = kimaritet.get('差し', 0) / total_wins * 100 if total_wins > 0 else 0
            makuri = kimaritet.get('まくり', 0) / total_wins * 100 if total_wins > 0 else 0

            return {
                'course_specific_1st_rate': first_rate,
                'course_nige_rate': nige,
                'course_sashi_rate': sashi,
                'course_makuri_rate': makuri
            }

        except (json.JSONDecodeError, AttributeError, KeyError, ZeroDivisionError):
            return {
                'course_specific_1st_rate': 16.7,
                'course_nige_rate': 0.0,
                'course_sashi_rate': 0.0,
                'course_makuri_rate': 0.0
            }
