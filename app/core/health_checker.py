from app.core.hash_ring import ConsistentHashRing
import asyncio
import httpx

class HealthChecker:
    def __init__(self,hash_ring: ConsistentHashRing, node_urls):
        self.hash_ring = hash_ring
        self.node_urls = node_urls
        self.failure_threshold = 3
        self.node_states = {node: True for node in node_urls}
        self.failed_nodes = {}
        for node in self.node_urls:
            self.failed_nodes[node] = 0

    async def start_monitoring(self):
        print("Health Checker background monitoring task started.", flush=True)
        try: 
            async with httpx.AsyncClient() as client:
                while True:
                    for node in self.node_urls:
                        try:
                            response = await client.get(f"{node}/health", timeout=3.0)
                            if response.status_code == 200:
                              
                                if not self.node_states[node]:
                                   
                                    print(f"[HealthChecker] Node {node} recovered. Re-adding to hash ring.", flush=True)
                                    self.hash_ring.add_node(node)
                                    self.node_states[node] = True
                                
                               
                                self.failed_nodes[node] = 0
                            else:
                                raise httpx.HTTPStatusError("Non-200 status", request=response.request, response=response)

                        except Exception as e:
                            
                            self.failed_nodes[node] += 1
                            print(f"[HealthChecker] Node {node} failed check ({self.failed_nodes[node]}/{self.failure_threshold}). Error: {e}", flush=True)

                            if self.failed_nodes[node] >= self.failure_threshold and self.node_states[node]:
                                
                                print(f"[HealthChecker] Circuit breaker tripped for {node}. Removing from hash ring.", flush=True)
                                self.hash_ring.remove_node(node)
                                self.node_states[node] = False

                    await asyncio.sleep(5)
        except asyncio.CancelledError:
            print("Background task was cleanly cancelled.", flush=True)
        except Exception as ex:
            print(f"[HealthChecker] Fatal error in monitoring loop: {ex}", flush=True)
        
