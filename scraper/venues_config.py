"""
競艇場（ボートレース場）情報設定

全24会場の情報を定義
- 会場ID
- 会場名
- 都道府県
- 地域
- 公式サイトURL
- 天気情報URL
"""

# 全24会場の情報
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


def get_venue_name(venue_id):
    """会場IDから会場名を取得"""
    venue = VENUES.get(venue_id)
    return venue['name'] if venue else f"不明({venue_id})"


def get_all_venue_ids():
    """全会場IDのリストを取得"""
    return list(VENUES.keys())


def get_venues_by_region(region):
    """地域別に会場情報を取得"""
    return {
        vid: info for vid, info in VENUES.items()
        if info['region'] == region
    }


# 地域リスト
REGIONS = ['関東', '東海', '近畿', '四国', '中国', '九州']


if __name__ == '__main__':
    # テスト: 会場情報の表示
    print("=" * 80)
    print("  全24会場情報")
    print("=" * 80)
    print()

    for region in REGIONS:
        venues = get_venues_by_region(region)
        print(f"【{region}地区】 {len(venues)}場")
        for vid, info in venues.items():
            print(f"  {vid:2d}. {info['name']:8s} ({info['prefecture']})")
        print()

    print(f"合計: {len(VENUES)}場")
