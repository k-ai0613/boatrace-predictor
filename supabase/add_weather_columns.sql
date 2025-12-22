-- racesテーブルに天気カラムを追加
-- 実行方法: Supabase SQL Editorで実行

-- 天気カラムを追加
ALTER TABLE races
ADD COLUMN IF NOT EXISTS temperature NUMERIC(4,1),
ADD COLUMN IF NOT EXISTS wind_speed INTEGER,
ADD COLUMN IF NOT EXISTS wind_direction VARCHAR(10),
ADD COLUMN IF NOT EXISTS water_temperature NUMERIC(4,1),
ADD COLUMN IF NOT EXISTS wave_height INTEGER,
ADD COLUMN IF NOT EXISTS weather_condition VARCHAR(20);

-- コメント追加
COMMENT ON COLUMN races.temperature IS '気温（℃）';
COMMENT ON COLUMN races.wind_speed IS '風速（m）';
COMMENT ON COLUMN races.wind_direction IS '風向き';
COMMENT ON COLUMN races.water_temperature IS '水温（℃）';
COMMENT ON COLUMN races.wave_height IS '波高（cm）';
COMMENT ON COLUMN races.weather_condition IS '天気（晴、曇、雨など）';

-- 天気バックフィル進捗管理テーブル
CREATE TABLE IF NOT EXISTS weather_backfill_progress (
    id SERIAL PRIMARY KEY,
    venue_id INTEGER NOT NULL,
    race_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    races_updated INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(venue_id, race_date)
);

-- インデックス追加（バックフィル効率化）
CREATE INDEX IF NOT EXISTS idx_races_weather_null
ON races(race_date, venue_id)
WHERE temperature IS NULL;

CREATE INDEX IF NOT EXISTS idx_weather_backfill_status
ON weather_backfill_progress(status);

-- 確認クエリ
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'races'
AND column_name IN ('temperature', 'wind_speed', 'wind_direction', 'water_temperature', 'wave_height', 'weather_condition');
