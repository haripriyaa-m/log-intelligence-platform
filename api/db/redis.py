import os
import json
import redis
from dotenv import load_dotenv

load_dotenv()

_client = None


def get_client() -> redis.Redis:
    global _client
    if _client is None:
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            # Use full URL — required for Upstash
            _client = redis.from_url(redis_url, decode_responses=True)
        else:
            # Local fallback
            _client = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                decode_responses=True,
            )
    return _client


def get_service_health(service: str) -> dict | None:
    r = get_client()
    raw = r.get(f"health:{service}")
    return json.loads(raw) if raw else None


def get_all_services() -> list[str]:
    r = get_client()
    return list(r.smembers("known_services"))


def get_recent_logs(service: str, limit: int = 30) -> list[dict]:
    r = get_client()
    raw_logs = r.lrange(f"recent_logs:{service}", 0, limit - 1)
    return [json.loads(log) for log in raw_logs]
