-- レーサー特性データ: コース別成績と決まり手統計を race_entries テーブルに追加

-- コース別成績率（1-6コース）
ALTER TABLE race_entries
ADD COLUMN IF NOT EXISTS course_1_rate DECIMAL(5,2),
ADD COLUMN IF NOT EXISTS course_2_rate DECIMAL(5,2),
ADD COLUMN IF NOT EXISTS course_3_rate DECIMAL(5,2),
ADD COLUMN IF NOT EXISTS course_4_rate DECIMAL(5,2),
ADD COLUMN IF NOT EXISTS course_5_rate DECIMAL(5,2),
ADD COLUMN IF NOT EXISTS course_6_rate DECIMAL(5,2);

-- 決まり手統計（6種類）
ALTER TABLE race_entries
ADD COLUMN IF NOT EXISTS winning_tech_nige DECIMAL(5,2),
ADD COLUMN IF NOT EXISTS winning_tech_sashi DECIMAL(5,2),
ADD COLUMN IF NOT EXISTS winning_tech_makuri DECIMAL(5,2),
ADD COLUMN IF NOT EXISTS winning_tech_makuri_sashi DECIMAL(5,2),
ADD COLUMN IF NOT EXISTS winning_tech_nuki DECIMAL(5,2),
ADD COLUMN IF NOT EXISTS winning_tech_megumare DECIMAL(5,2);

-- 実際の決まり手（レース結果、1着のみ）
ALTER TABLE race_entries
ADD COLUMN IF NOT EXISTS winning_technique VARCHAR(20);

-- カラムコメント
COMMENT ON COLUMN race_entries.course_1_rate IS '1コース勝率（%）';
COMMENT ON COLUMN race_entries.course_2_rate IS '2コース勝率（%）';
COMMENT ON COLUMN race_entries.course_3_rate IS '3コース勝率（%）';
COMMENT ON COLUMN race_entries.course_4_rate IS '4コース勝率（%）';
COMMENT ON COLUMN race_entries.course_5_rate IS '5コース勝率（%）';
COMMENT ON COLUMN race_entries.course_6_rate IS '6コース勝率（%）';

COMMENT ON COLUMN race_entries.winning_tech_nige IS '決まり手: 逃げ（回数または%）';
COMMENT ON COLUMN race_entries.winning_tech_sashi IS '決まり手: 差し（回数または%）';
COMMENT ON COLUMN race_entries.winning_tech_makuri IS '決まり手: まくり（回数または%）';
COMMENT ON COLUMN race_entries.winning_tech_makuri_sashi IS '決まり手: まくり差し（回数または%）';
COMMENT ON COLUMN race_entries.winning_tech_nuki IS '決まり手: 抜き（回数または%）';
COMMENT ON COLUMN race_entries.winning_tech_megumare IS '決まり手: 恵まれ（回数または%）';
COMMENT ON COLUMN race_entries.winning_technique IS '実際の決まり手（レース結果、1着のみ）';
