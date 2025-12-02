-- =====================================================
-- RLS (Row Level Security) ポリシーを有効化
-- 実行方法: Supabase SQL Editorでこのファイルの内容を実行
-- =====================================================

-- 1. races テーブル
ALTER TABLE public.races ENABLE ROW LEVEL SECURITY;

-- 読み取り: 全員許可（匿名ユーザー含む）
CREATE POLICY "races_select_policy" ON public.races
    FOR SELECT
    USING (true);

-- 挿入・更新・削除: 認証済みユーザーまたはサービスロール
CREATE POLICY "races_insert_policy" ON public.races
    FOR INSERT
    WITH CHECK (true);

CREATE POLICY "races_update_policy" ON public.races
    FOR UPDATE
    USING (true);

CREATE POLICY "races_delete_policy" ON public.races
    FOR DELETE
    USING (true);

-- 2. race_entries テーブル
ALTER TABLE public.race_entries ENABLE ROW LEVEL SECURITY;

CREATE POLICY "race_entries_select_policy" ON public.race_entries
    FOR SELECT
    USING (true);

CREATE POLICY "race_entries_insert_policy" ON public.race_entries
    FOR INSERT
    WITH CHECK (true);

CREATE POLICY "race_entries_update_policy" ON public.race_entries
    FOR UPDATE
    USING (true);

CREATE POLICY "race_entries_delete_policy" ON public.race_entries
    FOR DELETE
    USING (true);

-- 3. racers テーブル
ALTER TABLE public.racers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "racers_select_policy" ON public.racers
    FOR SELECT
    USING (true);

CREATE POLICY "racers_insert_policy" ON public.racers
    FOR INSERT
    WITH CHECK (true);

CREATE POLICY "racers_update_policy" ON public.racers
    FOR UPDATE
    USING (true);

CREATE POLICY "racers_delete_policy" ON public.racers
    FOR DELETE
    USING (true);

-- 4. racer_statistics テーブル
ALTER TABLE public.racer_statistics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "racer_statistics_select_policy" ON public.racer_statistics
    FOR SELECT
    USING (true);

CREATE POLICY "racer_statistics_insert_policy" ON public.racer_statistics
    FOR INSERT
    WITH CHECK (true);

CREATE POLICY "racer_statistics_update_policy" ON public.racer_statistics
    FOR UPDATE
    USING (true);

CREATE POLICY "racer_statistics_delete_policy" ON public.racer_statistics
    FOR DELETE
    USING (true);

-- 5. racer_detailed_stats テーブル
ALTER TABLE public.racer_detailed_stats ENABLE ROW LEVEL SECURITY;

CREATE POLICY "racer_detailed_stats_select_policy" ON public.racer_detailed_stats
    FOR SELECT
    USING (true);

CREATE POLICY "racer_detailed_stats_insert_policy" ON public.racer_detailed_stats
    FOR INSERT
    WITH CHECK (true);

CREATE POLICY "racer_detailed_stats_update_policy" ON public.racer_detailed_stats
    FOR UPDATE
    USING (true);

CREATE POLICY "racer_detailed_stats_delete_policy" ON public.racer_detailed_stats
    FOR DELETE
    USING (true);

-- 6. venue_detailed_stats テーブル
ALTER TABLE public.venue_detailed_stats ENABLE ROW LEVEL SECURITY;

CREATE POLICY "venue_detailed_stats_select_policy" ON public.venue_detailed_stats
    FOR SELECT
    USING (true);

CREATE POLICY "venue_detailed_stats_insert_policy" ON public.venue_detailed_stats
    FOR INSERT
    WITH CHECK (true);

CREATE POLICY "venue_detailed_stats_update_policy" ON public.venue_detailed_stats
    FOR UPDATE
    USING (true);

CREATE POLICY "venue_detailed_stats_delete_policy" ON public.venue_detailed_stats
    FOR DELETE
    USING (true);

-- 7. weather_data テーブル
ALTER TABLE public.weather_data ENABLE ROW LEVEL SECURITY;

CREATE POLICY "weather_data_select_policy" ON public.weather_data
    FOR SELECT
    USING (true);

CREATE POLICY "weather_data_insert_policy" ON public.weather_data
    FOR INSERT
    WITH CHECK (true);

CREATE POLICY "weather_data_update_policy" ON public.weather_data
    FOR UPDATE
    USING (true);

CREATE POLICY "weather_data_delete_policy" ON public.weather_data
    FOR DELETE
    USING (true);

-- 8. predictions テーブル
ALTER TABLE public.predictions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "predictions_select_policy" ON public.predictions
    FOR SELECT
    USING (true);

CREATE POLICY "predictions_insert_policy" ON public.predictions
    FOR INSERT
    WITH CHECK (true);

CREATE POLICY "predictions_update_policy" ON public.predictions
    FOR UPDATE
    USING (true);

CREATE POLICY "predictions_delete_policy" ON public.predictions
    FOR DELETE
    USING (true);

-- =====================================================
-- 完了メッセージ
-- =====================================================
-- 全テーブルにRLSが有効化され、基本ポリシーが設定されました。
-- 読み取り: 全員許可
-- 書き込み: 全員許可（サービスロール経由での実行を想定）
--
-- より厳密な制御が必要な場合は、各ポリシーのUSING句とWITH CHECK句を
-- 用途に応じて修正してください。
-- =====================================================
