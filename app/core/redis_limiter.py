import time
import uuid

import redis.asyncio as redis


class RedisSlidingWindowRateLimiter:
    LUA_SCRIPT = """
    local key = KEYS[1]
    local now_ms = tonumber(ARGV[1])
    local window_ms = tonumber(ARGV[2])
    local limit = tonumber(ARGV[3])
    local member = ARGV[4]
    local ttl_seconds = tonumber(ARGV[5])

    local window_start = now_ms - window_ms

    redis.call("ZREMRANGEBYSCORE", key, 0, window_start)

    local current_count = redis.call("ZCARD", key)
    if current_count >= limit then
        local oldest = redis.call("ZRANGE", key, 0, 0, "WITHSCORES")
        local retry_after_ms = window_ms

        if oldest[2] ~= nil then
            retry_after_ms = window_ms - (now_ms - tonumber(oldest[2]))
        end

        if retry_after_ms < 1000 then
            retry_after_ms = 1000
        end

        return {0, 0, math.ceil(retry_after_ms / 1000)}
    end

    redis.call("ZADD", key, now_ms, member)
    redis.call("EXPIRE", key, ttl_seconds)

    return {1, limit - current_count - 1, 0}
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        max_limit_per_minute: int = 100,
        window_seconds: int = 60,
        key_prefix: str = "rate_limit",
    ):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.max_limit = max_limit_per_minute
        self.window_seconds = window_seconds
        self.window_ms = window_seconds * 1000
        self.key_prefix = key_prefix
        self._script_sha = None

    async def request_validation(self, user_id: str):
        key = f"{self.key_prefix}:{user_id}"
        now_ms = int(time.time() * 1000)
        member = f"{now_ms}:{uuid.uuid4()}"

        try:
            result = await self._run_script(key, now_ms, member)
        except redis.RedisError:
            raise

        request_allowed = bool(int(result[0]))
        remaining_requests = int(result[1])
        retry_after = int(result[2])

        if request_allowed:
            return {
                "request_allowed": True,
                "remaining_requests": remaining_requests,
            }

        return {
            "request_allowed": False,
            "remaining_requests": 0,
            "retry_after": retry_after,
        }

    async def _run_script(self, key: str, now_ms: int, member: str):
        if self._script_sha is None:
            self._script_sha = await self.redis.script_load(self.LUA_SCRIPT)

        try:
            return await self.redis.evalsha(
                self._script_sha,
                1,
                key,
                now_ms,
                self.window_ms,
                self.max_limit,
                member,
                self.window_seconds,
            )
        except redis.ResponseError as exc:
            if "NOSCRIPT" not in str(exc):
                raise

            self._script_sha = await self.redis.script_load(self.LUA_SCRIPT)
            return await self.redis.evalsha(
                self._script_sha,
                1,
                key,
                now_ms,
                self.window_ms,
                self.max_limit,
                member,
                self.window_seconds,
            )

    async def close(self):
        await self.redis.aclose()
