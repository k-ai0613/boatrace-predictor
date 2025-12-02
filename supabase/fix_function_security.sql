-- =====================================================
-- 関数のsearch_pathセキュリティ問題を修正
-- 実行方法: Supabase SQL Editorでこのファイルの内容を実行
-- =====================================================

-- まず既存の関数を確認
-- SELECT proname, prosecdef, proconfig FROM pg_proc WHERE proname IN ('update_racer_statistics_timestamp', 'update_detailed_stats_timestamp');

-- =====================================================
-- 1. update_racer_statistics_timestamp 関数の修正
-- =====================================================

-- 既存の関数を削除して再作成
DROP FUNCTION IF EXISTS public.update_racer_statistics_timestamp() CASCADE;

-- セキュアな関数として再作成
CREATE OR REPLACE FUNCTION public.update_racer_statistics_timestamp()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp  -- search_pathを明示的に設定
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

-- 関数の所有者をpostgresに設定（オプション）
-- ALTER FUNCTION public.update_racer_statistics_timestamp() OWNER TO postgres;

-- =====================================================
-- 2. update_detailed_stats_timestamp 関数の修正
-- =====================================================

-- 既存の関数を削除して再作成
DROP FUNCTION IF EXISTS public.update_detailed_stats_timestamp() CASCADE;

-- セキュアな関数として再作成
CREATE OR REPLACE FUNCTION public.update_detailed_stats_timestamp()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp  -- search_pathを明示的に設定
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

-- 関数の所有者をpostgresに設定（オプション）
-- ALTER FUNCTION public.update_detailed_stats_timestamp() OWNER TO postgres;

-- =====================================================
-- トリガーの再作成（必要に応じて）
-- =====================================================

-- racer_statistics テーブルのトリガー
DROP TRIGGER IF EXISTS update_racer_statistics_timestamp_trigger ON public.racer_statistics;
CREATE TRIGGER update_racer_statistics_timestamp_trigger
    BEFORE UPDATE ON public.racer_statistics
    FOR EACH ROW
    EXECUTE FUNCTION public.update_racer_statistics_timestamp();

-- racer_detailed_stats テーブルのトリガー
DROP TRIGGER IF EXISTS update_racer_detailed_stats_timestamp_trigger ON public.racer_detailed_stats;
CREATE TRIGGER update_racer_detailed_stats_timestamp_trigger
    BEFORE UPDATE ON public.racer_detailed_stats
    FOR EACH ROW
    EXECUTE FUNCTION public.update_detailed_stats_timestamp();

-- venue_detailed_stats テーブルのトリガー（必要に応じて）
DROP TRIGGER IF EXISTS update_venue_detailed_stats_timestamp_trigger ON public.venue_detailed_stats;
CREATE TRIGGER update_venue_detailed_stats_timestamp_trigger
    BEFORE UPDATE ON public.venue_detailed_stats
    FOR EACH ROW
    EXECUTE FUNCTION public.update_detailed_stats_timestamp();

-- =====================================================
-- 完了メッセージ
-- =====================================================
-- 2つの関数のsearch_pathが明示的に設定され、
-- セキュリティ問題が修正されました。
--
-- SECURITY DEFINERを使用していますが、search_pathを
-- 'public, pg_temp'に固定することで、スキーマインジェクション
-- 攻撃を防止しています。
-- =====================================================
