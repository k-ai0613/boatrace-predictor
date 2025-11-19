-- 出走表データのカラムを race_entries テーブルに追加

-- 選手情報
ALTER TABLE race_entries
ADD COLUMN IF NOT EXISTS racer_grade VARCHAR(10),
ADD COLUMN IF NOT EXISTS win_rate DECIMAL(4,2),
ADD COLUMN IF NOT EXISTS place_rate_2 DECIMAL(5,2),
ADD COLUMN IF NOT EXISTS place_rate_3 DECIMAL(5,2),
ADD COLUMN IF NOT EXISTS weight DECIMAL(4,1);

-- モーター情報
ALTER TABLE race_entries
ADD COLUMN IF NOT EXISTS motor_number INTEGER,
ADD COLUMN IF NOT EXISTS motor_rate_2 DECIMAL(5,2);

-- ボート情報
ALTER TABLE race_entries
ADD COLUMN IF NOT EXISTS boat_hull_number INTEGER,
ADD COLUMN IF NOT EXISTS boat_rate_2 DECIMAL(5,2);

-- 展示情報
ALTER TABLE race_entries
ADD COLUMN IF NOT EXISTS exhibition_time DECIMAL(5,2);

-- インデックスを追加（パフォーマンス向上）
CREATE INDEX IF NOT EXISTS idx_race_entries_motor_number ON race_entries(motor_number);
CREATE INDEX IF NOT EXISTS idx_race_entries_boat_hull_number ON race_entries(boat_hull_number);
CREATE INDEX IF NOT EXISTS idx_race_entries_racer_grade ON race_entries(racer_grade);

COMMENT ON COLUMN race_entries.racer_grade IS '選手の級別（A1, A2, B1, B2）';
COMMENT ON COLUMN race_entries.win_rate IS '選手の全国勝率';
COMMENT ON COLUMN race_entries.place_rate_2 IS '選手の全国2連率（%）';
COMMENT ON COLUMN race_entries.place_rate_3 IS '選手の全国3連率（%）';
COMMENT ON COLUMN race_entries.weight IS '選手の体重（kg）';
COMMENT ON COLUMN race_entries.motor_number IS 'モーター番号';
COMMENT ON COLUMN race_entries.motor_rate_2 IS 'モーター2連率（%）';
COMMENT ON COLUMN race_entries.boat_hull_number IS 'ボート（艇体）番号';
COMMENT ON COLUMN race_entries.boat_rate_2 IS 'ボート2連率（%）';
COMMENT ON COLUMN race_entries.exhibition_time IS '展示タイム（秒）';
