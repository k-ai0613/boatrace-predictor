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
