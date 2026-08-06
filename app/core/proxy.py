import httpx
from fastapi import Request, Response, HTTPException

async def forward_request(request: Request, target_node_url: str) -> Response:
    """
    Takes an incoming FastAPI request, forwards it to the target backend node URL
    using an asynchronous HTTP client, and returns the response.
    """
    # Reconstruct the full target URL 
    path = request.url.path
    query_params = request.url.query
    target_url = f"{target_node_url.rstrip('/')}{path}"
    if query_params:
        target_url += f"?{query_params}"

    method = request.method
    headers = dict(request.headers)
    headers.pop("host", None) 

    body = await request.body()

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            backend_response = await client.request(
                method=method,
                url=target_url,
                headers=headers,
                content=body,
                cookies=request.cookies
            )

            # 4. Return the response back to the gateway client
            return Response(
                content=backend_response.content,
                status_code=backend_response.status_code,
                headers=dict(backend_response.headers)
            )

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Gateway Timeout: Target backend node timed out.")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Service Unavailable: Failed to connect to backend node. Error: {str(e)}")