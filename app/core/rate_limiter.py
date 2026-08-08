from collections import defaultdict, deque
import time
import asyncio

class SlidingWindowRateLimiter:
    def __init__(self, max_limit_per_minute: int = 100, window_seconds: int = 60):
        self.max_limit = max_limit_per_minute
        self.window_seconds = window_seconds
        self.requests = defaultdict(deque)
        self.shared_lock = asyncio.Lock()

    async def request_validation(self, user_id):
        async with self.shared_lock:
            now = time.time()
            user_requests = self.requests[user_id]

            while user_requests and now - user_requests[0] >= self.window_seconds:
                user_requests.popleft()

            if len(user_requests) < self.max_limit:
                user_requests.append(now)

                return {
                    "request_allowed": True,
                    "remaining_requests": self.max_limit - len(user_requests),
                }

            retry_after = self.window_seconds - (now - user_requests[0])

            return {
                "request_allowed": False,
                "remaining_requests": 0,
                "retry_after": max(1, int(retry_after)),
            }
