# Supabase セキュリティ修正

このディレクトリには、Supabaseデータベースのセキュリティ問題を修正するためのSQLスクリプトが含まれています。

## 実行方法

### 1. Supabaseダッシュボードにログイン

https://app.supabase.com にアクセスし、プロジェクトを選択します。

### 2. SQL Editorを開く

左側のメニューから「SQL Editor」を選択します。

### 3. SQLスクリプトを実行

#### ステップ1: RLSポリシーの有効化

1. `enable_rls_policies.sql` の内容をコピー
2. SQL Editorに貼り付け
3. 「Run」ボタンをクリックして実行

これにより、以下の8つのテーブルにRLSが有効化されます：
- `races`
- `race_entries`
- `racers`
- `racer_statistics`
- `racer_detailed_stats`
- `venue_detailed_stats`
- `weather_data`
- `predictions`

#### ステップ2: 関数のセキュリティ修正

1. `fix_function_security.sql` の内容をコピー
2. SQL Editorに貼り付け
3. 「Run」ボタンをクリックして実行

これにより、以下の2つの関数のsearch_path問題が修正されます：
- `update_racer_statistics_timestamp`
- `update_detailed_stats_timestamp`

## 設定されたポリシー

### 読み取り（SELECT）
- **全員許可**（匿名ユーザー含む）
- 競艇データは公開情報のため、誰でも読み取り可能

### 書き込み（INSERT/UPDATE/DELETE）
- **全員許可**（サービスロール経由での実行を想定）
- Pythonスクリプトやバックエンドからの書き込みを許可

## カスタマイズ

より厳密なアクセス制御が必要な場合は、各ポリシーの `USING` 句と `WITH CHECK` 句を修正してください。

例：認証済みユーザーのみに書き込みを許可する場合：

```sql
CREATE POLICY "races_insert_policy" ON public.races
    FOR INSERT
    WITH CHECK (auth.role() = 'authenticated');
```

## 確認方法

SQLを実行後、Supabaseダッシュボードで以下を確認します：

1. 左メニューから「Database」→「Tables」を選択
2. 各テーブルを開き、「Policies」タブを確認
3. RLSが有効化され、ポリシーが表示されていることを確認

## トラブルシューティング

### エラー: "policy already exists"

既にポリシーが存在する場合は、先に削除してから実行します：

```sql
DROP POLICY IF EXISTS "races_select_policy" ON public.races;
```

### エラー: "function does not exist"

関数が既に別の定義で存在する場合は、`CASCADE` オプションで削除されるため、
トリガーも再作成されます。問題が解決しない場合は、手動でトリガーを確認してください：

```sql
SELECT * FROM information_schema.triggers
WHERE trigger_schema = 'public';
```
