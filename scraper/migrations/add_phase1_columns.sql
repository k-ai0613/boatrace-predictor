-- フェーズ1: 追加データカラムを race_entries テーブルに追加

-- 当地成績
ALTER TABLE race_entries
ADD COLUMN IF NOT EXISTS local_win_rate DECIMAL(4,2),
ADD COLUMN IF NOT EXISTS local_place_rate_2 DECIMAL(5,2);

-- 平均ST
ALTER TABLE race_entries
ADD COLUMN IF NOT EXISTS average_st DECIMAL(3,2);

-- F・L回数
ALTER TABLE race_entries
ADD COLUMN IF NOT EXISTS flying_count INTEGER,
ADD COLUMN IF NOT EXISTS late_count INTEGER;

-- 実際の進入コース
ALTER TABLE race_entries
ADD COLUMN IF NOT EXISTS actual_course INTEGER;

-- インデックスを追加（パフォーマンス向上）
CREATE INDEX IF NOT EXISTS idx_race_entries_actual_course ON race_entries(actual_course);

-- カラムコメント
COMMENT ON COLUMN race_entries.local_win_rate IS '選手の当地勝率';
COMMENT ON COLUMN race_entries.local_place_rate_2 IS '選手の当地2連率（%）';
COMMENT ON COLUMN race_entries.average_st IS '選手の平均スタートタイミング（秒）';
COMMENT ON COLUMN race_entries.flying_count IS 'フライング回数';
COMMENT ON COLUMN race_entries.late_count IS '出遅れ回数';
COMMENT ON COLUMN race_entries.actual_course IS '実際の進入コース（1-6）';
