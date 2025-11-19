-- フェーズ2: 追加データカラムを各テーブルに追加

-- races テーブルに出走時刻を追加
ALTER TABLE races
ADD COLUMN IF NOT EXISTS race_time VARCHAR(10);

-- weather_data テーブルに風向きを追加
ALTER TABLE weather_data
ADD COLUMN IF NOT EXISTS wind_direction VARCHAR(20);

-- race_entries テーブルに直近成績を追加
ALTER TABLE race_entries
ADD COLUMN IF NOT EXISTS prev_session_result VARCHAR(20),
ADD COLUMN IF NOT EXISTS current_session_result VARCHAR(20);

-- カラムコメント
COMMENT ON COLUMN races.race_time IS 'レース出走時刻（HH:MM形式）';
COMMENT ON COLUMN weather_data.wind_direction IS '風向き（東西南北など）';
COMMENT ON COLUMN race_entries.prev_session_result IS '前節成績（例: 1-2-1-4）';
COMMENT ON COLUMN race_entries.current_session_result IS '今節成績（例: 2-3-1）';
