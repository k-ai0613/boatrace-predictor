-- フェーズ4: モーター・ボート詳細情報を race_entries テーブルに追加

-- モーター・ボート3連率を追加
ALTER TABLE race_entries
ADD COLUMN IF NOT EXISTS motor_rate_3 DECIMAL(5,2),
ADD COLUMN IF NOT EXISTS boat_rate_3 DECIMAL(5,2);

-- カラムコメント
COMMENT ON COLUMN race_entries.motor_rate_3 IS 'モーター3連率（%）';
COMMENT ON COLUMN race_entries.boat_rate_3 IS 'ボート3連率（%）';

-- 注: オッズデータは別途 odds テーブルとして実装予定
-- CREATE TABLE IF NOT EXISTS odds (
--     id SERIAL PRIMARY KEY,
--     race_id INTEGER REFERENCES races(id),
--     odds_type VARCHAR(20),  -- 'tansho', 'fukusho', '2rentan', '2renpuku', '3rentan', '3renpuku'
--     combination VARCHAR(50), -- 艇番の組み合わせ (例: '1', '1-2', '1-2-3')
--     odds_value DECIMAL(8,2),
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );
