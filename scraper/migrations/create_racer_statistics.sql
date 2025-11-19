-- レーサー統計テーブル: 過去のレース結果から計算した統計データを保存

CREATE TABLE IF NOT EXISTS racer_statistics (
    racer_number INTEGER PRIMARY KEY REFERENCES racers(racer_number),

    -- 天候別統計 (JSONB: {"sunny": {"races": 100, "wins": 15, "win_rate": 15.0, ...}, ...})
    weather_stats JSONB,

    -- 会場別統計 (JSONB: {"1": {"races": 50, "wins": 8, "win_rate": 16.0, ...}, ...})
    venue_stats JSONB,

    -- コース別統計（実績ベース） (JSONB: {"1": {"races": 30, "wins": 12, ...}, ...})
    course_stats JSONB,

    -- 決まり手統計（実績ベース） (JSONB: {"nige": 20, "sashi": 15, ...})
    winning_technique_stats JSONB,

    -- 統計計算に使用したデータ範囲
    data_from_date DATE,
    data_to_date DATE,

    -- 最終更新日時
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_racer_stats_updated ON racer_statistics(updated_at);

-- コメント
COMMENT ON TABLE racer_statistics IS 'レーサー別の集計統計（過去レース結果から算出）';
COMMENT ON COLUMN racer_statistics.weather_stats IS '天候別成績統計 (JSON)';
COMMENT ON COLUMN racer_statistics.venue_stats IS '会場別成績統計 (JSON)';
COMMENT ON COLUMN racer_statistics.course_stats IS 'コース別成績統計（実績ベース） (JSON)';
COMMENT ON COLUMN racer_statistics.winning_technique_stats IS '決まり手別統計（実績ベース） (JSON)';
COMMENT ON COLUMN racer_statistics.data_from_date IS '統計データ開始日';
COMMENT ON COLUMN racer_statistics.data_to_date IS '統計データ終了日';
COMMENT ON COLUMN racer_statistics.calculated_at IS '統計計算日時';
COMMENT ON COLUMN racer_statistics.updated_at IS '最終更新日時';

-- 更新日時の自動更新トリガー
CREATE OR REPLACE FUNCTION update_racer_statistics_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER racer_statistics_update_timestamp
    BEFORE UPDATE ON racer_statistics
    FOR EACH ROW
    EXECUTE FUNCTION update_racer_statistics_timestamp();
