from fastapi import FastAPI, Request
import sys
import uvicorn

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def catch_all(request: Request, full_path: str):
    port = request.url.port
    body = await request.body()
    return {
        "status": "success",
        "handled_by_backend_port": port,
        "path": f"/{full_path}",
        "method": request.method,
        "message": f"Hello from backend worker running on port {port}!"
    }

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    uvicorn.run(app, host="127.0.0.1", port=port)