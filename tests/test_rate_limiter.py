import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.rate_limiter import SlidingWindowRateLimiter

async def test_rate_limiter_basic():
    print("Test 1: Basic Allowance and Counter Decrement")
    limiter = SlidingWindowRateLimiter(max_limit_per_minute=3)
    user = "user_123"

    # Request 1
    res1 = await limiter.request_validation(user)
    print(f"Req 1: {res1}")
    assert res1["request_allowed"] is True
    assert res1["remaining_requests"] == 2

    # Request 2
    res2 = await limiter.request_validation(user)
    print(f"Req 2: {res2}")
    assert res2["request_allowed"] is True
    assert res2["remaining_requests"] == 1

    # Request 3
    res3 = await limiter.request_validation(user)
    print(f"Req 3: {res3}")
    assert res3["request_allowed"] is True
    assert res3["remaining_requests"] == 0
    print("Basic allowance test passed.\n")


async def test_rate_limiter_blocking():
    print("Test 2: Threshold Breach and Block (429 Scenario)")
    limiter = SlidingWindowRateLimiter(max_limit_per_minute=2)
    user = "user_malicious"

    # Fill up limit
    await limiter.request_validation(user)
    await limiter.request_validation(user)

    
    res_blocked = await limiter.request_validation(user)
    print(f"Blocked Req: {res_blocked}")
    
    assert res_blocked["request_allowed"] is False
    assert res_blocked["remaining_requests"] == 0
    assert "retry_after" in res_blocked
    print("Blocking and retry_after check passed.\n")


async def test_rate_limiter_concurrency():
    print("Test 3: High Concurrency Race Condition Stress Test")
    # Allow 50 requests total
    limiter = SlidingWindowRateLimiter(max_limit_per_minute=50)
    user = "heavy_user"

    # Firing 100 concurrent requests simultaneously using asyncio.gather
    # Exactly 50 should pass, and 50 should be blocked if thread safety holds.
    tasks = [limiter.request_validation(user) for _ in range(100)]
    results = await asyncio.gather(*tasks)

    allowed_count = sum(1 for r in results if r["request_allowed"] is True)
    blocked_count = sum(1 for r in results if r["request_allowed"] is False)

    print(f"Concurrent batch sent: 100")
    print(f"Allowed: {allowed_count}, Blocked: {blocked_count}")

    assert allowed_count == 50, f"Expected 50 allowed requests, got {allowed_count}"
    assert blocked_count == 50, f"Expected 50 blocked requests, got {blocked_count}"
    print("Concurrency lock check passed successfully!")


async def main():
    await test_rate_limiter_basic()
    await test_rate_limiter_blocking()
    await test_rate_limiter_concurrency()
    print("All Rate Limiter tests passed.")

if __name__ == "__main__":
    asyncio.run(main())