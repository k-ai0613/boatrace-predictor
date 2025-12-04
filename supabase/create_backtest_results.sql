-- バックテスト結果保存テーブル
CREATE TABLE IF NOT EXISTS backtest_results (
    id SERIAL PRIMARY KEY,
    run_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    total_races INTEGER NOT NULL,

    -- 単勝
    win_correct INTEGER NOT NULL,
    win_accuracy DECIMAL(5,2) NOT NULL,
    top2_correct INTEGER NOT NULL,
    top3_correct INTEGER NOT NULL,

    -- 2連単
    nirentan_top5 INTEGER NOT NULL,
    nirentan_top5_accuracy DECIMAL(5,2) NOT NULL,
    nirentan_top10 INTEGER NOT NULL,

    -- 2連複
    nirenpuku_top5 INTEGER NOT NULL,
    nirenpuku_top5_accuracy DECIMAL(5,2) NOT NULL,

    -- 3連単
    sanrentan_top10 INTEGER NOT NULL,
    sanrentan_top10_accuracy DECIMAL(5,2) NOT NULL,
    sanrentan_top20 INTEGER NOT NULL,

    -- 3連複
    sanrenpuku_top10 INTEGER NOT NULL,
    sanrenpuku_top10_accuracy DECIMAL(5,2) NOT NULL,

    -- メタ情報
    model_version VARCHAR(100),
    notes TEXT
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_backtest_results_run_date ON backtest_results(run_date DESC);

-- RLSポリシー
ALTER TABLE backtest_results ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read access on backtest_results"
    ON backtest_results FOR SELECT
    USING (true);

CREATE POLICY "Allow public insert access on backtest_results"
    ON backtest_results FOR INSERT
    WITH CHECK (true);

COMMENT ON TABLE backtest_results IS 'モデル精度のバックテスト結果履歴';
