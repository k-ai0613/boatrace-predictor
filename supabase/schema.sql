-- =====================================================
-- 競艇予測分析ツール - データベーススキーマ
-- =====================================================

-- races（レース基本情報）
CREATE TABLE IF NOT EXISTS races (
  id SERIAL PRIMARY KEY,
  race_date DATE NOT NULL,
  venue_id INT NOT NULL,           -- 場ID (1-24)
  race_number INT NOT NULL,        -- レース番号 (1-12)
  grade VARCHAR(10),               -- SG, G1, G2, G3, 一般
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(race_date, venue_id, race_number)
);

CREATE INDEX idx_races_date_venue ON races(race_date, venue_id);
CREATE INDEX idx_races_date ON races(race_date);

-- racers（選手マスタ）
CREATE TABLE IF NOT EXISTS racers (
  id SERIAL PRIMARY KEY,
  racer_number INT UNIQUE NOT NULL,
  name VARCHAR(100) NOT NULL,
  grade VARCHAR(5),                -- A1, A2, B1, B2
  branch VARCHAR(50),              -- 支部
  birth_date DATE,
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_racers_number ON racers(racer_number);
CREATE INDEX idx_racers_grade ON racers(grade);

-- race_entries（出走情報）
CREATE TABLE IF NOT EXISTS race_entries (
  id SERIAL PRIMARY KEY,
  race_id INT REFERENCES races(id) ON DELETE CASCADE,
  boat_number INT NOT NULL,        -- 艇番 (1-6)
  racer_id INT NOT NULL,
  motor_number INT,
  start_timing FLOAT,              -- ST (スタートタイミング)
  course INT,                      -- 実際の進入コース (1-6)
  result_position INT,             -- 着順 (1-6)
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(race_id, boat_number)
);

CREATE INDEX idx_entries_race ON race_entries(race_id);
CREATE INDEX idx_entries_racer ON race_entries(racer_id);
CREATE INDEX idx_entries_result ON race_entries(race_id, result_position);

-- racer_stats（選手成績）
CREATE TABLE IF NOT EXISTS racer_stats (
  id SERIAL PRIMARY KEY,
  racer_id INT REFERENCES racers(id) ON DELETE CASCADE,
  stats_date DATE NOT NULL,        -- 集計時点
  win_rate FLOAT,                  -- 勝率
  second_rate FLOAT,               -- 2連対率
  third_rate FLOAT,                -- 3連対率
  avg_start_timing FLOAT,          -- 平均ST
  venue_id INT,                    -- NULL=全国、値あり=当地
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(racer_id, stats_date, venue_id)
);

CREATE INDEX idx_racer_stats_racer_date ON racer_stats(racer_id, stats_date);
CREATE INDEX idx_racer_stats_venue ON racer_stats(venue_id, stats_date);

-- motors（モーター情報）
CREATE TABLE IF NOT EXISTS motors (
  id SERIAL PRIMARY KEY,
  venue_id INT NOT NULL,
  motor_number INT NOT NULL,
  year INT NOT NULL,               -- 年度
  second_rate FLOAT,               -- 2連対率
  third_rate FLOAT,                -- 3連対率
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(venue_id, motor_number, year)
);

CREATE INDEX idx_motors_venue_year ON motors(venue_id, year);

-- weather_data（天気情報）
CREATE TABLE IF NOT EXISTS weather_data (
  id SERIAL PRIMARY KEY,
  venue_id INT NOT NULL,
  record_datetime TIMESTAMP NOT NULL,

  -- 基本気象情報
  temperature FLOAT,               -- 気温(℃)
  humidity FLOAT,                  -- 湿度(%)
  pressure FLOAT,                  -- 気圧(hPa)

  -- 風情報（最重要）
  wind_speed FLOAT NOT NULL,       -- 風速(m/s)
  wind_direction INT,              -- 風向き(0-359度)
  wind_direction_text VARCHAR(10), -- 風向き('北', '南東'など)

  -- 水面状態
  wave_height FLOAT,               -- 波高(cm)
  water_temperature FLOAT,         -- 水温(℃)

  -- 天気状態
  weather_condition VARCHAR(20),   -- '晴れ', '曇り', '雨'など

  -- データソース
  source VARCHAR(50) DEFAULT 'venue_official',
  is_realtime BOOLEAN DEFAULT false,

  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(venue_id, record_datetime)
);

CREATE INDEX idx_weather_venue_date ON weather_data(venue_id, record_datetime);
CREATE INDEX idx_weather_realtime ON weather_data(venue_id, is_realtime)
  WHERE is_realtime = true;

-- predictions（予測結果）
CREATE TABLE IF NOT EXISTS predictions (
  id SERIAL PRIMARY KEY,
  race_id INT REFERENCES races(id) ON DELETE CASCADE,
  boat_number INT NOT NULL,
  predicted_win_prob FLOAT,        -- 1着確率
  predicted_second_prob FLOAT,     -- 2着確率
  predicted_third_prob FLOAT,      -- 3着確率
  predicted_fourth_prob FLOAT,     -- 4着確率
  predicted_fifth_prob FLOAT,      -- 5着確率
  predicted_sixth_prob FLOAT,      -- 6着確率
  model_version VARCHAR(50),
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(race_id, boat_number, model_version)
);

CREATE INDEX idx_predictions_race ON predictions(race_id);

-- =====================================================
-- サンプルデータ用のコメント
-- =====================================================

COMMENT ON TABLE races IS 'レース基本情報';
COMMENT ON TABLE racers IS '選手マスタデータ';
COMMENT ON TABLE race_entries IS '出走情報（各レースの艇ごとの情報）';
COMMENT ON TABLE racer_stats IS '選手の成績統計';
COMMENT ON TABLE motors IS 'モーター性能情報';
COMMENT ON TABLE weather_data IS '気象データ（風速・風向きが最重要）';
COMMENT ON TABLE predictions IS 'AI予測結果';
