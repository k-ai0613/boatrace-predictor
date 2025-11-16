import pandas as pd
import numpy as np


class FeatureEngineer:
    """特徴量を生成するクラス"""

    def __init__(self, historical_data):
        """
        Args:
            historical_data: 過去のレースデータ（DataFrame）
        """
        self.historical_data = historical_data
        self.venue_course_stats = self._calculate_venue_course_stats()

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

            # 1. 選手関連
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
        course = boat.get('course', boat.get('boat_number', 1))

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
