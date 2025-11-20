-- =====================================================
-- 詳細統計テーブル作成マイグレーション
-- boatrace-db.netから取得するデータ用
-- =====================================================

-- racer_detailed_stats（選手詳細統計）
CREATE TABLE IF NOT EXISTS racer_detailed_stats (
    id SERIAL PRIMARY KEY,
    racer_number INT NOT NULL REFERENCES racers(racer_number) ON DELETE CASCADE,

    -- プロフィール情報
    registration_period INT,         -- 登録期
    branch VARCHAR(50),              -- 支部

    -- 通算成績
    total_races INT,                 -- 総出走数
    total_wins INT,                  -- 総1着数
    overall_win_rate FLOAT,          -- 勝率
    overall_1st_rate FLOAT,          -- 1着率
    overall_2nd_rate FLOAT,          -- 2連対率
    overall_3rd_rate FLOAT,          -- 3連対率
    total_優出 INT,                  -- 優出数
    total_優勝 INT,                  -- 優勝数
    avg_start_timing FLOAT,          -- 平均ST

    -- グレード別成績（JSONB）
    -- {"SG": {"races": 100, "wins": 15, "win_rate": 6.5}, "G1": {...}, ...}
    grade_stats JSONB,

    -- 艇番別成績（JSONB）
    -- {"1": {"races": 200, "1st_rate": 35.5, "2nd_rate": 55.0}, "2": {...}, ...}
    boat_number_stats JSONB,

    -- コース別成績（JSONB）
    -- {"1": {"races": 150, "win_rate": 6.8, "1st_rate": 55.0, "決まり手": {"逃げ": 50, "差し": 10}}, ...}
    course_stats JSONB,

    -- 場別成績（JSONB）
    -- {"01": {"venue_name": "桐生", "races": 50, "1st_rate": 25.0, "2nd_rate": 45.0}, ...}
    venue_stats JSONB,

    -- その他統計
    sg_appearances INT,              -- SG出場回数
    flying_count INT,                -- フライング回数
    late_start_count INT,            -- 出遅れ回数

    -- メタデータ
    data_source VARCHAR(100) DEFAULT 'boatrace-db.net',
    collected_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(racer_number)
);

CREATE INDEX idx_racer_detailed_stats_racer ON racer_detailed_stats(racer_number);
CREATE INDEX idx_racer_detailed_stats_updated ON racer_detailed_stats(updated_at);

COMMENT ON TABLE racer_detailed_stats IS '選手詳細統計（boatrace-db.netから取得）';
COMMENT ON COLUMN racer_detailed_stats.grade_stats IS 'グレード別成績（JSON）';
COMMENT ON COLUMN racer_detailed_stats.boat_number_stats IS '艇番別成績（JSON）';
COMMENT ON COLUMN racer_detailed_stats.course_stats IS 'コース別成績・決まり手（JSON）';
COMMENT ON COLUMN racer_detailed_stats.venue_stats IS '場別成績（JSON）';


-- venue_detailed_stats（会場詳細統計）
CREATE TABLE IF NOT EXISTS venue_detailed_stats (
    id SERIAL PRIMARY KEY,
    venue_id INT NOT NULL UNIQUE,    -- 会場ID (1-24)
    venue_name VARCHAR(50) NOT NULL, -- 会場名

    -- コース別成績（JSONB）
    -- {"1": {"1st_rate": 55.2, "2nd_rate": 72.3, "決まり手": {"逃げ": 95.5, "差し": 2.1}}, ...}
    course_stats JSONB,

    -- モーター成績（JSONB）
    -- [{"motor_no": 1, "races": 50, "win_rate": 6.5, "1st_rate": 35.0, "2nd_rate": 55.0}, ...]
    motor_stats JSONB,

    -- ボート成績（JSONB）
    -- [{"boat_no": 1, "races": 50, "win_rate": 6.5, "1st_rate": 35.0, "2nd_rate": 55.0}, ...]
    boat_stats JSONB,

    -- 展示タイム順位別成績（JSONB）
    -- {"1": {"races": 100, "1st_rate": 45.0}, "2": {...}, ...}
    exhibition_time_stats JSONB,

    -- 出目データ（JSONB）
    -- 3連単の出目統計
    winning_number_stats JSONB,

    -- 会場特性（後で追加可能）
    water_quality VARCHAR(50),       -- 水質（淡水/海水）

    -- メタデータ
    data_source VARCHAR(100) DEFAULT 'boatrace-db.net',
    collected_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_venue_detailed_stats_venue ON venue_detailed_stats(venue_id);
CREATE INDEX idx_venue_detailed_stats_updated ON venue_detailed_stats(updated_at);

COMMENT ON TABLE venue_detailed_stats IS '会場詳細統計（boatrace-db.netから取得）';
COMMENT ON COLUMN venue_detailed_stats.course_stats IS 'コース別成績・決まり手（JSON）';
COMMENT ON COLUMN venue_detailed_stats.motor_stats IS 'モーター成績（JSON）';
COMMENT ON COLUMN venue_detailed_stats.boat_stats IS 'ボート成績（JSON）';
COMMENT ON COLUMN venue_detailed_stats.exhibition_time_stats IS '展示タイム順位別成績（JSON）';


-- 更新日時の自動更新トリガー
CREATE OR REPLACE FUNCTION update_detailed_stats_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER racer_detailed_stats_update_timestamp
    BEFORE UPDATE ON racer_detailed_stats
    FOR EACH ROW
    EXECUTE FUNCTION update_detailed_stats_timestamp();

CREATE TRIGGER venue_detailed_stats_update_timestamp
    BEFORE UPDATE ON venue_detailed_stats
    FOR EACH ROW
    EXECUTE FUNCTION update_detailed_stats_timestamp();
