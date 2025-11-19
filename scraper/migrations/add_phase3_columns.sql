-- フェーズ3: 追加データカラムを各テーブルに追加

-- race_entries テーブルに直近5走と展示タイム詳細を追加
ALTER TABLE race_entries
ADD COLUMN IF NOT EXISTS recent_5_races VARCHAR(30),
ADD COLUMN IF NOT EXISTS exhibition_turn_time DECIMAL(5,2),
ADD COLUMN IF NOT EXISTS exhibition_straight_time DECIMAL(5,2);

-- weather_data テーブルに潮位を追加
ALTER TABLE weather_data
ADD COLUMN IF NOT EXISTS tide_level DECIMAL(6,2);

-- カラムコメント
COMMENT ON COLUMN race_entries.recent_5_races IS '直近5走の成績（例: 1-3-2-4-1）';
COMMENT ON COLUMN race_entries.exhibition_turn_time IS '展示航走まわり足タイム（秒）';
COMMENT ON COLUMN race_entries.exhibition_straight_time IS '展示航走直線タイム（秒）';
COMMENT ON COLUMN weather_data.tide_level IS '潮位（cm）';
