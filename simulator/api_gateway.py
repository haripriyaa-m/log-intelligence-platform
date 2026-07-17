import random
from datetime import datetime

ENDPOINTS = ["/api/orders", "/api/payment", "/api/profile", "/api/products", "/api/cart"]
METHODS = ["GET", "POST", "PUT"]

def _timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _user_id():
    return f"u_{random.randint(1000, 9999)}"

def generate_normal_logs():
    logs = []
    endpoint = random.choice(ENDPOINTS)
    method = random.choice(METHODS)
    latency = random.randint(20, 200)
    user = _user_id()
    logs.append(f"{_timestamp()} INFO  [api_gateway] {method} {endpoint} 200 — {latency}ms — user: {user}")
    return logs

def generate_anomaly_503_cascade():
    """ANOMALY: Multiple endpoints returning 503 — downstream service down"""
    logs = []
    for _ in range(random.randint(8, 15)):
        endpoint = random.choice(ENDPOINTS)
        method = random.choice(METHODS)
        logs.append(f"{_timestamp()} ERROR [api_gateway] {method} {endpoint} 503 — service unavailable")
    logs.append(f"{_timestamp()} FATAL [api_gateway] Circuit breaker OPEN — downstream failure detected")
    return logs

def generate_anomaly_latency_creep():
    """ANOMALY: Response times gradually climbing — memory leak or resource exhaustion"""
    logs = []
    latency = 200
    for _ in range(random.randint(10, 15)):
        latency += random.randint(100, 300)
        endpoint = random.choice(ENDPOINTS)
        logs.append(f"{_timestamp()} WARN  [api_gateway] High latency — GET {endpoint} — {latency}ms")
    logs.append(f"{_timestamp()} ERROR [api_gateway] Request timeout — latency exceeded 5000ms threshold")
    return logs