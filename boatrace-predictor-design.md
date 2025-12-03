# 競艇予測分析ツール - 完全設計書

## 目次
1. [プロジェクト概要](#1-プロジェクト概要)
2. [システムアーキテクチャ](#2-システムアーキテクチャ)
3. [データベース設計](#3-データベース設計)
4. [データ収集戦略](#4-データ収集戦略)
5. [負荷制御とレート制限](#5-負荷制御とレート制限)
6. [天気データ収集](#6-天気データ収集)
7. [分析・予測エンジン](#7-分析予測エンジン)
8. [フロントエンド実装](#8-フロントエンド実装)
9. [開発フェーズ](#9-開発フェーズ)
10. [コード実装例](#10-コード実装例)

---

## 1. プロジェクト概要

### 1.1 目的
競艇レースの結果を多角的に分析し、各艇の勝率や推奨購入券種を提示するツール

### 1.2 主な機能
- レースデータと天気データの取得・蓄積
- 多角的な分析による予測
- 各艇の着順確率の算出（1号艇が1着になる確率:XX%など）
- 推奨購入券種の提案（単勝、2連単、3連単、2連複、3連複）

### 1.3 システム要件

| 項目 | 要件 |
|------|------|
| データ取得方法 | 自動スクレイピング |
| 過去データ期間 | 20年分（段階的に3-4ヶ月かけて収集） |
| リアルタイム性 | レース直前の最新データ取得 |
| 利用シーン | PC・スマホ両対応（レスポンシブデザイン） |
| 予算 | 0円（完全無料運用） |

---

## 2. システムアーキテクチャ

### 2.1 インフラ構成（コスト0円）

```
┌─────────────────────────────────────────────────────────┐
│                     GitHub Actions                       │
│  - データ収集（月2,000分無料）                              │
│  - 定期実行スケジューラー                                   │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    Supabase（無料枠）                     │
│  - PostgreSQL（500MB）                                   │
│  - Storage（1GB）                                        │
│  - Auth（50,000 MAU）                                    │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│              Vercel（無料）                               │
│  - Next.js フロントエンド                                 │
│  - Serverless Functions（バックエンドAPI）                │
└─────────────────────────────────────────────────────────┘
```

### 2.2 データ量見積もり

```
レース数: 24場 × 12R × 365日 × 20年 = 約210万レース
データ量: 
  - 1レース × 6艇 = 6レコード
  - 1レコード ≈ 1KB
  - 合計: 約1.2GB（圧縮後500MB程度）

対策:
  - 直近1年分のみDBに保存（約60MB）
  - 古いデータはJSON圧縮してGitHub Releaseに保存
  - 分析時に必要に応じてロード
```

### 2.3 技術スタック

| レイヤー | 技術 |
|---------|------|
| **フロントエンド** | Next.js 14 (App Router), React, TypeScript |
| **UIライブラリ** | Tailwind CSS, shadcn/ui |
| **グラフ表示** | Recharts |
| **バックエンド** | Vercel Serverless Functions |
| **データ収集** | Python 3.11, aiohttp, BeautifulSoup4 |
| **データベース** | Supabase (PostgreSQL 15) |
| **機械学習** | scikit-learn, XGBoost, pandas |
| **定期実行** | GitHub Actions |

---

## 3. データベース設計

### 3.1 ER図

```
┌──────────────┐       ┌──────────────────┐       ┌──────────────┐
│   races      │──1:N──│  race_entries    │──N:1──│   racers     │
│              │       │                  │       │              │
│ - id         │       │ - id             │       │ - id         │
│ - race_date  │       │ - race_id        │       │ - racer_num  │
│ - venue_id   │       │ - boat_number    │       │ - name       │
│ - race_num   │       │ - racer_id       │       │ - grade      │
│ - grade      │       │ - motor_number   │       └──────────────┘
└──────────────┘       │ - start_timing   │
                       │ - course         │
                       │ - result_position│
                       └──────────────────┘
                                │
                                │N:1
                                ↓
                       ┌──────────────────┐
                       │     motors       │
                       │                  │
                       │ - id             │
                       │ - venue_id       │
                       │ - motor_number   │
                       │ - year           │
                       │ - second_rate    │
                       └──────────────────┘
```

### 3.2 テーブル定義

#### races（レース基本情報）
```sql
CREATE TABLE races (
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
```

#### race_entries（出走情報）
```sql
CREATE TABLE race_entries (
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
```

#### racers（選手マスタ）
```sql
CREATE TABLE racers (
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
```

#### racer_stats（選手成績）
```sql
CREATE TABLE racer_stats (
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
```

#### motors（モーター情報）
```sql
CREATE TABLE motors (
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
```

#### weather_data（天気情報）
```sql
CREATE TABLE weather_data (
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
```

#### predictions（予測結果）
```sql
CREATE TABLE predictions (
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
```

---

## 4. データ収集戦略

### 4.1 過去20年分の段階的収集プラン

| フェーズ | 期間 | 優先度 | 推定日数 | 理由 |
|---------|------|--------|---------|------|
| Phase 1 | 直近1年（2024年） | 最高 | 5日 | 最新データで精度検証 |
| Phase 2 | 2-3年前（2022-2023） | 高 | 10日 | モデル訓練の基礎データ |
| Phase 3 | 4-5年前（2020-2021） | 中 | 10日 | データ量を増やす |
| Phase 4 | 6-10年前（2015-2019） | 中 | 25日 | 長期傾向の把握 |
| Phase 5 | 11-20年前（2005-2014） | 低 | 50日 | 履歴データ（参考程度） |

**合計推定期間: 約100日（3-4ヶ月）**

### 4.2 データソース

#### 競艇公式データ
```
ベースURL: https://www.boatrace.jp

【レース結果】
URL: /owpc/pc/race/raceresult
パラメータ:
  - hd: 日付 (YYYYMMDD)
  - jcd: 場コード (01-24)
  - rno: レース番号 (1-12)

【選手データ】
URL: /owpc/pc/data/racersearch
パラメータ:
  - toban: 登録番号

【モーターデータ】
レース結果ページから抽出
```

#### 天気データ
各ボートレース場の公式サイトから取得（後述）

### 4.3 収集スケジュール

```yaml
# GitHub Actions スケジュール

過去データ収集:
  実行: 毎日1回（深夜3時 JST）
  処理: 1日分のみ取得
  期間: 3-4ヶ月で完了

リアルタイムデータ:
  実行: 1日3回（7時、12時、17時 JST）
  処理: 当日のレース結果と天気
  目的: 最新情報の維持

天気データ:
  実行: 1日3回（同上）
  処理: 全24場の天気情報
  所要時間: 約2-3分
```

---

## 5. 負荷制御とレート制限

### 5.1 基本方針

**相手サーバーへの負荷を最小限に抑える**

| 制限項目 | 設定値 | 理由 |
|---------|--------|------|
| リクエスト間隔 | 2-3秒 | サーバー負荷軽減 |
| 同時接続数 | 2-3リクエスト | 並列処理の制限 |
| 1分あたり | 20リクエスト | バースト制御 |
| 1時間あたり | 500リクエスト | 持続的な制限 |
| 1日あたり | 10,000リクエスト | 全体上限 |
| User-Agent | 適切に設定 | ボット識別 |
| リトライ | Exponential backoff | 過度な再試行防止 |

### 5.2 負荷見積もり

```
【1日あたりのリクエスト数】

過去データ収集（1日分）:
  24場 × 12R = 288リクエスト
  間隔: 2秒/リクエスト
  所要時間: 約10分

天気データ収集（1日3回）:
  24場 × 3回 = 72リクエスト
  間隔: 3秒/リクエスト
  所要時間: 約4分/回

合計:
  約360リクエスト/日
  総所要時間: 約25分/日
  平均: 0.004リクエスト/秒（非常に低負荷）
```

### 5.3 レート制限実装

#### RateLimiter クラス
```python
import asyncio
import time
from collections import deque

class RateLimiter:
    """
    複数の時間窓でリクエストレートを制限
    
    Args:
        requests_per_second: 秒あたりのリクエスト数
        requests_per_minute: 分あたりのリクエスト数
        requests_per_hour: 時間あたりのリクエスト数
        requests_per_day: 日あたりのリクエスト数
        concurrent_requests: 同時実行可能なリクエスト数
    """
    
    def __init__(
        self,
        requests_per_second=0.5,   # 2秒に1リクエスト
        requests_per_minute=20,    # 1分に20リクエスト
        requests_per_hour=500,     # 1時間に500リクエスト
        requests_per_day=10000,    # 1日10,000リクエスト
        concurrent_requests=3       # 同時実行3つまで
    ):
        self.requests_per_second = requests_per_second
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.requests_per_day = requests_per_day
        self.concurrent_requests = concurrent_requests
        
        self.request_times = deque()
        self.semaphore = asyncio.Semaphore(concurrent_requests)
        
    async def acquire(self):
        """リクエスト許可を取得"""
        async with self.semaphore:
            await self._wait_if_needed()
            self.request_times.append(time.time())
            
    async def _wait_if_needed(self):
        """必要に応じて待機"""
        now = time.time()
        
        # 古いレコードを削除
        self._cleanup_old_requests(now)
        
        # 各制限をチェック
        wait_time = max(
            self._check_limit(now, 1, self.requests_per_second),
            self._check_limit(now, 60, self.requests_per_minute),
            self._check_limit(now, 3600, self.requests_per_hour),
            self._check_limit(now, 86400, self.requests_per_day)
        )
        
        if wait_time > 0:
            await asyncio.sleep(wait_time)
    
    def _cleanup_old_requests(self, now):
        """24時間以上前のレコードを削除"""
        while self.request_times and now - self.request_times[0] > 86400:
            self.request_times.popleft()
    
    def _check_limit(self, now, window_seconds, max_requests):
        """指定期間内のリクエスト数をチェック"""
        cutoff = now - window_seconds
        recent_requests = sum(1 for t in self.request_times if t > cutoff)
        
        if recent_requests >= max_requests:
            oldest_in_window = next(t for t in self.request_times if t > cutoff)
            return (oldest_in_window + window_seconds) - now
        return 0
```

---

## 6. 天気データ収集

### 6.1 ボートレース場マスタ

全24場の公式サイトURLとエンドポイント:

```python
VENUES = {
    # 関東地区
    1: {
        'name': '桐生',
        'prefecture': '群馬県',
        'region': '関東',
        'official_url': 'https://www.boatrace-kiryu.jp/',
        'weather_url': 'https://www.boatrace-kiryu.jp/modules/yosou/group-yosou.php?day='
    },
    2: {
        'name': '戸田',
        'prefecture': '埼玉県',
        'region': '関東',
        'official_url': 'https://www.boatrace-toda.jp/',
        'weather_url': 'https://www.boatrace-toda.jp/modules/yosou/group-yosou.php?day='
    },
    3: {
        'name': '江戸川',
        'prefecture': '東京都',
        'region': '関東',
        'official_url': 'https://www.boatrace-edogawa.jp/',
        'weather_url': 'https://www.boatrace-edogawa.jp/modules/yosou/group-yosou.php?day='
    },
    4: {
        'name': '平和島',
        'prefecture': '東京都',
        'region': '関東',
        'official_url': 'https://www.boatrace-heiwajima.jp/',
        'weather_url': 'https://www.boatrace-heiwajima.jp/modules/yosou/group-yosou.php?day='
    },
    5: {
        'name': '多摩川',
        'prefecture': '東京都',
        'region': '関東',
        'official_url': 'https://www.boatrace-tamagawa.jp/',
        'weather_url': 'https://www.boatrace-tamagawa.jp/modules/yosou/group-yosou.php?day='
    },
    
    # 東海地区
    6: {
        'name': '浜名湖',
        'prefecture': '静岡県',
        'region': '東海',
        'official_url': 'https://www.boatrace-hamanako.jp/',
        'weather_url': 'https://www.boatrace-hamanako.jp/modules/yosou/group-yosou.php?day='
    },
    7: {
        'name': '蒲郡',
        'prefecture': '愛知県',
        'region': '東海',
        'official_url': 'https://www.boatrace-gamagori.jp/',
        'weather_url': 'https://www.boatrace-gamagori.jp/modules/yosou/group-yosou.php?day='
    },
    8: {
        'name': '常滑',
        'prefecture': '愛知県',
        'region': '東海',
        'official_url': 'https://www.boatrace-tokoname.jp/',
        'weather_url': 'https://www.boatrace-tokoname.jp/modules/yosou/group-yosou.php?day='
    },
    9: {
        'name': '津',
        'prefecture': '三重県',
        'region': '東海',
        'official_url': 'https://www.boatrace-tsu.jp/',
        'weather_url': 'https://www.boatrace-tsu.jp/modules/yosou/group-yosou.php?day='
    },
    
    # 近畿地区
    10: {
        'name': '三国',
        'prefecture': '福井県',
        'region': '近畿',
        'official_url': 'https://www.boatrace-mikuni.jp/',
        'weather_url': 'https://www.boatrace-mikuni.jp/modules/yosou/group-yosou.php?day='
    },
    11: {
        'name': 'びわこ',
        'prefecture': '滋賀県',
        'region': '近畿',
        'official_url': 'https://www.boatrace-biwako.jp/',
        'weather_url': 'https://www.boatrace-biwako.jp/modules/yosou/group-yosou.php?day='
    },
    12: {
        'name': '住之江',
        'prefecture': '大阪府',
        'region': '近畿',
        'official_url': 'https://www.boatrace-suminoe.jp/',
        'weather_url': 'https://www.boatrace-suminoe.jp/modules/yosou/group-yosou.php?day='
    },
    13: {
        'name': '尼崎',
        'prefecture': '兵庫県',
        'region': '近畿',
        'official_url': 'https://www.boatrace-amagasaki.jp/',
        'weather_url': 'https://www.boatrace-amagasaki.jp/modules/yosou/group-yosou.php?day='
    },
    
    # 四国地区
    14: {
        'name': '鳴門',
        'prefecture': '徳島県',
        'region': '四国',
        'official_url': 'https://www.boatrace-naruto.jp/',
        'weather_url': 'https://www.boatrace-naruto.jp/modules/yosou/group-yosou.php?day='
    },
    15: {
        'name': '丸亀',
        'prefecture': '香川県',
        'region': '四国',
        'official_url': 'https://www.boatrace-marugame.jp/',
        'weather_url': 'https://www.boatrace-marugame.jp/modules/yosou/group-yosou.php?day='
    },
    
    # 中国地区
    16: {
        'name': '児島',
        'prefecture': '岡山県',
        'region': '中国',
        'official_url': 'https://www.boatrace-kojima.jp/',
        'weather_url': 'https://www.boatrace-kojima.jp/modules/yosou/group-yosou.php?day='
    },
    17: {
        'name': '宮島',
        'prefecture': '広島県',
        'region': '中国',
        'official_url': 'https://www.boatrace-miyajima.com/',
        'weather_url': 'https://www.boatrace-miyajima.com/modules/yosou/group-yosou.php?day='
    },
    18: {
        'name': '徳山',
        'prefecture': '山口県',
        'region': '中国',
        'official_url': 'https://www.boatrace-tokuyama.jp/',
        'weather_url': 'https://www.boatrace-tokuyama.jp/modules/yosou/group-yosou.php?day='
    },
    19: {
        'name': '下関',
        'prefecture': '山口県',
        'region': '中国',
        'official_url': 'https://www.boatrace-shimonoseki.jp/',
        'weather_url': 'https://www.boatrace-shimonoseki.jp/modules/yosou/group-yosou.php?day='
    },
    
    # 九州地区
    20: {
        'name': '若松',
        'prefecture': '福岡県',
        'region': '九州',
        'official_url': 'https://www.boatrace-wakamatsu.com/',
        'weather_url': 'https://www.boatrace-wakamatsu.com/modules/yosou/group-yosou.php?day='
    },
    21: {
        'name': '芦屋',
        'prefecture': '福岡県',
        'region': '九州',
        'official_url': 'https://www.boatrace-ashiya.com/',
        'weather_url': 'https://www.boatrace-ashiya.com/modules/yosou/group-yosou.php?day='
    },
    22: {
        'name': '福岡',
        'prefecture': '福岡県',
        'region': '九州',
        'official_url': 'https://www.boatrace-fukuoka.com/',
        'weather_url': 'https://www.boatrace-fukuoka.com/modules/yosou/group-yosou.php?day='
    },
    23: {
        'name': '唐津',
        'prefecture': '佐賀県',
        'region': '九州',
        'official_url': 'https://www.boatrace-karatsu.jp/',
        'weather_url': 'https://www.boatrace-karatsu.jp/modules/yosou/group-yosou.php?day='
    },
    24: {
        'name': '大村',
        'prefecture': '長崎県',
        'region': '九州',
        'official_url': 'https://www.boatrace-omura.jp/',
        'weather_url': 'https://www.boatrace-omura.jp/modules/yosou/group-yosou.php?day='
    }
}
```

### 6.2 天気データの重要性

競艇において天気情報（特に風）は結果に大きく影響:

| 要素 | 重要度 | 影響 |
|------|--------|------|
| **風速・風向き** | ★★★★★ | コース有利不利が変わる |
| 気温 | ★★★☆☆ | モーター性能に影響 |
| 波高 | ★★★★☆ | 水面の走りやすさ |
| 水温 | ★★☆☆☆ | 季節的な傾向 |

### 6.3 収集タイミング

```
1日3回の収集:
  07:00 JST - 午前のレース前
  12:00 JST - 昼のレース前
  17:00 JST - 夜のレース前

リアルタイムデータ:
  レース直前の実測値を優先的に使用
  予測値よりも精度が高い
```

---

## 7. 分析・予測エンジン

### 7.1 特徴量設計

#### 主要特徴量（合計50-100個程度）

**1. 選手関連（15-20特徴量）**
```python
- racer_win_rate          # 全国勝率
- racer_win_rate_venue    # 当地勝率
- racer_second_rate       # 2連対率
- racer_third_rate        # 3連対率
- racer_grade_score       # 級別スコア (A1=4, A2=3, B1=2, B2=1)
- racer_avg_st            # 平均スタートタイミング
- racer_avg_st_venue      # 当地平均ST
- racer_recent_form       # 直近5走の平均着順
- racer_course_win_rate   # このコースでの勝率
- racer_venue_experience  # 当地出走回数
```

**2. モーター関連（5-10特徴量）**
```python
- motor_second_rate       # モーター2連対率
- motor_third_rate        # モーター3連対率
- motor_recent_races      # 節間（期間中）の成績
- motor_age               # モーター使用期間
```

**3. コース・場所関連（10-15特徴量）**
```python
- course                  # 進入コース (1-6)
- course_win_rate_venue   # この場でのコース別1着率
- venue_characteristic    # 場の特性スコア
- is_inner_course         # インコース(1-3)フラグ
```

**4. 天気関連（10-15特徴量）**
```python
- wind_speed              # 風速
- wind_direction          # 風向き(角度)
- wind_impact_score       # コースごとの風の影響度
- temperature             # 気温
- weather_condition_num   # 天気状態(晴=1, 曇=2, 雨=3)
- wave_height             # 波高
```

**5. 複合特徴量（10-20特徴量）**
```python
- racer_motor_score       # 選手勝率 × モーター2連対率
- course_advantage        # コース勝率 × 選手級別スコア
- wind_course_interaction # 風向き × コース
- racer_venue_compatibility # 選手と場の相性
```

**6. 時系列特徴量（5-10特徴量）**
```python
- recent_5races_avg       # 直近5走の平均着順
- recent_10races_avg      # 直近10走の平均着順
- trend_score             # 成績のトレンド（上昇/下降）
```

### 7.2 特徴量エンジニアリング実装

```python
import pandas as pd
import numpy as np

class FeatureEngineer:
    """特徴量を生成するクラス"""
    
    def __init__(self, historical_data):
        """
        Args:
            historical_data: 過去のレースデータ（DataFrame）
        """
        self.historical_data = historical_data
        self.venue_course_stats = self._calculate_venue_course_stats()
        
    def create_features(self, race_data):
        """
        1レース分の特徴量を生成
        
        Args:
            race_data: 1レースの6艇分のデータ（DataFrame）
            
        Returns:
            DataFrame: 特徴量（6行 × 特徴量数列）
        """
        features_list = []
        
        for idx, boat in race_data.iterrows():
            features = {}
            
            # 1. 選手関連
            features.update(self._racer_features(boat))
            
            # 2. モーター関連
            features.update(self._motor_features(boat))
            
            # 3. コース関連
            features.update(self._course_features(boat))
            
            # 4. 天気関連
            features.update(self._weather_features(boat))
            
            # 5. 複合特徴量
            features.update(self._composite_features(boat, features))
            
            # 6. 時系列特徴量
            features.update(self._temporal_features(boat))
            
            features_list.append(features)
        
        return pd.DataFrame(features_list)
    
    def _racer_features(self, boat):
        """選手関連の特徴量"""
        return {
            'racer_win_rate': boat['racer_win_rate'],
            'racer_win_rate_venue': boat['racer_win_rate_venue'],
            'racer_second_rate': boat['racer_second_rate'],
            'racer_third_rate': boat['racer_third_rate'],
            'racer_grade_score': self._grade_to_score(boat['grade']),
            'racer_avg_st': boat['avg_start_timing'],
            'racer_avg_st_venue': boat.get('avg_st_venue', boat['avg_start_timing']),
            'racer_venue_experience': boat.get('venue_race_count', 0),
        }
    
    def _motor_features(self, boat):
        """モーター関連の特徴量"""
        return {
            'motor_second_rate': boat['motor_second_rate'],
            'motor_third_rate': boat['motor_third_rate'],
        }
    
    def _course_features(self, boat):
        """コース関連の特徴量"""
        venue_id = boat['venue_id']
        course = boat['course']
        
        # この場・このコースでの1着率
        course_win_rate = self.venue_course_stats.get(
            (venue_id, course), 
            {'win_rate': 0.15}  # デフォルト値
        )['win_rate']
        
        return {
            'course': course,
            'course_win_rate_venue': course_win_rate,
            'is_inner_course': 1 if course <= 3 else 0,
            'is_course_1': 1 if course == 1 else 0,
        }
    
    def _weather_features(self, boat):
        """天気関連の特徴量"""
        wind_speed = boat.get('wind_speed', 0)
        wind_direction = boat.get('wind_direction', 0)
        course = boat['course']
        
        return {
            'wind_speed': wind_speed,
            'wind_direction': wind_direction,
            'wind_impact_score': self._calculate_wind_impact(
                wind_speed, wind_direction, course
            ),
            'temperature': boat.get('temperature', 20),
            'wave_height': boat.get('wave_height', 0),
        }
    
    def _composite_features(self, boat, base_features):
        """複合特徴量"""
        return {
            'racer_motor_score': (
                base_features['racer_win_rate'] * 
                base_features['motor_second_rate']
            ),
            'course_advantage': (
                base_features['course_win_rate_venue'] * 
                base_features['racer_grade_score']
            ),
            'total_ability_score': (
                base_features['racer_win_rate'] * 0.4 +
                base_features['motor_second_rate'] * 0.3 +
                base_features['course_win_rate_venue'] * 0.3
            )
        }
    
    def _temporal_features(self, boat):
        """時系列特徴量"""
        racer_id = boat['racer_id']
        recent_races = self._get_recent_races(racer_id, n=10)
        
        if len(recent_races) == 0:
            return {
                'recent_5races_avg': 3.5,
                'recent_10races_avg': 3.5,
                'trend_score': 0
            }
        
        recent_5 = recent_races.head(5)['result_position'].mean()
        recent_10 = recent_races['result_position'].mean()
        
        # トレンドスコア（最近が良ければプラス）
        if len(recent_races) >= 5:
            first_half = recent_races.tail(5)['result_position'].mean()
            second_half = recent_races.head(5)['result_position'].mean()
            trend_score = first_half - second_half  # 着順が下がる=良い
        else:
            trend_score = 0
        
        return {
            'recent_5races_avg': recent_5,
            'recent_10races_avg': recent_10,
            'trend_score': trend_score
        }
    
    def _grade_to_score(self, grade):
        """級別をスコア化"""
        scores = {'A1': 4, 'A2': 3, 'B1': 2, 'B2': 1}
        return scores.get(grade, 0)
    
    def _calculate_wind_impact(self, wind_speed, wind_direction, course):
        """
        風がコースに与える影響を計算
        
        風向きとコースの関係:
        - 追い風: スピードが出やすい
        - 向かい風: スピードが落ちる
        - 横風: コースによって有利不利
        """
        # 簡易的な計算（実際はもっと複雑）
        if wind_speed < 2:
            return 0  # 影響小
        
        # コース1は追い風で有利、向かい風で不利
        base_impact = wind_speed * np.cos(np.radians(wind_direction - 90))
        
        if course == 1:
            return base_impact
        elif course in [2, 3]:
            return base_impact * 0.5
        else:
            return -base_impact * 0.3
    
    def _calculate_venue_course_stats(self):
        """場・コース別の統計を事前計算"""
        stats = {}
        
        for venue_id in range(1, 25):
            venue_data = self.historical_data[
                self.historical_data['venue_id'] == venue_id
            ]
            
            for course in range(1, 7):
                course_data = venue_data[venue_data['course'] == course]
                
                if len(course_data) > 0:
                    win_rate = (course_data['result_position'] == 1).mean()
                    stats[(venue_id, course)] = {'win_rate': win_rate}
        
        return stats
    
    def _get_recent_races(self, racer_id, n=10):
        """選手の直近n走を取得"""
        racer_races = self.historical_data[
            self.historical_data['racer_id'] == racer_id
        ].sort_values('race_date', ascending=False)
        
        return racer_races.head(n)
```

### 7.3 予測モデル

```python
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, log_loss
import pickle
import numpy as np

class RacePredictor:
    """レース結果を予測するクラス"""
    
    def __init__(self):
        self.model = None
        self.feature_names = None
        
    def train(self, training_data, labels):
        """
        モデルを訓練
        
        Args:
            training_data: 特徴量（DataFrame）
            labels: 着順ラベル (1-6)
        """
        X = training_data
        y = labels - 1  # 0-5に変換（XGBoostのため）
        
        # 訓練・検証データに分割
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # XGBoostで多クラス分類
        self.model = xgb.XGBClassifier(
            objective='multi:softprob',
            num_class=6,              # 1-6着
            max_depth=8,
            learning_rate=0.05,
            n_estimators=300,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric='mlogloss'
        )
        
        # 訓練
        eval_set = [(X_train, y_train), (X_test, y_test)]
        self.model.fit(
            X_train, y_train,
            eval_set=eval_set,
            early_stopping_rounds=20,
            verbose=True
        )
        
        # 評価
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        y_pred_proba = self.model.predict_proba(X_test)
        logloss = log_loss(y_test, y_pred_proba)
        
        print(f"\n=== Model Evaluation ===")
        print(f"Accuracy: {accuracy:.3f}")
        print(f"Log Loss: {logloss:.3f}")
        
        # 特徴量重要度
        self._print_feature_importance(X.columns)
        
        self.feature_names = X.columns.tolist()
        
    def predict_probabilities(self, race_features):
        """
        各艇の着順確率を予測
        
        Args:
            race_features: 1レース6艇分の特徴量（DataFrame）
            
        Returns:
            numpy.ndarray: 確率行列 (6艇 × 6着順)
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        probs = self.model.predict_proba(race_features)
        return probs  # shape: (6, 6)
    
    def recommend_bets(self, probabilities, odds_data=None):
        """
        推奨購入券種を計算
        
        Args:
            probabilities: 着順確率 (6艇 × 6着順)
            odds_data: オッズデータ（オプション）
            
        Returns:
            list: 推奨購入券種のリスト
        """
        recommendations = []
        
        # 1. 単勝
        for boat in range(6):
            win_prob = probabilities[boat][0]  # 1着確率
            
            if odds_data and 'win' in odds_data:
                expected_value = win_prob * odds_data['win'][boat]
            else:
                # オッズがない場合は確率のみで判断
                expected_value = win_prob
            
            if win_prob > 0.25:  # 25%以上の確率
                recommendations.append({
                    'type': '単勝',
                    'bet': f"{boat + 1}",
                    'probability': win_prob,
                    'expected_value': expected_value if odds_data else None,
                    'confidence': self._calculate_confidence(win_prob)
                })
        
        # 2. 2連単
        for boat1 in range(6):
            for boat2 in range(6):
                if boat1 == boat2:
                    continue
                
                # 1着・2着の同時確率
                prob = probabilities[boat1][0] * probabilities[boat2][1]
                
                if odds_data and 'exacta' in odds_data:
                    expected_value = prob * odds_data['exacta'][boat1][boat2]
                else:
                    expected_value = prob
                
                if prob > 0.10:  # 10%以上
                    recommendations.append({
                        'type': '2連単',
                        'bet': f"{boat1 + 1}-{boat2 + 1}",
                        'probability': prob,
                        'expected_value': expected_value if odds_data else None,
                        'confidence': self._calculate_confidence(prob)
                    })
        
        # 3. 3連単
        for boat1 in range(6):
            for boat2 in range(6):
                for boat3 in range(6):
                    if boat1 == boat2 or boat2 == boat3 or boat1 == boat3:
                        continue
                    
                    prob = (probabilities[boat1][0] * 
                           probabilities[boat2][1] * 
                           probabilities[boat3][2])
                    
                    if prob > 0.05:  # 5%以上
                        recommendations.append({
                            'type': '3連単',
                            'bet': f"{boat1 + 1}-{boat2 + 1}-{boat3 + 1}",
                            'probability': prob,
                            'expected_value': None,  # オッズデータ必要
                            'confidence': self._calculate_confidence(prob)
                        })
        
        # 4. 2連複
        for boat1 in range(6):
            for boat2 in range(boat1 + 1, 6):
                # boat1-boat2 または boat2-boat1 の確率
                prob = (probabilities[boat1][0] * probabilities[boat2][1] +
                       probabilities[boat2][0] * probabilities[boat1][1])
                
                if prob > 0.15:
                    recommendations.append({
                        'type': '2連複',
                        'bet': f"{boat1 + 1}={boat2 + 1}",
                        'probability': prob,
                        'expected_value': None,
                        'confidence': self._calculate_confidence(prob)
                    })
        
        # 3連複も同様に実装可能
        
        # 期待値または確率でソート
        if odds_data:
            recommendations.sort(
                key=lambda x: x['expected_value'] or 0, 
                reverse=True
            )
        else:
            recommendations.sort(
                key=lambda x: x['probability'], 
                reverse=True
            )
        
        return recommendations
    
    def _calculate_confidence(self, probability):
        """信頼度を計算"""
        if probability > 0.5:
            return "高"
        elif probability > 0.3:
            return "中"
        else:
            return "低"
    
    def _print_feature_importance(self, feature_names):
        """特徴量重要度を表示"""
        importance = self.model.feature_importances_
        indices = np.argsort(importance)[::-1]
        
        print("\n=== Feature Importance (Top 20) ===")
        for i in range(min(20, len(indices))):
            idx = indices[i]
            print(f"{i+1}. {feature_names[idx]}: {importance[idx]:.4f}")
    
    def save(self, filepath):
        """モデルを保存"""
        model_data = {
            'model': self.model,
            'feature_names': self.feature_names
        }
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        print(f"Model saved to {filepath}")
    
    def load(self, filepath):
        """モデルを読み込み"""
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        self.model = model_data['model']
        self.feature_names = model_data['feature_names']
        print(f"Model loaded from {filepath}")
```

### 7.4 モデル評価指標

```python
from sklearn.metrics import confusion_matrix, classification_report
import matplotlib.pyplot as plt
import seaborn as sns

class ModelEvaluator:
    """モデルの性能を評価"""
    
    @staticmethod
    def evaluate(y_true, y_pred, y_pred_proba):
        """
        総合評価を実施
        
        Args:
            y_true: 実際の着順
            y_pred: 予測着順
            y_pred_proba: 予測確率
        """
        # 1. 精度
        accuracy = accuracy_score(y_true, y_pred)
        print(f"Overall Accuracy: {accuracy:.3f}")
        
        # 2. 1着予測の精度（最重要）
        win_accuracy = ModelEvaluator._calculate_win_accuracy(
            y_true, y_pred_proba
        )
        print(f"Win Prediction Accuracy: {win_accuracy:.3f}")
        
        # 3. 混同行列
        ModelEvaluator._plot_confusion_matrix(y_true, y_pred)
        
        # 4. クラス別レポート
        print("\n=== Classification Report ===")
        print(classification_report(
            y_true, y_pred,
            target_names=['1着', '2着', '3着', '4着', '5着', '6着']
        ))
        
        # 5. 期待値の検証
        ModelEvaluator._evaluate_expected_value(y_true, y_pred_proba)
    
    @staticmethod
    def _calculate_win_accuracy(y_true, y_pred_proba):
        """1着予測の精度を計算"""
        predicted_winners = np.argmax(y_pred_proba[:, :, 0], axis=1)
        actual_winners = np.where(y_true == 1)[0]
        
        correct = np.sum(predicted_winners == actual_winners)
        return correct / len(actual_winners)
    
    @staticmethod
    def _plot_confusion_matrix(y_true, y_pred):
        """混同行列を可視化"""
        cm = confusion_matrix(y_true, y_pred)
        
        plt.figure(figsize=(10, 8))
        sns.heatmap(
            cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=['1着', '2着', '3着', '4着', '5着', '6着'],
            yticklabels=['1着', '2着', '3着', '4着', '5着', '6着']
        )
        plt.xlabel('Predicted')
        plt.ylabel('Actual')
        plt.title('Confusion Matrix')
        plt.tight_layout()
        plt.savefig('confusion_matrix.png')
        print("Confusion matrix saved to confusion_matrix.png")
    
    @staticmethod
    def _evaluate_expected_value(y_true, y_pred_proba):
        """期待値の検証（仮想購入シミュレーション）"""
        # 実装省略（実際のオッズデータが必要）
        pass
```

---

## 8. フロントエンド実装

### 8.1 ディレクトリ構造

```
boatrace-predictor/
├── app/
│   ├── page.tsx                      # トップページ
│   ├── layout.tsx                    # 共通レイアウト
│   ├── races/
│   │   ├── page.tsx                  # レース一覧
│   │   └── [date]/
│   │       └── [venue]/
│   │           └── [race]/
│   │               └── page.tsx      # レース詳細・予測表示
│   ├── analysis/
│   │   └── page.tsx                  # 分析ダッシュボード
│   └── api/
│       ├── races/
│       │   └── route.ts              # レース一覧API
│       ├── predict/
│       │   └── route.ts              # 予測API
│       └── weather/
│           └── route.ts              # 天気データAPI
├── components/
│   ├── ui/                           # shadcn/ui コンポーネント
│   ├── RaceSelector.tsx              # レース選択UI
│   ├── PredictionDisplay.tsx         # 予測結果表示
│   ├── ProbabilityChart.tsx          # 確率チャート
│   ├── RecommendedBets.tsx           # 推奨購入券種
│   ├── RacerInfo.tsx                 # 選手情報
│   ├── WeatherDisplay.tsx            # 天気情報
│   └── HistoricalPerformance.tsx    # 過去成績
├── lib/
│   ├── supabase.ts                   # Supabase クライアント
│   ├── predictor.ts                  # 予測ロジック
│   └── utils.ts                      # ユーティリティ関数
├── types/
│   └── index.ts                      # 型定義
└── public/
    └── images/                       # 画像アセット
```

### 8.2 主要コンポーネント

#### PredictionDisplay.tsx
```typescript
'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'

interface Prediction {
  boatNumber: number
  racerName: string
  racerNumber: number
  grade: string
  motorNumber: string
  winProb: number
  secondProb: number
  thirdProb: number
  fourthProb: number
  fifthProb: number
  sixthProb: number
}

interface PredictionDisplayProps {
  predictions: Prediction[]
  weather?: {
    temperature: number
    windSpeed: number
    windDirection: string
  }
}

export default function PredictionDisplay({ 
  predictions,
  weather 
}: PredictionDisplayProps) {
  // 1着確率でソート
  const sortedPredictions = [...predictions].sort(
    (a, b) => b.winProb - a.winProb
  )

  return (
    <div className="space-y-6">
      {/* 天気情報 */}
      {weather && (
        <Card>
          <CardHeader>
            <CardTitle>気象条件</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-6">
              <div>
                <p className="text-sm text-gray-600">気温</p>
                <p className="text-2xl font-bold">{weather.temperature}°C</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">風速</p>
                <p className="text-2xl font-bold">{weather.windSpeed}m/s</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">風向き</p>
                <p className="text-2xl font-bold">{weather.windDirection}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 予測結果 */}
      <div className="space-y-4">
        <h2 className="text-2xl font-bold">着順確率予測</h2>
        
        {sortedPredictions.map((pred, index) => (
          <Card key={pred.boatNumber} className="hover:shadow-lg transition-shadow">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between mb-4">
                {/* 艇番と選手情報 */}
                <div className="flex items-center gap-4">
                  <div 
                    className={`
                      text-4xl font-bold w-16 h-16 rounded-full 
                      flex items-center justify-center text-white
                      ${getBoatColor(pred.boatNumber)}
                    `}
                  >
                    {pred.boatNumber}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="text-xl font-semibold">{pred.racerName}</p>
                      <Badge variant={getGradeBadgeVariant(pred.grade)}>
                        {pred.grade}
                      </Badge>
                    </div>
                    <p className="text-sm text-gray-600">
                      登録: {pred.racerNumber} / モーター: {pred.motorNumber}
                    </p>
                  </div>
                </div>
                
                {/* 1着確率 */}
                <div className="text-right">
                  <p className="text-sm text-gray-600">1着確率</p>
                  <p className="text-4xl font-bold text-blue-600">
                    {(pred.winProb * 100).toFixed(1)}%
                  </p>
                  {index === 0 && (
                    <Badge className="mt-2" variant="default">
                      本命
                    </Badge>
                  )}
                </div>
              </div>
              
              {/* 確率バー */}
              <div className="space-y-2">
                <ProbabilityBar 
                  label="1着" 
                  probability={pred.winProb} 
                  color="blue"
                />
                <ProbabilityBar 
                  label="2着" 
                  probability={pred.secondProb} 
                  color="red"
                />
                <ProbabilityBar 
                  label="3着" 
                  probability={pred.thirdProb} 
                  color="green"
                />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

function ProbabilityBar({ 
  label, 
  probability, 
  color 
}: { 
  label: string
  probability: number
  color: string 
}) {
  const percentage = probability * 100

  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-600">{label}</span>
        <span className="font-semibold">{percentage.toFixed(1)}%</span>
      </div>
      <Progress 
        value={percentage} 
        className={`h-2 ${getProgressColor(color)}`}
      />
    </div>
  )
}

function getBoatColor(boatNumber: number): string {
  const colors = {
    1: 'bg-white text-black border-2 border-black',
    2: 'bg-black',
    3: 'bg-red-600',
    4: 'bg-blue-600',
    5: 'bg-yellow-500 text-black',
    6: 'bg-green-600'
  }
  return colors[boatNumber as keyof typeof colors] || 'bg-gray-600'
}

function getGradeBadgeVariant(grade: string) {
  if (grade === 'A1') return 'default'
  if (grade === 'A2') return 'secondary'
  return 'outline'
}

function getProgressColor(color: string): string {
  const colors = {
    blue: 'bg-blue-500',
    red: 'bg-red-500',
    green: 'bg-green-500'
  }
  return colors[color as keyof typeof colors] || 'bg-gray-500'
}
```

#### RecommendedBets.tsx
```typescript
'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { TrendingUp } from 'lucide-react'

interface Recommendation {
  type: string
  bet: string
  probability: number
  confidence: string
  expectedValue?: number
}

interface RecommendedBetsProps {
  recommendations: Recommendation[]
}

export default function RecommendedBets({ 
  recommendations 
}: RecommendedBetsProps) {
  // 券種ごとにグループ化
  const groupedRecs = recommendations.reduce((acc, rec) => {
    if (!acc[rec.type]) {
      acc[rec.type] = []
    }
    acc[rec.type].push(rec)
    return acc
  }, {} as Record<string, Recommendation[]>)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="w-5 h-5" />
          推奨購入券種
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {Object.entries(groupedRecs).map(([type, recs]) => (
            <div key={type}>
              <h3 className="text-lg font-semibold mb-3">{type}</h3>
              <div className="space-y-2">
                {recs.slice(0, 5).map((rec, index) => (
                  <div 
                    key={index}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-2xl font-bold text-blue-600">
                        {rec.bet}
                      </span>
                      <Badge variant={getConfidenceBadgeVariant(rec.confidence)}>
                        信頼度: {rec.confidence}
                      </Badge>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-gray-600">確率</p>
                      <p className="text-xl font-bold">
                        {(rec.probability * 100).toFixed(1)}%
                      </p>
                      {rec.expectedValue && (
                        <p className="text-sm text-green-600">
                          期待値: {rec.expectedValue.toFixed(2)}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

function getConfidenceBadgeVariant(confidence: string) {
  if (confidence === '高') return 'default'
  if (confidence === '中') return 'secondary'
  return 'outline'
}
```

### 8.3 API実装

#### app/api/predict/route.ts
```typescript
import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase'

export async function POST(request: NextRequest) {
  try {
    const { raceId } = await request.json()
    
    // 1. レースデータ取得
    const supabase = createClient()
    const { data: raceData, error } = await supabase
      .from('race_entries')
      .select(`
        *,
        races(*),
        racers(*),
        racer_stats(*)
      `)
      .eq('race_id', raceId)
    
    if (error) throw error
    
    // 2. 特徴量生成
    const features = await generateFeatures(raceData)
    
    // 3. 予測実行（Python APIを呼び出し）
    const predictions = await callPredictionAPI(features)
    
    // 4. 推奨券種計算
    const recommendations = calculateRecommendations(predictions)
    
    return NextResponse.json({
      predictions,
      recommendations
    })
    
  } catch (error) {
    console.error('Prediction error:', error)
    return NextResponse.json(
      { error: 'Prediction failed' },
      { status: 500 }
    )
  }
}

async function generateFeatures(raceData: any[]) {
  // 特徴量生成ロジック
  // （実際はPythonサーバーで実行推奨）
  return raceData
}

async function callPredictionAPI(features: any) {
  // Python予測サーバーへのリクエスト
  // または事前訓練済みモデルのTensorFlow.js版を使用
  return []
}

function calculateRecommendations(predictions: any[]) {
  // 推奨券種計算
  return []
}
```

---

## 9. 開発フェーズ

### Phase 1: 環境構築とデータ収集基盤（Week 1-2）

#### Week 1
- [ ] Supabase プロジェクトセットアップ
- [ ] データベーステーブル作成
- [ ] GitHub リポジトリセットアップ
- [ ] 開発環境構築

#### Week 2
- [ ] スクレイピングスクリプト実装
- [ ] レート制限機構実装
- [ ] GitHub Actions ワークフロー作成
- [ ] 直近1週間分のデータで動作確認

### Phase 2: 過去データ収集と分析準備（Week 3-4）

#### Week 3-4
- [ ] Phase 1（直近1年）データ収集開始
- [ ] データクレンジングスクリプト作成
- [ ] 天気データ収集実装
- [ ] データ整合性チェック

### Phase 3: 予測モデル開発（Week 5-6）

#### Week 5
- [ ] 特徴量エンジニアリング実装
- [ ] 訓練データ準備
- [ ] 基本統計分析

#### Week 6
- [ ] XGBoost モデル訓練
- [ ] モデル評価と検証
- [ ] ハイパーパラメータチューニング

### Phase 4: フロントエンド開発（Week 7-8）

#### Week 7
- [ ] Next.js プロジェクトセットアップ
- [ ] 基本レイアウト実装
- [ ] レース選択UI実装

#### Week 8
- [ ] 予測表示コンポーネント実装
- [ ] レスポンシブ対応
- [ ] API統合

### Phase 5: テストと改善（Week 9-10）

#### Week 9
- [ ] 実データでの検証
- [ ] バグ修正
- [ ] UI/UX改善

#### Week 10
- [ ] モデルチューニング
- [ ] パフォーマンス最適化
- [ ] ドキュメント整備
- [ ] デプロイ

---

## 10. コード実装例

### 10.1 データ収集スクリプト

#### scraper/boatrace_scraper.py
```python
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import random
import os
from dotenv import load_dotenv
import psycopg2
from rate_limiter import RateLimiter

load_dotenv()

class BoatRaceScraper:
    """
    競艇データを収集するスクレイパー
    
    特徴:
    - 非同期処理による高速化
    - レート制限による負荷軽減
    - リトライ機構
    - データベース保存
    """
    
    def __init__(self):
        self.base_url = "https://www.boatrace.jp"
        self.session = None
        self.rate_limiter = RateLimiter(
            requests_per_second=0.5,
            concurrent_requests=3
        )
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'ja,en-US;q=0.7',
            'Referer': 'https://www.boatrace.jp/',
        }
        
        # データベース接続
        self.db_conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        
    async def fetch_with_retry(self, url, max_retries=3):
        """リトライ機能付きフェッチ"""
        for attempt in range(max_retries):
            try:
                await self.rate_limiter.acquire()
                
                async with self.session.get(
                    url,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        return await response.text()
                    elif response.status == 429:
                        wait_time = (2 ** attempt) * 5
                        print(f"Rate limited. Waiting {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    elif response.status == 404:
                        return None
                    else:
                        print(f"HTTP {response.status}: {url}")
                        
            except asyncio.TimeoutError:
                print(f"Timeout on attempt {attempt + 1}")
            except Exception as e:
                print(f"Error on attempt {attempt + 1}: {e}")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(random.uniform(2, 5))
        
        return None
    
    async def fetch_race_result(self, date, venue_id, race_number):
        """レース結果を取得"""
        url = (
            f"{self.base_url}/owpc/pc/race/raceresult"
            f"?hd={date.strftime('%Y%m%d')}"
            f"&jcd={str(venue_id).zfill(2)}"
            f"&rno={race_number}"
        )
        
        html = await self.fetch_with_retry(url)
        if html:
            soup = BeautifulSoup(html, 'html.parser')
            return self.parse_race_result(
                soup, date, venue_id, race_number
            )
        return None
    
    def parse_race_result(self, soup, date, venue_id, race_number):
        """HTMLからレースデータを抽出"""
        try:
            # グレード取得
            grade_elem = soup.select_one('.grade')
            grade = grade_elem.text.strip() if grade_elem else '一般'
            
            # 結果テーブル
            result_table = soup.select_one('table.is-w495')
            if not result_table:
                return None
            
            rows = result_table.select('tbody tr')
            entries = []
            
            for row in rows:
                cols = row.select('td')
                if len(cols) < 8:
                    continue
                
                entry = {
                    'result_position': int(cols[0].text.strip()),
                    'boat_number': int(cols[1].text.strip()),
                    'racer_number': int(cols[2].text.strip()),
                    'racer_name': cols[3].text.strip(),
                    'start_timing': float(cols[5].text.strip()),
                    'course': int(cols[6].text.strip()) if cols[6].text.strip() else None,
                }
                entries.append(entry)
            
            return {
                'date': date,
                'venue_id': venue_id,
                'race_number': race_number,
                'grade': grade,
                'entries': entries
            }
            
        except Exception as e:
            print(f"Parse error: {e}")
            return None
    
    async def scrape_single_day(self, date):
        """1日分のデータを取得"""
        print(f"Scraping {date.strftime('%Y-%m-%d')}...")
        results = []
        
        for venue_id in range(1, 25):
            venue_results = []
            
            # 12レースを3つずつバッチ処理
            for race_batch in self._batch(range(1, 13), 3):
                tasks = [
                    self.fetch_race_result(date, venue_id, race_num)
                    for race_num in race_batch
                ]
                batch_results = await asyncio.gather(*tasks)
                venue_results.extend([r for r in batch_results if r])
            
            results.extend(venue_results)
            print(f"  Venue {venue_id}: {len(venue_results)} races")
            
            await asyncio.sleep(2)
        
        # データベースに保存
        self.save_to_db(results)
        
        return results
    
    def _batch(self, iterable, n):
        """リストをバッチに分割"""
        l = list(iterable)
        for i in range(0, len(l), n):
            yield l[i:i + n]
    
    def save_to_db(self, results):
        """データベースに保存"""
        cursor = self.db_conn.cursor()
        
        try:
            for race in results:
                # レース基本情報を保存
                cursor.execute("""
                    INSERT INTO races (race_date, venue_id, race_number, grade)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (race_date, venue_id, race_number) DO NOTHING
                    RETURNING id
                """, (
                    race['date'],
                    race['venue_id'],
                    race['race_number'],
                    race['grade']
                ))
                
                result = cursor.fetchone()
                if result:
                    race_id = result[0]
                    
                    # 出走情報を保存
                    for entry in race['entries']:
                        cursor.execute("""
                            INSERT INTO race_entries 
                            (race_id, boat_number, racer_id, start_timing, 
                             course, result_position)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON CONFLICT DO NOTHING
                        """, (
                            race_id,
                            entry['boat_number'],
                            entry['racer_number'],
                            entry['start_timing'],
                            entry['course'],
                            entry['result_position']
                        ))
            
            self.db_conn.commit()
            print(f"Saved {len(results)} races to database")
            
        except Exception as e:
            self.db_conn.rollback()
            print(f"Database error: {e}")
        finally:
            cursor.close()
    
    async def run(self, start_date, end_date):
        """期間指定で実行"""
        async with aiohttp.ClientSession() as session:
            self.session = session
            current_date = start_date
            
            while current_date <= end_date:
                await self.scrape_single_day(current_date)
                current_date += timedelta(days=1)
                await asyncio.sleep(5)
    
    def close(self):
        """リソースを解放"""
        self.db_conn.close()


async def main():
    """メイン処理"""
    scraper = BoatRaceScraper()
    
    try:
        # 直近3日分を取得
        end_date = datetime.now()
        start_date = end_date - timedelta(days=3)
        
        await scraper.run(start_date, end_date)
        
    finally:
        scraper.close()


if __name__ == '__main__':
    asyncio.run(main())
```

### 10.2 GitHub Actions ワークフロー

#### .github/workflows/scrape_daily.yml
```yaml
name: Scrape Daily Data

on:
  schedule:
    # 毎日 JST 7:00, 14:00, 20:00 に実行
    - cron: '0 22 * * *'  # JST 7:00 (UTC 22:00前日)
    - cron: '0 5 * * *'   # JST 14:00 (UTC 5:00)
    - cron: '0 11 * * *'  # JST 20:00 (UTC 11:00)
  workflow_dispatch:      # 手動実行可能

jobs:
  scrape:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        cache: 'pip'
    
    - name: Install dependencies
      run: |
        pip install -r scraper/requirements.txt
    
    - name: Run daily scraper
      env:
        DATABASE_URL: ${{ secrets.DATABASE_URL }}
      run: |
        python scraper/daily_scraper.py
    
    - name: Log completion
      run: |
        echo "Scrape completed at $(date)" >> scrape.log
        git config user.name github-actions
        git config user.email github-actions@github.com
        git add scrape.log
        git commit -m "Update scrape log" || exit 0
        git push || exit 0
```

#### .github/workflows/scrape_historical.yml
```yaml
name: Scrape Historical Data

on:
  schedule:
    # 毎日深夜3時に1日分だけ収集
    - cron: '0 18 * * *'  # JST 3:00 (UTC 18:00前日)
  workflow_dispatch:
    inputs:
      phase:
        description: 'Collection phase (1-5)'
        required: true
        default: '1'
      days:
        description: 'Number of days to scrape'
        required: true
        default: '1'

jobs:
  scrape-historical:
    runs-on: ubuntu-latest
    timeout-minutes: 350
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        cache: 'pip'
    
    - name: Install dependencies
      run: |
        pip install -r scraper/requirements.txt
    
    - name: Run historical scraper
      env:
        DATABASE_URL: ${{ secrets.DATABASE_URL }}
        PHASE: ${{ github.event.inputs.phase || '1' }}
        MAX_DAYS: ${{ github.event.inputs.days || '1' }}
      run: |
        python scraper/historical_scraper.py \
          --phase $PHASE \
          --max-days $MAX_DAYS
    
    - name: Update progress
      run: |
        echo "Phase ${{ github.event.inputs.phase }}: Scraped on $(date)" >> progress.log
        git config user.name github-actions
        git config user.email github-actions@github.com
        git add progress.log
        git commit -m "Update historical scraping progress" || exit 0
        git push || exit 0
```

### 10.3 requirements.txt

```text
# scraper/requirements.txt
aiohttp==3.9.1
beautifulsoup4==4.12.2
psycopg2-binary==2.9.9
python-dotenv==1.0.0
lxml==4.9.3
```

---

## まとめ

### システムの特徴

✅ **完全無料運用**
- GitHub Actions（月2,000分無料）
- Supabase（500MB無料）
- Vercel（無料デプロイ）

✅ **負荷を考慮した設計**
- リクエスト間隔: 2-3秒
- 同時接続: 2-3リクエスト
- 1日約360リクエスト

✅ **段階的なデータ収集**
- Phase 1: 直近1年（5日）
- Phase 2-5: 19年分（95日）
- 合計: 約100日（3-4ヶ月）

✅ **高精度な予測**
- XGBoostによる機械学習
- 50-100個の特徴量
- 各ボートレース場の実測天気データ

✅ **使いやすいUI**
- PC・スマホ対応
- リアルタイム予測
- 推奨購入券種の提案

### 次のステップ

1. **環境構築**: Supabase、GitHub、Vercelのセットアップ
2. **スクレイパー実装**: 上記コードを参考に実装
3. **データ収集開始**: Phase 1（直近1年）から開始
4. **モデル訓練**: 1年分のデータが溜まったら訓練開始
5. **UI開発**: Next.jsで予測表示画面を構築
6. **テスト・改善**: 実データで検証と改善

このドキュメントを参考に、段階的に実装を進めていきましょう！

  1. 実データ収集の開始
    - GitHub Actionsで過去データを段階的に収集
    - まず直近1年分のデータを優先的に収集
  2. モデルの再訓練
    - 実データが溜まったら再訓練
    - 精度30-40%を目標に調整
  3. ハイパーパラメータチューニング
    - Learning rate、Max depth、N_estimatorsなどを最適化