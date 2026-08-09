from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    GATEWAY_PORT: int = 8000
    DEFAULT_RATE_LIMIT: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    BACKEND_NODES: str = "http://localhost:8001,http://localhost:8002,http://localhost:8003"
    RATE_LIMIT_BACKEND: str = "redis"
    REDIS_URL: str = "redis://localhost:6379/0"

    @property
    def node_list(self) -> List[str]:
        return [node.strip() for node in self.BACKEND_NODES.split(",") if node.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()