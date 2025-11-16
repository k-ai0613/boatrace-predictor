-- weather_dataテーブルにrace_idカラムを追加し、レースに紐付ける

-- 1. race_idカラムを追加
ALTER TABLE weather_data
ADD COLUMN IF NOT EXISTS race_id INT REFERENCES races(id) ON DELETE CASCADE;

-- 2. 既存の制約を削除（venue_id, record_datetimeのUNIQUE制約）
ALTER TABLE weather_data
DROP CONSTRAINT IF EXISTS weather_data_venue_id_record_datetime_key;

-- 3. venue_id, record_datetime, wind_speedをNULL許可に変更（race_idベースで管理する場合）
ALTER TABLE weather_data
ALTER COLUMN venue_id DROP NOT NULL;

ALTER TABLE weather_data
ALTER COLUMN record_datetime DROP NOT NULL;

ALTER TABLE weather_data
ALTER COLUMN wind_speed DROP NOT NULL;

-- 4. race_idにUNIQUE制約を追加
ALTER TABLE weather_data
ADD CONSTRAINT weather_data_race_id_unique UNIQUE(race_id);

-- 5. race_idにインデックスを作成
CREATE INDEX IF NOT EXISTS idx_weather_race ON weather_data(race_id);
