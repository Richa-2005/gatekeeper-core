import asyncio
import httpx
import time

GATEWAY_URL = "http://127.0.0.1:8000/api/v1/test"

async def send_single_request(client: httpx.AsyncClient, request_id: int):
   
    fake_ip = f"192.168.1.{request_id % 10}" 
    
    headers = {
        "X-Forwarded-For": fake_ip
    }
    
    start_time = time.time()
    try:
        response = await client.get(GATEWAY_URL, headers=headers, timeout=5.0)
        duration = (time.time() - start_time) * 1000
        
        target_node = response.headers.get("X-Target-Node", "Unknown")
        rate_limit_remaining = response.headers.get("X-RateLimit-Remaining", "N/A")
        
        return {
            "status_code": response.status_code,
            "target_node": target_node,
            "remaining": rate_limit_remaining,
            "latency_ms": duration
        }
    except Exception as e:
        return {
            "status_code": 500,
            "error": str(e)
        }

async def run_load_test(total_requests: int = 50, concurrency: int = 10):
    print(f"Starting load test: {total_requests} requests with concurrency {concurrency}...")
    
    async with httpx.AsyncClient() as client:
        tasks = []
        for i in range(total_requests):
            tasks.append(send_single_request(client, i))
            
            if len(tasks) >= concurrency:
                results = await asyncio.gather(*tasks)
                process_results(results)
                tasks = []
                
        if tasks:
            results = await asyncio.gather(*tasks)
            process_results(results)

def process_results(results):
    for r in results:
        if "error" in r:
            print(f"Error: {r['error']}")
        else:
            print(f"Status: {r['status_code']} | Node: {r['target_node']} | Remaining: {r['remaining']} | Latency: {r['latency_ms']:.2f}ms")

if __name__ == "__main__":
    asyncio.run(run_load_test(total_requests=30, concurrency=5))